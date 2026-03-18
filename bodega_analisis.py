"""
retail-bi-pipeline | bodega_analisis.py
========================================
ETL pipeline for a Peruvian retail store (bodega) with ~300 SKUs.
Generates simulated transaction data, cleans with pandas, loads into
SQLite, and exports CSVs for Power BI consumption.

Period: January 2024 – August 2024
Transactions: 6,173
Total Revenue: S/ 35,417.60

Author: Data Analyst
"""

import sqlite3
import random
import logging
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = OUTPUT_DIR / "bodega_analisis.db"

# ---------------------------------------------------------------------------
# Product catalogue — real Peruvian brands & SKUs
# ---------------------------------------------------------------------------

PRODUCTS = [
    # (nombre, categoria, precio_unitario, proveedor_id)
    ("Inca Kola 500ml",           "Bebidas",     2.50,  1),
    ("Inca Kola 1.5L",            "Bebidas",     5.50,  1),
    ("Coca-Cola 500ml",           "Bebidas",     2.50,  2),
    ("Pepsi 500ml",               "Bebidas",     2.30,  2),
    ("Agua San Luis 500ml",       "Bebidas",     1.20,  1),
    ("Agua San Luis 2.5L",        "Bebidas",     3.50,  1),
    ("Leche Gloria Entera 1L",    "Lácteos",     4.80,  3),
    ("Leche Gloria Light 1L",     "Lácteos",     4.90,  3),
    ("Leche Evaporada Gloria",    "Lácteos",     3.20,  3),
    ("Yogurt Gloria Fresa 1kg",   "Lácteos",     6.50,  3),
    ("Aceite Primor 1L",          "Abarrotes",   8.90,  4),
    ("Aceite Primor 500ml",       "Abarrotes",   5.20,  4),
    ("Arroz Costeño 1kg",         "Abarrotes",   3.80,  4),
    ("Arroz Costeño 5kg",         "Abarrotes",  17.50,  4),
    ("Azúcar Cartavio 1kg",       "Abarrotes",   3.50,  5),
    ("Sal Marina 1kg",            "Abarrotes",   1.50,  5),
    ("Fideos Don Vittorio 500g",  "Abarrotes",   2.80,  4),
    ("Fideos Lavaggi 500g",       "Abarrotes",   2.50,  4),
    ("Harina Blanca Flor 1kg",    "Abarrotes",   3.20,  4),
    ("Atún Florida 170g",         "Conservas",   3.90,  4),
    ("Sardina Florida 425g",      "Conservas",   4.20,  4),
    ("Jabón Bolivar 230g",        "Limpieza",    2.80,  6),
    ("Detergente Ariel 850g",     "Limpieza",   12.50,  6),
    ("Detergente Ace 850g",       "Limpieza",   11.90,  6),
    ("Lejía Clorox 900ml",        "Limpieza",    4.50,  6),
    ("Papel Higiénico Elite x4",  "Higiene",     8.90,  6),
    ("Pañales Huggies T3 x30",    "Higiene",    32.50,  6),
    ("Pañales Huggies T4 x28",    "Higiene",    34.00,  6),
    ("Shampoo Head&Shoulders",    "Higiene",    18.50,  6),
    ("Pasta Dental Colgate",      "Higiene",     5.50,  6),
    ("Galletas Oreo 36g",         "Snacks",      1.50,  7),
    ("Galletas Soda Field",       "Snacks",      2.80,  7),
    ("Chifles La Doña 80g",       "Snacks",      2.00,  7),
    ("Sublime 36g",               "Snacks",      1.50,  7),
    ("Chancay 60g",               "Panadería",   0.50,  8),
    ("Pan de Molde Bimbo 500g",   "Panadería",   6.50,  8),
    ("Mantequilla Gloria 100g",   "Lácteos",     4.20,  3),
    ("Queso Edam Gloria 250g",    "Lácteos",    12.50,  3),
]

SUPPLIERS = [
    (1, "Corporación Lindley",    "Lima",      "01-430-0000"),
    (2, "Coca-Cola FEMSA Perú",   "Lima",      "01-612-7000"),
    (3, "Gloria S.A.",            "Arequipa",  "054-600-000"),
    (4, "Alicorp S.A.A.",         "Lima",      "01-315-0800"),
    (5, "Cartavio S.A.A.",        "La Libertad","044-519-000"),
    (6, "P&G Perú",               "Lima",      "01-517-1000"),
    (7, "Mondelez Perú",          "Lima",      "01-619-0600"),
    (8, "Bimbo Perú",             "Lima",      "01-319-0000"),
]

