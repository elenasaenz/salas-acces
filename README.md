# RRS Meta Extractor
The developed system will be used to extract data from public social media posts of ACCES venues (https://salasdeconciertos.com/salas-asociadas/). 
The extracted information will be stored in a private relational database consisting of three tables: artists, venues, and events. 
This database will be updated with the extracted data (artist, venue, and date) for subsequent analysis and visualization.

## Requested Permissions
We are requesting both the Page Public Content Access and pages_read_engagement permissions to retrieve public posts from Facebook and Instagram Pages. This permission will allow our tool to collect public posts related to concerts held at ACCES venues and extract relevant data to be stored in our database.

## System Description

This system analyzes public social media posts from various ACCES venues to extract events with:
- Date and time
- Artists
- Location
These posts may contain text, images, links, and occasionally videos. Extracted data will be stored in a relational database. The artists, venues, and events tables will be automatically updated with this information.

## Solution

- Development in Dify of a workflow that processes posts (images and text)
- Uses local and private LLM (gemma3:27b) to extract information in JSON format
- Stores the data in PostgreSQL (also managed locally and privately)

## Structure

In the structure, the meta_api_connector.py simulates how the system extracts and organizes sample data. For example, a post may include an artist name, venue, and date. This data is then processed and stored in the corresponding tables (artists, venues, and events). Once the tool is granted access to real data, it will follow the same process using actual social media content.

- `meta_api_connector.py`: Simulates connection with the Meta API. This script demonstrates the use cases that require the requested permissions: Page Public Content Access and pages_read_engagement.
- `database_schema.py`: Database schema

## Evaluation

Langfuse is used to evaluate the accuracy of the system by comparing the results with a reference dataset.

## Justification for Data Use
The company will use the collected data to build a database of ACCES music events, which can be used to generate reports, visualizations, and analytics. Information such as the artist name, venue, and event date will be essential for planning future events, making attendance forecasts, and optimizing marketing and promotional strategies for concerts.

We would like to emphasize that the entire process will be managed privately. Both the language model and the database have been deployed locally to ensure full control and data privacy.

This is the process followed by the system to extract and store concert data in the database. Although we are currently using simulated data, the process will remain the same with real data once the necessary permissions are approved. Thank you for reviewing this demonstration.
##
