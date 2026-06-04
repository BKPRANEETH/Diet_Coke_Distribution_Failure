# Data Dictionary & Calibration Assumptions

> The transactional dataset is a **transparent simulation** (`src/generate_data.py`), not real Coca-Cola data. It is engineered to reproduce the documented April-2026 Diet Coke can shortage (see `references.md`). Every assumption is below so the work is fully auditable.

## `data/raw/orders.csv` — one row per order line (71,195 rows)
| Column | Type | Description |
|---|---|---|
| order_id | str | Unique sales-order line id |
| order_date | date | Date order placed (2026-01-01 to 2026-05-31) |
| requested_delivery_date | date | Customer-requested delivery date |
| actual_delivery_date | date | Simulated actual delivery date |
| depot | str | BLR-North / BLR-South / BLR-East |
| customer_id | str | One of ~520 outlets |
| channel | str | Quick-Commerce / Modern-Trade / General-Trade / HoReCa |
| distance_km | float | Depot-to-customer distance |
| sku_id, sku_name, brand | str | Product identity |
| sugar_type | str | Zero (low-sugar) or Reg (regular) |
| pack_format | str | **CAN** or **PET** — the key analytical dimension |
| ordered_cases | int | Cases ordered |
| delivered_cases | int | Cases delivered (≤ ordered) |
| on_time, in_full, otif | 0/1 | Service flags; otif = on_time AND in_full |
| failure_reason | str | Primary reason if not OTIF (else "None") |
| net_realization_per_case | int (₹) | Distributor net realization per case |
| contrib_margin_per_case | int (₹) | Contribution margin per case |
| shortfall_cases, lost_revenue_inr, lost_margin_inr | derived | ordered − delivered, × realization, × margin |

## Calibration assumptions (and their basis)
| Assumption | Value | Basis |
|---|---|---|
| Pre-crisis OTIF | ~89% | FMCG "good" 85–95% (FourKites/MetricHQ); set below 95% target deliberately |
| Crisis onset | 15 Apr 2026 | "Bare since mid-April" (Sahi, Open Magazine) |
| Crisis shape | sharp onset → ~45% can supply trough → late-May partial recovery | Reuters rationing reports; gradual restocking (Business Standard) |
| Pack-format exposure | CAN constrained, PET unaffected | Diet Coke "predominantly cans, minimal PET/glass" (Packaging South Asia) |
| Diet/Zero demand weight | 1.3–1.6× in QC/MT | Low-sugar 5%→30% of volumes; QC "daily ritual" demand (Sahi) |
| Net realization / case | ₹350–540 (CAN premium > PET) | Scaled from VBL ~₹164/case mixed anchor; cans premium |
| Summer uplift | Apr +22%, May +30% | Heatwave double-digit cola growth (Outlook Business) |

## `data/raw/sku_master.csv`
8 SKUs across CAN and PET formats with base daily volume and per-case economics. See file.

## Reproducibility
`SEED = 42`. Re-running `generate_data.py` then `analyze_dmaic.py` reproduces every number in `reports/results.json` exactly.
