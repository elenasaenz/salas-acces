"""
Pseudocode for evaluating the extraction of information from social media posts.
"""

from datetime import datetime
import json
import csv
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context
import requests
import argparse
import psycopg2

# Import our Meta API connector
from meta_api_connector import get_posts_with_images

# ==========================
# MANUAL CONFIGURATION
# ==========================
# Langfuse credentials and configuration for experiment tracking
LANGFUSE_SECRET_KEY = "sk-lf-xxxx"
LANGFUSE_PUBLIC_KEY = "pk-lf-xxxx"
LANGFUSE_HOST = "http://localhost:3000/"

# LLM API access configuration
LLM_API_KEY = "sk-xxxx"
LLM_API_BASE = "https://api.example.com/"
LLM_MODEL_DEFAULT = "gemma3:27b"  # Default model

# Dify API configuration for queries
DIFY_WORKFLOW_URL = "http://localhost:8080/v1/workflows/run"
DIFY_AUTH_TOKEN = "app-xxxx"

# PostgreSQL database configuration
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "sala_acces"
DB_USER = "userxxx"
DB_PASSWORD = "xxxx"
# ==========================

def parse_arguments():
    """
    Configures and processes command line arguments to parameterize the script.
    
    Returns:
        argparse.Namespace: Object with the processed arguments
    """
    parser = argparse.ArgumentParser(description='Evaluar extracción de información de posts con Langfuse')
    parser.add_argument('--evaluator-model', type=str, default=LLM_MODEL_DEFAULT,
                        help=f'LLM model for evaluation (default: {LLM_MODEL_DEFAULT})')
    parser.add_argument('--run-name', type=str, default=f"posts-eval-{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}",
                    help='Experiment name (default: generated with timestamp)')
    parser.add_argument('--run-description', type=str, default='evaluacion posts redes sociales',
                    help='Experiment description (default: social media posts evaluation)')
    parser.add_argument('--metrics', type=str, default='distancia JSON',
                    help='Metrics to evaluate, separated by commas')
    parser.add_argument('--dataset', type=str, default='dataset.csv',
                    help='Path to the CSV dataset file (default: dataset.csv)')
    parser.add_argument('--save-to-db', action='store_true',
                    help='Save results to the database')

    return parser.parse_args()

# Get command line arguments
args = parse_arguments()
EVALUATOR_MODEL = args.evaluator_model
RUN_NAME = args.run_name
RUN_DESCRIPTION = args.run_description
METRICS = [metric.strip() for metric in args.metrics.split(',')]
DATASET_PATH = args.dataset
SAVE_TO_DB = args.save_to_db

# Initialize Langfuse client for experiment tracking
langfuse = Langfuse(
    secret_key=LANGFUSE_SECRET_KEY,
    public_key=LANGFUSE_PUBLIC_KEY,
    host=LANGFUSE_HOST,
)

# Configure Langfuse decorator to observe functions
langfuse_context.configure(
    secret_key=LANGFUSE_SECRET_KEY,
    public_key=LANGFUSE_PUBLIC_KEY,
    host=LANGFUSE_HOST,
    enabled=True,
)

# Class to represent a dataset item
class DatasetItem:
    def __init__(self, id, input_data, expected_output, metadata=None):
        self.id = id
        self.input = input_data
        self.expected_output = expected_output
        self.metadata = metadata or {}
    
    def observe(self, run_name, run_description, run_metadata):
        """
        Creates a trace in Langfuse for this item.
        
        Args:
            run_name (str): Experiment name
            run_description (str): Experiment description
            run_metadata (dict): Additional metadata
            
        Returns:
            str: ID of the created trace
        """
        trace = langfuse.trace(
            name=run_name,
            metadata={
                "item_id": self.id,
                **run_metadata
            },
            user_id=f"item_{self.id}",
            tags=["evaluation"]
        )
        return trace.id

# Class to represent a dataset
class Dataset:
    def __init__(self, items):
        self.items = items

# Function to load dataset from CSV
def load_dataset_from_csv(csv_path):
    """
    Loads a dataset from a CSV file.
    
    Args:
        csv_path (str): Path to the CSV file
        
    Returns:
        Dataset: Dataset object with loaded items
    """
    items = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Create dataset item
            dataset_item = DatasetItem(
                id=row['id'],
                input_data=json.loads(row['input']),
                expected_output=json.loads(row['expected_output'])
            )
            items.append(dataset_item)
    
    print(f"Dataset loaded: {len(items)} items")
    return Dataset(items)

# Function to calculate the distance between two JSON objects
def calculate_json_distance(json1, json2):
    """
    Calculates the distance between two JSON objects.
    
    Args:
        json1: First JSON object
        json2: Second JSON object
        
    Returns:
        float: Distance between the two objects (0-1)
    """
    from langchain.evaluation import JsonEditDistanceEvaluator
    evaluator = JsonEditDistanceEvaluator()
    
    # Convert to JSON strings
    json1_str = json.dumps(json1, ensure_ascii=False)
    json2_str = json.dumps(json2, ensure_ascii=False)
    
    # Evaluate the distance
    result = evaluator.evaluate_strings(
        prediction=json1_str,
        reference=json2_str
    )
    
    # The score is the similarity, so the distance is 1 - score
    distance = result["score"]
    similarity = 1.0 - distance
    
    return distance, similarity

