FROM nginx:1.10.1-alpine

COPY index.html /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 8080

RUN apk add --no-cache bash

#CMD ["nginx","-g", "daemon off;", "preview" ,"--host","0.0.0.0", "--port 8080"]
CMD ["nginx", "-g", "daemon off;"]