FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y python3 python3-pip squid && \
    rm -rf /var/lib/apt/lists/*

COPY squid.conf /etc/squid/squid.conf
COPY tunnel_server.py /app/tunnel_server.py
COPY start.sh /app/start.sh

RUN pip3 install --no-cache-dir websockets && \
    chmod +x /app/start.sh

EXPOSE 3128
EXPOSE 8080
CMD ["/app/start.sh"]
