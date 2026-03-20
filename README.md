# Retail BI Pipeline — Bodega Analytics

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/pandas-2.2.2-150458?style=for-the-badge&logo=pandas&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/Power%20BI-F2C811?style=for-the-badge&logo=powerbi&logoColor=black" />
  <img src="https://img.shields.io/badge/status-active-brightgreen?style=for-the-badge" />
</p>

---

## Overview / Descripción

**EN** — End-to-end ETL and business intelligence pipeline for a Peruvian retail store (bodega). The pipeline generates realistic synthetic transaction data using authentic Peruvian consumer brands, performs data cleaning with pandas, persists results in a star-schema SQLite database, and exports analysis-ready CSVs consumed by a Power BI dashboard.

**ES** — Pipeline ETL de extremo a extremo para una bodega peruana. Genera datos sintéticos realistas usando marcas peruanas auténticas, realiza limpieza con pandas, persiste los resultados en una base de datos SQLite con esquema estrella y exporta CSVs listos para ser consumidos por un dashboard de Power BI.

---

## Business Context / Contexto del Negocio

| Attribute | Detail |
|---|---|
| **Business type** | Independent retail store (bodega) |
| **Location** | Lima, Perú |
| **Active SKUs** | ~300 products across 8 categories |
| **Analysis period** | January 2024 – August 2024 (8 months) |
| **Total transactions** | 6,173 sales records |
| **Total revenue** | S/ 35,417.60 |
| **Brands covered** | Inca Kola · Gloria · Alicorp · Huggies · Bimbo · P&G |

---

## Key Findings / Hallazgos Principales

### Revenue Overview

| Metric | Value |
|---|---|
| Total Revenue | **S/ 35,417.60** |
| Average Ticket | **S/ 5.74** |
| Total Transactions | **6,173** |
| Best-selling category | **Abarrotes (S/ 7,633)** |
| Top product | **Aceite Primor 1L (S/ 3,106)** |
| Highest avg. ticket | **Pañales Huggies T3 (S/ 32.52)** |

### Peak Hours

Traffic analysis reveals two distinct peak windows driving the majority of daily sales:

```
Morning rush   ▸  07:00 – 09:00   (breakfast / pre-work shopping)
Evening rush   ▸  20:00 – 21:00   (post-work / dinner prep)
```

### Revenue by Category

| Category | Revenue (S/) | Share |
|---|---:|---:|
| Abarrotes | 7,633 | 21.6% |
| Bebidas | 6,840 | 19.3% |
| Higiene | 5,210 | 14.7% |
| Lácteos | 4,890 | 13.8% |
| Limpieza | 4,100 | 11.6% |
| Conservas | 2,780 | 7.9% |
| Snacks | 2,490 | 7.0% |
| Panadería | 1,474 | 4.2% |

### Top 5 Products by Revenue

| Rank | Product | Revenue (S/) |
|:---:|---|---:|
| 1 | Aceite Primor 1L | 3,106 |
| 2 | Pañales Huggies T3 x30 | 2,890 |
| 3 | Arroz Costeño 5kg | 2,650 |
| 4 | Leche Gloria Entera 1L | 2,410 |
| 5 | Detergente Ariel 850g | 2,230 |

---

## Tech Stack

| Layer | Tool | Version |
|---|---|---|
| Language | Python | 3.11+ |
| Data manipulation | pandas | 2.2.2 |
| Numerical computing | NumPy | 1.26.4 |
| Database | SQLite (via stdlib `sqlite3`) | 3.x |
| Visualisation | Power BI Desktop | February 2024 |
| Version control | Git / GitHub | — |

---

## Repository Structure

```
retail-bi-pipeline/
│
├── data/
│   └── raw/                    # Source / ingestion files (CSV, XLSX, etc.)
│
├── output/                     # Generated artefacts
│   ├── productos.csv           # Dimension: product catalogue
│   ├── ventas.csv              # Fact: all transactions (6,173 rows)
│   ├── proveedores.csv         # Dimension: supplier master
│   ├── resumen_diario.csv      # Aggregated daily KPIs
│   └── bodega_analisis.db      # SQLite database (star schema)
│
├── dashboard/
│   └── bodega_dashboard.pbix   # Power BI report file
│
├── bodega_analisis.py          # Main ETL pipeline script
├── analysis.sql                # Advanced SQL queries (window functions, CTEs)
├── requirements.txt            # Python dependencies
├── .gitignore
└── README.md
```

---

## Data Model — Star Schema

```
                    ┌─────────────────────┐
                    │   dim_proveedores   │
                    │─────────────────────│
                    │ proveedor_id  (PK)  │
                    │ nombre              │
                    │ ciudad              │
                    │ telefono            │
                    └──────────┬──────────┘
                               │  1
                               │
┌──────────────────┐    ┌──────┴──────────────┐
│  dim_productos   │    │    fact_ventas       │
│──────────────────│    │─────────────────────│
│ producto_id (PK) │◄───│ venta_id      (PK)  │
│ producto         │  N │ timestamp           │
│ categoria        │    │ producto_id   (FK)  │
│ precio_referencia│    │ cantidad            │
│ proveedor_id(FK) │    │ precio_unit         │
└──────────────────┘    │ total               │
                        │ hora                │
                        │ dia_sem             │
                        │ mes                 │
                        │ semana              │
                        └─────────────────────┘
```

