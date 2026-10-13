# Loading the data into Power BI (Power Query)

1. Home > **Transform data** > Home > **Manage Parameters** > New. Name `DataFolder`, type Text, value e.g. `C:\Projects\ecommerce-sales-profitability-intelligence\data\processed\star\` (keep the trailing backslash).
2. For each of the five files create a Blank Query (Advanced Editor) with the code below, changing only the file name and column list.
3. Close & Apply. Then build the relationships from `dax_measures.md`.

Always pass the culture `"en-US"` so decimal points parse correctly on machines with other regional settings, and keep `postal_code` as **text**.

```m
// fact_sales
let
    Source   = Csv.Document(File.Contents(DataFolder & "fact_sales.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"row_id", Int64.Type}, {"order_id", type text}, {"order_date_key", Int64.Type}, {"ship_date_key", Int64.Type},
        {"ship_mode", type text}, {"ship_days", Int64.Type}, {"customer_key", Int64.Type}, {"product_key", Int64.Type},
        {"geography_key", Int64.Type}, {"sales", type number}, {"quantity", Int64.Type}, {"discount", type number},
        {"profit", type number}, {"is_return", Int64.Type}, {"is_price_outlier", Int64.Type}, {"ship_date_invalid", Int64.Type}}, "en-US")
in
    Typed
```
```m
// dim_geography  (postal_code must stay text)
let
    Source   = Csv.Document(File.Contents(DataFolder & "dim_geography.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {{"geography_key", Int64.Type}, {"country", type text}, {"state", type text},
                                                    {"region", type text}, {"city", type text}, {"postal_code", type text}}, "en-US")
in
    Typed
```
```m
// dim_date
let
    Source   = Csv.Document(File.Contents(DataFolder & "dim_date.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {{"date_key", Int64.Type}, {"full_date", type date}, {"year", Int64.Type},
        {"quarter", Int64.Type}, {"month_num", Int64.Type}, {"month_name", type text}, {"year_month", type text},
        {"day_name", type text}, {"is_weekend", Int64.Type}}, "en-US")
in
    Typed
```
`dim_customer` (`customer_key` Int64; `customer_id`, `customer_name`, `segment` text) and `dim_product` (`product_key` Int64; `product_id`, `product_name`, `category`, `sub_category` text) follow the same pattern.

**Alternative:** connect to PostgreSQL (Get data > PostgreSQL database) and import the five tables; if the connector asks for Npgsql, install it, or use the CSV route above.

**Check after loading:** row counts must be fact 8,679 · customers 754 · products 174 · geographies 72 · dates 1,826.
