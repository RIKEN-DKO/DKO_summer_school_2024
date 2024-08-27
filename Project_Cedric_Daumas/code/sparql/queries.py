list_terms_query = """
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbp: <http://dbpedia.org/property/>
SELECT DISTINCT ?term ?type ?label ?property ?qtd 
###<FROM>###
WHERE {{
    {{
        ?term a owl:Class.
        BIND("class" as ?type)
        {{
            SELECT ?term (COUNT(*) as ?qtd) WHERE{{ 
                [] rdf:type ?term.
            }} GROUP BY ?term
        }}
    }}UNION{{
        ?term a rdfs:Class.
        BIND("class" as ?type)
        {{
            SELECT ?term (COUNT(*) as ?qtd) WHERE{{ 
                [] rdf:type ?term.
            }} GROUP BY ?term
        }}
    }}UNION{{
        ?term a rdf:Property.
        BIND("property" as ?type)
        {{
            SELECT ?term (COUNT(*) as ?qtd) WHERE{{ 
                [] ?term [].
            }} GROUP BY ?term
        }}
    }}UNION{{
        ?term a owl:DatatypeProperty.
        BIND("property" as ?type)
        {{
            SELECT ?term (COUNT(*) as ?qtd) WHERE{{ 
                [] ?term [].
            }} GROUP BY ?term
        }}
    }}
    UNION{{
        ?term a owl:ObjectProperty.
        BIND("property" as ?type)
        {{
            SELECT ?term (COUNT(*) as ?qtd) WHERE{{ 
                [] ?term [].
            }} GROUP BY ?term
        }}
    }}
FILTER(!REGEX(STR(?term),"http://www.w3.org/2002/07/owl#","i"))
FILTER(!REGEX(STR(?term),"http://www.w3.org/2000/01/rdf-schema#","i"))
FILTER(!REGEX(STR(?term),"http://www.w3.org/1999/02/22-rdf-syntax-ns#","i"))
FILTER(!REGEX(STR(?term),"http://www.w3.org/2001/XMLSchema#","i"))  
FILTER(!REGEX(STR(?term),"http://www.ontotext.com/","i"))  
OPTIONAL{{
        ?term ?property ?label1.
        FILTER(
            ?property = rdfs:label ||
            ?property = foaf:name ||
            ?property = skos:prefLabel ||
            ?property = dc:title ||
            ?property = dcterms:title ||
            ?property = dbo:name ||
            ?property = dbp:name ||
            ?property = dbo:name ||
            ?property = dbp:name 
        )
        ###<LANG>###
    }}
    BIND(COALESCE(?label1,?term) as ?label)
}}
"""


list_resources_query =f"""
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbp: <http://dbpedia.org/property/>
SELECT DISTINCT ?term ?type ?label ?property ?qtd 
###<FROM>###
WHERE {{
    ?term ?p ?o.

    FILTER(!REGEX(STR(?term),"http://www.w3.org/2002/07/owl#","i"))
    FILTER(!REGEX(STR(?term),"http://www.w3.org/2000/01/rdf-schema#","i"))
    FILTER(!REGEX(STR(?term),"http://www.w3.org/1999/02/22-rdf-syntax-ns#","i"))
    FILTER(!REGEX(STR(?term),"http://www.w3.org/2001/XMLSchema#","i"))  
    FILTER(!REGEX(STR(?term),"http://www.ontotext.com/","i"))  

    FILTER NOT EXISTS {{
        {{
            ?term a owl:Class.
        }}UNION{{
            ?term a rdfs:Class.
        }}UNION{{
            ?term a rdf:Property.
        }}UNION{{
            ?term a owl:DatatypeProperty.
        }}
        UNION{{
            ?term a owl:ObjectProperty.
        }}
    }}

    OPTIONAL{{
        ?term ?property ?label1.
        FILTER(
            ?property = rdfs:label ||
            ?property = foaf:name ||
            ?property = skos:prefLabel ||
            ?property = dc:title ||
            ?property = dcterms:title ||
            ?property = dbo:name ||
            ?property = dbp:name ||
            ?property = dbo:name ||
            ?property = dbp:name 
        )
        ###<LANG>###
        
    }}
    BIND("resource" as ?type)
    BIND(COALESCE(?label1,?term) as ?label)
    {{
        SELECT ?term (COUNT(*) as ?qtd) WHERE{{ 
            {{?a ?b ?term.}}
            UNION
            {{?term ?c ?d.}}
        }} GROUP BY ?term
    }}
}}
"""

