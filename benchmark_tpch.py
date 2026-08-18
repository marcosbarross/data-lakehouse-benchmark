import os
import re
import time
from trino.dbapi import connect
import matplotlib.pyplot as plt
import statistics

# Configuracoes do Trino
TRINO_HOST = '192.168.56.80'
TRINO_PORT = 30080
TRINO_USER = 'trino'
SCHEMA = 'benchmark'

# Catalogos para comparar
CATALOGS = ['iceberg', 'delta_lake']

# Numero de iteracoes por query
ITERATIONS = 3

# Bucket padrao provisionado no MinIO pelo Ansible.
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'warehouse')
DELTA_STORAGE_SCHEME = 's3a'

# Queries do TPC-H parametrizadas
TPCH_QUERIES = {
    "Q1": """
    SELECT
        returnflag,
        linestatus,
        sum(quantity) AS sum_qty,
        sum(extendedprice) AS sum_base_price,
        sum(extendedprice * (1 - discount)) AS sum_disc_price,
        sum(extendedprice * (1 - discount) * (1 + tax)) AS sum_charge,
        avg(quantity) AS avg_qty,
        avg(extendedprice) AS avg_price,
        avg(discount) AS avg_disc,
        count(*) AS count_order
    FROM {catalog}.{schema}.lineitem
    WHERE shipdate <= DATE '1998-12-01' - INTERVAL '90' DAY
    GROUP BY returnflag, linestatus
    ORDER BY returnflag, linestatus
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
    FROM {catalog}.{schema}.part p
    JOIN {catalog}.{schema}.partsupp ps ON p.partkey = ps.partkey
    JOIN {catalog}.{schema}.supplier s ON s.suppkey = ps.suppkey
    JOIN {catalog}.{schema}.nation n ON s.nationkey = n.nationkey
    JOIN {catalog}.{schema}.region r ON n.regionkey = r.regionkey
    WHERE p.size = 15
      AND p.type LIKE '%BRASS'
      AND r.name = 'EUROPE'
      AND ps.supplycost = (
          SELECT min(ps2.supplycost)
          FROM {catalog}.{schema}.partsupp ps2
          JOIN {catalog}.{schema}.supplier s2 ON s2.suppkey = ps2.suppkey
          JOIN {catalog}.{schema}.nation n2 ON s2.nationkey = n2.nationkey
          JOIN {catalog}.{schema}.region r2 ON n2.regionkey = r2.regionkey
          WHERE p.partkey = ps2.partkey
            AND r2.name = 'EUROPE'
      )
    ORDER BY s.acctbal DESC, n.name, s.name, p.partkey
    LIMIT 100
    """,
    "Q3": """
    SELECT
        l.orderkey,
        sum(l.extendedprice * (1 - l.discount)) AS revenue,
        o.orderdate,
        o.shippriority
    FROM {catalog}.{schema}.customer c
    JOIN {catalog}.{schema}.orders o ON c.custkey = o.custkey
    JOIN {catalog}.{schema}.lineitem l ON l.orderkey = o.orderkey
    WHERE c.mktsegment = 'BUILDING'
      AND o.orderdate < DATE '1995-03-15'
      AND l.shipdate > DATE '1995-03-15'
    GROUP BY l.orderkey, o.orderdate, o.shippriority
    ORDER BY revenue DESC, o.orderdate
    LIMIT 10
    """,
    "Q4": """
    SELECT
        o.orderpriority,
        count(*) AS order_count
    FROM {catalog}.{schema}.orders o
    WHERE o.orderdate >= DATE '1993-07-01'
      AND o.orderdate < DATE '1993-07-01' + INTERVAL '3' MONTH
      AND EXISTS (
          SELECT 1
          FROM {catalog}.{schema}.lineitem l
          WHERE l.orderkey = o.orderkey
            AND l.commitdate < l.receiptdate
      )
    GROUP BY o.orderpriority
    ORDER BY o.orderpriority
    """,
    "Q5": """
    SELECT
        n.name,
        sum(l.extendedprice * (1 - l.discount)) AS revenue
    FROM {catalog}.{schema}.customer c
    JOIN {catalog}.{schema}.orders o ON c.custkey = o.custkey
    JOIN {catalog}.{schema}.lineitem l ON l.orderkey = o.orderkey
    JOIN {catalog}.{schema}.supplier s ON l.suppkey = s.suppkey
    JOIN {catalog}.{schema}.nation n ON s.nationkey = n.nationkey
    JOIN {catalog}.{schema}.region r ON n.regionkey = r.regionkey
    WHERE r.name = 'ASIA'
      AND o.orderdate >= DATE '1994-01-01'
      AND o.orderdate < DATE '1994-01-01' + INTERVAL '1' YEAR
      AND c.nationkey = s.nationkey
    GROUP BY n.name
    ORDER BY revenue DESC
    """,
    "Q6": """
    SELECT
        sum(extendedprice * discount) AS revenue
    FROM {catalog}.{schema}.lineitem
    WHERE shipdate >= DATE '1994-01-01'
      AND shipdate < DATE '1994-01-01' + INTERVAL '1' YEAR
      AND discount BETWEEN 0.05 AND 0.07
      AND quantity < 24
    """,
    "Q7": """
    SELECT
        supp_nation,
        cust_nation,
        l_year,
        sum(volume) AS revenue
    FROM (
        SELECT
            n1.name AS supp_nation,
            n2.name AS cust_nation,
            extract(YEAR FROM l.shipdate) AS l_year,
            l.extendedprice * (1 - l.discount) AS volume
        FROM {catalog}.{schema}.supplier s
        JOIN {catalog}.{schema}.lineitem l ON s.suppkey = l.suppkey
        JOIN {catalog}.{schema}.orders o ON l.orderkey = o.orderkey
        JOIN {catalog}.{schema}.customer c ON o.custkey = c.custkey
        JOIN {catalog}.{schema}.nation n1 ON s.nationkey = n1.nationkey
        JOIN {catalog}.{schema}.nation n2 ON c.nationkey = n2.nationkey
        WHERE ((n1.name = 'FRANCE' AND n2.name = 'GERMANY')
            OR (n1.name = 'GERMANY' AND n2.name = 'FRANCE'))
          AND l.shipdate BETWEEN DATE '1995-01-01' AND DATE '1996-12-31'
    ) AS shipping
    GROUP BY supp_nation, cust_nation, l_year
    ORDER BY supp_nation, cust_nation, l_year
    """,
    "Q8": """
    SELECT
        o_year,
        sum(CASE WHEN nation = 'BRAZIL' THEN volume ELSE 0 END) / sum(volume) AS mkt_share
    FROM (
        SELECT
            extract(YEAR FROM o.orderdate) AS o_year,
            l.extendedprice * (1 - l.discount) AS volume,
            n2.name AS nation
        FROM {catalog}.{schema}.part p
        JOIN {catalog}.{schema}.lineitem l ON p.partkey = l.partkey
        JOIN {catalog}.{schema}.supplier s ON l.suppkey = s.suppkey
        JOIN {catalog}.{schema}.orders o ON l.orderkey = o.orderkey
        JOIN {catalog}.{schema}.customer c ON o.custkey = c.custkey
        JOIN {catalog}.{schema}.nation n1 ON c.nationkey = n1.nationkey
        JOIN {catalog}.{schema}.nation n2 ON s.nationkey = n2.nationkey
        JOIN {catalog}.{schema}.region r ON n1.regionkey = r.regionkey
        WHERE r.name = 'AMERICA'
          AND o.orderdate BETWEEN DATE '1995-01-01' AND DATE '1996-12-31'
          AND p.type = 'ECONOMY ANODIZED STEEL'
    ) AS all_nations
    GROUP BY o_year
    ORDER BY o_year
    """,
    "Q9": """
    SELECT
        nation,
        o_year,
        sum(amount) AS sum_profit
    FROM (
        SELECT
            n.name AS nation,
            extract(YEAR FROM o.orderdate) AS o_year,
            l.extendedprice * (1 - l.discount) - ps.supplycost * l.quantity AS amount
        FROM {catalog}.{schema}.part p
        JOIN {catalog}.{schema}.lineitem l ON p.partkey = l.partkey
        JOIN {catalog}.{schema}.partsupp ps ON l.partkey = ps.partkey AND l.suppkey = ps.suppkey
        JOIN {catalog}.{schema}.supplier s ON l.suppkey = s.suppkey
        JOIN {catalog}.{schema}.orders o ON l.orderkey = o.orderkey
        JOIN {catalog}.{schema}.nation n ON s.nationkey = n.nationkey
        WHERE p.name LIKE '%green%'
    ) AS profit
    GROUP BY nation, o_year
    ORDER BY nation, o_year DESC
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
    FROM {catalog}.{schema}.customer c
    JOIN {catalog}.{schema}.orders o ON c.custkey = o.custkey
    JOIN {catalog}.{schema}.lineitem l ON l.orderkey = o.orderkey
    JOIN {catalog}.{schema}.nation n ON c.nationkey = n.nationkey
    WHERE o.orderdate >= DATE '1993-10-01'
      AND o.orderdate < DATE '1993-10-01' + INTERVAL '3' MONTH
      AND l.returnflag = 'R'
    GROUP BY c.custkey, c.name, c.acctbal, c.phone, n.name, c.address, c.comment
    ORDER BY revenue DESC
    LIMIT 20
    """
}

