#!/usr/bin/env bash
set -euo pipefail

squid -N -f /etc/squid/squid.conf &

exec python3 /app/tunnel_server.py
