import sys
#from contextlib import AbstractContextManager
from contextlib import contextmanager
from ShExJSG import ShExJ
from rdflib import Graph
from sparql_slurper import SlurpyGraph

from pyshex.shape_expressions_language.p5_context import Context
from pyshex.shapemap_structure_and_language.p1_notation_and_terminology import Node


#class slurper(AbstractContextManager):
#@contextmanager
class slurper():
    def __init__(self, cntxt: Context, n: Node, S: ShExJ.Shape):
        self.graph = cntxt.graph
        self.tracing = isinstance(self.graph, SlurpyGraph) and cntxt.debug_context.trace_slurps
        self.n = n
        self.S = S

    def __iter__(self):
        return self

    def __next__(self):
        return self

    def throw(self, type, val, traceback):
        return

    def __enter__(self) -> Graph:
        if self.tracing:
            self.g_triples = self.graph.total_triples
            self.g_time = self.graph.total_slurptime
            print("# ← <" + self.n + ">@" + self.S.id + " ", end="")
            sys.stdout.flush()
        return self.graph

    def __exit__(self, exctype, excinst, exctb):
        if self.tracing:
            new_triples = self.graph.total_triples - self.g_triples
            if new_triples:
                print(" " + new_triples + " triples "
                      "(" + int((self.graph.total_slurptime - self.g_time) * 1000) + " μs)")
            else:
                print(" (Cached)")
        #self._cm_obj.__exit__(exctype, excinst, exctb)
        return True
