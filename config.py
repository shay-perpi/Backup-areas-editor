import json
import os
import geojson
import psycopg2

s3_path_key = os.getenv('path_key', 'backups/area_zones.json')
s3_credentials = os.getenv("s3_credentials", None)
pg_credential = os.getenv("pg_credential", None)

pg_credential = dict(json.loads(pg_credential))
s3_credentials = dict(json.loads(s3_credentials))


schema_in_db = os.getenv("schemaInDB", "RasterCatalogManager")
table_in_db = os.getenv("tableInDB", 'records')
record_id_in_db = os.getenv("recordInDB", 'identifier')
table_query = '"{}".{}'.format(schema_in_db, table_in_db,record_id_in_db)


def validate_footprint(input_foot_print):
    footprint_data = {
        "coordinates": [eval(input_foot_print)]
    }
    try:
        geojson.loads(json.dumps(footprint_data))
        print(f"is valid {input_foot_print}")
        return True
    except ValueError as e:
        print(f"Footprint validation failed: {e}")
        return False


# Example usage without specifying the "type"


def validate_record_id(record_id):
    try:
        # Replace these values with your PostgreSQL connection details
        db_connection = psycopg2.connect(database=pg_credential["pg_job_task_table"],
                                         host=pg_credential["pg_host"],
                                         user=pg_credential["pg_user"],
                                         password=pg_credential["pg_pass"],
                                         port=pg_credential["pg_port"])
        # Create a cursor
        cursor = db_connection.cursor()

        # Perform a query to check if the record ID exists
        cursor.execute(f"SELECT COUNT(*) FROM {table_query} WHERE {record_id_in_db}= %s", (record_id,))
        count = cursor.fetchone()[0]

        # Close the cursor and connection
        cursor.close()
        db_connection.close()

        return count > 0  # Returns True if the record ID exists, False otherwise
    except Exception as e:
        print(f"Error checking record ID in PostgreSQL: {str(e)}")
        return False


def calculate_resolution_deg(zoom_level):
    resolutions = [
        1.0, 0.3515625, 0.17578125, 0.087890625, 0.0439453125,
        0.02197265625, 0.010986328125, 0.0054931640625, 0.00274658203125,
        0.001373291015625, 0.0006866455078125, 0.00034332275390625,
        0.000171661376953125, 0.0000858306884765625, 0.00004291534423828125,
        0.000021457672119140625, 0.000010728836059570312, 0.000005364418029785156,
        0.000002682209014892578, 0.000001341104507446289, 6.705522537231445e-7,
        3.3527612686157227e-7, 1.6763806343078613e-7
    ]

    if 0 <= zoom_level <= 22:
        return resolutions[zoom_level]
    else:
        return None
