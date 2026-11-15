-- Warehouse initialisation: schemas, roles, least-privilege grants.
-- Run by docker/postgres/init/01_init_warehouse.sh with psql variables:
--   :dbname  :airbyte_user/:airbyte_password  :dbt_user/:dbt_password  :streamlit_user/:streamlit_password
-- The script is idempotent, so it can also be re-run by hand as the admin user:
--   docker compose exec -T warehouse-postgres sh /docker-entrypoint-initdb.d/01_init_warehouse.sh
--
-- Layers and owners
--   raw        written by Airbyte        (owner: airbyte role)
--   staging    built by dbt              (owner: dbt role)
--   analytics  built by dbt, read by app (owner: dbt role)

-- 1. Roles (login, no superuser, no create-db, no create-role) ----------------
SELECT format('CREATE ROLE %I LOGIN', :'airbyte_user')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'airbyte_user') \gexec
SELECT format('CREATE ROLE %I LOGIN', :'dbt_user')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'dbt_user') \gexec
SELECT format('CREATE ROLE %I LOGIN', :'streamlit_user')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'streamlit_user') \gexec

SELECT format('ALTER ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'airbyte_user', :'airbyte_password') \gexec
SELECT format('ALTER ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'dbt_user', :'dbt_password') \gexec
SELECT format('ALTER ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'streamlit_user', :'streamlit_password') \gexec

-- The dashboard role can never write, even if a grant is added by mistake.
SELECT format('ALTER ROLE %I SET default_transaction_read_only = on', :'streamlit_user') \gexec

-- 2. Database access: connect only, nothing inherited from PUBLIC ------------
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', :'dbname') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I, %I, %I', :'dbname', :'airbyte_user', :'dbt_user', :'streamlit_user') \gexec
SELECT format('GRANT TEMPORARY ON DATABASE %I TO %I', :'dbname', :'airbyte_user') \gexec

-- The default public schema is not used by the pipeline.
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- 3. Schemas -------------------------------------------------------------------
SELECT format('CREATE SCHEMA IF NOT EXISTS raw AUTHORIZATION %I', :'airbyte_user') \gexec
SELECT format('CREATE SCHEMA IF NOT EXISTS staging AUTHORIZATION %I', :'dbt_user') \gexec
SELECT format('CREATE SCHEMA IF NOT EXISTS analytics AUTHORIZATION %I', :'dbt_user') \gexec

-- Make ownership correct even when the schemas already existed.
SELECT format('ALTER SCHEMA raw OWNER TO %I', :'airbyte_user') \gexec
SELECT format('ALTER SCHEMA staging OWNER TO %I', :'dbt_user') \gexec
SELECT format('ALTER SCHEMA analytics OWNER TO %I', :'dbt_user') \gexec

REVOKE ALL ON SCHEMA raw, staging, analytics FROM PUBLIC;

-- 4. raw: Airbyte writes, dbt reads --------------------------------------------
SELECT format('GRANT USAGE ON SCHEMA raw TO %I', :'dbt_user') \gexec
SELECT format('GRANT SELECT ON ALL TABLES IN SCHEMA raw TO %I', :'dbt_user') \gexec
SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA raw GRANT SELECT ON TABLES TO %I',
              :'airbyte_user', :'dbt_user') \gexec

-- 5. analytics: dbt writes, the dashboard reads ---------------------------------
SELECT format('GRANT USAGE ON SCHEMA analytics TO %I', :'streamlit_user') \gexec
SELECT format('GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO %I', :'streamlit_user') \gexec
SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA analytics GRANT SELECT ON TABLES TO %I',
              :'dbt_user', :'streamlit_user') \gexec

-- 6. Search paths (explicit schema names are still preferred in SQL) -------------
SELECT format('ALTER ROLE %I SET search_path = raw', :'airbyte_user') \gexec
SELECT format('ALTER ROLE %I SET search_path = staging, analytics', :'dbt_user') \gexec
SELECT format('ALTER ROLE %I SET search_path = analytics', :'streamlit_user') \gexec
