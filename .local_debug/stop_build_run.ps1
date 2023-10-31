$container_id=docker ps --filter name=meross_local_broker --format "{{.ID}}"
docker stop $container_id
& .local_debug\build_addon_locally.ps1
& .local_debug\run_addon_locally.ps1
