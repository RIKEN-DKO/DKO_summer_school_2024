# Applied research on large-scale language models in semantic webdata retrieval


## Example datasets for question to SPARQL generation

### RIKEN MetaDB
`datasets/rikenmetadb/dataset_train.json`

### BGEE dataset 

https://www.bgee.org/support/tutorial-query-bgee-knowledge-graph-sparql  

Example question:
`Q01:   Question: What are the species present in Bgee? 
`
SPARQL query:
```
PREFIX up: <http://purl.uniprot.org/core/>
SELECT ?species {
	?species a up:Taxon .
}
```


### Getting the SPARQL schema (TBOX)

Execute on [RIKEN MetaDB](https://metadb.riken.jp/metadb/sparql) SPARQL - endpoint. Change  `###<FROM>###` to the target database.
```
# Prefixes define shorthand notations for URIs, making the query more readable.
PREFIX owl: <http://www.w3.org/2002/07/owl#>  # Web Ontology Language - defines classes, properties, and individuals
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>  # RDF Schema - provides basic elements for describing ontologies
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>  # RDF Syntax - defines the RDF data model
PREFIX foaf: <http://xmlns.com/foaf/0.1/>  # Friend of a Friend - describes persons, their activities, and their relations to other people and objects
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>  # Simple Knowledge Organization System - used for knowledge organization systems like thesauri and taxonomies
PREFIX dc: <http://purl.org/dc/elements/1.1/>  # Dublin Core - standard for cross-domain resource description
PREFIX dcterms: <http://purl.org/dc/terms/>  # Dublin Core Terms - provides additional properties and classes for resource description
PREFIX dbo: <http://dbpedia.org/ontology/>  # DBpedia Ontology - provides structured data extracted from Wikipedia
PREFIX dbp: <http://dbpedia.org/property/>  # DBpedia Properties - properties used in DBpedia data

# The SELECT clause specifies the variables we want to retrieve.
SELECT DISTINCT ?term ?type ?label
###<FROM>###
WHERE {
  # UNION clause combines different conditions for selecting terms.
  {
    ?term a owl:Class.  # Check if the term is an owl:Class
    BIND("class" AS ?type)  # Bind the string "class" to the variable ?type
  }
  UNION
  {
    ?term a rdfs:Class.  # Check if the term is an rdfs:Class
    BIND("class" AS ?type)  # Bind the string "class" to the variable ?type
  }
  UNION
  {
    ?term a rdf:Property.  # Check if the term is an rdf:Property
    BIND("property" AS ?type)  # Bind the string "property" to the variable ?type
  }
  UNION
  {
    ?term a owl:DatatypeProperty.  # Check if the term is an owl:DatatypeProperty
    BIND("property" AS ?type)  # Bind the string "property" to the variable ?type
  }
  UNION
  {
    ?term a owl:ObjectProperty.  # Check if the term is an owl:ObjectProperty
    BIND("property" AS ?type)  # Bind the string "property" to the variable ?type
  }

  # OPTIONAL clause tries to get a human-readable label for the term.
  OPTIONAL {
    ?term ?property ?label1.
    FILTER(
      ?property IN (rdfs:label, foaf:name, skos:prefLabel, dc:title, dcterms:title, dbo:name, dbp:name)
    )
  }

  # BIND function assigns a value to ?label. If ?label1 is found, it uses that; otherwise, it uses the term itself.
  BIND(COALESCE(?label1, STR(?term)) AS ?label)
}#LIMIT 100

```

For ABOX see folder `queries`


## Generating Synthetic Dataset

Prompt for generating SPARQL datasets for the RIKEN MetadataBase, see `Project_Cedric_Daumas/code/context/prompts.py`. Example to generate dataset `Project_Cedric_Daumas/code/generate_datasets.py`.   


## Querying SPARQL endpoint

```python
    def run_sparql(self, query):
        if len(query) == 0:
            print("Empty query", file=sys.stderr)
            return []
        query = self.add_database_to_query(query)
        try:
            result_set = []
            if self.url_endpoint is not None and 'http' in self.url_endpoint:
                encoded_query = urllib.parse.quote(query)
                full_url = f"{self.url_endpoint}?format=application%2Fsparql-results%2Bjson&query={encoded_query}"
                response = requests.get(full_url, headers={"Accept": "application/sparql-results+json"})
                if response.status_code == 200:
                    results = response.json()
                    for result in results["results"]["bindings"]:
                        result_item = {}
                        for var in result:
                            if 'datatype' in result[var]:
                                result_item["?" + var] = f'\"{str(result[var]["value"])}\"^^<{str(result[var]["datatype"])}>'
                            else:
                                result_item["?" + var] = str(result[var]["value"])
                        result_set.append(result_item)
                else:
                    print(f"Unexpected response status code: {response.status_code}", file=sys.stderr)
                    print("Response content:", response.text, file=sys.stderr)
            else:
                results = self.run_sparql_rdflib(query)
                encoder = JSONResultSerializer(results)
                output = io.StringIO()
                encoder.serialize(output)
                print(file=output)
                for result in results:
                    result_item = {}
                    for var in results.vars:
                        result_item["?" + var] = str(result[var])
                    result_set.append(result_item)
            return result_set
        except Exception as e:
            print("Error running SPARQL query:", file=sys.stderr)
            print(query, file=sys.stderr)
            print("Error message:", e, file=sys.stderr)
            return None

```
More details in `Project_Cedric_Daumas/code/sparql/EndpointRiken.py`. 

## Training local LLM model

See `Project_Cedric_Daumas/code/training/peft_finetune.py` 

## Paper for generating synthetic data

Interesting to add these elements to the workflow: https://arxiv.org/pdf/2405.11706

https://ceur-ws.org/Vol-3747/text2kg_paper14.pdf

LLM-assisted Knowledge Graph Engineering: Experiments with ChatGPT: https://library.oapen.org/bitstream/handle/20.500.12657/90451/1/978-3-658-43705-3.pdf#page=103

LLM-Based SPARQL Generation with Selected Schema from Large Scale Knowledge Base: https://link.springer.com/chapter/10.1007/978-981-99-7224-1_24

