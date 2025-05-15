# RRS Meta Extractor

Sistema para extraer información de posts de redes sociales de salas ACCES.

## Descripción

Este sistema analiza posts de redes sociales de las distintas salas ACCES para extraer eventos con:
- Fecha y hora
- Artistas
- Lugar

## Solución

- Desarrollo en Dify de un flujo que procesa posts (imágenes y texto)
- Utiliza LLM (gemma3:27b) para extraer información en formato JSON
- Almacena los datos en PostgreSQL

## Estructura

- `meta_api_connector.py`: Simula conexión con la API de Meta
- `evaluation.py`: Evaluación del sistema
- `database_schema.py`: Esquema de la base de datos

## Evaluación

Se utiliza Langfuse para evaluar la precisión del sistema comparando los resultados con un dataset de referencia.
