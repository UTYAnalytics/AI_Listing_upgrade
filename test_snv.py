# import os

# # Accessing the environment variable
# my_github_token = os.getenv('MY_GITHUB_TOKEN')

# # Print the environment variable (for demonstration purposes)
# print(f"MY_GITHUB_TOKEN: {my_github_token}")

# # Use the environment variable in your application logic
# # ...

from config import (
    config,
    format_header,
    get_newest_file,
    trigger_github_workflow,
    check_workflow_status,
)
# workflow_status = check_workflow_status('9414807187')
# status = workflow_status.get("status")
# conclusion = workflow_status.get("conclusion")
# print(conclusion)

workflow_response = trigger_github_workflow(
                                'B0D2DJBHCR'
                            )
# run_id = workflow_response.get("id")

print(workflow_response)