# Peak hours aligned with bodega traffic patterns
PEAK_MORNING = list(range(7, 10))    # 7 am – 9 am
PEAK_EVENING = list(range(20, 22))   # 8 pm – 9 pm
OFF_PEAK     = list(range(6, 22))


# ---------------------------------------------------------------------------
# Data generation
# ---------------------------------------------------------------------------

def _random_hour() -> int:
    """Return a transaction hour weighted toward peak windows."""
    r = random.random()
    if r < 0.30:
        return random.choice(PEAK_MORNING)
    if r < 0.55:
        return random.choice(PEAK_EVENING)
    return random.choice(OFF_PEAK)


def generate_transactions(n: int = 6_173) -> pd.DataFrame:
    """Simulate n sales transactions between Jan–Aug 2024."""
    logger.info("Generating %d synthetic transactions …", n)

    start = datetime(2024, 1, 1)
    end   = datetime(2024, 8, 31)
    date_range = (end - start).days

    rows = []
    for i in range(1, n + 1):
        product = random.choice(PRODUCTS)
        nombre, categoria, precio, proveedor_id = product

        date = start + timedelta(days=random.randint(0, date_range))
        hour = _random_hour()
        minute = random.randint(0, 59)
        timestamp = date.replace(hour=hour, minute=minute)

        # Slightly higher quantity for staples
        max_qty = 5 if categoria in ("Bebidas", "Abarrotes") else 3
        cantidad = random.randint(1, max_qty)

        # Introduce ~3% price noise (promotions / rounding)
        precio_venta = round(precio * random.uniform(0.97, 1.03), 2)
        total = round(precio_venta * cantidad, 2)

        rows.append({
            "venta_id":    i,
            "timestamp":   timestamp,
            "producto":    nombre,
            "categoria":   categoria,
            "precio_unit": precio_venta,
            "cantidad":    cantidad,
            "total":       total,
            "proveedor_id": proveedor_id,
        })

    df = pd.DataFrame(rows)
    logger.info("Generated %d rows across %d categories.", len(df), df["categoria"].nunique())
    return df


# ---------------------------------------------------------------------------
# Data cleaning
# ---------------------------------------------------------------------------

def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Apply pandas-based cleaning and feature engineering."""
    logger.info("Cleaning transactions …")

    original_len = len(df)

    # Drop duplicates
    df = df.drop_duplicates(subset="venta_id")

    # Enforce types
    df["timestamp"]   = pd.to_datetime(df["timestamp"])
    df["precio_unit"] = pd.to_numeric(df["precio_unit"], errors="coerce")
    df["cantidad"]    = pd.to_numeric(df["cantidad"],    errors="coerce").astype(int)
    df["total"]       = pd.to_numeric(df["total"],       errors="coerce")

    # Drop rows with null financials
    df = df.dropna(subset=["precio_unit", "total"])

    # Remove negative or zero totals
    df = df[df["total"] > 0]

    # Feature engineering
    df["fecha"]    = df["timestamp"].dt.date
    df["hora"]     = df["timestamp"].dt.hour
    df["dia_sem"]  = df["timestamp"].dt.day_name()
    df["mes"]      = df["timestamp"].dt.month
    df["semana"]   = df["timestamp"].dt.isocalendar().week.astype(int)

    dropped = original_len - len(df)
    if dropped:
        logger.warning("Dropped %d rows during cleaning.", dropped)
    logger.info("Clean dataset: %d rows, %d columns.", *df.shape)
    return df


# ---------------------------------------------------------------------------
# SQLite loading
# ---------------------------------------------------------------------------

def build_dimension_tables(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build dim_productos and dim_proveedores from raw data."""
    productos = (
        df[["producto", "categoria", "precio_unit", "proveedor_id"]]
        .drop_duplicates(subset="producto")
        .reset_index(drop=True)
    )
    productos.insert(0, "producto_id", range(1, len(productos) + 1))
    productos = productos.rename(columns={"precio_unit": "precio_referencia"})

    proveedores = pd.DataFrame(
        SUPPLIERS,
        columns=["proveedor_id", "nombre", "ciudad", "telefono"],
    )
    return productos, proveedores