**Analytical Views included in the DB:**

| View | Description |
|---|---|
| `v_ventas_diarias` | Daily revenue, transaction count and average ticket |
| `v_top_productos` | Products ranked by total revenue and units sold |
| `v_ventas_categoria` | Revenue aggregation per product category |

---

## Quick Start

### 1 — Clone the repository

```bash
git clone https://github.com/<your-username>/retail-bi-pipeline.git
cd retail-bi-pipeline
```

### 2 — Create and activate a virtual environment

```bash
# macOS / Linux
python -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### 4 — Run the pipeline

```bash
python bodega_analisis.py
```

Expected output:

```
2024-01-01 00:00:00 [INFO] Starting retail-bi-pipeline ...
2024-01-01 00:00:00 [INFO] Generating 6173 synthetic transactions ...
2024-01-01 00:00:00 [INFO] Clean dataset: 6173 rows, 11 columns.
2024-01-01 00:00:00 [INFO] Loading data into SQLite -> output/bodega_analisis.db
2024-01-01 00:00:00 [INFO] Exported 4 CSV files.

-------------------------------------------------------
  RETAIL BI PIPELINE -- ANALISIS BODEGA 2024
-------------------------------------------------------
  Periodo         : Ene 2024 -- Ago 2024
  Transacciones   : 6,173
  Ingresos totales: S/ 35,417.60
  Ticket promedio : S/ 5.74
-------------------------------------------------------
```

### 5 — Explore the SQLite database (optional)

```bash
sqlite3 output/bodega_analisis.db

sqlite> SELECT * FROM v_top_productos LIMIT 10;
sqlite> SELECT * FROM v_ventas_categoria;
sqlite> .quit
```

### 6 — Open the Power BI dashboard

1. Open `dashboard/bodega_dashboard.pbix` in **Power BI Desktop**.
2. In *Transform Data > Data Source Settings*, update the file paths to point to your local `output/` folder.
3. Click **Refresh** to load the latest data.

---

## Dashboard Preview

> Screenshots of the Power BI report. Refresh after running the pipeline to reproduce locally.

| Page | Description |
|---|---|
| `01_overview` | KPI cards · Revenue trend · Category bar chart |
| `02_products` | Top 20 products · ABC analysis matrix |
| `03_time` | Hourly heatmap · Day-of-week breakdown · Weekly trend |
| `04_suppliers` | Supplier revenue contribution · City map |

```
+----------------------------------------------------------+
|  Bodega Analytics -- Power BI Dashboard                  |
|----------------------------------------------------------|
|                                                          |
|  S/ 35,417.60    6,173 txns    S/ 5.74 avg ticket        |
|  ------------    ----------    --------------------      |
|                                                          |
|  Revenue by Category           Top Products             |
|  +-------------------+         +--------------------+   |
|  | Abarrotes  ||||   |         | 1. Aceite Primor    |   |
|  | Bebidas    |||    |         | 2. Huggies T3       |   |
|  | Higiene    ||     |         | 3. Arroz Costeno    |   |
|  | Lacteos    ||     |         | 4. Leche Gloria     |   |
|  +-------------------+         +--------------------+   |
+----------------------------------------------------------+
```

*Replace with actual screenshots once the dashboard is published.*

---

## Pipeline Architecture

```
 +--------------+     +---------------+     +--------------+
 |  Data Layer  |---->|  ETL (Python) |---->|  Output      |
 |              |     |               |     |              |
 | - Synthetic  |     | - Generate    |     | - SQLite DB  |
 |   generator  |     | - Clean       |     | - CSVs       |
 | - data/raw/  |     | - Transform   |     | - Power BI   |
 +--------------+     +---------------+     +--------------+
                             |
                      bodega_analisis.py
```

---

## SQL Analysis — analysis.sql

The file `analysis.sql` contains six analytical sections designed to answer real business questions directly against the SQLite database. Run the full script or copy individual queries into any SQLite client.

```bash
sqlite3 output/bodega_analisis.db < analysis.sql
```

| Section | Technique | Business Question |
|---|---|---|
| 1. Revenue Overview | `SUM`, `AVG`, `LAG`, window frame | How is revenue trending month over month? |
| 2. Product Analysis | `RANK() OVER PARTITION BY`, cumulative `SUM` | Which products drive 80 % of revenue (ABC)? |
| 3. Category Analysis | `CASE` pivot, `SUM OVER ()` | How does each category perform across months? |
| 4. Time-Based Analysis | `CASE` segmentation, `UNION ALL` | When are peak hours and best/worst trading days? |
| 5. Supplier Analysis | multi-table `JOIN`, `OVER ()` share | Which suppliers generate the most revenue? |
| 6. Advanced Analytics | rolling averages, market basket, milestone tracker | What are cross-sell opportunities and revenue milestones? |

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'feat: add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## License

Distributed under the MIT License. See `LICENSE` for more information.

---

## About the Author

Data Analyst with experience in Python, SQL, and business intelligence for retail and e-commerce verticals. Focused on translating raw transactional data into actionable business decisions.

<p align="left">
  <a href="https://www.linkedin.com/in/your-profile">
    <img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" />
  </a>
  &nbsp;
  <a href="https://github.com/your-username">
    <img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white" />
  </a>
</p>

---

<p align="center">Made in Lima, Peru</p>
