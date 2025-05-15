# RRS Meta Extractor

System for extracting information from social media posts of ACCES venues.

## Description

This system analyzes social media posts from various ACCES venues to extract events with:
- Date and time
- Artists
- Location

## Solution

- Development in Dify of a workflow that processes posts (images and text)
- Uses LLM (gemma3:27b) to extract information in JSON format
- Stores the data in PostgreSQL

## Structure

- `meta_api_connector.py`: Simulates connection with the Meta API
- `evaluation.py`: System evaluation
- `database_schema.py`: Database schema

## Evaluation

Langfuse is used to evaluate the accuracy of the system by comparing the results with a reference dataset.
