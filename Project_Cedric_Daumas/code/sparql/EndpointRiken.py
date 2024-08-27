from rdflib import Graph
from rdflib.util import guess_format
from rdflib.plugins.sparql.results.jsonresults import JSONResultSerializer
from SPARQLWrapper import SPARQLWrapper, JSON
from re import finditer,findall
import os
import pickle 
import io
from io import StringIO, BytesIO
from sparql.Utils import getGraph
from sparql.queries import list_terms_query,list_resources_query,tbox_long

from configs import NUMBER_HOPS,LIMIT_BY_PROPERTY
import requests
import urllib.parse
import sys


class Endpoint:
    def __init__(self, url_endpoint=None, database=None):
        self.url_endpoint = url_endpoint
        self.database = database
        self.path_labels = "sparql/temp/labels.obj"
        self.path_counts = "sparql/temp/counts.obj"
        self.visited_nodes = set()
        self.graph = None
        self.labels = {}
        if url_endpoint != None and os.path.exists(self.path_labels):
            print("Loading labels on endpoint cache...")
            self.load_labels()
            print("Labels on endpoint cache loaded!")

        self.counts = {}
        if url_endpoint != None and os.path.exists(self.path_counts):
            print("Loading counts on endpoint cache...")
            self.load_counts()
            print("Counts on endpoint cache loaded!")

        

    def save_labels(self):
        with open(self.path_labels,"wb") as file:
            pickle.dump(self.labels, file)

    def load_labels(self):
        with open(self.path_labels,"rb") as file:
            self.labels = pickle.load(file)

    def save_counts(self):
        with open(self.path_counts,"wb") as file:
            pickle.dump(self.counts, file)

    def load_counts(self):
        with open(self.path_counts,"rb") as file:
            self.counts = pickle.load(file)


    @staticmethod
    def from_rdflib_in_memory(graph):
        endpoint = Endpoint()
        endpoint.graph = graph
        return endpoint
    
    
    @staticmethod
    def from_rdflib_in_string(triples):
        print("Triples data being parsed:", file=sys.stderr)
        print(triples, file=sys.stderr)
        graph = getGraph(triples)
        return Endpoint.from_rdflib_in_memory(graph)
    
    # @staticmethod
    # def from_rdflib_in_string(triples):
    #     graph = getGraph(triples)
    #     return Endpoint.from_rdflib_in_memory(graph)

    def __str__(self):
        g = Graph()
        return str(g.parse(self.url_endpoint,format=guess_format(self.url_endpoint)).serialize())
        
    def run_sparql_rdflib(self,query):
        if self.graph == None and self.url_endpoint != None:
            g = Graph()
            self.graph = g.parse(self.url_endpoint,format=guess_format(self.url_endpoint)).serialize()
        qres = self.graph.query(query)
        return qres
    
    def run_sparql_old(self, query):
        try:
            result_set = []
            if self.url_endpoint != None and 'http' in self.url_endpoint:
                # print("Endpoint is a valid remote SPARQL endpoint")
                sparql = SPARQLWrapper(self.url_endpoint)
                sparql.setQuery(query)
                sparql.setReturnFormat(JSON)
                sparql.addCustomHttpHeader("Accept", "application/sparql-results+json")
                response = sparql.query()

                # Debugging prints
                print("Response status:", response.response.status)
                print("Response headers:", response.response.headers)
                
                content = response.response.read()
                content_type = response.response.info().get_content_type()

                if content_type == 'application/sparql-results+json':
                    results = sparql.query().convert()
                    for result in results["results"]["bindings"]:
                        result_item = {}
                        for var in result:
                            if 'datatype' in result[var]:
                                result_item["?" + var] = f'\"{str(result[var]["value"])}\"^^<{str(result[var]["datatype"])}>'
                            else:
                                result_item["?" + var] = str(result[var]["value"])
                        result_set.append(result_item)
                else:
                    # Log the content for debugging
                    print("Unexpected response content type:", content_type)
                    print("Response content:", content.decode('utf-8'))

            else:
                # Endpoint is a local file
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
            print(e)
            print(query)
            return None
        

    def add_database_to_query(self, query):
        if self.database:
            query = query.replace("WHERE", f"FROM <{self.database}> WHERE")
            print('Added database to query:', self.database)
        return query
    
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

            
         
    def getOneResource(self,uri):
        query = f"""SELECT * WHERE{{
                        ?r a <{uri}>.
                        {{
                            SELECT ?r (COUNT(*) as ?qtd) WHERE{{
                                ?r ?s ?o
                            }}GROUP BY ?r
                        }}
                    }} ORDER BY DESC(?qtd)
                    LIMIT 1
                    """
        # print(query)
        result = self.run_sparql(query)
        resourceUri = result[0]["?r"]
        triples = self.describe_(resourceUri,0,2)[0]
        return triples
        
    def describe(self,uri,number_hops=NUMBER_HOPS,limit_by_property=LIMIT_BY_PROPERTY):
        # print("Describe: "+str(uri))
        triples,is_class = self.describe_(uri,number_hops,limit_by_property)
        if is_class:
            triples += self.getOneResource(uri)
        return triples
    
    def filterAxiomsTriples(self, uri):
        filterPrefixes = ['http://www.w3.org/2002/07/owl#','http://www.w3.org/1999/02/22-rdf-syntax-ns#','http://www.w3.org/2000/01/rdf-schema#','http://www.w3.org/2001/XMLSchema#']
        for filterPrefix in filterPrefixes:
            if uri.startswith(filterPrefix):
                return False
        return True
    
    def filterSelfEquivalenceAxioms(self,s ,p ,o):        
        if str(p) == "http://www.w3.org/2000/01/rdf-schema#subClassOf" and (str(s) == str(o)):
            return False
        if str(p) == "http://www.w3.org/2000/01/rdf-schema#subPropertyOf" and (str(s) == str(o)):
            return False
        if str(p) == "http://www.w3.org/2002/07/owl#equivalentClass" and (str(s) == str(o)):
            return False
        if str(p) == "http://www.w3.org/2002/07/owl#equivalentProperty" and (str(s) == str(o)):
            return False
        if str(p) == "http://www.w3.org/2002/07/owl#sameAs" and (str(s) == str(o)):
            return False
        if str(p) == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" and str(s) == "http://www.w3.org/2000/01/rdf-schema#Class":
            return False
        if str(p) == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" and str(s) == "http://www.w3.org/2002/07/owl#Class":
            return False
        return True
    
    def filterProperty(self,p):
        if str(p) == "http://www.w3.org/2000/01/rdf-schema#isDefinedBy":
            return False
        if str(p) == "http://www.w3.org/2000/01/rdf-schema#seeAlso":
            return False
        return True
    
    def describe_(self,uri,number_hops = NUMBER_HOPS,limit_by_property = LIMIT_BY_PROPERTY):
        # print(f"visitando {uri}")
        is_class = False
        self.visited_nodes.add(uri)
        next_nodes = set()
        count_by_property = {}
        describe = ""
        query = f"""SELECT DISTINCT ?p ?o WHERE{{
            <{uri}> ?p ?o.
            FILTER(?o != <http://www.w3.org/2000/01/rdf-schema#Resource>)
            FILTER(?o != <http://www.w3.org/2002/07/owl#Thing>)
        }}"""
        # print(query)
        triples = self.run_sparql(query)
        #outgoing properties
        for triple in triples:
            # print(triple)
            if self.filterProperty(triple["?p"]):
                if 'http' in triple["?o"] and not "^^" in triple["?o"]:#Object Property
                    # print(triple)
                    if self.filterSelfEquivalenceAxioms(uri,triple["?p"],triple["?o"]):
                        describe += f"""<{uri}> <{triple["?p"]}> <{triple["?o"]}>.\n"""
                    if triple["?p"] == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" and (triple["?o"] == "http://www.w3.org/2000/01/rdf-schema#Class" or triple["?o"] == "http://www.w3.org/2002/07/owl#Class"):
                        is_class = True
                    if limit_by_property > -1:# Limiting number of triples for property
                        if not triple["?p"] in count_by_property:
                            count_by_property[triple["?p"]] = 0
                        if count_by_property[triple["?p"]] < limit_by_property:
                            count_by_property[triple["?p"]]+=1
                            if self.filterAxiomsTriples(triple["?o"]):
                                next_nodes.add(triple["?o"])
                    elif self.filterAxiomsTriples(triple["?o"]):
                        next_nodes.add(triple["?o"])
                else:#Datatype Property
                    if "^^" in triple["?o"]: #has datatype
                        describe += f"""<{uri}> <{triple["?p"]}> {triple["?o"]}.\n"""
                    else:
                        describe += f"""<{uri}> <{triple["?p"]}> "{triple["?o"]}".\n"""
        #ingoing properties
        query = f"""SELECT DISTINCT ?s ?p WHERE{{
            ?s ?p <{uri}>.
            FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
            FILTER(?s != <http://www.w3.org/2002/07/owl#Nothing>)
        }}"""
        # print(query)
        triples = self.run_sparql(query)
        for triple in triples:
            if self.filterSelfEquivalenceAxioms(triple["?s"],triple["?p"],uri):
                describe += f"""<{triple["?s"]}> <{triple["?p"]}> <{uri}>.\n"""
            if limit_by_property > -1:
                if not triple["?p"] in count_by_property:
                    count_by_property[triple["?p"]] = 0
                if count_by_property[triple["?p"]] < limit_by_property:
                    count_by_property[triple["?p"]]+=1
                    if self.filterAxiomsTriples(triple["?s"]):
                        next_nodes.add(triple["?s"])
            elif self.filterAxiomsTriples(triple["?s"]):
                next_nodes.add(triple["?s"])
        if number_hops > 0:
            number_hops-=1
            for next_node in next_nodes:
                if next_node not in self.visited_nodes:
                    describe += self.describe_(next_node,number_hops,limit_by_property)[0]
        return describe,is_class
    
    def camel_case_split(self,identifier):
        matches = finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
        return " ".join([m.group(0) for m in matches])

    def unpackNumber(self,text):
        number = 0 
        matchs = findall("\"[0-9]+\"",text)
        if len(matchs) > 0:
            number = int(matchs[0].replace("\"","").replace("\'",""))
        return number

    def listTerms(self, language=None, limit=10000):
        query = list_terms_query
        
        # Replace the placeholder with the actual language filter or remove it if language is None
        language_filter = f'FILTER(LANG(?label1) = "{language}")' if language else ''
        query = query.replace('###<LANG>###', language_filter)
        
        count_query = query.replace("DISTINCT ?term ?type ?label ?property ?qtd", "(COUNT(DISTINCT *) as ?qtd_max)")
        qtd = self.unpackNumber(self.run_sparql(count_query)[0]["?qtd_max"])
        print("Terms quantity: " + str(qtd))

        #Lets use tbox query with more results
        if qtd == 0:
            print('No term found with original query, trying with tbox_long query')
            query = tbox_long
            count_query = query.replace("DISTINCT ?term ?type ?label ?property ?qtd", "(COUNT(DISTINCT *) as ?qtd_max)")
            qtd = self.unpackNumber(self.run_sparql(count_query)[0]["?qtd_max"])
            print("Terms quantity: " + str(qtd))

        

        query_limit_template = query + f"LIMIT {limit} OFFSET $offset"
        results = []
        offset = 0
        while offset < qtd:
            query_limit = query_limit_template.replace("$offset", str(offset))
            offset += limit
            results += self.run_sparql(query_limit)
        for result in results:
            uri = result['?term']
            if uri not in self.labels:
                self.labels[uri] = []
            if "?property" in result:
                type_label = result["?property"]
            else:
                result['?label'] = self.uri_to_label(result['?label'])
                type_label = "URI"
            self.labels[uri].append([result['?label'], type_label])
            if uri not in self.counts:
                self.counts[uri] = self.unpackNumber(result['?qtd'])
        return results

    def listResources(self,language=None,limit=10000):
        query = list_resources_query

        # Replace the placeholder with the actual language filter or remove it if language is None
        language_filter = f'FILTER(LANG(?label1) = "{language}")' if language else ''
        query = query.replace('###<LANG>###', language_filter)
        # print(query)
        count_query = query.replace("DISTINCT ?term ?type ?label ?property ?qtd","(COUNT(DISTINCT *) as ?qtd_max)")
        qtd = self.unpackNumber(self.run_sparql(count_query)[0]["?qtd_max"])
        print("Terms quantity: "+str(qtd))
        query_limit_template = query+f"LIMIT {limit} OFFSET $offset"
        results = []
        offset = 0
        while offset < qtd:
            query_limit = query_limit_template.replace("$offset",str(offset))
            offset+= limit
            results+= self.run_sparql(query_limit)
        for result in results:
            uri = result['?term']
            if not uri in self.labels:
                self.labels[uri] = []
            if "?property" in result:
                type_label = result["?property"]
            else:
                result['?label'] = self.uri_to_label(result['?label'])
                type_label = "URI"
                # print("Criou label para "+str(uri))
            self.labels[uri].append([result['?label'],type_label])
            if not uri in self.counts:
                self.counts[uri]= self.unpackNumber(result['?qtd'])
        return results
    
    def countRankResource(self,url):
        url = url.replace("<","").replace(">","")
        if url in self.counts:
            return self.counts[url]
        query = f"""
            SELECT (COUNT( DISTINCT *) as ?count) WHERE{{
                {{
                    <{url}> ?p ?o.
                }}UNION{{
                    ?s <{url}> ?o.
                }}UNION{{
                    ?s ?p <{url}>.
                }}
            }}
        """
        qtd = int(self.run_sparql(query)[0]["?count"].replace('"^^<http://www.w3.org/2001/XMLSchema#integer>','').replace('"',""))
        self.counts[url] = qtd
        return qtd
    
    def struct_result_query(self,sparql):
        try:
            query_results = self.run_sparql(sparql)
            question_formulated = f'''
                {{"query":"```sparql\n{sparql}\n```",
                "result": {query_results} }}
                '''
            return question_formulated,query_results
        except Exception as e:
            raise e
    
    def get_labels(self,uri):
        uri = uri.replace("<","").replace(">","")
        if uri in self.labels:
            return self.labels[uri]
        labels_ =  self.get_labels_(uri)
        self.labels[uri]= labels_
        return labels_
    
    def uri_to_label(self, uri):
        # print(uri)
        slices = uri.split("/")
        raw_label = slices[-1]
        if "#" in raw_label:
            raw_label = raw_label.replace("#"," ")
        elif not "." in slices[-2]:
            raw_label = slices[-2]+" "+raw_label

        label_from_uri = self.camel_case_split(raw_label).replace("_"," ").strip()
        return label_from_uri
    
    def get_labels_(self,uri):
        query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dc: <http://purl.org/dc/elements/1.1/>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbp: <http://dbpedia.org/property/>
        SELECT DISTINCT ?label ?property WHERE{{
            <{uri}> ?property ?label.
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
        }}"""
        results = self.run_sparql(query)
        labels = []
        for result in results:
            labels.append([result["?label"],result["?property"]])
        label_from_uri = self.uri_to_label(uri)
        if not label_from_uri in labels:
            labels.append([label_from_uri,"URI"])
        return labels
    
    def get_resource_class(self,uri):
        query = f"""
        SELECT DISTINCT ?class WHERE{{
            <{uri}> a ?class   
        }}
        """
        results = self.run_sparql(query)
        classes = []
        for result in results:
            classes.append(result["?class"])
        return classes
    
    def get_resource_comments(self,uri):
        query = f"""
        SELECT DISTINCT ?comment WHERE{{
            <{uri}> <http://www.w3.org/2000/01/rdf-schema#comment> ?comment   
        }}
        """
        results = self.run_sparql(query)
        comments = []
        for result in results:
            comments.append(result["?comment"])
        return comments
    
    def get_property_domain(self,uri):
        query = f"""
        SELECT DISTINCT ?domain WHERE{{
            <{uri}> <http://www.w3.org/2000/01/rdf-schema#domain> ?domain   
        }}
        """
        results = self.run_sparql(query)
        domain = []
        for result in results:
            domain.append(result["?domain"])
        return domain
    
    def get_property_range(self,uri):
        query = f"""
        SELECT DISTINCT ?range WHERE{{
            <{uri}> <http://www.w3.org/2000/01/rdf-schema#range> ?range   
        }}
        """
        results = self.run_sparql(query)
        range = []
        for result in results:
            range.append(result["?range"])
        return range
    
    def get_metadata(self,uri):
        if "http://www.w3.org/2002/07/owl#" in uri or "http://www.w3.org/2000/01/rdf-schema#" in uri or "http://www.w3.org/1999/02/22-rdf-syntax-ns#" in uri or "http://www.w3.org/2001/XMLSchema#" in uri or "http://www.ontotext.com/" in uri or ".png" in uri or ".jpg" in uri:
            return ""
        triples = ""
        labels = self.get_labels(uri)
        
        for label in labels:
            if label[1] != 'URI':
                triples+= f"<{uri}> <{label[1]}> \"{label[0]}\".\n"

        classes = self.get_resource_class(uri)
        for classe in classes:
            triples+= f"<{uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <{classe}>.\n"
            if classe != "http://www.w3.org/1999/02/22-rdf-syntax-ns#Property" and classe != "http://www.w3.org/2002/07/owl#DatatypeProperty" and classe != "http://www.w3.org/2002/07/owl#ObjectProperty":
                triples+= f"<{classe}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2002/07/owl#Class>.\n"
            labels = self.get_labels(str(classe))
            for label in labels:
                if label[1] != 'URI':
                    triples+= f"<{str(classe)}> <{label[1]}> \"{label[0]}\".\n"
            comments_str = ""
            comments = self.get_resource_comments(str(classe))
            for comment in comments:
                comments_str+=comment+" "
            if comments_str != "":
                triples+= f"<{str(classe)}> <http://www.w3.org/2000/01/rdf-schema#comment> \"{comments_str}\".\n"
        return triples
    
    def get_metada_property(self,uri):
        if "http://www.w3.org/2002/07/owl#" in uri or "http://www.w3.org/2000/01/rdf-schema#" in uri or "http://www.w3.org/1999/02/22-rdf-syntax-ns#" in uri or "http://www.w3.org/2001/XMLSchema#" in uri or "http://www.ontotext.com/" in uri or ".png" in uri or ".jpg" in uri:
            return ""
        triples = self.get_metadata(uri)

        classes = self.get_resource_class(uri)
        for classe in classes:
            triples+= f"<{uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <{classe}>.\n"
        if '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>' not in triples:
            triples+= f"<{uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/1999/02/22-rdf-syntax-ns#Property>.\n"
        
        # print(triples)
        domains = self.get_property_domain(uri)
        for domain in domains:
            triples+= f"<{uri}> <http://www.w3.org/2000/01/rdf-schema#domain> <{domain}>.\n"
        ranges = self.get_property_range(uri)
        for range in ranges:
            triples+= f"<{uri}> <http://www.w3.org/2000/01/rdf-schema#range> <{range}>.\n"

        return triples
    