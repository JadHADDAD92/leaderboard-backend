FROM postgres:13
COPY ./build/db_init-dev.sh /docker-entrypoint-initdb.d/db_init.sh
