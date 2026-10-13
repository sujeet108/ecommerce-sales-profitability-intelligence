-- Run from psql, inside the project folder, AFTER schema.sql:
--   psql -U postgres -d ecommerce_bi -f sql/schema.sql
--   psql -U postgres -d ecommerce_bi -f sql/load_data_postgres.sql
-- (\copy reads files from YOUR machine; paths are relative to where you started psql)
\copy dim_customer  FROM 'data/processed/star/dim_customer.csv'  WITH (FORMAT csv, HEADER true)
\copy dim_product   FROM 'data/processed/star/dim_product.csv'   WITH (FORMAT csv, HEADER true)
\copy dim_geography FROM 'data/processed/star/dim_geography.csv' WITH (FORMAT csv, HEADER true)
\copy dim_date      FROM 'data/processed/star/dim_date.csv'      WITH (FORMAT csv, HEADER true)
\copy fact_sales    FROM 'data/processed/star/fact_sales.csv'    WITH (FORMAT csv, HEADER true)
