FROM php:8.3-apache-bookworm
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends mariadb-server mariadb-client unzip \
 && docker-php-ext-install pdo_mysql \
 && rm -rf /var/lib/apt/lists/* \
 && printf '[mysqld]\ninnodb_buffer_pool_size=48M\nmax_connections=25\nperformance_schema=OFF\n' >/etc/mysql/mariadb.conf.d/99-render-memory.cnf
COPY Student_Result_Management_System.zip /tmp/srms.zip
RUN unzip -q /tmp/srms.zip -d /tmp/project \
 && cp /tmp/project/Student_Result_Management_System/index.php /var/www/html/index.php \
 && cp -R /tmp/project/Student_Result_Management_System/assets /var/www/html/assets \
 && cp /tmp/project/Student_Result_Management_System/docker-entrypoint.sh /usr/local/bin/launch-app \
 && chmod +x /usr/local/bin/launch-app \
 && chown -R www-data:www-data /var/www/html \
 && rm -rf /tmp/project /tmp/srms.zip
ENV PORT=10000 DB_NAME=iu_result_portal DB_USER=resultapp DB_HOST=127.0.0.1 DB_PORT=3306 SEED_DEMO=1 DB_PASSWORD=LocalDemoDbOnly
EXPOSE 10000
CMD ["/usr/local/bin/launch-app"]
