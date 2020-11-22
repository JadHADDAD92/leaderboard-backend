#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER leaderboard;
    CREATE DATABASE treederboards;
    CREATE DATABASE testtreederboards;
    GRANT ALL PRIVILEGES ON DATABASE treederboards TO leaderboard;
    GRANT ALL PRIVILEGES ON DATABASE testtreederboards TO leaderboard;
EOSQL
psql -d treederboards -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'
psql -d testtreederboards -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'
