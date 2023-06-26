from typing import Dict, NamedTuple, Union, List, Tuple, Optional, Callable, Type

import time
import collections
import toolforge
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import Graph, URIRef, Literal, BNode

QueryTriple = Tuple[Optional[URIRef], Optional[URIRef], Optional[Union[Literal, URIRef]]]


NodeType = Union[URIRef, Literal, BNode]

#RDFTriple = collections.namedtuple('s', ['p', 'o'])
RDFTriple = collections.namedtuple('RDFTriple', ['s', 'p', 'o'])
#class RDFTriple(NamedTuple):
    #s: Union[URIRef, BNode]
    #p: URIRef
    #o:  Union[Literal, URIRef, BNode]

class SlurpyGraph(Graph):
    """ A Graph that acts as a "cache" for a SPARQL endpoint """
    def __init__(self, endpoint: str, *args, persistent_bnodes: bool = False, **kwargs) -> None:
        """ Create a graph

        :param endpoint: URL of SPARQL endpoint
        :param persistent_bnodes: BNodes persist across SPARQL calls
        """
        user_agent = toolforge.set_user_agent("pyshexy")
        self.sparql = SPARQLWrapper(endpoint, agent=user_agent)
        self.persistent_bnodes = persistent_bnodes
        self.sparql.setReturnFormat(JSON)
        self.resolved_nodes = [(None, None, None)]

        self.debug_slurps = False
        self._query_result_hook = None
        self.graph_name = None
        self.total_slurptime = 0.0
        self.total_calls = 0
        self.total_queries = 0
        self.total_triples = 0
        self.sparql_locked = False
        super().__init__(*args, **kwargs)

    def add_result_hook(self, hook: Type["QueryResultHook"]) -> Type["QueryResultHook"]:
        """
        Add a query result hook to the chain
        :param hook: hook to add
        :return: added hook (same as hook to add)
        """
        hook.next_hook = self._query_result_hook
        self._query_result_hook = hook
        return hook

    def _map_type(self, node: Dict) -> NodeType:
        if not self.persistent_bnodes and node['type'] == 'bnode':
            raise ValueError("SlurpyGraph cannot process BNodes")
        return URIRef(node['value']) if node['type'] == 'uri' else \
            BNode(node['value']) if node['type'] == 'bnode' else \
            Literal(node['value'], datatype=node.get('datatype'))

    @staticmethod
    def _repr_element(node: Union[URIRef, BNode, Literal]) -> str:
        #return f"<{node}>" if isinstance(node, URIRef) else f"_:{node}" if isinstance(node, BNode) else '"{node}"'
        return "<" + node  + ">" if isinstance(node, URIRef) else "_:" + node if isinstance(node, BNode) else '"' + node + '"'

    def already_resolved(self, pattern: QueryTriple) -> bool:
        """ Determine whether pattern has already been loaded into the cache.

        The "wild card" - `(None, None, None)` - always counts as resolved.

        :param pattern: pattern to check
        :return: True it is a subset of elements already loaded
        """
        if self.sparql_locked or pattern == (None, None, None):
            return True
            gquery = "graph" + gn + "{{"
        for resolved_node in self.resolved_nodes:
            if resolved_node != (None, None, None) and \
                    (pattern[0] == resolved_node[0] or resolved_node[0] is None) and \
                    (pattern[1] == resolved_node[1] or resolved_node[1] is None) and\
                    (pattern[2] == resolved_node[2] or resolved_node[2] is None):
                return True
        return False

    def triples(self, pattern: QueryTriple):
        """ Return the triples that match pattern

        :param pattern: `(s, p, o)` tuple, with `None` as wild cards
        :return: Generator for resulting triples
        """
        self.total_calls += 1
        if self.graph_name is not None:
            gn = "?g" if not self.graph_name else self.graph_name
            #gquery = f"graph {gn} {{"
            gquery = "graph" + gn + "{{"
            gqueryend = '}'
        else:
            gquery = gqueryend = ''
        if not self.already_resolved(pattern):
            subj = self._repr_element(pattern[0]) if pattern[0] is not None else '?s'
            pred = self._repr_element(pattern[1]) if pattern[1] is not None else '?p'
            obj = self._repr_element(pattern[2]) if pattern[2] is not None else '?o'
            #query = f"SELECT ?s ?p ?o {{{gquery}{subj} {pred} {obj}{gqueryend}}}"
            query = "SELECT ?s ?p ?o {{" + gquery + subj + " " + pred + " " + obj + gqueryend + "}}"
            start = time.time()
            if self.debug_slurps:
                #print(f"SPARQL: ({query})", end="")
                print("SPARQL: " + query, end="")
            self.sparql.setQuery(query)
            resp = self.sparql.query().convert()
            elapsed = time.time() - start
            ntriples = len(resp['results']['bindings'])
            self.total_slurptime += elapsed
            self.total_triples += ntriples
            self.total_queries += 1
            if self.debug_slurps:
                #print(f" ({round(elapsed, 2)} secs) - {ntriples} triples")
                print(" (" + round(elapsed, 2) + " secs - " + ntriples + " triples")
            query_result = self._query_result_hook(self) if self._query_result_hook is not None else None
            for row in resp['results']['bindings']:
                triple = RDFTriple(pattern[0] if pattern[0] is not None else self._map_type(row['s']),
                                   pattern[1] if pattern[1] is not None else self._map_type(row['p']),
                                   pattern[2] if pattern[2] is not None else self._map_type(row['o']))
                self.add(triple)
                if query_result:
                    query_result.add(triple)
            if query_result:
                query_result.done()
            self.resolved_nodes.append(pattern)
        return super().triples(pattern)

    def serialize(self, destination=None, format="xml",
                  base=None, encoding=None, **args):
        self.sparql_locked = True
        try:
            rval = super().serialize(destination, format, base, encoding, **args)
        finally:
            self.sparql_locked = False
        return rval


class QueryResultHook:
    """
    QueryResultHook: used for printing and other processing out the outcome of a slurper query
    """
    next_hook = None

    def __init__(self, sg: SlurpyGraph) -> None:
        self.chained_hook = self.next_hook(sg) if self.next_hook is not None else None

    def add(self, t: RDFTriple) -> None:
        """
        Add a triple as a query result
        :param t: triple being added
        """
        if self.chained_hook is not None:
            self.chained_hook.add(t)

    def done(self) -> None:
        """
        All triples were added for this result
        """
        if self.chained_hook is not None:
            self.chained_hook.done()


class QueryResultPrinter(QueryResultHook):
    """
    Query result hook to print query results
    """
    include_namespaces = False

    def __init__(self, sg: SlurpyGraph) -> None:
        self.g = Graph(namespace_manager=sg.namespace_manager)
        super().__init__(sg)

    def add(self, t: RDFTriple) -> None:
        self.g.add(t)
        super().add(t)

    def done(self) -> None:
        g_str = self.g.serialize(format="turtle").decode()
        print('RESULTS:\n\t' + '\n\t'.join([l for l in g_str.split('\n')
                                            if self.include_namespaces or (l and not l.startswith('@prefix'))]))
