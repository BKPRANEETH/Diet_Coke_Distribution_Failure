# Data — provenance & honesty note

- `raw/orders.csv` and `raw/sku_master.csv` are **simulated** by `../src/generate_data.py`.
- They are **not** real Coca-Cola data. They are calibrated to the real, cited April-2026
  Diet Coke can shortage and to public FMCG benchmarks — see `../docs/data_dictionary.md`
  and `../docs/references.md`.
- `processed/` is produced by `../src/analyze_dmaic.py` (aggregated DMAIC tables).
- Everything is deterministic (`SEED = 42`) and fully reproducible.