# Function to connect to the database
def connect_to_db():
    """
    Establishes a connection to the PostgreSQL database.
    
    Returns:
        connection: Connection to the database
    """
    try:
        connection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        print("Database connection established")
        return connection
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

# Function to save artists to the database
def save_artist_to_db(connection, artist_name):
    """
    Saves an artist to the database.
    
    Args:
        connection: Connection to the database
        artist_name (str): Artist name
        
    Returns:
        int: ID of the artist in the database
    """
    try:
        cursor = connection.cursor()
        
        # Check if the artist already exists
        cursor.execute("SELECT id FROM artista WHERE nombre = %s", (artist_name,))
        result = cursor.fetchone()
        
        if result:
            # If the artist already exists, return its ID
            return result[0]
        else:
            # If the artist doesn't exist, create it
            cursor.execute(
                "INSERT INTO artista (nombre) VALUES (%s) RETURNING id",
                (artist_name,)
            )
            artist_id = cursor.fetchone()[0]
            connection.commit()
            return artist_id
    except Exception as e:
        print(f"Error saving artist to the database: {e}")
        connection.rollback()
        return None

# Function to save venue to the database
def save_venue_to_db(connection, venue_name):
    """
    Saves a venue to the database.
    
    Args:
        connection: Connection to the database
        venue_name (str): Venue name
        
    Returns:
        int: ID of the venue in the database
    """
    try:
        cursor = connection.cursor()
        
        # Check if the venue already exists
        cursor.execute("SELECT id FROM sala WHERE nombre = %s", (venue_name,))
        result = cursor.fetchone()
        
        if result:
            # If the venue already exists, return its ID
            return result[0]
        else:
            # If the venue doesn't exist, create it
            # In a real case, more data would be added here such as city, capacity, etc.
            cursor.execute(
                "INSERT INTO sala (nombre) VALUES (%s) RETURNING id",
                (venue_name,)
            )
            venue_id = cursor.fetchone()[0]
            connection.commit()
            return venue_id
    except Exception as e:
        print(f"Error saving venue to the database: {e}")
        connection.rollback()
        return None

# Function to save event to the database
def save_event_to_db(connection, artist_id, venue_id, event_date):
    """
    Saves an event to the database.
    
    Args:
        connection: Connection to the database
        artist_id (int): Artist ID
        venue_id (int): Venue ID
        event_date (str): Event date
        
    Returns:
        int: ID of the event in the database
    """
    try:
        cursor = connection.cursor()
        
        # Check if the event already exists
        cursor.execute(
            "SELECT id FROM eventos WHERE artista_id = %s AND sala_id = %s AND fecha = %s",
            (artist_id, venue_id, event_date)
        )
        result = cursor.fetchone()
        
        if result:
            # If the event already exists, return its ID
            return result[0]
        else:
            # If the event doesn't exist, create it
            cursor.execute(
                "INSERT INTO eventos (artista_id, sala_id, fecha) VALUES (%s, %s, %s) RETURNING id",
                (artist_id, venue_id, event_date)
            )
            event_id = cursor.fetchone()[0]
            connection.commit()
            return event_id
    except Exception as e:
        print(f"Error saving event to the database: {e}")
        connection.rollback()
        return None

# Function to save results to the database
def save_results_to_db(connection, output):
    """
    Saves the extraction results to the database.
    
    Args:
        connection: Connection to the database
        output (dict): Extraction results
    """
    try:
        # Extract artists, dates and locations
        artistas = output.get("artistas", [])
        fechas = output.get("fecha", [])
        ubicaciones = output.get("ubicacion", [])
        
        # If there are no artists, dates or locations, there's nothing to save
        if not artistas or not fechas or not ubicaciones:
            print("Not enough data to save to the database")
            return
        
        # For each artist, save to the database
        for artista in artistas:
            artist_id = save_artist_to_db(connection, artista)
            
            # For each location, save to the database
            for ubicacion in ubicaciones:
                venue_id = save_venue_to_db(connection, ubicacion)
                
                # For each date, save to the database
                for fecha in fechas:
                    event_id = save_event_to_db(connection, artist_id, venue_id, fecha)
                    print(f"Event saved to the database with ID {event_id}")
    except Exception as e:
        print(f"Error saving results to the database: {e}")

