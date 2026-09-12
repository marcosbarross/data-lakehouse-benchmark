-- Template documental. O setup executável é benchmark.phase2_optimization.setup.
--
-- Iceberg: particionamento oculto por transformação, consumido por filtros em shipdate.
CREATE TABLE iceberg.{optimized_schema}.lineitem
WITH (partitioning = ARRAY['month(shipdate)']) AS
SELECT * FROM {source_catalog}.{source_schema}.lineitem;

CREATE TABLE iceberg.{optimized_schema}.customer
WITH (partitioning = ARRAY['mktsegment']) AS
SELECT * FROM {source_catalog}.{source_schema}.customer;

-- Delta no Trino aceita apenas particionamento por coluna; Z-Order não é sintaxe do Trino 483.
-- Execute no mecanismo Delta escolhido (Spark/Databricks) após a carga, se disponível:
-- OPTIMIZE delta.`s3a://warehouse/benchmark_phase2_delta/optimized/lineitem`
-- ZORDER BY (shipdate);
