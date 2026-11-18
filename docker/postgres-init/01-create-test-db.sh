#!/bin/sh
# Runs once, when the Postgres volume is first created.
# Creates a separate database for the automated tests so they never touch dev data.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
  CREATE DATABASE ${POSTGRES_DB}_test OWNER "$POSTGRES_USER";
SQL
