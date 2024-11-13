FROM nginx:latest

RUN addgroup --system --gid 3000  g_app
RUN adduser --system  --no-create-home --uid 3000 --gid 3000 --disabled-password --disabled-login  u_app

RUN rm -rf /etc/nginx/conf.d/default.conf
COPY conf.nginx /etc/nginx/conf.d/app.conf