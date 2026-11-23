# Static site served by unprivileged nginx (runs as UID 101, listens on 8080).
FROM nginxinc/nginx-unprivileged:1.28.1-alpine

COPY nginx.conf /etc/nginx/nginx.conf
COPY index.html /usr/share/nginx/html/index.html

# Cloud Run sends traffic to $PORT (8080 by default).
EXPOSE 8080

USER 101

CMD ["nginx", "-g", "daemon off;"]
