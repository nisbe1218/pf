#!/bin/bash
# Update docker-compose.yml to add shared preprocess volume

cd /c/Users/PC\ DELL/pf

# Add preprocess_tmp volume to backend volumes
sed -i '/backend:/,/ports:/{
  /volumes:/,/ports:/ {
    /- \.\/backend:\/app/a\      - preprocess_tmp:/tmp/preprocess
  }
}' docker-compose.yml

# Add preprocess_tmp volume to celery-worker volumes
sed -i '/celery-worker:/,/environment:/{
  /volumes:/,/environment:/ {
    /- \.\/backend:\/app/a\      - preprocess_tmp:/tmp/preprocess
  }
}' docker-compose.yml

# Add preprocess_tmp to volumes section
sed -i '/^volumes:/,/^[^ ]/  {
  /redis_data:/a\  preprocess_tmp:
}' docker-compose.yml

echo "✅ Updated docker-compose.yml with shared preprocess volume"
