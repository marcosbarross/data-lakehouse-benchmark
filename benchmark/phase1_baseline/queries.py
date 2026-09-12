"""Definições completas das 22 consultas canônicas do TPC-H (Q1 a Q22)."""
from __future__ import annotations

TABLES: list[str] = [
    "region",
    "nation",
    "supplier",
    "part",
    "partsupp",
    "customer",
    "orders",
    "lineitem",
]

TPCH_QUERIES: dict[str, str] = {
    "Q1": """
    SELECT
      l.returnflag,
      l.linestatus,
      sum(l.quantity)                                       AS sum_qty,
      sum(l.extendedprice)                                  AS sum_base_price,
      sum(l.extendedprice * (1 - l.discount))               AS sum_disc_price,
      sum(l.extendedprice * (1 - l.discount) * (1 + l.tax)) AS sum_charge,
      avg(l.quantity)                                       AS avg_qty,
      avg(l.extendedprice)                                  AS avg_price,
      avg(l.discount)                                       AS avg_disc,
      count(*)                                              AS count_order
    FROM
      {catalog}.{schema}.lineitem AS l
    WHERE
      l.shipdate <= DATE '1998-12-01' - INTERVAL '90' DAY
    GROUP BY
      l.returnflag,
      l.linestatus
    ORDER BY
      l.returnflag,
      l.linestatus
    """,
    "Q2": """
    SELECT
      s.acctbal,
      s.name,
      n.name,
      p.partkey,
      p.mfgr,
      s.address,
      s.phone,
      s.comment
    FROM
      {catalog}.{schema}.part p,
      {catalog}.{schema}.supplier s,
      {catalog}.{schema}.partsupp ps,
      {catalog}.{schema}.nation n,
      {catalog}.{schema}.region r
    WHERE
      p.partkey = ps.partkey
      AND s.suppkey = ps.suppkey
      AND p.size = 15
      AND p.type like '%BRASS'
      AND s.nationkey = n.nationkey
      AND n.regionkey = r.regionkey
      AND r.name = 'EUROPE'
      AND ps.supplycost = (
        SELECT
          min(ps.supplycost)
        FROM
          {catalog}.{schema}.partsupp ps,
          {catalog}.{schema}.supplier s,
          {catalog}.{schema}.nation n,
          {catalog}.{schema}.region r
        WHERE
          p.partkey = ps.partkey
          AND s.suppkey = ps.suppkey
          AND s.nationkey = n.nationkey
          AND n.regionkey = r.regionkey
          AND r.name = 'EUROPE'
      )
    ORDER BY
      s.acctbal desc,
      n.name,
      s.name,
      p.partkey
    LIMIT 100
    """,
    "Q3": """
    SELECT
      l.orderkey,
      sum(l.extendedprice * (1 - l.discount)) AS revenue,
      o.orderdate,
      o.shippriority
    FROM
      {catalog}.{schema}.customer AS c,
      {catalog}.{schema}.orders AS o,
      {catalog}.{schema}.lineitem AS l
    WHERE
      c.mktsegment = 'BUILDING'
      AND c.custkey = o.custkey
      AND l.orderkey = o.orderkey
      AND o.orderdate < DATE '1995-03-15'
      AND l.shipdate > DATE '1995-03-15'
    GROUP BY
      l.orderkey,
      o.orderdate,
      o.shippriority
    ORDER BY
      revenue DESC,
      o.orderdate
    LIMIT 10
    """,
    "Q4": """
    SELECT 
      o.orderpriority, 
      count(*) AS order_count 
    FROM 
      {catalog}.{schema}.orders o
    WHERE  
      o.orderdate >= DATE '1993-07-01'
      AND o.orderdate < DATE '1993-07-01' + INTERVAL '3' MONTH
      AND EXISTS (
        SELECT 
          * 
        FROM 
          {catalog}.{schema}.lineitem l
        WHERE 
          l.orderkey = o.orderkey 
          AND l.commitdate < l.receiptdate
      )
    GROUP BY 
      o.orderpriority
    ORDER BY 
      o.orderpriority
    """,
    "Q5": """
    SELECT
      n.name,
      sum(l.extendedprice * (1 - l.discount)) AS revenue
    FROM
      {catalog}.{schema}.customer AS c,
      {catalog}.{schema}.orders AS o,
      {catalog}.{schema}.lineitem AS l,
      {catalog}.{schema}.supplier AS s,
      {catalog}.{schema}.nation AS n,
      {catalog}.{schema}.region AS r
    WHERE
      c.custkey = o.custkey
      AND l.orderkey = o.orderkey
      AND l.suppkey = s.suppkey
      AND c.nationkey = s.nationkey
      AND s.nationkey = n.nationkey
      AND n.regionkey = r.regionkey
      AND r.name = 'ASIA'
      AND o.orderdate >= DATE '1994-01-01'
      AND o.orderdate < DATE '1994-01-01' + INTERVAL '1' YEAR
    GROUP BY
      n.name
    ORDER BY
      revenue DESC
    """,
    "Q6": """
    SELECT 
      sum(l.extendedprice*l.discount) AS revenue
    FROM 
      {catalog}.{schema}.lineitem l
    WHERE 
      l.shipdate >= DATE '1994-01-01'
      AND l.shipdate < DATE '1994-01-01' + INTERVAL '1' YEAR
      AND l.discount BETWEEN .06 - 0.01 AND .06 + 0.01
      AND l.quantity < 24
    """,
    "Q7": """
    SELECT
      supp_nation,
      cust_nation,
      l_year,
      sum(volume) AS revenue
    FROM (
           SELECT
             n1.name                          AS supp_nation,
             n2.name                          AS cust_nation,
             extract(YEAR FROM l.shipdate)      AS l_year,
             l.extendedprice * (1 - l.discount) AS volume
           FROM
             {catalog}.{schema}.supplier AS s,
             {catalog}.{schema}.lineitem AS l,
             {catalog}.{schema}.orders AS o,
             {catalog}.{schema}.customer AS c,
             {catalog}.{schema}.nation AS n1,
             {catalog}.{schema}.nation AS n2
           WHERE
             s.suppkey = l.suppkey
             AND o.orderkey = l.orderkey
             AND c.custkey = o.custkey
             AND s.nationkey = n1.nationkey
             AND c.nationkey = n2.nationkey
             AND (
               (n1.name = 'FRANCE' AND n2.name = 'GERMANY')
               OR (n1.name = 'GERMANY' AND n2.name = 'FRANCE')
             )
             AND l.shipdate BETWEEN DATE '1995-01-01' AND DATE '1996-12-31'
         ) AS shipping
    GROUP BY
      supp_nation,
      cust_nation,
      l_year
    ORDER BY
      supp_nation,
      cust_nation,
      l_year
    """,
    "Q8": """
    SELECT
      o_year,
      sum(CASE
          WHEN nation = 'BRAZIL'
            THEN volume
          ELSE 0
          END) / sum(volume) AS mkt_share
    FROM (
           SELECT
             extract(YEAR FROM o.orderdate)     AS o_year,
             l.extendedprice * (1 - l.discount) AS volume,
             n2.name                          AS nation
           FROM
             {catalog}.{schema}.part AS p,
             {catalog}.{schema}.supplier AS s,
             {catalog}.{schema}.lineitem AS l,
             {catalog}.{schema}.orders AS o,
             {catalog}.{schema}.customer AS c,
             {catalog}.{schema}.nation AS n1,
             {catalog}.{schema}.nation AS n2,
             {catalog}.{schema}.region AS r
           WHERE
             p.partkey = l.partkey
             AND s.suppkey = l.suppkey
             AND l.orderkey = o.orderkey
             AND o.custkey = c.custkey
             AND c.nationkey = n1.nationkey
             AND n1.regionkey = r.regionkey
             AND r.name = 'AMERICA'
             AND s.nationkey = n2.nationkey
             AND o.orderdate BETWEEN DATE '1995-01-01' AND DATE '1996-12-31'
             AND p.type = 'ECONOMY ANODIZED STEEL'
         ) AS all_nations
    GROUP BY
      o_year
    ORDER BY
      o_year
    """,
    "Q9": """
    SELECT
      nation,
      o_year,
      sum(amount) AS sum_profit
    FROM (
           SELECT
             n.name                                                          AS nation,
             extract(YEAR FROM o.orderdate)                                  AS o_year,
             l.extendedprice * (1 - l.discount) - ps.supplycost * l.quantity AS amount
           FROM
             {catalog}.{schema}.part AS p,
             {catalog}.{schema}.supplier AS s,
             {catalog}.{schema}.lineitem AS l,
             {catalog}.{schema}.partsupp AS ps,
             {catalog}.{schema}.orders AS o,
             {catalog}.{schema}.nation AS n
           WHERE
             s.suppkey = l.suppkey
             AND ps.suppkey = l.suppkey
             AND ps.partkey = l.partkey
             AND p.partkey = l.partkey
             AND o.orderkey = l.orderkey
             AND s.nationkey = n.nationkey
             AND p.name LIKE '%green%'
         ) AS profit
    GROUP BY
      nation,
      o_year
    ORDER BY
      nation,
      o_year DESC
    """,
    "Q10": """
    SELECT
      c.custkey,
      c.name,
      sum(l.extendedprice * (1 - l.discount)) AS revenue,
      c.acctbal,
      n.name,
      c.address,
      c.phone,
      c.comment
    FROM
      {catalog}.{schema}.lineitem AS l,
      {catalog}.{schema}.orders AS o,
      {catalog}.{schema}.customer AS c,
      {catalog}.{schema}.nation AS n
    WHERE
      c.custkey = o.custkey
      AND l.orderkey = o.orderkey
      AND o.orderdate >= DATE '1993-10-01'
      AND o.orderdate < DATE '1993-10-01' + INTERVAL '3' MONTH
      AND l.returnflag = 'R'
      AND c.nationkey = n.nationkey
    GROUP BY
      c.custkey,
      c.name,
      c.acctbal,
      c.phone,
      n.name,
      c.address,
      c.comment
    ORDER BY
      revenue DESC
    LIMIT 20
    """,
    "Q11": """
    SELECT 
      ps.partkey, 
      sum(ps.supplycost*ps.availqty) AS value
    FROM 
      {catalog}.{schema}.partsupp ps,
      {catalog}.{schema}.supplier s,
      {catalog}.{schema}.nation n
    WHERE 
      ps.suppkey = s.suppkey 
      AND s.nationkey = n.nationkey 
      AND n.name = 'GERMANY'
    GROUP BY 
      ps.partkey
    HAVING 
      sum(ps.supplycost*ps.availqty) > (
        SELECT 
          sum(ps.supplycost*ps.availqty) * 0.0001000000
        FROM 
          {catalog}.{schema}.partsupp ps,
          {catalog}.{schema}.supplier s,
          {catalog}.{schema}.nation n
        WHERE 
          ps.suppkey = s.suppkey 
          AND s.nationkey = n.nationkey 
          AND n.name = 'GERMANY'
      )
    ORDER BY 
      value DESC
    """,
    "Q12": """
    SELECT
      l.shipmode,
      sum(CASE
          WHEN o.orderpriority = '1-URGENT'
               OR o.orderpriority = '2-HIGH'
            THEN 1
          ELSE 0
          END) AS high_line_count,
      sum(CASE
          WHEN o.orderpriority <> '1-URGENT'
               AND o.orderpriority <> '2-HIGH'
            THEN 1
          ELSE 0
          END) AS low_line_count
    FROM
      {catalog}.{schema}.orders AS o,
      {catalog}.{schema}.lineitem AS l
    WHERE
      o.orderkey = l.orderkey
      AND l.shipmode IN ('MAIL', 'SHIP')
      AND l.commitdate < l.receiptdate
      AND l.shipdate < l.commitdate
      AND l.receiptdate >= DATE '1994-01-01'
      AND l.receiptdate < DATE '1994-01-01' + INTERVAL '1' YEAR
    GROUP BY
      l.shipmode
    ORDER BY
      l.shipmode
    """,
    "Q13": """
    SELECT 
      c_count, 
      count(*) as custdist
    FROM (
      SELECT 
        c.custkey, 
        count(o.orderkey)
      FROM 
        {catalog}.{schema}.customer c
        LEFT OUTER JOIN
        {catalog}.{schema}.orders o
      ON 
        c.custkey = o.custkey
        AND o.comment NOT LIKE '%special%requests%'
      GROUP BY c.custkey
    ) AS c_orders (c_custkey, c_count)
    GROUP BY 
      c_count
    ORDER BY 
      custdist DESC, 
      c_count DESC
    """,
    "Q14": """
    SELECT 100.00 * sum(CASE
                        WHEN p.type LIKE 'PROMO%'
                          THEN l.extendedprice * (1 - l.discount)
                        ELSE 0
                        END) / sum(l.extendedprice * (1 - l.discount)) AS promo_revenue
    FROM
      {catalog}.{schema}.lineitem AS l,
      {catalog}.{schema}.part AS p
    WHERE
      l.partkey = p.partkey
      AND l.shipdate >= DATE '1995-09-01'
      AND l.shipdate < DATE '1995-09-01' + INTERVAL '1' MONTH
    """,
    "Q15": """
    WITH revenue0 AS (
      SELECT 
        l.suppkey as supplier_no,
        sum(l.extendedprice*(1-l.discount)) as total_revenue
      FROM 
        {catalog}.{schema}.lineitem l
      WHERE 
        l.shipdate >= DATE '1996-01-01'
        AND l.shipdate < DATE '1996-01-01' + INTERVAL '3' MONTH
      GROUP BY 
        l.suppkey
    )
     
    
    SELECT 
      s.suppkey, 
      s.name, 
      s.address, 
      s.phone, 
      total_revenue
    FROM 
      {catalog}.{schema}.supplier s,
      revenue0
    WHERE 
      s.suppkey = supplier_no 
      AND total_revenue = (SELECT max(total_revenue) FROM revenue0)
    ORDER BY 
      s.suppkey
    """,
    "Q16": """
    SELECT
      p.brand,
      p.type,
      p.size,
      count(DISTINCT ps.suppkey) AS supplier_cnt
    FROM
      {catalog}.{schema}.partsupp AS ps,
      {catalog}.{schema}.part AS p
    WHERE
      p.partkey = ps.partkey
      AND p.brand <> 'Brand#45'
      AND p.type NOT LIKE 'MEDIUM POLISHED%'
      AND p.size IN (49, 14, 23, 45, 19, 3, 36, 9)
      AND ps.suppkey NOT IN (
        SELECT s.suppkey
        FROM
          {catalog}.{schema}.supplier AS s
        WHERE
          s.comment LIKE '%Customer%Complaints%'
      )
    GROUP BY
      p.brand,
      p.type,
      p.size
    ORDER BY
      supplier_cnt DESC,
      p.brand,
      p.type,
      p.size
    """,
    "Q17": """
    SELECT 
      sum(l.extendedprice)/7.0 as avg_yearly 
    FROM 
      {catalog}.{schema}.lineitem l,
      {catalog}.{schema}.part p
    WHERE 
      p.partkey = l.partkey 
      AND p.brand = 'Brand#23' 
      AND p.container = 'MED BOX'
      AND l.quantity < (
        SELECT 
          0.2*avg(l.quantity) 
        FROM 
          {catalog}.{schema}.lineitem l
        WHERE 
        l.partkey = p.partkey
      )
    """,
    "Q18": """
    SELECT
      c.name,
      c.custkey,
      o.orderkey,
      o.orderdate,
      o.totalprice,
      sum(l.quantity)
    FROM
      {catalog}.{schema}.customer AS c,
      {catalog}.{schema}.orders AS o,
      {catalog}.{schema}.lineitem AS l
    WHERE
      o.orderkey IN (
        SELECT l.orderkey
        FROM
          {catalog}.{schema}.lineitem AS l
        GROUP BY
          l.orderkey
        HAVING
          sum(l.quantity) > 300
      )
      AND c.custkey = o.custkey
      AND o.orderkey = l.orderkey
    GROUP BY
      c.name,
      c.custkey,
      o.orderkey,
      o.orderdate,
      o.totalprice
    ORDER BY
      o.totalprice DESC,
      o.orderdate
    LIMIT 100
    """,
    "Q19": """
    SELECT 
      sum(l.extendedprice* (1 - l.discount)) as revenue
    FROM 
      {catalog}.{schema}.lineitem l,
      {catalog}.{schema}.part p
    WHERE
      p.partkey = l.partkey
      AND
      ((
        p.brand = 'Brand#12'
        AND p.container IN ('SM CASE', 'SM BOX', 'SM PACK', 'SM PKG') 
        AND l.quantity >= 1 
        AND l.quantity <= 1 + 10 
        AND p.size BETWEEN 1 AND 5
        AND l.shipmode IN ('AIR', 'AIR REG') 
        AND l.shipinstruct = 'DELIVER IN PERSON'
      )
      OR (
        p.brand ='Brand#23'
        AND p.container IN ('MED BAG', 'MED BOX', 'MED PKG', 'MED PACK') 
        AND l.quantity >=10 
        AND l.quantity <=10 + 10 
        AND p.size BETWEEN 1 AND 10 
        AND l.shipmode IN ('AIR', 'AIR REG') 
        AND l.shipinstruct = 'DELIVER IN PERSON'
      ) 
      OR (
        p.brand = 'Brand#34'
        AND p.container IN ( 'LG CASE', 'LG BOX', 'LG PACK', 'LG PKG') 
        AND l.quantity >=20 
        AND l.quantity <= 20 + 10 
        AND p.size BETWEEN 1 AND 15
        AND l.shipmode IN ('AIR', 'AIR REG') 
        AND l.shipinstruct = 'DELIVER IN PERSON'
      ))
    """,
    "Q20": """
    SELECT 
      s.name, 
      s.address 
    FROM 
      {catalog}.{schema}.supplier s,
      {catalog}.{schema}.nation n
    WHERE 
      s.suppkey IN (
        SELECT 
          ps.suppkey 
        FROM 
          {catalog}.{schema}.partsupp ps
        WHERE 
          ps.partkey IN (
            SELECT 
              p.partkey 
            FROM 
              {catalog}.{schema}.part p
            WHERE 
              p.name like 'forest%'
          ) 
          AND ps.availqty > (
            SELECT 
              0.5*sum(l.quantity) 
            FROM 
              {catalog}.{schema}.lineitem l
            WHERE 
              l.partkey = ps.partkey 
              AND l.suppkey = ps.suppkey 
              AND l.shipdate >= date('1994-01-01')
              AND l.shipdate < date('1994-01-01') + interval '1' YEAR
          )
      )
      AND s.nationkey = n.nationkey 
      AND n.name = 'CANADA'
    ORDER BY 
      s.name
    """,
    "Q21": """
    SELECT 
      s.name, 
      count(*) as numwait
    FROM 
      {catalog}.{schema}.supplier s,
      {catalog}.{schema}.lineitem l1,
      {catalog}.{schema}.orders o,
      {catalog}.{schema}.nation n
    WHERE 
      s.suppkey = l1.suppkey 
      AND o.orderkey = l1.orderkey
      AND o.orderstatus = 'F'
      AND l1.receiptdate> l1.commitdate
      AND EXISTS (
        SELECT 
          * 
        FROM 
          {catalog}.{schema}.lineitem l2
        WHERE 
          l2.orderkey = l1.orderkey
          AND l2.suppkey <> l1.suppkey
      ) 
      AND NOT EXISTS (
        SELECT 
          * 
        FROM 
          {catalog}.{schema}.lineitem l3
        WHERE 
          l3.orderkey = l1.orderkey 
          AND l3.suppkey <> l1.suppkey 
          AND l3.receiptdate > l3.commitdate
      ) 
      AND s.nationkey = n.nationkey 
      AND n.name = 'SAUDI ARABIA'
    GROUP BY 
      s.name
    ORDER BY 
      numwait DESC, 
      s.name
    LIMIT 
      100
    """,
    "Q22": """
    SELECT 
      cntrycode, 
      count(*) AS numcust, 
      sum(acctbal) AS totacctbal
    FROM 
      (
        SELECT 
          substr(c.phone,1,2) AS cntrycode,
          c.acctbal
        FROM 
          {catalog}.{schema}.customer c
        WHERE 
          substr(c.phone,1,2) IN ('13', '31', '23', '29', '30', '18', '17')
          AND c.acctbal > (
            SELECT 
              avg(c.acctbal) 
            FROM 
              {catalog}.{schema}.customer c
            WHERE 
              c.acctbal > 0.00 
              AND substr(c.phone,1,2) IN ('13', '31', '23', '29', '30', '18', '17')
          ) 
          AND NOT EXISTS (
            SELECT 
              * 
            FROM 
              {catalog}.{schema}.orders o
            WHERE 
              o.custkey = c.custkey
          )
      ) AS custsale
    GROUP BY 
      cntrycode
    ORDER BY 
      cntrycode
    """,
}
