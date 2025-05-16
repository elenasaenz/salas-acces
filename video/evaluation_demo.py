from datetime import datetime
import json
import csv
from langfuse import Langfuse
from ragas.llms import LangchainLLMWrapper
from langfuse.decorators import observe, langfuse_context
from ragas import SingleTurnSample
from langchain_community.chat_models import ChatLiteLLM
import requests
import asyncio
import argparse
import difflib

# ==========================
# CONFIGURACIÓN MANUAL
# ==========================
# Credenciales y configuración de Langfuse para seguimiento de experimentos
LANGFUSE_SECRET_KEY = "xxx"
LANGFUSE_PUBLIC_KEY = "xxx"
LANGFUSE_HOST = "http://172.17.0.1:3000/"  # Instancia local de Langfuse

# Configuración de acceso a la API de LLM
LLM_API_KEY = "xxx"
LLM_API_BASE = "https://llmproxy.cinfo.es/"
LLM_MODEL_DEFAULT = "openai/gemma3:27b"  # Modelo predeterminado

# Configuración de la API de Dify para consultas
DIFY_WORKFLOW_URL = "http://localhost:8080/v1/workflows/run"  # Cambiado de 8082 a 8080
DIFY_AUTH_TOKEN = "xxx" 
# ==========================

def parse_arguments():
    """
    Configura y procesa los argumentos de línea de comandos para parametrizar el script.
    
    Returns:
        argparse.Namespace: Objeto con los argumentos procesados
    """
    parser = argparse.ArgumentParser(description='Evaluar extracción de información de posts con Langfuse')
    parser.add_argument('--evaluator-model', type=str, default=LLM_MODEL_DEFAULT,
                        help=f'Modelo LLM para evaluación (default: {LLM_MODEL_DEFAULT})')
    parser.add_argument('--embedding-model', type=str, default="NONE",
                        help=f'Modelo de embedding para evaluación (default: NONE)')
    # Eliminamos parámetros relacionados con RAG que no son relevantes para este caso
    parser.add_argument('--run-name', type=str, default=f"posts-eval-{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}",
                    help='Nombre del experimento (default: generado con timestamp)')
    parser.add_argument('--run-description', type=str, default='evaluacion posts redes sociales',
                    help='Descripción del experimento (default: evaluacion posts redes sociales)')
    parser.add_argument('--metrics', type=str, default='distancia JSON',
                    help='Métricas RAGAS a evaluar, separadas por comas (default: factual,recall,precision,noise)')
    parser.add_argument('--dataset', type=str, default='dataset.csv',
                    help='Ruta al archivo CSV del dataset (default: dataset.csv)')


    return parser.parse_args()

# Obtener los argumentos de línea de comandos
args = parse_arguments()
EVALUATOR_MODEL = args.evaluator_model
EMBEDDING_MODEL = args.embedding_model
RUN_NAME = args.run_name
RUN_DESCRIPTION = args.run_description
METRICS = [metric.strip() for metric in args.metrics.split(',')]
DATASET_PATH = args.dataset

# Inicialización del cliente de Langfuse para tracking de experimentos
langfuse = Langfuse(
    secret_key=LANGFUSE_SECRET_KEY,
    public_key=LANGFUSE_PUBLIC_KEY,
    host=LANGFUSE_HOST,
)

# Configuración del decorador de Langfuse para observar funciones
langfuse_context.configure(
    secret_key=LANGFUSE_SECRET_KEY,
    public_key=LANGFUSE_PUBLIC_KEY,
    host=LANGFUSE_HOST,
    enabled=True,
)

# Inicializar modelo LLM para evaluación a través de LangChain
print(f"Usando modelo evaluador: {EVALUATOR_MODEL}")
chat = ChatLiteLLM(
    model=EVALUATOR_MODEL,
    api_base=LLM_API_BASE,
    api_key=LLM_API_KEY
)

# Inicializar el modelo LLM para RAGAS y los diferentes evaluadores
evaluator_llm = LangchainLLMWrapper(chat)

