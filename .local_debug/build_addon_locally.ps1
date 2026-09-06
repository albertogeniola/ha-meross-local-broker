# Note: on windows + WSL, in case of port binding issues,
# you might need to run "net stop nat" and "net start nat" within
# a prompt with admin rights.
docker build --build-arg BUILD_ARCH="amd64" --build-arg BUILD_FROM="ghcr.io/home-assistant/amd64-base-debian:bookworm" -t local/meross_local_broker "meross_local_broker"
