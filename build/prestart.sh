#! /usr/bin/env bash

# Let the DB start
sleep 10;
# Run migrations
cd app
alembic upgrade head
cd ..