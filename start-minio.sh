# Use this script to start a docker container for a local development minio deployment

# TO RUN ON WINDOWS:
# 1. Install WSL (Windows Subsystem for Linux) - https://learn.microsoft.com/en-us/windows/wsl/install
# 2. Install Docker Desktop for Windows - https://docs.docker.com/docker-for-windows/install/
# 3. Open WSL - `wsl`
# 4. Run this script - `./start-minio.sh`

# On Linux and macOS you can run this script directly - `./start-minio.sh`

CONTAINER_NAME="fe-questions-minio"

if ! [ -x "$(command -v docker)" ]; then
  echo -e "Docker is not installed. Please install docker and try again.\nDocker install guide: https://docs.docker.com/engine/install/"
  exit 1
fi

if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
  echo "MinIO container '$CONTAINER_NAME' already running"
  exit 0
fi

if [ "$(docker ps -q -a -f name=$CONTAINER_NAME)" ]; then
  docker start "$CONTAINER_NAME"
  echo "Existing MinIO container '$CONTAINER_NAME' started"
  exit 0
fi

# import env variables from .env
set -a
source .env

# Run a containerized MinIO deployment with the user credentials
docker run -p 9000:9000 -p 9001:9001 \
  --name $CONTAINER_NAME \
  -e MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY \
  -e MINIO_SECRET_KEY=$MINIO_SECRET_KEY \
  quay.io/minio/minio server /data --console-address ":9001"