TABLES = ['region', 'nation', 'supplier', 'part', 'partsupp', 'customer', 'orders', 'lineitem']


def get_connection(catalog=None):
    """Retorna conexao ao Trino"""
    try:
        return connect(
            host=TRINO_HOST,
            port=TRINO_PORT,
            user=TRINO_USER,
            catalog=catalog or 'system',
            schema='default' if not catalog else None
        )
    except Exception as e:
        print(f"[ERRO] Falha ao conectar: {e}")
        return None


def schema_exists(cursor, catalog, schema):
    """Verifica se schema existe no catalogo"""
    try:
        cursor.execute(f"SHOW SCHEMAS IN {catalog}")
        schemas = [row[0] for row in cursor.fetchall()]
        return schema in schemas
    except Exception:
        return False


def table_exists(cursor, catalog, schema, table):
    """Verifica se tabela existe"""
    try:
        cursor.execute(f"SHOW TABLES IN {catalog}.{schema}")
        tables = [row[0] for row in cursor.fetchall()]
        return table in tables
    except Exception:
        return False


def get_bucket_from_iceberg(cursor):
    """Extrai o nome do bucket do schema iceberg existente"""
    try:
        cursor.execute(f"SHOW CREATE SCHEMA iceberg.{SCHEMA}")
        result = cursor.fetchall()
        create_sql = result[0][0]
        match = re.search(r"s3(?:a)?://([^/]+)", create_sql)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"[AVISO] Nao foi possivel extrair bucket do iceberg: {e}")
    return None


