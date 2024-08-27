# from core.QuestionHandler import QuestionHandler
import re
from openai import OpenAI
from sparql.Utils import  generate_sparql_prefix
from configs import TEMPERATURE_TRANSLATE
import csv
import io
import re
from collections import defaultdict
from context.prompts import prompt_get_sparqls
from sparql.queries import tbox_short,abox
import json
import logging

client = OpenAI()

# class DatasetGenerator(QuestionHandler):
class DatasetGenerator():
    def __init__(self, 
                 endpoint, 
                 model_name="gpt-3.5-turbo-16k",
                 database="http://metadb.riken.jp/db/Glycomics_mouse"
                 ):
        print("Using model: ",model_name)
        # super().__init__(endpoint, t_box_index, normalizer, a_box_index, model_name)
        self.endpoint = endpoint
        self.model_name = model_name
        self.database = database

        
    
    def generate_questions_and_sparql(self, 
                                      class_label, 
                                      num_questions, 
                                      ):
        database = self.database
        database_prefix = generate_sparql_prefix(database)
        prompt = f"""
        Generate {num_questions} questions and a corresponding SPARQL queries for the following class: {class_label}
        - In each sparql query include `FROM <{database}>`.
        - Use prefixes in the SPARQL queries:
        ```
        {database_prefix}
        ```
        
        """

        completion = client.chat.completions.create(model=self.model_name, messages=[{"role": "user", "content": prompt}], temperature=TEMPERATURE_TRANSLATE)
        
        print('Model used:',completion.model)
        # Extract questions and SPARQL queries from the completion
        qa_pairs = []
        for choice in completion.choices:
            qa_pairs.append(choice.message.content)
        
        return qa_pairs

    def get_query_result(self,file_query=None):
        if file_query:
            with open(file_query, 'r') as file:
                query = file.read()

        #Adding the database prefix
        #TODO run_sparql should FROM  automatically
        # query = query.replace("###<FROM>###",f"FROM <{self.database}>")
        # print(query)
        result = self.endpoint.run_sparql(query=query)

        return result

    def extract_prefix(self,uri):
        match = re.match(r'^(.*[\/#])([^\/#]+)$', uri)
        if match:
            return match.groups()
        return None, uri

    def json_to_csv_with_prefixes(self, json_results, skip_repeat_rows=False, max_rows_same_prefix=None):
        # Extract all URIs and identify prefixes
        prefixes = {"http://www.w3.org/2001/XMLSchema#": "xsd"}
        simplified_results = []
        seen_rows = set()
        prefix_counts = defaultdict(int)

        def sanitize_prefix(name):
            """Sanitize the prefix to ensure it's a valid NCName."""
            name = re.sub(r'[^a-zA-Z0-9_]', '_', name)  # Replace invalid characters with underscores
            if name[0].isdigit():
                name = f"ns_{name}"  # Prefix with 'ns_' if the name starts with a digit
            return name

        def add_prefix(uri):
            prefix, local_name = self.extract_prefix(uri)
            if prefix:
                if prefix not in prefixes:
                    # Use the last part of the prefix path as the prefix name
                    raw_prefix_name = prefix.rstrip('/').split('/')[-1]
                    sanitized_prefix = sanitize_prefix(raw_prefix_name)
                    prefixes[prefix] = sanitized_prefix
                return f"{prefixes[prefix]}:{local_name}"
            return uri

        for result in json_results:
            simplified_result = {}
            current_prefix = None
            for key, value in result.items():
                if value.startswith('http'):
                    prefixed_value = add_prefix(value)
                    simplified_result[key] = prefixed_value
                    if current_prefix is None:
                        current_prefix = prefixed_value.split(':')[0]
                else:
                    # Check if the value contains a URI for literals
                    match = re.match(r'\"(.+)\"(\^\^<(.+)>)', value)
                    if match:
                        literal_value, _, datatype_uri = match.groups()
                        prefixed_value = f"\"{literal_value}\"^^{add_prefix(datatype_uri)}"
                        simplified_result[key] = prefixed_value
                    else:
                        simplified_result[key] = value

            # Convert the simplified result to a tuple to make it hashable
            result_tuple = tuple(simplified_result.items())

            if skip_repeat_rows:
                if result_tuple in seen_rows:
                    continue  # Skip this row since it's a duplicate
                seen_rows.add(result_tuple)

            if max_rows_same_prefix is not None and current_prefix is not None:
                if prefix_counts[current_prefix] >= max_rows_same_prefix:
                    continue  # Skip if we've reached the max count for this prefix
                prefix_counts[current_prefix] += 1

            simplified_results.append(simplified_result)

        # Create a list of prefixes
        prefix_list = [f"PREFIX {name}: <{prefix}>" for prefix, name in prefixes.items()]

        # Create CSV content
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=simplified_results[0].keys())
        writer.writeheader()
        writer.writerows(simplified_results)

        csv_content = output.getvalue()
        output.close()

        # Combine prefixes and CSV content
        result = "\n".join(prefix_list) + "\n\n" + csv_content

        return result

    def create_nl2sparql_dataset_from_TABOX(self, 
        tbox_query=tbox_short,
        abox_query=abox,
        n_questions=2,
        tbox_limit=100,
        filter_emptyres_queries=False
        ):
        #database_prefix = generate_sparql_prefix(self.database)
        tbox_query_limit = tbox_query + f"LIMIT {tbox_limit}"

        tbox_sparql_res=self.endpoint.run_sparql(query=tbox_query_limit)
        if len(tbox_sparql_res)==0:
            logging.warning("No results from T-Box query")
            return None
        

        TBOX = self.json_to_csv_with_prefixes(tbox_sparql_res,
                                              skip_repeat_rows=True,
                                              max_rows_same_prefix=3
                                              )
        abox_sparql_res=self.endpoint.run_sparql(query=abox_query)
        if len(abox_sparql_res)==0:
            logging.warning("No results from A-Box query")
            return None
        ABOX = self.json_to_csv_with_prefixes(abox_sparql_res,
                                              skip_repeat_rows=True)
       
        prompt = prompt_get_sparqls.format(TBOX=TBOX, ABOX=ABOX, n_questions=n_questions, database=self.database)

        #Calling LLM
        completion = client.chat.completions.create(model=self.model_name, messages=[{"role": "user", "content": prompt}], temperature=TEMPERATURE_TRANSLATE)
        
        # Extract questions and SPARQL queries from the completion
        # TODO delete nex for loop
        qa_pairs = []
        for choice in completion.choices:
            qa_pairs.append(choice.message.content)
        
        json_dataset=json.loads(parse_openai_output(qa_pairs[0]))
        filtered_dataset = json_dataset
        #REmove bad sparql queries
        if filter_emptyres_queries:
            filtered_dataset = []
            for triplet in json_dataset:
                res = self.endpoint.run_sparql(triplet['sparql_query'])
                if len(res)>0:
                    filtered_dataset.append(triplet)
            
        return {
            'llm_output': qa_pairs,
            'filtered_dataset':filtered_dataset}

    def create_nl2sparql_dataset_per_class(self, num_questions_per_class,num_classes_limit=10):
        """
        Iterate each class from the TBOX and try to generate questions for each class
        """
        all_elements_tbox = self.t_box_index.list_all_elements()[:num_classes_limit]
        
        #Also wotk with A-Box
        dataset = []

        for element in all_elements_tbox:
            class_label = element['metadata']['?label']
            qa_pairs = self.generate_questions_and_sparql(class_label, num_questions_per_class)
            
            for pair in qa_pairs:
                dataset.append({
                    "class_label": class_label,
                    "qa_pair": pair
                })
        
        return dataset
    

    
    def extract_questions_and_sparql(self,text):
        # Split the text into lines
        lines = text.strip().split('\n')
        
        dataset = []
        current_question = None
        current_sparql = None
        for line in lines:
            # Check if the line starts with 'Question'
            if line.startswith("Question"):
                if current_question and current_sparql:
                    dataset.append({'question': current_question, 'sparql': current_sparql})
                    current_question = None
                    current_sparql = None
                # Extract the question text
                current_question = line.split(":", 1)[1].strip()
            # Check if the line starts with 'SPARQL query'
            elif line.startswith("SPARQL Query"):
                # Initialize SPARQL query collector
                current_sparql = ""
            elif current_sparql is not None:
                # Append the SPARQL query lines
                current_sparql += line + "\n"
        
        # Add the last pair to the dataset if exists
        if current_question and current_sparql:
            dataset.append({'question': current_question, 'sparql': current_sparql.strip()})
        
        return dataset
    

