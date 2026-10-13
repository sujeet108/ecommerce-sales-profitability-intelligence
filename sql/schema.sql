-- =====================================================================
-- Star schema for the E-commerce Sales & Profitability project
-- Grain of fact_sales: one order line.
-- Written in standard SQL so it runs on PostgreSQL 14+ AND SQLite
-- (this repo's automated tests run it on SQLite; see docs/methodology.md).
-- =====================================================================
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_geography;
DROP TABLE IF EXISTS dim_date;

CREATE TABLE dim_customer (
    customer_key   INTEGER      PRIMARY KEY,
    customer_id    VARCHAR(20)  NOT NULL UNIQUE,
    customer_name  VARCHAR(100) NOT NULL,
    segment        VARCHAR(20)  NOT NULL CHECK (segment IN ('Consumer','Corporate','Home Office'))
);

CREATE TABLE dim_product (
    product_key    INTEGER      PRIMARY KEY,
    product_id     VARCHAR(20)  NOT NULL UNIQUE,
    product_name   VARCHAR(150) NOT NULL,
    category       VARCHAR(30)  NOT NULL,
    sub_category   VARCHAR(30)  NOT NULL
);

CREATE TABLE dim_geography (
    geography_key  INTEGER      PRIMARY KEY,
    country        VARCHAR(30)  NOT NULL,
    state          VARCHAR(40)  NOT NULL,
    region         VARCHAR(20)  NOT NULL CHECK (region IN ('West','East','Central','South')),
    city           VARCHAR(60)  NOT NULL,
    postal_code    VARCHAR(10)  NOT NULL,          -- text: keeps leading zeros; 'Unknown' when missing
    UNIQUE (country, state, city, postal_code)
);

CREATE TABLE dim_date (
    date_key       INTEGER      PRIMARY KEY,       -- YYYYMMDD
    full_date      DATE         NOT NULL UNIQUE,
    year           SMALLINT     NOT NULL,
    quarter        SMALLINT     NOT NULL,
    month_num      SMALLINT     NOT NULL,
    month_name     VARCHAR(10)  NOT NULL,
    year_month     CHAR(7)      NOT NULL,          -- 'YYYY-MM', sorts correctly as text
    day_name       VARCHAR(10)  NOT NULL,
    is_weekend     SMALLINT     NOT NULL
);

CREATE TABLE fact_sales (
    row_id            INTEGER       PRIMARY KEY,
    order_id          VARCHAR(20)   NOT NULL,       -- NOT unique: one order has many lines
    order_date_key    INTEGER       NOT NULL REFERENCES dim_date (date_key),
    ship_date_key     INTEGER       NULL     REFERENCES dim_date (date_key),   -- NULL when the source date was invalid
    ship_mode         VARCHAR(20)   NOT NULL,
    ship_days         INTEGER       NULL,
    customer_key      INTEGER       NOT NULL REFERENCES dim_customer (customer_key),
    product_key       INTEGER       NOT NULL REFERENCES dim_product (product_key),
    geography_key     INTEGER       NOT NULL REFERENCES dim_geography (geography_key),
    sales             NUMERIC(12,2) NOT NULL,       -- net of discount; negative on returns
    quantity          INTEGER       NOT NULL,       -- negative on returns
    discount          NUMERIC(4,2)  NOT NULL CHECK (discount >= 0 AND discount <= 1),
    profit            NUMERIC(12,2) NOT NULL,
    is_return         SMALLINT      NOT NULL DEFAULT 0,
    is_price_outlier  SMALLINT      NOT NULL DEFAULT 0,
    ship_date_invalid SMALLINT      NOT NULL DEFAULT 0
);

CREATE INDEX ix_fact_order_id   ON fact_sales (order_id);
CREATE INDEX ix_fact_order_date ON fact_sales (order_date_key);
CREATE INDEX ix_fact_customer   ON fact_sales (customer_key);
CREATE INDEX ix_fact_product    ON fact_sales (product_key);
CREATE INDEX ix_fact_geography  ON fact_sales (geography_key);
