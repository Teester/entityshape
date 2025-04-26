# entityshape

An API to compare a Wikidata item with an EntitySchema.
The API is available at <http://entityshape.toolforge.org/api>.

The API requires the following parameters to be provided with requests:
1. __language__: e.g. _en_ the language to return property names in
2. __entity__: e.g. _Q42_ the Wikidata entity to check
3. __entityschema__: e.g. _E14_ the EntitySchema to check against

The API returns a JSON object containing the following:
1. __error__: details of any error which may have occurred
2. __schema__: the EntitySchema checked against
3. __name__: the display name of the EntitySchema
4. __validity__: the validity of the schema (currently unused)
5. __properties__: a json object describing the validity of each property in the entity
6. __statements__: a json object describing the validity of each statement in the entity

This repository also contains the source code for the user script at
<https://www.wikidata.org/wiki/User:Teester/EntityShape.js>,
which allows use of this API on Wikidata entity pages.

## Translations

The UI can be translated into multiple languages which will use the user's language to decide what language to display or fall back to english if the language is not available.
At the moment, there are 2 languages available - *en* and *ga*.  
Visit https://www.wikidata.org/wiki/User_talk:Teester/EntityShape.js for details on how to contribute translations to the project.