#!/usr/bin/with-contenv bashio
# ==============================================================================
# Configure NGINX for use with Meross Local Broker
# ==============================================================================
ingress_entry=$(bashio::addon.ingress_entry)
ingress_port=$(bashio::addon.ingress_port)
ingress_interface=$(bashio::addon.ip_address)

# Safe defaults
if [[ $ingress_interface = "" ]]; then
    ingress_interface="0.0.0.0"
fi

if [[ $ingress_port = "" ]]; then
    ingress_port="8099"
fi

if [[ $ingress_entry = "" ]]; then
    ingress_entry="/"
fi


bashio::log.info "Substituting ingress_entry with ${ingress_entry}"
sed -i "s#%%ingress_entry%%#${ingress_entry}#g" /etc/nginx/ingress.conf

bashio::log.info "Substituting interface with ${ingress_interface}"
sed -i "s/%%ingress_interface%%/${ingress_interface}/g" /etc/nginx/ingress.conf

bashio::log.info "Substituting port with ${ingress_port}"
sed -i "s/%%ingress_port%%/${ingress_port}/g" /etc/nginx/ingress.conf


# Prepare log dir
mkdir -p /var/log/nginx
chown nobody:nogroup /var/log/nginx
chmod 02755 /var/log/nginx