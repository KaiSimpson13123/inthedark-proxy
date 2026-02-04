#!/bin/sh
set -eu

squid -N -f /etc/squid/squid.conf &

exec python3 /app/tunnel_server.py