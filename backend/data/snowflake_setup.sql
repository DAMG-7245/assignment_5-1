USE ROLE ACCOUNTADMIN;

-- ----------------------------------------------------------------------------
-- Step #1: Create and assign role for LANG Project
-- ----------------------------------------------------------------------------
SET MY_USER = CURRENT_USER();
CREATE OR REPLACE ROLE LANG_ROLE;
GRANT ROLE LANG_ROLE TO ROLE SYSADMIN;
GRANT ROLE LANG_ROLE TO USER IDENTIFIER($MY_USER);
GRANT EXECUTE TASK ON ACCOUNT TO ROLE LANG_ROLE;
GRANT MONITOR EXECUTION ON ACCOUNT TO ROLE LANG_ROLE;
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE LANG_ROLE;

-- ----------------------------------------------------------------------------
-- Step #2: Create Database and Warehouse for LANG Project
-- ----------------------------------------------------------------------------
CREATE OR REPLACE DATABASE LANG_DB;
GRANT OWNERSHIP ON DATABASE LANG_DB TO ROLE LANG_ROLE;

CREATE OR REPLACE WAREHOUSE LANG_WH 
    WAREHOUSE_SIZE = XSMALL 
    AUTO_SUSPEND = 300 
    AUTO_RESUME = TRUE;
GRANT OWNERSHIP ON WAREHOUSE LANG_WH TO ROLE LANG_ROLE;

USE ROLE LANG_ROLE;
USE WAREHOUSE LANG_WH;
USE DATABASE LANG_DB;
 
-- Schemas
CREATE OR REPLACE SCHEMA EXTERNAL;
CREATE OR REPLACE SCHEMA RAW;