# Set up logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

def parse_openai_output(output_text):
    # Split the output by pairs
    pairs = output_text.strip().split("###")[1:]

    results = []

    for i, pair in enumerate(pairs, start=1):
        label_uri_map = re.search(r"\*\*label2uri:\*\*\s*```(?:\s+)?\n\s*'(.*?)':(.*?)\s*```", pair)
        question = re.search(r"\*\*question:\*\*\s*(.*?)\n", pair)
        sparql_query = re.search(r"\*\*SPARQL:\*\*\s*```sparql(.*?)```", pair, re.DOTALL)

        if not label_uri_map:
            logging.warning(f"Failed to parse label2URI map for Pair {i}")
        if not question:
            logging.warning(f"Failed to parse Question for Pair {i}")
        if not sparql_query:
            logging.warning(f"Failed to parse SPARQL Query for Pair {i}")

        if label_uri_map and question and sparql_query:
            label = label_uri_map.group(1).strip()
            uri = label_uri_map.group(2).strip()
            question_text = question.group(1).strip()
            sparql_query_text = sparql_query.group(1).strip()

            result = {
                "label2URI": {
                    "label": label,
                    "uri": uri
                },
                "question": question_text,
                "sparql_query": sparql_query_text
            }

            results.append(result)
        else:
            logging.warning(f"Incomplete data for Pair {i}, skipping this pair.")

    if not results:
        logging.warning("No valid pairs were parsed from the input text.")
    
    return json.dumps(results, indent=2)