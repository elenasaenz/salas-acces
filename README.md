# RRS Meta Extractor
The developed system will be used to extract data from public social media posts of ACCES venues (https://salasdeconciertos.com/salas-asociadas/).
The concert venues we aim to analyze are part of an association of venues (ACCES), and the service we are developing is intended to provide ACCES with access to this information.
The extracted information will be stored in a private relational database consisting of three tables: artists, venues, and events. 
This database will be updated with the extracted data (artist, venue, and date) for subsequent analysis and visualization.

## Requested Permissions
We are requesting  the Page Public Content Access permission to retrieve public posts from Facebook Pages. 
This permission is essential for our system to retrieve public posts from Facebook Pages associated with ACCES venues. These posts typically include valuable information such as event dates, performing artists, and venue locations, which are crucial for constructing a detailed and up-to-date database of music events.

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

- `meta_api_connector.py`: Simulates connection with the Meta API. This script demonstrates the use cases that require the requested permissions: Page Public Content Access.
- `database_schema.py`: Database schema

## Evaluation

Langfuse is used to evaluate the accuracy of the system by comparing the results with a reference dataset.

## Privacy and Security Measures

- All data processing and storage occur within a fully private and controlled environment.
- The language model employed for data extraction and the PostgreSQL database are deployed locally, ensuring that no data is transmitted to or stored on external servers.
- Our system only accesses publicly available content and strictly adheres to Meta’s data use policies and guidelines.


## Justification for Data Use
The company will use the collected data to build a database of ACCES music events, which can be used to generate reports, visualizations, and analytics. Information such as the artist name, venue, and event date will be essential for planning future events, making attendance forecasts, and optimizing marketing and promotional strategies for concerts.

Granting Page Public Content Access permission is critical to the functionality and success of our system. The access will empower us to collect and process only publicly available data from ACCES venue pages, ensuring compliance with Meta’s platform policies while delivering significant value to the ACCES association and its stakeholders.

This is the process followed by the system to extract and store concert data in the database. Although we are currently using simulated data, the process will remain the same with real data once the necessary permissions are approved. Thank you for reviewing this demonstration.
##
