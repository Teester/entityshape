# entityshape
An api to compare a wikidata item with an entityschema

This api is available at http://entityshape.toolforge.org/api.  The api requires 3 parameters to return a result as follows:
1. __language__: e.g. _en_ the language to return property names in
2. __entity__: e.g. _Q42_ the wikidata entity to check
3. __entityschema__: e.g. _E14_ the entityschema to check against

The api returns a json object containing the following:
1. __error__: details of any error which may have occurred
2. __schema__: the entityschema checked against
3. __name__: the display name of the entityschema
4. __validity__: the validity of the schema (currently unused)
5. __properties__: a json object describing the validity of each property in the entity
6. __statements__: a json object describing the validity of each statement in the entity

This repository also contains the source code for the user script at https://www.wikidata.org/w/User:Teester/EntityShape.js which allow use of this api on wikidata entity pages