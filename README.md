# DMPy: IDEA-FAST Data Management Portal Python Client

This library provides a suite of utilities for managing data using the DMPy library, including user state display, file management, data management, and study field management. These functionalities are divided into various function definitions, each of which performs a specific task.

## Functions

### `state()`

This function displays the current user's information and the studies they can access. It establishes a connection with DMP and gather user information. The function prints the username, first and last name, email, account creation and expiration times, and studies the user can access.

### `list_files(study_id: str, participants: Optional[List[str]] = None, kinds: Optional[List[str]] = None, devices: Optional[List[str]] = None, file_ids: Optional[List[str]] = None)`

The function lists files in a given study. The function accepts several optional arguments for filtering, including `participants`, `kinds`, `devices`, and `file_ids`.

### `get_file_content(file_id: str, stream: bool = True)`

This function retrieves the content of a file given its ID.

### `archive_preview(file_id: str, file_name: str)`

This function prints the structure of a compressed archive file.

### `stream_text_from_archive(file_id, file_name)`

This function extracts and returns text data from a compressed archive file.

### `upload_data(study_id: str, file_name: str, file_content: bytes, participant_id: str, device_id: str, start_date: int, end_date: int)`

This function uploads data to a specified study.

### `get_study_fields(study_id: str)`

This function retrieves fields related to a specific study.

### `create_new_field(study_id: str, field_id: str, field_name: str, data_type: str, possible_values: List = None, unit: str = None, comments: str = None)`

This function creates a new field in the data management system.

`get_data_records(study_id: str, field_ids: List[str] = None, data_format: str = None, version_id: str = '0')`

This function retrieves clinical data records from a specified study given a list of fields ids

### `upload_data_in_array(study_id: str, data: List[dict])`

This function uploads a list of data to a specified study
