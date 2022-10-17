FROM postgres:15
COPY ./build/db_init.sh /docker-entrypoint-initdb.d/
