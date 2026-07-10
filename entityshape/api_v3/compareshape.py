import json
import re
from typing import Dict, Any, List, Set, Tuple

class WikidataShExValidator:
    def __init__(self, shexj_content: str):
        self.schema = json.loads(shexj_content)
        self.graph: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    def load_ntriples(self, nt_content: str):
        self.graph = {}
        lines = nt_content.splitlines()
        nt_regex = re.compile(r'^<([^>]+)>\s+<([^>]+)>\s+(.+)\s+\.$')

        for idx, line in enumerate(lines, start=1):
            clean_line = line.strip()
            if not clean_line or clean_line.startswith("#"):
                continue
            match = nt_regex.match(clean_line)
            if match:
                s, p, o = match.groups()
                triple_data = {"value": o, "line_number": idx, "raw": clean_line}
                self.graph.setdefault(s, {}).setdefault(p, []).append(triple_data)

    def _get_shape_by_id(self, shape_id: str) -> Dict[str, Any]:
        for shape in self.schema.get("shapes", []):
            if shape.get("id") == shape_id:
                return shape
        raise ValueError(f"Shape ID '{shape_id}' not found.")

    def _evaluate_node_constraint(self, stmt_value: str, value_expr: Dict[str, Any]) -> Tuple[bool, str]:
        """Evaluates standard primitive constraints (datatypes, nodeKinds, lists)."""
        if value_expr.get("type") != "NodeConstraint":
            return True, "Valid"

        if "values" in value_expr:
            allowed = [v["value"] if isinstance(v, dict) else v for v in value_expr["values"]]
            clean_stmt = stmt_value.strip("<>")
            if clean_stmt in allowed or stmt_value in allowed:
                return True, "Value matches allowed list"
            return False, f"Value '{stmt_value}' not in allowed list."

        node_kind = value_expr.get("nodeKind")
        if node_kind == "iri" and not (stmt_value.startswith("<") and stmt_value.endswith(">")):
            return False, "Expected an IRI link."
        elif node_kind == "literal" and stmt_value.startswith("<") and stmt_value.endswith(">"):
            return False, "Expected a literal value."

        return True, "Valid"

    def validate_node(self, focus_node: str, start_shape_id: str, visited: Set[Tuple[str, str]] = None) -> Dict[str, Any]:
        focus_node_iri = f"http://www.wikidata.org/entity/{focus_node}"
        if visited is None:
            visited = set()

        current_execution_pair = (focus_node_iri, start_shape_id)
        if current_execution_pair in visited:
            return {
                "focus_node": focus_node_iri,
                "target_shape": start_shape_id,
                "status": "PASS",
                "info": "Circular reference detected, provisionally passing to break loop."
            }

        visited.add(current_execution_pair)

        # Handle a potential string-based start_shape_id variant mapping
        shape = self._get_shape_by_id(start_shape_id)
        node_data = self.graph.get(focus_node_iri, {})
        extra_properties = shape.get("extra", [])

        report = {
            "focus_node": focus_node_iri,
            "target_shape": start_shape_id,
            "status": "PASS",
            "property_evaluations": []
        }

        expression = shape.get("expression", {})
        constraints = []
        if expression.get("type") == "TripleConstraint":
            constraints.append(expression)
        elif expression.get("type") == "EachOf":
            constraints = expression.get("expressions", [])

        overall_pass = True

        for constraint in constraints:
            if constraint.get("type") != "TripleConstraint":
                continue

            predicate = constraint["predicate"]
            min_card = constraint.get("min", 1)
            max_card = constraint.get("max", 1)
            is_extra = predicate in extra_properties

            statements = node_data.get(predicate, [])
            prop_report = {
                "predicate": predicate,
                "is_marked_extra": is_extra,
                "status": "PASS",
                "statements_evaluated": []
            }

            value_expr = constraint.get("valueExpr")
            matching_statements_count = 0

            for stmt in statements:
                matches_constraint = True
                stmt_reason = "Valid"

                if value_expr:
                    # FIX: Handle shorthand string-style shape reference
                    # e.g., valueExpr: "county"
                    if isinstance(value_expr, str):
                        target_shape_ref = value_expr
                        sub_node_iri = stmt["value"].strip("<>")

                        sub_report = self.validate_node(sub_node_iri, target_shape_ref, visited.copy())
                        if sub_report["status"] == "FAIL":
                            matches_constraint = False
                            stmt_reason = f"Subshape Failure on linked node '{sub_node_iri}' matching shorthand shape '{target_shape_ref}'."
                            prop_report["nested_subshape_error"] = sub_report
                        else:
                            stmt_reason = f"Linked node '{sub_node_iri}' successfully validated against shorthand subshape."

                    # Handle normal dictionary-style expressions
                    elif isinstance(value_expr, dict):
                        expr_type = value_expr.get("type")

                        if expr_type == "NodeConstraint":
                            matches_constraint, stmt_reason = self._evaluate_node_constraint(stmt["value"], value_expr)

                        elif expr_type == "ShapeRef":
                            target_shape_ref = value_expr["reference"]
                            sub_node_iri = stmt["value"].strip("<>")

                            sub_report = self.validate_node(sub_node_iri, target_shape_ref, visited.copy())
                            if sub_report["status"] == "FAIL":
                                matches_constraint = False
                                stmt_reason = f"Subshape Failure on linked node '{sub_node_iri}' matching '{target_shape_ref}'."
                                prop_report["nested_subshape_error"] = sub_report
                            else:
                                stmt_reason = f"Linked node '{sub_node_iri}' successfully validated against subshape."

                if matches_constraint:
                    matching_statements_count += 1
                else:
                    if is_extra:
                        stmt_reason = f"[EXTRA Outlier ignored] {stmt_reason}"

                stmt_report = {
                    "line": stmt["line_number"],
                    "raw_triple": stmt["raw"],
                    "status": "PASS" if matches_constraint else "FAIL",
                    "info": stmt_reason
                }

                if not matches_constraint and not is_extra:
                    prop_report["status"] = "FAIL"
                    overall_pass = False

                prop_report["statements_evaluated"].append(stmt_report)

            counted_for_cardinality = matching_statements_count if is_extra else len(statements)
            prop_report["cardinality"] = {
                "expected_min": min_card, "expected_max": max_card, "counted_for_cardinality": counted_for_cardinality
            }

            if counted_for_cardinality < min_card or (max_card != -1 and counted_for_cardinality > max_card):
                prop_report["status"] = "FAIL"
                overall_pass = False

            report["property_evaluations"].append(prop_report)

        report["status"] = "PASS" if overall_pass else "FAIL"
        return report
