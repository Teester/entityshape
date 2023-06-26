from typing import List

import jsonasobj
import toolforge
import requests
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import URIRef


class SPARQLQuery:
    def __init__(self, sparql_endpoint: str, sparql_file_uri_or_text: str,
                 print_query: bool=False, print_results: bool=False) -> None:
        """ Set up the query to run

        :param sparql_endpoint: URL of sparql endpoint
        :param sparql_file_uri_or_text: URI, filename or SPARQL text
        :param print_query: Print the sparql results query
        :param print_results: Print query results
        """
        self.print_results = print_results
        if '\n' in sparql_file_uri_or_text or '\r' in sparql_file_uri_or_text or ' ' in sparql_file_uri_or_text:
            self.query = sparql_file_uri_or_text
        elif ':/' in sparql_file_uri_or_text:
            req = requests.get(sparql_file_uri_or_text)
            if not req.ok:
                raise ValueError("Unable to read " + sparql_file_uri_or_text)
            self.query = req.text
        else:
            with open(sparql_file_uri_or_text) as f:
                self.query = f.read()
        if print_query:
            print("SPARQL:")
            print(self.query)
        user_agent = toolforge.set_user_agent("pyshexy")
        self.endpoint = SPARQLWrapper(sparql_endpoint, agent=user_agent)
        self.endpoint.setQuery(self.query)
        self.endpoint.setReturnFormat(JSON)

    def focus_nodes(self) -> List[URIRef]:
        result = self.endpoint.query()

        processed_results = jsonasobj.load(result.response)
        if self.print_results:
            print('\t' + ('\n\t'.join([row.item.value for row in processed_results.results.bindings[:10]])))
            if len(processed_results.results.bindings) > 10:
                print('\n\t     ...')
            print('\n')
        return [URIRef(row.item.value) for row in processed_results.results.bindings]