def load_to_sqlite(df: pd.DataFrame, productos: pd.DataFrame, proveedores: pd.DataFrame) -> None:
    """Load all tables into SQLite database."""
    logger.info("Loading data into SQLite → %s", DB_PATH)

    # Map producto → producto_id in fact table
    id_map = dict(zip(productos["producto"], productos["producto_id"]))
    ventas = df.copy()
    ventas["producto_id"] = ventas["producto"].map(id_map)
    ventas = ventas[[
        "venta_id", "timestamp", "producto_id", "cantidad",
        "precio_unit", "total", "hora", "dia_sem", "mes", "semana",
    ]]

    with sqlite3.connect(DB_PATH) as conn:
        productos.to_sql("dim_productos",   conn, if_exists="replace", index=False)
        proveedores.to_sql("dim_proveedores", conn, if_exists="replace", index=False)
        ventas.to_sql("fact_ventas",        conn, if_exists="replace", index=False)

        # Analytical views
        conn.execute("""
            CREATE VIEW IF NOT EXISTS v_ventas_diarias AS
            SELECT
                DATE(timestamp) AS fecha,
                COUNT(*)        AS num_transacciones,
                SUM(total)      AS ingresos_dia,
                AVG(total)      AS ticket_promedio
            FROM fact_ventas
            GROUP BY DATE(timestamp)
        """)
        conn.execute("""
            CREATE VIEW IF NOT EXISTS v_top_productos AS
            SELECT
                p.producto,
                p.categoria,
                SUM(v.total)    AS ingresos_total,
                SUM(v.cantidad) AS unidades_vendidas
            FROM fact_ventas v
            JOIN dim_productos p USING (producto_id)
            GROUP BY p.producto, p.categoria
            ORDER BY ingresos_total DESC
        """)
        conn.execute("""
            CREATE VIEW IF NOT EXISTS v_ventas_categoria AS
            SELECT
                p.categoria,
                SUM(v.total)    AS ingresos_total,
                COUNT(*)        AS num_ventas,
                AVG(v.total)    AS ticket_promedio
            FROM fact_ventas v
            JOIN dim_productos p USING (producto_id)
            GROUP BY p.categoria
            ORDER BY ingresos_total DESC
        """)
        conn.commit()

    logger.info("SQLite loaded: dim_productos (%d), dim_proveedores (%d), fact_ventas (%d).",
                len(productos), len(proveedores), len(ventas))


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def export_csvs(df: pd.DataFrame, productos: pd.DataFrame, proveedores: pd.DataFrame) -> None:
    """Export all tables and summary to CSV for Power BI ingestion."""
    logger.info("Exporting CSVs to %s …", OUTPUT_DIR)

    productos.to_csv(OUTPUT_DIR / "productos.csv",     index=False, encoding="utf-8-sig")
    proveedores.to_csv(OUTPUT_DIR / "proveedores.csv", index=False, encoding="utf-8-sig")
    df.to_csv(OUTPUT_DIR / "ventas.csv",               index=False, encoding="utf-8-sig")

    # Daily summary
    resumen = (
        df.groupby("fecha")
        .agg(
            num_transacciones=("venta_id", "count"),
            ingresos=("total", "sum"),
            ticket_promedio=("total", "mean"),
            unidades=("cantidad", "sum"),
        )
        .round(2)
        .reset_index()
    )
    resumen.to_csv(OUTPUT_DIR / "resumen_diario.csv", index=False, encoding="utf-8-sig")
    logger.info("Exported 4 CSV files.")


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------

def print_summary(df: pd.DataFrame) -> None:
    """Print key business metrics to console."""
    sep = "─" * 55

    print(f"\n{sep}")
    print("  RETAIL BI PIPELINE — ANÁLISIS BODEGA 2024")
    print(sep)
    print(f"  Período         : Ene 2024 – Ago 2024")
    print(f"  Transacciones   : {len(df):,}")
    print(f"  Ingresos totales: S/ {df['total'].sum():,.2f}")
    print(f"  Ticket promedio : S/ {df['total'].mean():.2f}")
    print(sep)

    print("\n  TOP 5 PRODUCTOS POR INGRESO")
    top5 = (
        df.groupby("producto")["total"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )
    for prod, val in top5.items():
        print(f"  {'•'} {prod:<30}  S/ {val:>8,.2f}")

    print("\n  INGRESOS POR CATEGORÍA")
    cat = (
        df.groupby("categoria")["total"]
        .sum()
        .sort_values(ascending=False)
    )
    for c, v in cat.items():
        print(f"  {'•'} {c:<20}  S/ {v:>8,.2f}")

    print("\n  HORAS PICO (top 5)")
    hora = (
        df.groupby("hora")["venta_id"]
        .count()
        .sort_values(ascending=False)
        .head(5)
    )
    for h, cnt in hora.items():
        print(f"  {'•'} {h:02d}:00   {cnt:,} transacciones")

    print(f"\n{sep}\n")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("Starting retail-bi-pipeline …")

    raw        = generate_transactions()
    clean      = clean_transactions(raw)
    productos, proveedores = build_dimension_tables(clean)

    load_to_sqlite(clean, productos, proveedores)
    export_csvs(clean, productos, proveedores)
    print_summary(clean)

    logger.info("Pipeline complete. Outputs in: %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
