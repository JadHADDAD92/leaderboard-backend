FROM postgres:11
COPY ./build/db_init.sh /docker-entrypoint-initdb.d/
