-- Kestra keeps its own state (flows, executions, queue) in a separate database
-- on the same Postgres server, so it never mixes with the pipeline tables.
CREATE DATABASE kestra;
