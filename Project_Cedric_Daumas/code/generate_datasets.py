"""
python generate_datasets.py datagen/data/test.txt  datagen/data/test --model_name gpt-4o-mini

"""
import os
import json
import argparse
import openai
from sparql.EndpointRiken import Endpoint
from datagen.datasetGenerator import DatasetGenerator
from configs import ENDPOINT_T_BOX_URL, ENDPOINT_A_BOX_URL

def generate_datasets(databases_file, output_dir, model_name="gpt-4", n_questions=15):
    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Read the list of databases from the file
    with open(databases_file, 'r') as f:
        databases = [line.strip() for line in f.readlines()]

    for database in databases:
        print(f"-------------------Processing database: {database}-------------------")
        
        try:
            # Initialize the endpoint for the current database
            endpoint_t_box = Endpoint(ENDPOINT_T_BOX_URL, database)
            endpoint_a_box = endpoint_t_box
            
            if ENDPOINT_A_BOX_URL and ENDPOINT_T_BOX_URL != ENDPOINT_A_BOX_URL:
                endpoint_a_box = Endpoint(ENDPOINT_A_BOX_URL, database)

            # Initialize the DatasetGenerator with the current database
            datagen = DatasetGenerator(endpoint_t_box, model_name=model_name, database=database)

            # Generate the dataset
            nl2sparql_dataset = datagen.create_nl2sparql_dataset_from_TABOX(n_questions=n_questions,
                                                                             filter_emptyres_queries=True)
            if nl2sparql_dataset is None:
                print("Dataset generation failed.")
                continue
            
            # Define the output file path
            output_file = os.path.join(output_dir, f"dataset_{database.replace('/', '_').replace(':', '_')}.json")

            # Save the dataset as a JSON file
            with open(output_file, 'w') as json_file:
                json.dump(nl2sparql_dataset, json_file, indent=2)
            
            print(f"Dataset saved to {output_file}")

        except openai.RateLimitError as e:
            print(f"RateLimitError: {e}. Skipping database {database} and continuing with the next one.")
            continue
        except Exception as e:
            print(f"An error occurred while processing {database}: {e}. Skipping to the next database.")
            continue

if __name__ == "__main__":
    # Initialize argparse
    parser = argparse.ArgumentParser(description="Generate NL2SPARQL datasets for multiple databases.")
    
    # Add arguments
    parser.add_argument('databases_file', type=str, help="The path to the file containing the list of databases.")
    parser.add_argument('output_dir', type=str, help="The directory where the generated JSON files will be saved.")
    parser.add_argument('--model_name', type=str, default="gpt-4o", help="The name of the model to use for generating datasets. Default is 'gpt-4'.")
    parser.add_argument('--num_questions_perdataset', type=int, default=15, help="The number of questions to generate for each dataset. Default is 15.")
    
    # Parse the arguments
    args = parser.parse_args()

    # Call the main function with the parsed arguments
    generate_datasets(args.databases_file, args.output_dir, model_name=args.model_name, n_questions=args.num_questions_perdataset)
