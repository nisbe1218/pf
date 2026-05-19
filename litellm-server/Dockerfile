FROM python:3.11-slim

WORKDIR /app

# Install the LiteLLM proxy with server dependencies
RUN pip install --no-cache-dir 'litellm[proxy]'

EXPOSE 4000

# Run the official LiteLLM proxy server
CMD ["litellm", "--host", "0.0.0.0", "--port", "4000"]
