# from dmpy import upload_data

# study_id = "8f223906-809c-41aa-8e58-3d4ee1f694b1"  # IDEA_Test
# file_name = "NRSJFKJ-VTPZTXXHZ-20230522-20230522.txt"
# file_path = file_name
# with open(file_path, 'rb') as file:
#     file_bytes = file.read()  # Read the entire file content into bytes
    
# participant_id = 'I7N3G6G'
# device_id = 'MMM7N3G6G'
# start_date = 1593817200000
# end_date = 1615852800000
# # Test the upload function
# uploaded_file_id = upload_data(study_id, file_name, file_bytes, participant_id, device_id, start_date, end_date)

from dmpy import upload_data
import time
 
# file name and path to upload. 
study_id = "8f223906-809c-41aa-8e58-3d4ee1f694b1"  # IDEA_Test
file_name = "NRSJFKJ-VTPZTXXHZ-20230522-20230522.txt"
participant_id = "NRSJFKG"
device_id = "VTPZTXXHZ"
# Use UNIX timestamp format for dates
start_date = int(time.mktime(time.strptime("2024-01-26", "%Y-%m-%d"))) * 1000
end_date = int(time.mktime(time.strptime("2024-01-27", "%Y-%m-%d"))) * 1000
 
# test the upload and log 
# Path to the file you want to upload
file_path = file_name
 
# Read the file content in binary mode
with open(file_path, 'rb') as file:
    file_content = file.read()
    print(file_content)

print(study_id, file_name, participant_id, device_id, start_date, end_date)
# Test the upload function
uploaded_file_id = upload_data(study_id, file_name, file_content, participant_id, device_id, start_date, end_date)