def get_delta_table_location(bucket, table):
    """Monta uma localizacao explicita para tabelas Delta no MinIO."""
    return f"{DELTA_STORAGE_SCHEME}://{bucket}/benchmark_delta/{table}"


def extract_bucket_from_minio_service(cursor):
    """Tenta descobrir bucket via variavel de ambiente ou configuracoes"""
    try:
        cursor.execute("SELECT * FROM iceberg.information_schema.schemata WHERE schema_name = 'benchmark'")
        return cursor.fetchall()
    except Exception:
        pass
    return None


def staging(cursor):
    """Cria schemas e tabelas em todos os catalogos se nao existirem"""
    print("\n[STAGING] Iniciando preparacao dos dados...")

    # Verificar se iceberg ja tem o schema benchmark
    iceberg_exists = schema_exists(cursor, 'iceberg', SCHEMA)

    bucket = None
    if iceberg_exists:
        print("[STAGING] Schema iceberg.benchmark ja existe. Extraindo bucket...")
        bucket = get_bucket_from_iceberg(cursor)
        print(f"[STAGING] Bucket detectado: {bucket}")
    else:
        print("[STAGING] Criando schema iceberg.benchmark...")
        cursor.execute(f"CREATE SCHEMA iceberg.{SCHEMA}")

    # O Delta Lake precisa de localizacao explicita em object storage.
    # Se nao conseguirmos inferir do Iceberg, usamos o bucket provisionado no MinIO.
    if not bucket:
        bucket = MINIO_BUCKET
        print(f"[STAGING] Usando bucket padrao do MinIO: {bucket}")

    # Verificar delta_lake
    delta_exists = schema_exists(cursor, 'delta_lake', SCHEMA)
    if not delta_exists:
        print("[STAGING] Criando schema delta_lake.benchmark...")
        try:
            cursor.execute(
                f"CREATE SCHEMA delta_lake.{SCHEMA} "
                f"WITH (location = '{DELTA_STORAGE_SCHEME}://{bucket}/benchmark_delta/')"
            )
            print("[STAGING] Schema delta_lake criado com location do MinIO.")
        except Exception as e:
            print(f"[ERRO] Falha ao criar schema delta_lake: {e}")
            return False

    # Criar tabelas nos dois catalogos
    for catalog in CATALOGS:
        print(f"\n[STAGING] Verificando tabelas em {catalog}.{SCHEMA}...")
        for table in TABLES:
            if table_exists(cursor, catalog, SCHEMA, table):
                print(f"  [OK] {table} ja existe em {catalog}")
            else:
                print(f"  [CRIANDO] {table} em {catalog}...")
                try:
                    if catalog == 'delta_lake':
                        table_location = get_delta_table_location(bucket, table)
                        cursor.execute(
                            f"CREATE TABLE {catalog}.{SCHEMA}.{table} "
                            f"WITH (location = '{table_location}') "
                            f"AS SELECT * FROM tpch.sf1.{table}"
                        )
                    else:
                        cursor.execute(
                            f"CREATE TABLE {catalog}.{SCHEMA}.{table} "
                            f"AS SELECT * FROM tpch.sf1.{table}"
                        )
                    print(f"  [OK] {table} criada em {catalog}")
                except Exception as e:
                    print(f"  [ERRO] Falha ao criar {table} em {catalog}: {e}")
                    return False

    print("\n[STAGING] Todos os dados estao prontos!")
    return True


