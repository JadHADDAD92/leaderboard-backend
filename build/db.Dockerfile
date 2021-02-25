FROM postgres:13
COPY ./build/db_init.sh /docker-entrypoint-initdb.d/
