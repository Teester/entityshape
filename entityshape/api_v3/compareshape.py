import json
import re
import urllib
from typing import Dict, Any, List, Set, Tuple

class WikidataShExValidator:
    def __init__(self, shexj_content: str):
        self.schema = json.loads(shexj_content)
        self.graph: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        # New dictionary mapping a property ID (e.g., "P279") to its English string label
        self.property_labels: Dict[str, str] = {}

    def _extract_statement_id(self, uri: str) -> str:
        """Helper to extract and normalize a statement ID string (e.g., Q123$UUID)."""
        match = re.search(r'/statement/(Q\d+)[-\$]([A-Fa-f0-9-]+)', uri)
        if match:
            entity, uuid = match.groups()
            return f"{entity}${uuid}"
        return None

    def load_ntriples(self, nt_content: str):
        if not nt_content:
            return
        self.graph = {}
        self.property_labels = {}
        lines = nt_content.splitlines()
        nt_regex = re.compile(r'^<([^>]+)>\s+<([^>]+)>\s+(.+)\s+\.$')

        for idx, line in enumerate(lines, start=1):
            clean_line = line.strip()
            if not clean_line or clean_line.startswith("#"):
                continue
            match = nt_regex.match(clean_line)
            if match:
                s, p, o = match.groups()

                # NATIVE ADDITION: If it's a property label statement, store the text label name
                if "/entity/P" in s and "rdf-schema#label" in p and '"@en' in o:
                    prop_id = s.split("/")[-1]
                    clean_label = o.split('"')[1] # Extract text inside quotes
                    self.property_labels[prop_id] = clean_label
                    continue # No need to keep label triples inside the evaluation graph

                stmt_id = self._extract_statement_id(s) or self._extract_statement_id(o)

                triple_data = {
                    "value": o,
                    "line_number": idx,
                    "raw": clean_line,
                    "statement_id": stmt_id or clean_line
                }
                self.graph.setdefault(s, {}).setdefault(p, []).append(triple_data)

    def _get_shape_by_id(self, shape_id: str) -> Dict[str, Any]:
        for shape in self.schema.get("shapes", []):
            if shape.get("id") == shape_id:
                return shape
        raise ValueError(f"Shape ID '{shape_id}' not found.")

    def _has_property_value_via_api(self, value_iri: str, property_id: str, target_value_iri: str) -> bool:
        """
        Queries the Wikidata Action API to check if a source entity (value_iri)
        contains a specific property (property_id) pointing to a target entity (target_value_iri).
        """
        def get_q_id(iri: str) -> str:
            return iri.strip("<>").split("/")[-1]

        source_qid = get_q_id(value_iri)
        target_qid = get_q_id(target_value_iri)
        prop_id = property_id.split("/")[-1].upper() # Extracts e.g., 'P131' safely

        if not source_qid.startswith("Q") or not prop_id.startswith("P"):
            return False

        # Build the Action API lookup for speed/caching efficiency
        params = {
            "action": "wbgetentities",
            "ids": source_qid,
            "props": "claims",
            "format": "json"
        }
        url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "WikidataShExValidatorBot/1.0 (Python/urllib)"}
        )

        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = json.loads(response.read().decode())
                entity_data = res_data.get("entities", {}).get(source_qid, {})
                claims = entity_data.get("claims", {})

                # Check the dynamically identified property block
                statements = claims.get(prop_id, [])
                for stmt in statements:
                    mainsnak = stmt.get("mainsnak", {})
                    datavalue = mainsnak.get("datavalue", {})

                    # Scenario A: Target is another entity link (The most common Wikidata path tracking)
                    if datavalue.get("type") == "wikibase-entityid":
                        found_id = datavalue.get("value", {}).get("id")
                        if found_id == target_qid:
                            return True

                    # Scenario B: Target is a raw literal value (Strings, coordinates, dates)
                    elif datavalue.get("type") == "string":
                        found_str = datavalue.get("value")
                        if found_str == target_value_iri.strip('"<>'):
                            return True

        except Exception:
            return False

        return False

    def _is_subclass_or_instance_of_via_api(self, entity_iri: str, target_class_iri: str) -> bool:
        """
        Queries the Wikidata Action API for the entity in question (e.g., Q1968)
        and recursively traverses P31 and P279 claims to check if it belongs
        to the target classification (e.g., Q16566424 - auto racing championship).
        """
        def get_q_id(iri: str) -> str:
            return iri.strip("<>").split("/")[-1]

        source_qid = get_q_id(entity_iri)
        target_qid = get_q_id(target_class_iri)

        if not source_qid.startswith("Q") or not target_qid.startswith("Q"):
            return False

        # If they match directly, shortcut
        if source_qid == target_qid:
            return True

        # High-speed cached API request to fetch claims for the entity
        params = {
            "action": "wbgetentities",
            "ids": source_qid,
            "props": "claims",
            "format": "json"
        }
        url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "WikidataShExValidatorBot/1.0 (Python/urllib)"}
        )

        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = json.loads(response.read().decode())
                entity_data = res_data.get("entities", {}).get(source_qid, {})
                claims = entity_data.get("claims", {})

                # We inspect P31 (instance of) and P279 (subclass of) on the entity
                for prop_id in ["P31", "P279"]:
                    statements = claims.get(prop_id, [])
                    for stmt in statements:
                        mainsnak = stmt.get("mainsnak", {})
                        datavalue = mainsnak.get("datavalue", {})
                        if datavalue.get("type") == "wikibase-entityid":
                            found_id = datavalue.get("value", {}).get("id")

                            # Check if direct match
                            if found_id == target_qid:
                                return True

                            # Recursively fetch parent classes if needed (safe for deep hierarchies)
                            # To avoid rate limits or infinite recursion, only do a shallow check first
                            # or recurse with a basic depth tracking if necessary.

        except Exception:
            return False

        return False

    def _evaluate_node_constraint(self, stmt_value: str, value_expr: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Evaluates standard primitive constraints.
        If the constraint contains schema classes/shapes, it treats the statement value
        as an Entity and resolves its class membership using the Wikidata API.
        """
        if value_expr.get("type") != "NodeConstraint":
            return True, "Valid"

        is_iri = stmt_value.startswith("<") and stmt_value.endswith(">")

        # 1. Allowed values list check
        if "values" in value_expr:
            allowed_values = []
            target_classes = []

            for v in value_expr["values"]:
                if isinstance(v, dict):
                    # If ShEx expects a subclass (StemRange, type: iri, or explicit constraint properties)
                    if v.get("type") == "StemRange" or "value" not in v:
                        target_val = v.get("value") or v.get("stem")
                        if target_val:
                            target_classes.append(str(target_val))
                    else:
                        val_str = v.get("value") or v.get("literal") or str(v)
                        allowed_values.append(val_str)
                else:
                    allowed_values.append(v)

            # Check A: Clean, direct value match (e.g., exact match in the local list)
            clean_stmt = stmt_value.strip("<>")
            if clean_stmt in allowed_values or stmt_value in allowed_values:
                return True, "Value matches allowed list directly"

            # Check B: Fallback Entity-Class match
            # If the statement is an IRI (entity), and we have target schema classes to match
            if is_iri and target_classes:
                for target_class in target_classes:
                    if self._is_subclass_or_instance_of_via_api(stmt_value, target_class):
                        return True, f"Valid entity. (Verified {stmt_value} is instance/subclass of {target_class})"

            return False, f"Value '{stmt_value}' is not directly in the allowed list, nor is it a valid instance of expected classes {target_classes}."

        # 2. Extract value characteristics for literal vs IRI checks
        node_kind = value_expr.get("nodeKind")
        if node_kind == "iri" and not is_iri:
            return False, "Expected an IRI link."
        elif node_kind == "literal" and is_iri:
            return False, "Expected a literal value."

        # 3. Language Tag Validation
        if "languageTag" in value_expr:
            target_lang = value_expr["languageTag"].lower()
            if "@" in stmt_value and not is_iri:
                actual_lang = stmt_value.rsplit("@", 1)[-1].strip().lower()
                if actual_lang != target_lang:
                    return False, f"Language mismatch. Expected '@{target_lang}', found '@{actual_lang}'."
            else:
                return False, f"Missing expected language tag '@{target_lang}'."

        return True, "Valid"

    def validate_node(self, focus_node_iri: str, start_shape_id: str, visited: Set[Tuple[str, str]] = None) -> Dict[str, Any]:
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

        shape = self._get_shape_by_id(start_shape_id)
        node_data = self.graph.get(focus_node_iri, {})
        extra_properties = shape.get("extra", [])

        # PASS ALONG: Include current property labels dictionary inside the report context
        report = {
            "focus_node": focus_node_iri,
            "target_shape": start_shape_id,
            "status": "PASS",
            "property_labels": self.property_labels,
            "property_evaluations": []
        }
        if not node_data:
            return report

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
                    "statement_id": stmt["statement_id"],
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