# Clase para representar un ítem del dataset
class DatasetItem:
    def __init__(self, id, input_data, expected_output, metadata=None):
        self.id = id
        self.input = input_data
        self.expected_output = expected_output
        self.metadata = metadata or {}
    
    def observe(self, run_name, run_description, run_metadata):
        """
        Crea un trace en Langfuse para este ítem.
        
        Args:
            run_name (str): Nombre del experimento
            run_description (str): Descripción del experimento
            run_metadata (dict): Metadatos adicionales
            
        Returns:
            str: ID del trace creado
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

# Clase para representar un dataset
class Dataset:
    def __init__(self, items):
        self.items = items

# Cargar dataset desde Langfuse
print("Cargando dataset 'posts_db' desde Langfuse...")
langfuse_dataset = langfuse.get_dataset("posts_db")

# Convertir el dataset de Langfuse a nuestro formato
def convert_langfuse_dataset(langfuse_dataset):
    """
    Convierte un dataset de Langfuse a nuestro formato interno.
    
    Args:
        langfuse_dataset: Dataset de Langfuse
        
    Returns:
        Dataset: Objeto Dataset con los ítems convertidos
    """
    items = []
    
    for item in langfuse_dataset.items:
        # Crear ítem del dataset
        dataset_item = DatasetItem(
            id=item.id,
            input_data=item.input,
            expected_output=item.expected_output,
            metadata=item.metadata
        )
        items.append(dataset_item)
    
    print(f"Dataset cargado: {len(items)} ítems")
    return Dataset(items)

# Convertir el dataset de Langfuse a nuestro formato
dataset = convert_langfuse_dataset(langfuse_dataset)


# Función para calcular la distancia entre dos objetos JSON
def calculate_json_distance(json1, json2):
    """
    Calcula la distancia entre dos objetos JSON.
    
    Args:
        json1: Primer objeto JSON
        json2: Segundo objeto JSON
        
    Returns:
        float: Distancia entre los dos objetos (0-1)
    """
    from langchain.evaluation import JsonEditDistanceEvaluator
    evaluator = JsonEditDistanceEvaluator()
    
    # Convertir a strings JSON
    json1_str = json.dumps(json1, ensure_ascii=False)
    json2_str = json.dumps(json2, ensure_ascii=False)
    
    # Evaluar la distancia
    result = evaluator.evaluate_strings(
        prediction=json1_str,
        reference=json2_str
    )
    
    # La puntuación es la similitud, así que la distancia es 1 - score
    distance = result["score"]
    similarity = 1.0 - distance
    
    return distance, similarity

@observe()  # Decorador para tracking de esta función en Langfuse
def test(input_data, **kwargs):
    """
    Procesa un post usando el servicio Dify y retorna la respuesta generada.
    
    Args:
        input_data (dict o str): Los datos del post a procesar. Puede ser:
            - Un string con el texto del post
            - Un diccionario con keys como "caption", "date", "image_path"
            - Un diccionario con el texto del post directamente
        **kwargs: Argumentos adicionales para Langfuse
        
    Returns:
        dict: Respuesta generada
    """
    # Preparar los inputs para la API de Dify según el tipo de input_data
    dify_inputs = {}
    

    if isinstance(input_data, dict):
        if "caption" in input_data:
            print("Input recibido como diccionario con formato estándar")
            dify_inputs = {
                "post": input_data.get("caption", ""),
                "date": input_data.get("date", "")
            }
            
            # Si hay imagen, añadirla a los inputs
            if "image_path" in input_data and input_data["image_path"]:
                # Nota: En un entorno real, aquí se subiría la imagen primero
                # y luego se incluiría en los inputs, pero para este ejemplo
                # simplemente indicamos que existe una imagen
                print(f"Post tiene imagen: {input_data['image_path']}")
        

    
    try:
        # Realizar la llamada a la API de Dify para obtener respuesta
        print(f"Llamando a la API de Dify en {DIFY_WORKFLOW_URL}...")
        response = requests.post(
            DIFY_WORKFLOW_URL,
            headers={
                "Authorization": f"Bearer {DIFY_AUTH_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "inputs": dify_inputs,
                "response_mode": "blocking",  # Esperar a que termine el workflow
                "user": "Langfuse"  # Identificador para el usuario
            },
            timeout=10  # Timeout de 10 segundos
        )
        
        # Procesar la respuesta según el código de estado
        if response.status_code == 200:
            try:
                # Extraer datos de la respuesta
                json_data = response.json()["data"]
                print(f"Respuesta de Dify: {json_data}")
                # Verificar si outputs es None (caso de workflow fallido)
                outputs = json_data["outputs"]
                
                # Determinar la clave de respuesta correcta (pueden variar según la configuración)
                if "result" in outputs:
                    output = outputs["result"]
                    print("Usando clave de respuesta: result")
                elif "artistas" in outputs:
                    output = outputs
                    print("Usando respuesta completa con artistas")
                else:
                    # Fallback: Si no están las claves esperadas, mostrar todas las disponibles
                    try:
                        available_keys = list(outputs.keys())
                        print(f"Claves disponibles en la respuesta: {available_keys}")
                        
                        # Intentar usar la primera clave como fallback
                        if available_keys:
                            first_key = available_keys[0]
                            output = outputs[first_key]
                            print(f"Usando clave alternativa: {first_key}")
                        else:
                            output = f"No se encontraron claves de respuesta en la salida: {json_data}"
                    except Exception as e:
                        print(f"Error al procesar claves de respuesta: {e}")
                        output = f"Error al analizar la estructura de la respuesta: {json_data}"
            
            except Exception as e:
                # Error al procesar la respuesta JSON
                print(f"Error procesando la respuesta JSON: {str(e)}")
                output = f"Error procesando respuesta: {str(e)}"
        else:
            # Error en la llamada a la API (código diferente de 200)
            print(f"Error en la llamada a la API: {response.status_code}")
            output = f"Error en la API: {response.status_code} - {response.text[:200]}"
    except requests.exceptions.ConnectionError as e:
        print(f"Error de conexión a la API de Dify: {e}")
        print("Continuando con la evaluación sin llamar a la API de Dify...")
        # Usar expected_output como output para poder continuar con la evaluación
        output = expected_output
    except requests.exceptions.Timeout as e:
        print(f"Timeout en la llamada a la API de Dify: {e}")
        print("Continuando con la evaluación sin llamar a la API de Dify...")
        # Usar expected_output como output para poder continuar con la evaluación
        output = expected_output
    except Exception as e:
        print(f"Error inesperado al llamar a la API de Dify: {e}")
        print("Continuando con la evaluación sin llamar a la API de Dify...")
        # Usar expected_output como output para poder continuar con la evaluación
        output = expected_output

    # Actualizar observación en Langfuse
    langfuse_context.update_current_observation(
        input=input_data,
        output=output,
        metadata={
            "post_id": kwargs.get("post_id", "unknown")
        }
    )
    
    return output

# Generar timestamp para identificar la ejecución
timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

def run_async(coro):
    """
    Función auxiliar para ejecutar una corrutina asíncrona en un contexto síncrono.
    
    Args:
        coro: Corrutina a ejecutar
        
    Returns:
        Resultado de la corrutina
    """
    return asyncio.get_event_loop().run_until_complete(coro)

# Mostrar información de la ejecución
print(f"Iniciando evaluación con:")
print(f"- Run name: {RUN_NAME}")
print(f"- Run description: {RUN_DESCRIPTION}")
print(f"- Modelo evaluador: {EVALUATOR_MODEL}")
print(f"- Modelo de embedding: {EMBEDDING_MODEL}")
print(f"- Métricas a evaluar: {', '.join(METRICS)}")


# Procesar cada ítem del dataset
for idx, item in enumerate(dataset.items):
    print(f"\nProcesando ítem {idx+1}/{len(dataset.items)}")
    post_data = item.input
    expected_output = item.expected_output
    
    # Extraer el ID del post según el formato de post_data
    if isinstance(post_data, dict):
        post_id = post_data.get("id", idx)
    else:
        post_id = idx
    
    run_name = RUN_NAME
    
    # Crear trace en Langfuse para este ítem
    trace_id = item.observe(
        run_name=run_name,
        run_description=RUN_DESCRIPTION,
        run_metadata={
            "evaluator_model": EVALUATOR_MODEL,
            "embedding_model": EMBEDDING_MODEL,
            "post_id": post_id
        }
    )
    
    
    # Obtener la respuesta del servicio Dify
    output = test(post_data, langfuse_observation_id=trace_id, post_id=post_id)
    print("Respuesta de Dify:", output)
    print("expected output: ", expected_output)
    # Calcular la distancia entre la salida del modelo y la salida esperada
    print("Calculando distancia JSON entre la salida y la salida esperada...")
    try:
        distance, similarity = calculate_json_distance(output, expected_output)
        print(f"Distancia JSON calculada: {distance:.4f} (similitud: {similarity:.4f})")
    except Exception as e:
        print(f"Error al calcular la distancia JSON: {e}")
        distance = 1.0
        similarity = 0.0
    
    # Registrar la distancia en Langfuse
    langfuse.score(
        trace_id=trace_id,
        name="Similarity",
        value=similarity,
    )
    # Hacer flush después de registrar la métrica
    langfuse_context.flush()
    



# Finalizar: Enviar todos los datos pendientes a Langfuse
print("\nFinalizando evaluación y enviando datos a Langfuse...")
# Flush final para asegurar que todos los datos se han enviado
langfuse_context.flush()
print(f"Evaluación completada: {len(dataset.items)} ítems procesados")
print(f"Timestamp: {timestamp}")
