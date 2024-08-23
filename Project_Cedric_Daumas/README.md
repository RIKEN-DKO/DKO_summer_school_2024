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