def execute_query(cursor, query_name, query):
    """Executa uma query e retorna o tempo de execucao"""
    start_time = time.time()
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        end_time = time.time()
        return end_time - start_time, len(results)
    except Exception as e:
        print(f"    [ERRO] {query_name}: {e}")
        return None, 0


def run_benchmark():
    """Executa staging + benchmark em todos os catalogos"""
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor()

    # Fazer staging
    if not staging(cursor):
        print("[ERRO] Staging falhou. Abortando.")
        cursor.close()
        conn.close()
        return None

    cursor.close()
    conn.close()

    # Rodar benchmark em cada catalogo
    results = {catalog: {} for catalog in CATALOGS}

    for catalog in CATALOGS:
        print(f"\n[BENCHMARK] Iniciando testes em {catalog}...")
        conn = get_connection(catalog=catalog)
        if not conn:
            continue
        cursor = conn.cursor()

        for query_name, query_template in TPCH_QUERIES.items():
            query = query_template.format(catalog=catalog, schema=SCHEMA)
            print(f"  [EXEC] {query_name} em {catalog}...")
            times = []

            for i in range(ITERATIONS):
                exec_time, row_count = execute_query(cursor, query_name, query)
                if exec_time:
                    times.append(exec_time)
                    print(f"    Iteracao {i+1}: {exec_time:.2f}s ({row_count} linhas)")

            if times:
                results[catalog][query_name] = {
                    'times': times,
                    'avg_time': statistics.mean(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'std_dev': statistics.stdev(times) if len(times) > 1 else 0
                }
                print(f"    [OK] Media: {results[catalog][query_name]['avg_time']:.2f}s")

        cursor.close()
        conn.close()

    return results


def generate_plots(results, output_dir='benchmark_plots'):
    """Gera graficos comparativos"""
    os.makedirs(output_dir, exist_ok=True)

    queries = sorted(TPCH_QUERIES.keys(), key=lambda x: int(x[1:]))
    # Apenas queries que rodaram em ambos catalogos
    common_queries = [q for q in queries if all(q in results[cat] for cat in CATALOGS)]

    # Grafico 1: Comparacao lado a lado (barras agrupadas)
    x = range(len(common_queries))
    width = 0.35

    fig, ax = plt.subplots(figsize=(16, 7))

    iceberg_times = [results['iceberg'][q]['avg_time'] for q in common_queries]
    delta_times = [results['delta_lake'][q]['avg_time'] for q in common_queries]

    bars1 = ax.bar([i - width/2 for i in x], iceberg_times, width,
                   label='Iceberg', color='#1f77b4', alpha=0.8)
    bars2 = ax.bar([i + width/2 for i in x], delta_times, width,
                   label='Delta Lake', color='#ff7f0e', alpha=0.8)

    ax.set_xlabel('Queries TPC-H', fontsize=12)
    ax.set_ylabel('Tempo Medio de Execucao (segundos)', fontsize=12)
    ax.set_title('Comparacao de Performance: Iceberg vs Delta Lake (TPC-H)', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(common_queries, rotation=45)
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3)

    # Adicionar valores em cima das barras
    for bar in bars1:
        h = bar.get_height()
        ax.annotate(f'{h:.2f}', xy=(bar.get_x() + bar.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=7)
    for bar in bars2:
        h = bar.get_height()
        ax.annotate(f'{h:.2f}', xy=(bar.get_x() + bar.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=7)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/iceberg_vs_deltalake.png', dpi=300, bbox_inches='tight')
    plt.close()

    # Grafico 2: Speedup do Delta Lake em relacao ao Iceberg (razao)
    speedup = []
    for q in common_queries:
        iceberg_t = results['iceberg'][q]['avg_time']
        delta_t = results['delta_lake'][q]['avg_time']
        if delta_t > 0:
            speedup.append(iceberg_t / delta_t)
        else:
            speedup.append(0)

    fig, ax = plt.subplots(figsize=(14, 6))
    colors = ['#2ca02c' if s > 1 else '#d62728' for s in speedup]
    bars = ax.bar(common_queries, speedup, color=colors, alpha=0.8)
    ax.axhline(y=1.0, color='black', linestyle='--', linewidth=1, label='Paridade (1.0x)')
    ax.set_xlabel('Queries TPC-H', fontsize=12)
    ax.set_ylabel('Speedup (Iceberg / Delta Lake)', fontsize=12)
    ax.set_title('Speedup do Delta Lake em relacao ao Iceberg (>1 = Delta Lake mais rapido)',
                 fontsize=13)
    ax.set_xticklabels(common_queries, rotation=45)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    for bar, s in zip(bars, speedup):
        h = bar.get_height()
        ax.annotate(f'{s:.2f}x', xy=(bar.get_x() + bar.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/speedup_deltalake_vs_iceberg.png', dpi=300, bbox_inches='tight')
    plt.close()

    # Grafico 3: Tempo total acumulado
    total_iceberg = sum(results['iceberg'][q]['avg_time'] for q in common_queries)
    total_delta = sum(results['delta_lake'][q]['avg_time'] for q in common_queries)

    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.bar(['Iceberg', 'Delta Lake'], [total_iceberg, total_delta],
                  color=['#1f77b4', '#ff7f0e'], alpha=0.8)
    ax.set_ylabel('Tempo Total Acumulado (segundos)', fontsize=12)
    ax.set_title(f'Tempo Total - {len(common_queries)} Queries TPC-H', fontsize=14)
    for bar, t in zip(bars, [total_iceberg, total_delta]):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                f'{t:.2f}s', ha='center', va='bottom', fontsize=12, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/total_time_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()

    return output_dir


def generate_markdown_report(results, output_dir):
    """Gera relatorio comparativo em Markdown"""
    queries = sorted(TPCH_QUERIES.keys(), key=lambda x: int(x[1:]))
    common_queries = [q for q in queries if all(q in results[cat] for cat in CATALOGS)]

    report = []
    report.append("# Benchmark Comparativo - Iceberg vs Delta Lake")
    report.append(f"\n**Data:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("\n## Configuracao do Ambiente\n")
    report.append(f"- **Host Trino:** {TRINO_HOST}:{TRINO_PORT}")
    report.append(f"- **Schema:** {SCHEMA}")
    report.append(f"- **Iteracoes por query:** {ITERATIONS}")
    report.append(f"- **Catalogo Iceberg:** Apache Iceberg (S3/MinIO)")
    report.append(f"- **Catalogo Delta Lake:** Delta Lake (S3/MinIO)")
    report.append(f"- **Infraestrutura:** k3s rodando em Vagrant (VirtualBox)")
    report.append("  - k3s-master: 2 vCPUs, 2GB RAM")
    report.append("  - k3s-worker1: 2 vCPUs, 8GB RAM")
    report.append("  - k3s-worker2: 2 vCPUs, 4GB RAM")
    report.append(f"- **Dataset:** TPC-H com Fator de Escala 1 (~1GB)")

    report.append("\n## Visao Geral dos Resultados\n")
    total_iceberg = sum(results['iceberg'][q]['avg_time'] for q in common_queries)
    total_delta = sum(results['delta_lake'][q]['avg_time'] for q in common_queries)

    winner = 'Delta Lake' if total_delta < total_iceberg else 'Iceberg'
    diff_pct = abs(total_iceberg - total_delta) / max(total_iceberg, total_delta) * 100

    report.append(f"- **Tempo total Iceberg:** {total_iceberg:.2f}s")
    report.append(f"- **Tempo total Delta Lake:** {total_delta:.2f}s")
    report.append(f"- **Melhor performer geral:** {winner} ({diff_pct:.1f}% mais rapido)")

    report.append("\n## Tabela Comparativa Detalhada\n")
    report.append("| Query | Iceberg (s) | Delta Lake (s) | Speedup Delta | Vencedor |")
    report.append("|-------|-------------|----------------|---------------|----------|")

    delta_wins = 0
    iceberg_wins = 0

    for q in common_queries:
        i_t = results['iceberg'][q]['avg_time']
        d_t = results['delta_lake'][q]['avg_time']
        speedup = i_t / d_t if d_t > 0 else 0
        winner_q = 'Delta Lake' if d_t < i_t else 'Iceberg'
        if d_t < i_t:
            delta_wins += 1
        else:
            iceberg_wins += 1
        report.append(f"| {q} | {i_t:.2f} | {d_t:.2f} | {speedup:.2f}x | {winner_q} |")

    report.append(f"\n**Resumo:** Delta Lake venceu em {delta_wins} queries, "
                  f"Iceberg venceu em {iceberg_wins} queries.")

    report.append("\n## Graficos\n")
    report.append("### Comparacao de Tempo Medio por Query\n")
    report.append(f"![Iceberg vs Delta Lake]({output_dir}/iceberg_vs_deltalake.png)\n")

    report.append("### Speedup Relativo do Delta Lake em relacao ao Iceberg\n")
    report.append(f"![Speedup]({output_dir}/speedup_deltalake_vs_iceberg.png)\n")

    report.append("### Tempo Total Acumulado\n")
    report.append(f"![Tempo Total]({output_dir}/total_time_comparison.png)\n")

    # Estatisticas adicionais
    report.append("## Estatisticas Descritivas\n")
    report.append("\n### Iceberg\n")
    report.append("| Query | Media (s) | Min (s) | Max (s) | Desvio Padrao (s) |")
    report.append("|-------|-----------|---------|---------|-------------------|")
    for q in common_queries:
        r = results['iceberg'][q]
        report.append(f"| {q} | {r['avg_time']:.2f} | {r['min_time']:.2f} | "
                      f"{r['max_time']:.2f} | {r['std_dev']:.2f} |")

    report.append("\n### Delta Lake\n")
    report.append("| Query | Media (s) | Min (s) | Max (s) | Desvio Padrao (s) |")
    report.append("|-------|-----------|---------|---------|-------------------|")
    for q in common_queries:
        r = results['delta_lake'][q]
        report.append(f"| {q} | {r['avg_time']:.2f} | {r['min_time']:.2f} | "
                      f"{r['max_time']:.2f} | {r['std_dev']:.2f} |")

    report.append("\n## Conclusao\n")
    report.append(f"Neste benchmark com {len(common_queries)} queries do TPC-H executadas "
                  f"{ITERATIONS} vezes cada, o **{winner}** apresentou melhor performance "
                  f"geral, sendo {diff_pct:.1f}% mais rapido que o concorrente no tempo "
                  f"acumulado.")
    report.append("\nObservacoes:")
    report.append("- As tabelas foram criadas em ambos catalogos a partir do dataset "
                  "sintetico TPC-H SF1 (~1GB).")
    report.append("- O staging e a execucao foram totalmente automatizados via Python.")
    report.append("- Os dados residem no MinIO em formato Parquet, gerenciados pelos "
                  "respectivos metadados de cada engine.")

    with open('benchmark_report.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    print(f"\n[OK] Relatorio gerado: benchmark_report.md")


if __name__ == "__main__":
    print("=" * 70)
    print("BENCHMARK COMPARATIVO: ICEBERG vs DELTA LAKE - DATA LAKEHOUSE")
    print("=" * 70)

    results = run_benchmark()

    if results and any(results[cat] for cat in CATALOGS):
        output_dir = generate_plots(results)
        generate_markdown_report(results, output_dir)
        print("\n[OK] Benchmark concluido com sucesso!")
        print(f"[OK] Graficos em: {output_dir}/")
        print("[OK] Relatorio em: benchmark_report.md")
    else:
        print("\n[ERRO] Benchmark falhou!")
