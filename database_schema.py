"""
Pseudocode for creating the PostgreSQL database schema.
"""

import psycopg2

# Database configuration
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "salas_acces"
DB_USER = "userxxx"
DB_PASSWORD = "xxxx"


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

def create_tables(connection):
    """
    Creates the necessary tables in the database.
    
    Args:
        connection: Connection to the database
    """
    try:
        cursor = connection.cursor()
        
        # Create artists table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS artista (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(255) NOT NULL
        )
        """)
        
        # Create venues table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sala (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(255) NOT NULL,
            ciudad VARCHAR(255),
            provincia VARCHAR(255),
            aforo INTEGER
        )
        """)
        
        # Create events table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id SERIAL PRIMARY KEY,
            artista_id INTEGER REFERENCES artista(id),
            sala_id INTEGER REFERENCES sala(id),
            fecha DATE NOT NULL
        )
        """)
        
        connection.commit()
        print("Tables created successfully")
    except Exception as e:
        print(f"Error creating tables: {e}")
        connection.rollback()

def insert_sample_data(connection):
    """
    Inserts sample data into the tables.
    
    Args:
        connection: Connection to the database
    """
    try:
        cursor = connection.cursor()
        
        # Insert sample artists
        artistas = [
            "javierturnes",
            "tulsamireniza",
            "freedoniasoul",
            "madmartintrio",
            "nubiyantwist",
            "insaniam",
            "nodropforus",
            "frequency"
        ]
        
        for artista in artistas:
            cursor.execute(
                "INSERT INTO artista (nombre) VALUES (%s) ON CONFLICT DO NOTHING",
                (artista,)
            )
        
        # Insert sample venues
        salas = [
            ("Riquela Club", "Santiago de Compostela", "A Coruña", 200),
            ("Clandestino", "A Coruña", "A Coruña", 150),
            ("Sala Malatesta", "Vigo", "Pontevedra", 300)
        ]
        
        for sala in salas:
            cursor.execute(
                "INSERT INTO sala (nombre, ciudad, provincia, aforo) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                sala
            )
        
        # Insert sample events
        eventos = [
            (1, 1, "2024-04-12"),  # javierturnes en Riquela Club
            (2, 1, "2024-04-19"),  # tulsamireniza en Riquela Club
            (3, 1, "2024-04-20"),  # freedoniasoul en Riquela Club
            (4, 1, "2024-04-26"),  # madmartintrio en Riquela Club
            (5, 1, "2024-04-28"),  # nubiyantwist en Riquela Club
            (6, 2, "2024-05-10"),  # insaniam en Clandestino
            (7, 2, "2024-05-10"),  # nodropforus en Clandestino
            (8, 2, "2024-05-10")   # frequency en Clandestino
        ]
        
        for evento in eventos:
            cursor.execute(
                "INSERT INTO eventos (artista_id, sala_id, fecha) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                evento
            )
        
        connection.commit()
        print("Sample data inserted successfully")
    except Exception as e:
        print(f"Error inserting sample data: {e}")
        connection.rollback()

def query_events(connection):
    """
    Queries events from the database.
    
    Args:
        connection: Connection to the database
    """
    try:
        cursor = connection.cursor()
        
        # Query events with artist and venue information
        cursor.execute("""
        SELECT e.id, a.nombre as artista, s.nombre as sala, s.ciudad, e.fecha
        FROM eventos e
        JOIN artista a ON e.artista_id = a.id
        JOIN sala s ON e.sala_id = s.id
        ORDER BY e.fecha
        """)
        
        events = cursor.fetchall()
        
        print("\nEvents in the database:")
        print("-----------------------------")
        for event in events:
            event_id, artista, sala, ciudad, fecha = event
            print(f"ID: {event_id}, Artista: {artista}, Sala: {sala} ({ciudad}), Fecha: {fecha}")
    except Exception as e:
        print(f"Error querying events: {e}")

def main():
    """
    Main function that creates the database schema.
    """
    # Connect to the database
    connection = connect_to_db()
    
    if connection:
        # Create tables
        create_tables(connection)
        
        # Insert sample data
        insert_sample_data(connection)
        
        # Query events
        query_events(connection)
        
        # Close connection
        connection.close()
        print("Database connection closed")

if __name__ == "__main__":
    main()
