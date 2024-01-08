# app.py (Streamlit application with centered layout)
import geojson
import boto3
import streamlit as st
import folium
from streamlit_folium import folium_static
import json
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
    except Exception as e:
        st.error(f"Error saving JSON to S3: {str(e)}")
        raise e


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
                    if new_area not in json_data["areas"]:
                        json_data["areas"].append(new_area)
                    else:
                        st.warning(f"Duplicate area found: {new_area['name']}. It won't be added.")

                # Save updated json_data to S3
                save_json_to_s3(json_data)

                st.success("Areas from the uploaded file added successfully!")

            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON file: {str(e)}")

    # Display areas for deletion
    st.write("## Delete Area")
    for area in json_data.get('areas', []):
        if st.button(f"Delete {area['name']}"):
            # Confirmation dialog
            confirmation = st.warning(f"Are you sure you want to delete {area['name']}?")

            col1, col2 = st.beta_columns(2)

            if col1.button("Yes", key=f"delete_{area['name']}"):
                json_data['areas'].remove(area)
                save_json_to_s3(json_data)
                confirmation.empty()  # Clear the confirmation message
                col1.success(f"Area '{area['name']}' deleted successfully!")

            if col2.button("No", key=f"cancel_{area['name']}"):
                confirmation.empty()  # Clear the confirmation message
                col2.info(f"Deletion of '{area['name']}' canceled.")


if __name__ == "__main__":
    main()
