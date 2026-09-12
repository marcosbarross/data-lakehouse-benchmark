"""Workload TPC-H focado em filtros seletivos e joins."""

QUERIES = {
    "Q3_partitioned_join": """
SELECT l.orderkey, sum(l.extendedprice * (1 - l.discount)) AS revenue
FROM {catalog}.{schema}.customer c
JOIN {catalog}.{schema}.orders o ON c.custkey = o.custkey
JOIN {catalog}.{schema}.lineitem l ON l.orderkey = o.orderkey
WHERE c.mktsegment = 'BUILDING'
  AND o.orderdate < DATE '1995-03-15'
  AND l.shipdate > DATE '1995-03-15'
GROUP BY l.orderkey ORDER BY revenue DESC LIMIT 10
""",
    "Q6_partitioned_filter": """
SELECT sum(extendedprice * discount) AS revenue
FROM {catalog}.{schema}.lineitem
WHERE shipdate >= DATE '1994-01-01' AND shipdate < DATE '1995-01-01'
  AND discount BETWEEN 0.05 AND 0.07 AND quantity < 24
""",
    "Q7_partitioned_join": """
SELECT extract(YEAR FROM l.shipdate) AS ship_year,
       sum(l.extendedprice * (1 - l.discount)) AS revenue
FROM {catalog}.{schema}.supplier s
JOIN {catalog}.{schema}.lineitem l ON s.suppkey = l.suppkey
JOIN {catalog}.{schema}.orders o ON l.orderkey = o.orderkey
JOIN {catalog}.{schema}.customer c ON o.custkey = c.custkey
JOIN {catalog}.{schema}.nation n1 ON s.nationkey = n1.nationkey
JOIN {catalog}.{schema}.nation n2 ON c.nationkey = n2.nationkey
WHERE ((n1.name = 'FRANCE' AND n2.name = 'GERMANY')
    OR (n1.name = 'GERMANY' AND n2.name = 'FRANCE'))
  AND l.shipdate BETWEEN DATE '1995-01-01' AND DATE '1996-12-31'
GROUP BY 1 ORDER BY 1
""",
    "Q19_unpartitioned_filter": """
SELECT sum(l.extendedprice * (1 - l.discount)) AS revenue
FROM {catalog}.{schema}.lineitem l
JOIN {catalog}.{schema}.part p ON p.partkey = l.partkey
WHERE p.brand IN ('Brand#12', 'Brand#23', 'Brand#34')
  AND p.container IN ('SM CASE', 'SM BOX', 'SM PACK', 'SM PKG')
  AND l.quantity BETWEEN 1 AND 11
  AND l.shipmode IN ('AIR', 'AIR REG') AND l.shipinstruct = 'DELIVER IN PERSON'
""",
}
