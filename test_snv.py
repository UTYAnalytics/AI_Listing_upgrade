import os

# Accessing the environment variable
my_env_var = os.getenv('MY_GITHUB_TOKEN')
my_secret = os.getenv('MY_GITHUB_TOKEN')

# Print the environment variables (for demonstration purposes)
print(f"MY_ENV_VAR: {my_env_var}")
print(f"MY_SECRET: {my_secret}")

# Use the environment variables in your application logic
# ...
