# app.py (Streamlit application with centered layout)
import geojson
import boto3
import streamlit as st
import folium
from streamlit_folium import folium_static
import json
import time
from urllib3.connectionpool import xrange
from streamlit_js_eval import streamlit_js_eval

from export_send import export_to_send
from config import s3_credentials, s3_path_key, calculate_resolution_deg, validate_record_id, validate_footprint

# Set your S3 credentials
AWS_ACCESS_KEY = s3_credentials["s3_user"]
AWS_SECRET_KEY = s3_credentials["s3_password"]
S3_BUCKET = s3_credentials["s3_bucket"]
S3_KEY = s3_path_key
s3_endpoint = s3_credentials["s3_ip"]
# Connect to S3
s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY,
                  endpoint_url=s3_endpoint)


# Load JSON from S3
def load_json_from_s3():
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
        data = json.loads(response['Body'].read())
        return data
    except Exception as e:
        st.error(f"Error loading JSON from S3: {str(e)}")
        return None


# Save JSON to S3
def save_json_to_s3(data):
    try:
        s3.put_object(Body=json.dumps(data, indent=2), Bucket=S3_BUCKET, Key=S3_KEY)
        st.success("JSON saved successfully!")
        time.sleep(2)
        st.rerun()

    except Exception as e:
        st.error(f"Error saving JSON to S3: {str(e)}")
        raise e


def delete_area(deleted_name, json_data):
    new_list = []
    # new_list = [obj for obj in json_data['areas'] if obj['name'] != deleted_name]
    for area in json_data['areas']:
        if area['name'] not in deleted_name:
            new_list.append(area)
    json_data['areas'] = new_list
    save_json_to_s3(json_data)


# ...

def main():
    st.set_page_config(
        page_title="Export BackUP Handler",
        page_icon="🌍",
        layout="centered"
    )

    st.title("Backup areas editor")

    # Load JSON from S3
    json_data = load_json_from_s3()

    # Display expander for Current JSON Data
    with st.expander("Current JSON Data", expanded=False):
        if json_data is not None:
            # Display current JSON data
            st.write("Current JSON Data:", json_data)

    st.markdown("""
     Valid area should be: \n
A name should be indicative for the user. \n
Footprint should be in the structure of a list with 5 coordinates [[X,Y],[X,Y],[X,Y],[X,Y],[X,Y]] numbers only.\n
Record ID that appears in the database without quotes.
    """)

    # Let the user choose between form and file upload
    option = st.radio("Choose an option:", ("Add New Area (Form)", "Upload JSON File"))

    if option == "Add New Area (Form)":
        # Form for adding new areas
        st.write("## Add New Area")
        new_area_name = st.text_input("Name:")
        new_area_footprint = st.text_area("Footprint (List of coordinates):", height=100)
        new_area_footprint = new_area_footprint.replace(" ", "").replace("\n", "")

        new_area_record_id = st.text_input("Record ID:")

        # Zoom level options
        zoom_level_options = list(range(23))

        # Display the zoom level dropdown
        selected_zoom_level = st.selectbox("Area Zoom Level:", zoom_level_options)

        if selected_zoom_level != "Choose...":
            # Calculate resolutionDeg based on the selected zoom level
            new_area_resolution_value = calculate_resolution_deg(selected_zoom_level)

            st.write(f"Zoom Level: {selected_zoom_level}")
            st.write(f"Resolution: {new_area_resolution_value}")

            if st.button("Add Area"):
                try:
                    # Validate the record ID before adding the area
                    if not validate_record_id(new_area_record_id):
                        st.error(f"Record ID '{new_area_record_id}' does not exist in the database.")
                        return  # Do not proceed if validation fails

                    # Validate the footprint before adding the area
                    if not validate_footprint(new_area_footprint):
                        st.error("Footprint is not valid.")
                        return  # Do not proceed if validation fails

                    # Check if the name is unique (case-insensitive)
                    if any(area['name'].lower() == new_area_name.lower() for area in json_data.get('areas', [])):
                        st.error(f"Area with name '{new_area_name}' already exists. Please choose a unique name.")
                        return  # Do not proceed if the name is not unique

                    new_area_resolution_value = calculate_resolution_deg(selected_zoom_level)

                    new_area = {
                        "name": new_area_name,
                        "Footprint": eval(new_area_footprint),
                        "record_id": new_area_record_id,
                        "resolutionDeg": new_area_resolution_value,
                        "zoomlevel": selected_zoom_level
                    }

                    json_data['areas'].append(new_area)
                    save_json_to_s3(json_data)

                    st.success(f"Area '{new_area_name}' added successfully!")
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON for Footprint: {str(e)}")

    elif option == "Upload JSON File":
        # File upload for adding new areas
        uploaded_file = st.file_uploader("Upload JSON File", type=["json"])

        if uploaded_file is not None:
            try:
                file_contents = uploaded_file.read()
                new_areas = json.loads(file_contents)["areas"]

                # Check for duplicates before adding new areas
                if "areas" not in json_data:
                    json_data["areas"] = []

                for new_area in new_areas:
                    # Check if the area already exists in json_data
                    if any(area['name'].lower() == new_area['name'].lower() for area in json_data.get('areas', [])):
                        st.warning(f"Duplicate area found: {new_area['name']}. It won't be added.")
                    else:
                        json_data["areas"].append(new_area)

                # Save updated json_data to S3
                save_json_to_s3(json_data)

                st.success("Areas from the uploaded file added successfully!")

            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON file: {str(e)}")

    # Display areas for deletion
    st.write("## Select Areas")

    # Checkbox to select areas for deletion
    selected_areas = {}
    for area in json_data['areas']:
        checkbox_key = f"chose_checkbox_{area['name']}"
        selected_areas[checkbox_key] = st.checkbox(f"{area['name']}", key=checkbox_key, value=False,)

    # Button to delete selected areas
    if st.button("Delete Selected Areas", type="primary"):
        areas_to_delete = []
        for checkbox_key, is_selected in selected_areas.items():
            if is_selected:
                area_name = checkbox_key.replace("chose_checkbox_", "")
                areas_to_delete.append(area_name)

        delete_area(areas_to_delete, json_data)

    # Button to export selected areas
    if st.button("Export Selected Areas", type="secondary"):
        areas_to_export = []
        export_list = []
        for checkbox_key, is_selected in selected_areas.items():
            if is_selected:
                area_name = checkbox_key.replace("chose_checkbox_", "")
                areas_to_export.append(area_name)
        for selected_export in json_data['areas']:
            if selected_export['name'] in areas_to_export:
                export_list.append(selected_export)
        export_to_send(export_list)
        st.success("Export areas")
        time.sleep(1)
        selected_areas.clear()
        streamlit_js_eval(js_expressions="parent.window.location.reload()")


if __name__ == "__main__":
    main()
