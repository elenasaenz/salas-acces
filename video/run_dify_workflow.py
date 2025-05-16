#!/usr/bin/env python3
import requests
import json
import os
import sys

# Constants
API_KEY = "xxx"
BASE_URL = "http://localhost:8080/v1"  # Updated URL as per specifications
IMAGE_PATH = "/home/elena.saenz/langchain_env/rrs_llm/img/img2.png"
USER_ID = "python-script-user"  # A unique identifier for the user

# Headers for authentication
headers = {
    "Authorization": f"Bearer {API_KEY}"
}

def upload_file(file_path, user_id):
    """
    Upload a file to the Dify API
    
    Args:
        file_path (str): Path to the file to upload
        user_id (str): User identifier
        
    Returns:
        dict: File information including the file ID
    """
    upload_url = f"{BASE_URL}/files/upload"
    
    # Get file mime type based on extension
    file_extension = os.path.splitext(file_path)[1].lower()
    mime_type_map = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.webp': 'image/webp',
        '.gif': 'image/gif'
    }
    mime_type = mime_type_map.get(file_extension, 'application/octet-stream')
    
    with open(file_path, 'rb') as file:
        files = {'file': (os.path.basename(file_path), file, mime_type)}
        data = {'user': user_id}
        
        response = requests.post(
            upload_url,
            headers=headers,
            files=files,
            data=data
        )
        
        # Handle different error codes as per specifications
        print(response.status_code)
        if response.status_code != 201:
            error_message = f"Error uploading file: {response.text}"
            
            if response.status_code == 400:
                if "no_file_uploaded" in response.text:
                    error_message = "Error: A file must be provided."
                elif "too_many_files" in response.text:
                    error_message = "Error: Currently only one file is accepted."
                elif "unsupported_preview" in response.text:
                    error_message = "Error: The file does not support preview."
                elif "unsupported_estimate" in response.text:
                    error_message = "Error: The file does not support estimation."
            elif response.status_code == 413:
                error_message = "Error: The file is too large."
            elif response.status_code == 415:
                error_message = "Error: Unsupported file type. Currently only document files are accepted."
            elif response.status_code == 503:
                if "s3_connection_failed" in response.text:
                    error_message = "Error: Unable to connect to S3 service."
                elif "s3_permission_denied" in response.text:
                    error_message = "Error: No permission to upload files to S3."
                elif "s3_file_too_large" in response.text:
                    error_message = "Error: File exceeds S3 size limit."
            elif response.status_code == 500:
                error_message = "Error: Internal server error."
                
            print(error_message)
            sys.exit(1)
        
        # Parse and validate response according to specifications
        response_data = response.json()
        expected_fields = ["id", "name", "size", "extension", "mime_type", "created_by", "created_at"]
        
        for field in expected_fields:
            if field not in response_data:
                print(f"Warning: Expected field '{field}' missing from response")
        
        return response_data

def run_workflow(file_info, user_id, response_mode="blocking"):
    """
    Execute the workflow with the uploaded file
    
    Args:
        file_info (dict): File information from the upload response
        user_id (str): User identifier
        response_mode (str): Response mode (streaming or blocking)
        
    Returns:
        requests.Response: Response from the workflow API
    """
    workflow_url = f"{BASE_URL}/workflows/run"
    
    # Determine file type from mime_type or extension
    file_type = "UNKNOWN"
    if "mime_type" in file_info:
        mime_to_type = {
            "image/png": "PNG",
            "image/jpeg": "JPEG",
            "image/webp": "WEBP",
            "image/gif": "GIF"
        }
        file_type = mime_to_type.get(file_info["mime_type"], "UNKNOWN")
    elif "extension" in file_info:
        ext_to_type = {
            "png": "PNG",
            "jpg": "JPEG",
            "jpeg": "JPEG",
            "webp": "WEBP",
            "gif": "GIF"
        }
        file_type = ext_to_type.get(file_info["extension"].lower(), "UNKNOWN")
    
    # Prepare the inputs with the file ID
    payload = {
        "inputs": {
            "image": [
                {
                    "transfer_method": "local_file",
                    "upload_file_id": file_info["id"],
                    "type": "image"
                }
            ]
        },
        "response_mode": response_mode,
        "user": user_id
    }
    
    response = requests.post(
        workflow_url,
        headers={**headers, "Content-Type": "application/json"},
        json=payload
    )
    
    if response.status_code != 200:
        print(f"Error running workflow: {response.text}")
        sys.exit(1)
        
    return response

def handle_streaming_response(response):
    """
    Handle a streaming response from the workflow API
    
    Args:
        response (requests.Response): Response from the workflow API
    """
    print("Streaming response:")
    for line in response.iter_lines():
        if line:
            try:
                # SSE format typically has "data: " prefix
                if line.startswith(b'data: '):
                    data = json.loads(line[6:])
                    print(data.get('text', ''), end='', flush=True)
            except json.JSONDecodeError:
                print(f"Error parsing SSE data: {line}")
    print()  # Add a newline at the end

def handle_blocking_response(response):
    """
    Handle a blocking response from the workflow API
    
    Args:
        response (requests.Response): Response from the workflow API
    """
    result = response.json()
    print("Workflow result:")
    print(json.dumps(result, indent=2))

def main():
    # Check if the image file exists
    if not os.path.exists(IMAGE_PATH):
        print(f"Error: Image file '{IMAGE_PATH}' not found.")
        sys.exit(1)
    
    print(f"Uploading image: {IMAGE_PATH}")
    file_info = upload_file(IMAGE_PATH, USER_ID)
    print(f"File uploaded successfully:")
    print(f"  ID: {file_info.get('id')}")
    print(f"  Name: {file_info.get('name')}")
    print(f"  Size: {file_info.get('size')} bytes")
    print(f"  Extension: {file_info.get('extension')}")
    print(f"  MIME Type: {file_info.get('mime_type')}")
    print(f"  Created By: {file_info.get('created_by')}")
    print(f"  Created At: {file_info.get('created_at')}")
    
    # Ask user for response mode
    while True:
        mode = input("Choose response mode (streaming/blocking) [blocking]: ").lower() or "blocking"
        if mode in ["streaming", "blocking"]:
            break
        print("Invalid mode. Please choose 'streaming' or 'blocking'.")
    
    print(f"Executing workflow with {mode} response mode...")
    response = run_workflow(file_info, USER_ID, mode)
    
    # Handle the response based on the response_mode
    if mode == "streaming":
        handle_streaming_response(response)
    else:
        handle_blocking_response(response)

if __name__ == "__main__":
    main()