#like list_terms but it gets more results it does group and qtd is alyas 1
tbox_long = """
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbp: <http://dbpedia.org/property/>

SELECT DISTINCT ?term ?type ?label ?property ?qtd
###<FROM>###
WHERE {
  {
    ?term a owl:Class.
    BIND("class" AS ?type)
  }
  UNION
  {
    ?term a rdfs:Class.
    BIND("class" AS ?type)
  }
  UNION
  {
    ?term a rdf:Property.
    BIND("property" AS ?type)
  }
  UNION
  {
    ?term a owl:DatatypeProperty.
    BIND("property" AS ?type)
  }
  UNION
  {
    ?term a owl:ObjectProperty.
    BIND("property" AS ?type)
  }

  OPTIONAL {
    ?term ?property ?label1.
    FILTER(
      ?property IN (rdfs:label, foaf:name, skos:prefLabel, dc:title, dcterms:title, dbo:name, dbp:name)
    )
    ###<LANG>###
  }

  BIND(COALESCE(?label1, STR(?term)) AS ?label)
  BIND(1 AS ?qtd)  # Bind the value 1 to the ?qtd variable
}


"""

#Version with less columns and no qtd
tbox_short = """
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
}
"""

abox = """
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbp: <http://dbpedia.org/property/>

SELECT DISTINCT ?class ?term ?termLabel
###<FROM>###
WHERE {
    {
        SELECT ?class (SAMPLE(?term) AS ?term) WHERE {
            ?term a ?class.
            FILTER NOT EXISTS { ?term a owl:Class. }
            FILTER NOT EXISTS { ?term a rdfs:Class. }
            FILTER NOT EXISTS { ?term a rdf:Property. }
            FILTER NOT EXISTS { ?term a owl:DatatypeProperty. }
            FILTER NOT EXISTS { ?term a owl:ObjectProperty. }
        }
        GROUP BY ?class
        ORDER BY ?class ?term
    }

    ?term ?p ?o.

    FILTER(!REGEX(STR(?term),"http://www.w3.org/2002/07/owl#","i"))
    FILTER(!REGEX(STR(?term),"http://www.w3.org/2000/01/rdf-schema#","i"))
    FILTER(!REGEX(STR(?term),"http://www.w3.org/1999/02/22-rdf-syntax-ns#","i"))
    FILTER(!REGEX(STR(?term),"http://www.w3.org/2001/XMLSchema#","i"))
    FILTER(!REGEX(STR(?term),"http://www.ontotext.com/","i"))

    FILTER NOT EXISTS {
        {
            ?term a owl:Class.
        } UNION {
            ?term a rdfs:Class.
        } UNION {
            ?term a rdf:Property.
        } UNION {
            ?term a owl:DatatypeProperty.
        } UNION {
            ?term a owl:ObjectProperty.
        }
    }

    OPTIONAL {
        ?term ?property ?termLabel1.
        FILTER(
            ?property = rdfs:label ||
            ?property = foaf:name ||
            ?property = skos:prefLabel ||
            ?property = dc:title ||
            ?property = dcterms:title ||
            ?property = dbo:name ||
            ?property = dbp:name
        )
    }

    BIND(COALESCE(?termLabel1, STR(?term)) AS ?termLabel)

    {
        SELECT ?term (COUNT(*) as ?qtd) WHERE { 
            { ?a ?b ?term. }
            UNION
            { ?term ?c ?d. }
        } GROUP BY ?term
    }
}


"""