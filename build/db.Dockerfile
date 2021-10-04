FROM postgres:14
COPY ./build/db_init.sh /docker-entrypoint-initdb.d/
