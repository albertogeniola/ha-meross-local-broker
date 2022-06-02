#!/usr/bin/with-contenv bashio
source /opt/utils/bashutils.sh
pushd /opt/custom_broker >/dev/null

DEBUG_MODE=$(get_option 'debug_mode' 'false')

# Start flask
bashio::log.info "Starting flask..."
if [[ $DEBUG_MODE == "true" ]]; then
  bashio::log.warning "Setting flask debug flags"
  export ENABLE_DEBUG=True
  debug_port=$(bashio::addon.port '10001')
  debug_port=${debug_port:-"10001"}
  export DEBUG_PORT=$debug_port
  exec python3 -m debugpy --listen 0.0.0.0:$DEBUG_PORT ./http_api.py
else
  bashio::log.info "Setting flask production flags"
  export ENABLE_DEBUG=False
  exec python3 ./http_api.py
fi
