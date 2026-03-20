"""
tests/test_pipeline.py
======================
Unit tests for the retail-bi-pipeline ETL functions.

Run:
    pytest tests/ -v
    pytest tests/ -v --tb=short   # compact traceback
"""

import sqlite3
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bodega_analisis import (
    build_dimension_tables,
    clean_transactions,
    generate_transactions,
    load_to_sqlite,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def raw_df():
    """Generate a small raw dataset once for the whole module."""
    return generate_transactions(n=200)


@pytest.fixture(scope="module")
def clean_df(raw_df):
    return clean_transactions(raw_df.copy())


@pytest.fixture(scope="module")
def dimension_tables(clean_df):
    return build_dimension_tables(clean_df)


# ---------------------------------------------------------------------------
# 1. Data generation
# ---------------------------------------------------------------------------

class TestGenerateTransactions:

    def test_row_count(self, raw_df):
        assert len(raw_df) == 200

    def test_required_columns(self, raw_df):
        expected = {"venta_id", "timestamp", "producto", "categoria",
                    "precio_unit", "cantidad", "total", "proveedor_id"}
        assert expected.issubset(raw_df.columns)

    def test_unique_venta_ids(self, raw_df):
        assert raw_df["venta_id"].nunique() == len(raw_df)

    def test_positive_totals(self, raw_df):
        assert (raw_df["total"] > 0).all()

    def test_positive_quantities(self, raw_df):
        assert (raw_df["cantidad"] >= 1).all()

    def test_date_range(self, raw_df):
        dates = pd.to_datetime(raw_df["timestamp"])
        assert dates.min() >= pd.Timestamp("2024-01-01")
        assert dates.max() <= pd.Timestamp("2024-08-31 23:59:59")

    def test_categories_are_known(self, raw_df):
        known = {"Bebidas", "Lácteos", "Abarrotes", "Conservas",
                 "Limpieza", "Higiene", "Snacks", "Panadería"}
        assert set(raw_df["categoria"].unique()).issubset(known)

    def test_peak_hours_are_overrepresented(self, raw_df):
        """Transactions in peak windows (7–9, 20–21) should exceed 40 % of total."""
        hours = pd.to_datetime(raw_df["timestamp"]).dt.hour
        peak = hours.isin(range(7, 10)) | hours.isin(range(20, 22))
        assert peak.mean() > 0.40

    def test_reproducibility(self):
        """Two calls after resetting to the same seed must produce identical datasets."""
        import random as _random
        _random.seed(42)
        np.random.seed(42)
        df1 = generate_transactions(n=50)

        _random.seed(42)
        np.random.seed(42)
        df2 = generate_transactions(n=50)

        pd.testing.assert_frame_equal(df1.reset_index(drop=True), df2.reset_index(drop=True))


# ---------------------------------------------------------------------------
# 2. Data cleaning
# ---------------------------------------------------------------------------

class TestCleanTransactions:

    def test_output_columns_include_engineered_features(self, clean_df):
        for col in ("fecha", "hora", "dia_sem", "mes", "semana"):
            assert col in clean_df.columns, f"Missing column: {col}"

    def test_no_null_financials(self, clean_df):
        assert clean_df["precio_unit"].isna().sum() == 0
        assert clean_df["total"].isna().sum() == 0

    def test_no_non_positive_totals(self, clean_df):
        assert (clean_df["total"] > 0).all()

    def test_hora_range(self, clean_df):
        assert clean_df["hora"].between(0, 23).all()

    def test_mes_range(self, clean_df):
        assert clean_df["mes"].between(1, 12).all()

    def test_semana_is_integer(self, clean_df):
        assert pd.api.types.is_integer_dtype(clean_df["semana"])

    def test_timestamp_dtype(self, clean_df):
        assert pd.api.types.is_datetime64_any_dtype(clean_df["timestamp"])

    def test_cantidad_dtype(self, clean_df):
        assert pd.api.types.is_integer_dtype(clean_df["cantidad"])

    def test_deduplication(self):
        """Duplicate venta_id rows must be removed."""
        raw = generate_transactions(n=50).copy()
        raw = pd.concat([raw, raw.head(5)], ignore_index=True)
        cleaned = clean_transactions(raw)
        assert cleaned["venta_id"].nunique() == len(cleaned)

    def test_negative_total_rows_dropped(self):
        """Rows with total <= 0 must be removed after cleaning."""
        raw = generate_transactions(n=50).copy()
        raw.loc[0, "total"] = -5.0
        raw.loc[1, "total"] = 0.0
        cleaned = clean_transactions(raw)
        assert (cleaned["total"] > 0).all()

    def test_total_integrity(self, clean_df):
        """Total must be roughly precio_unit * cantidad (within 5 % noise)."""
        computed = clean_df["precio_unit"] * clean_df["cantidad"]
        ratio = (clean_df["total"] / computed).replace([np.inf, -np.inf], np.nan).dropna()
        assert ratio.between(0.90, 1.10).all(), "total deviates too far from unit_price * quantity"


# ---------------------------------------------------------------------------
# 3. Dimension tables
# ---------------------------------------------------------------------------

class TestBuildDimensionTables:

    def test_productos_has_producto_id(self, dimension_tables):
        productos, _ = dimension_tables
        assert "producto_id" in productos.columns

    def test_productos_no_duplicates(self, dimension_tables):
        productos, _ = dimension_tables
        assert productos["producto"].nunique() == len(productos)

    def test_proveedores_count(self, dimension_tables):
        _, proveedores = dimension_tables
        assert len(proveedores) == 8

    def test_proveedores_columns(self, dimension_tables):
        _, proveedores = dimension_tables
        assert set(proveedores.columns) == {"proveedor_id", "nombre", "ciudad", "telefono"}

    def test_productos_price_reference_positive(self, dimension_tables):
        productos, _ = dimension_tables
        assert (productos["precio_referencia"] > 0).all()


# ---------------------------------------------------------------------------
# 4. SQLite loading
# ---------------------------------------------------------------------------

class TestLoadToSqlite:

    def test_tables_exist(self, clean_df, dimension_tables, tmp_path):
        productos, proveedores = dimension_tables
        db_path = tmp_path / "test.db"

        # Patch DB_PATH temporarily
        import bodega_analisis as bm
        original = bm.DB_PATH
        bm.DB_PATH = db_path
        try:
            load_to_sqlite(clean_df, productos, proveedores)
        finally:
            bm.DB_PATH = original

        with sqlite3.connect(db_path) as conn:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert {"dim_productos", "dim_proveedores", "fact_ventas"}.issubset(tables)

    def test_fact_row_count_matches(self, clean_df, dimension_tables, tmp_path):
        productos, proveedores = dimension_tables
        db_path = tmp_path / "test_count.db"

        import bodega_analisis as bm
        original = bm.DB_PATH
        bm.DB_PATH = db_path
        try:
            load_to_sqlite(clean_df, productos, proveedores)
        finally:
            bm.DB_PATH = original

        with sqlite3.connect(db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM fact_ventas").fetchone()[0]
        assert count == len(clean_df)

    def test_views_exist(self, clean_df, dimension_tables, tmp_path):
        productos, proveedores = dimension_tables
        db_path = tmp_path / "test_views.db"

        import bodega_analisis as bm
        original = bm.DB_PATH
        bm.DB_PATH = db_path
        try:
            load_to_sqlite(clean_df, productos, proveedores)
        finally:
            bm.DB_PATH = original

        with sqlite3.connect(db_path) as conn:
            views = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view'"
            ).fetchall()}
        expected_views = {"v_ventas_diarias", "v_top_productos", "v_ventas_categoria"}
        assert expected_views.issubset(views)

    def test_no_nulls_in_fact_ventas(self, clean_df, dimension_tables, tmp_path):
        productos, proveedores = dimension_tables
        db_path = tmp_path / "test_nulls.db"

        import bodega_analisis as bm
        original = bm.DB_PATH
        bm.DB_PATH = db_path
        try:
            load_to_sqlite(clean_df, productos, proveedores)
        finally:
            bm.DB_PATH = original

        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql("SELECT * FROM fact_ventas", conn)
        critical = ["venta_id", "producto_id", "cantidad", "precio_unit", "total"]
        assert df[critical].isna().sum().sum() == 0


# ---------------------------------------------------------------------------
# 5. Business logic assertions
# ---------------------------------------------------------------------------

class TestBusinessLogic:

    def test_abarrotes_is_top3_category(self, clean_df):
        top3 = (
            clean_df.groupby("categoria")["total"]
            .sum()
            .sort_values(ascending=False)
            .head(3)
            .index.tolist()
        )
        assert "Abarrotes" in top3

    def test_aceite_primor_in_top5_products(self, clean_df):
        top5 = (
            clean_df.groupby("producto")["total"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
            .index.tolist()
        )
        assert "Aceite Primor 1L" in top5

    def test_peak_hours_rank_highest(self, clean_df):
        """Hours 7–9 and 20–21 combined must account for > 35 % of transactions."""
        peak = clean_df["hora"].isin(list(range(7, 10)) + list(range(20, 22)))
        assert peak.mean() > 0.35

    def test_total_revenue_reasonable(self, clean_df):
        """Full 6,173-row dataset should produce revenue in a plausible range."""
        if len(clean_df) == 200:
            pytest.skip("Fixture uses 200 rows; full-scale check requires n=6173")
        revenue = clean_df["total"].sum()
        assert 20_000 < revenue < 200_000, f"Revenue out of expected range: {revenue}"