@observe()  # Decorator for tracking this function in Langfuse
def process_post(input_data, **kwargs):
    """
    Processes a post using the Dify service and returns the generated response.
    
    Args:
        input_data (dict or str): The post data to process. Can be:
            - A string with the post text
            - A dictionary with keys like "caption", "date", "image_path"
            - A dictionary with the post text directly
        **kwargs: Additional arguments for Langfuse
        
    Returns:
        dict: Generated response
    """
    # Prepare inputs for the Dify API according to the input_data type
    dify_inputs = {}
    
    if isinstance(input_data, dict):
        if "caption" in input_data:
            print("Input received as dictionary with standard format")
            dify_inputs = {
                "post": input_data.get("caption", ""),
                "date": input_data.get("date", "")
            }
            
            # If there's an image, add it to the inputs
            if "image_path" in input_data and input_data["image_path"]:
                print(f"Post has image: {input_data['image_path']}")
    
    try:
        # Make the call to the Dify API to get a response
        print(f"Calling the Dify API at {DIFY_WORKFLOW_URL}...")
        response = requests.post(
            DIFY_WORKFLOW_URL,
            headers={
                "Authorization": f"Bearer {DIFY_AUTH_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "inputs": dify_inputs,
                "response_mode": "blocking",  # Wait for the workflow to finish
                "user": "Langfuse"  # User identifier
            },
            timeout=10  # Timeout de 10 segundos
        )
        
        # Process the response according to the status code
        if response.status_code == 200:
            try:
                # Extract data from the response
                json_data = response.json()["data"]
                print(f"Dify response: {json_data}")
                outputs = json_data["outputs"]
                
                # Determine the correct response key
                if "result" in outputs:
                    output = outputs["result"]
                elif "artistas" in outputs:
                    output = outputs
                else:
                    # Fallback: If the expected keys are not present, show all available ones
                    available_keys = list(outputs.keys())
                    if available_keys:
                        first_key = available_keys[0]
                        output = outputs[first_key]
                    else:
                        output = f"No response keys found in the output: {json_data}"
            
            except Exception as e:
                # Error processing the JSON response
                print(f"Error processing the JSON response: {str(e)}")
                output = f"Error processing response: {str(e)}"
        else:
            # Error in the API call (code different from 200)
            print(f"Error in the API call: {response.status_code}")
            output = f"API error: {response.status_code} - {response.text[:200]}"
    except Exception as e:
        print(f"Unexpected error calling the Dify API: {e}")
        output = f"Error: {str(e)}"

    # Update observation in Langfuse
    langfuse_context.update_current_observation(
        input=input_data,
        output=output,
        metadata={
            "post_id": kwargs.get("post_id", "unknown")
        }
    )
    
    return output

def main():
    """
    Main function that executes the evaluation.
    """
    # Generate timestamp to identify the execution
    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    
    # Show execution information
    print(f"Starting evaluation with:")
    print(f"- Run name: {RUN_NAME}")
    print(f"- Run description: {RUN_DESCRIPTION}")
    print(f"- Evaluator model: {EVALUATOR_MODEL}")
    print(f"- Metrics to evaluate: {', '.join(METRICS)}")
    
    # Load dataset from CSV
    dataset = load_dataset_from_csv(DATASET_PATH)
    
    # Connect to the database if necessary
    connection = None
    if SAVE_TO_DB:
        connection = connect_to_db()
    
    # Process each item in the dataset
    for idx, item in enumerate(dataset.items):
        print(f"\nProcessing item {idx+1}/{len(dataset.items)}")
        post_data = item.input
        expected_output = item.expected_output
        
        # Extract the post ID according to the post_data format
        if isinstance(post_data, dict):
            post_id = post_data.get("id", idx)
        else:
            post_id = idx
        
        # Create trace in Langfuse for this item
        trace_id = item.observe(
            run_name=RUN_NAME,
            run_description=RUN_DESCRIPTION,
            run_metadata={
                "evaluator_model": EVALUATOR_MODEL,
                "post_id": post_id
            }
        )
        
        # Get the response from the Dify service
        output = process_post(post_data, langfuse_observation_id=trace_id, post_id=post_id)
        print("Dify response:", output)
        print("Expected output: ", expected_output)
        
        # Calculate the distance between the model output and the expected output
        print("Calculating JSON distance between the output and the expected output...")
        try:
            distance, similarity = calculate_json_distance(output, expected_output)
            print(f"Calculated JSON distance: {distance:.4f} (similarity: {similarity:.4f})")
        except Exception as e:
            print(f"Error calculating JSON distance: {e}")
            distance = 1.0
            similarity = 0.0
        
        # Register the distance in Langfuse
        langfuse.score(
            trace_id=trace_id,
            name="Similarity",
            value=similarity,
        )
        
        # Save results to the database if necessary
        if SAVE_TO_DB and connection:
            save_results_to_db(connection, output)
    
    # Close database connection if necessary
    if connection:
        connection.close()
    
    # Finalize: Send all pending data to Langfuse
    print("\nFinalizing evaluation and sending data to Langfuse...")
    langfuse_context.flush()
    print(f"Evaluation completed: {len(dataset.items)} items processed")
    print(f"Timestamp: {timestamp}")

if __name__ == "__main__":
    # Example of use: get posts from Meta and evaluate them
    print("Getting posts from Meta...")
    posts = get_posts_with_images()
    print(f"Obtained {len(posts)} posts")
    
    # Execute the evaluation
    main()
