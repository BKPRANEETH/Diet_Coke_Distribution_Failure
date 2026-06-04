"""
generate_data.py
================
Generates a realistic, fully SYNTHETIC order-line dataset for Coca-Cola's
Diet Coke (and adjacent low-sugar) secondary distribution in Bangalore,
Jan 1 - May 31 2026.

WHY SYNTHETIC: Coca-Cola's internal distributor order data is not public.
The data is engineered to reproduce the *documented, real* event - the
April-2026 Diet Coke can shortage in Bengaluru caused by an aluminium-can
supply shock (Strait of Hormuz / Gulf aluminium disruption). Macro facts
and benchmarks are cited in docs/references.md. The transactional data is a
calibrated simulation, NOT real Coca-Cola data.

The generator embeds three TRUE structural drivers that the DMAIC analysis
is designed to rediscover:
  1. Single-pack-format dependence  -> CAN SKUs collapse, PET SKUs survive.
  2. Time-localised supply shock      -> failures spike from ~15-Apr-2026.
  3. Channel sensitivity              -> quick-commerce has tighter windows.

Run:  python src/generate_data.py
Out:  data/raw/sku_master.csv
      data/raw/orders.csv   (order-line granularity)
"""

import numpy as np
import pandas as pd
from pathlib import Path

SEED = 42
rng = np.random.default_rng(SEED)

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# 1. CALENDAR  (Jan 1 - May 31 2026)
# --------------------------------------------------------------------------
dates = pd.date_range("2026-01-01", "2026-05-31", freq="D")

# Crisis ramp for CAN availability (fraction of can demand fulfillable at DC).
# Calibrated to the real timeline: normal -> sharp onset mid-Apr -> trough
# late-Apr/early-May -> partial recovery late-May.
def can_supply_factor(d: pd.Timestamp) -> float:
    if d < pd.Timestamp("2026-04-15"):
        return 1.0                                   # pre-crisis, full supply
    if d < pd.Timestamp("2026-04-25"):               # sharp onset
        t = (d - pd.Timestamp("2026-04-15")).days / 10
        return 1.0 - 0.55 * t                        # 1.00 -> 0.45
    if d < pd.Timestamp("2026-05-20"):               # trough (rationing)
        return 0.45 + rng.normal(0, 0.04)
    # partial recovery
    t = (d - pd.Timestamp("2026-05-20")).days / 11
    return min(0.78, 0.45 + 0.33 * t)

# Summer demand uplift (Apr-May heatwave drives cola demand)
def season_factor(d: pd.Timestamp) -> float:
    base = {1: 0.92, 2: 0.95, 3: 1.05, 4: 1.22, 5: 1.30}[d.month]
    weekend = 1.10 if d.weekday() >= 5 else 1.0      # quick-commerce weekend peak
    return base * weekend

# --------------------------------------------------------------------------
# 2. SKU MASTER
#    pack_format is the crux: CAN SKUs are exposed, PET/GLASS are not.
#    Economics in INR per physical case (distributor net realization &
#    contribution margin). Calibrated to FMCG-beverage norms; documented
#    in docs/data_dictionary.md.
# --------------------------------------------------------------------------
sku_master = pd.DataFrame([
    # sku_id, sku_name, brand, sugar, pack_format, cases/day base, net_real, contrib_margin
    ["DC-CAN-300", "Diet Coke 300ml Can",      "Diet Coke", "Zero", "CAN",   34, 540, 168],
    ["DC-CAN-250", "Diet Coke 250ml Can",      "Diet Coke", "Zero", "CAN",   18, 470, 150],
    ["CZ-CAN-300", "Coke Zero 300ml Can",      "Coke Zero", "Zero", "CAN",   26, 520, 160],
    ["CZ-PET-750", "Coke Zero 750ml PET",      "Coke Zero", "Zero", "PET",   16, 430, 132],
    ["DC-PET-750", "Diet Coke 750ml PET",      "Diet Coke", "Zero", "PET",    6, 450, 138],
    ["CC-PET-750", "Coca-Cola 750ml PET",      "Coca-Cola", "Reg",  "PET",   40, 360, 104],
    ["TU-PET-750", "Thums Up 750ml PET",       "Thums Up",  "Reg",  "PET",   38, 350, 100],
    ["CC-CAN-300", "Coca-Cola 300ml Can",      "Coca-Cola", "Reg",  "CAN",   22, 500, 150],
], columns=["sku_id","sku_name","brand","sugar_type","pack_format",
            "base_cases_per_day","net_realization_per_case","contrib_margin_per_case"])

# --------------------------------------------------------------------------
# 3. NETWORK: depots, routes, channels, customers
# --------------------------------------------------------------------------
depots = ["BLR-North", "BLR-South", "BLR-East"]
channels = {
    # channel: (share of order lines, on-time window tightness, demand weight on Diet/Zero)
    "Quick-Commerce": (0.30, 0.070, 1.6),  # Blinkit/Zepto/Instamart dark stores
    "Modern-Trade":   (0.25, 0.050, 1.3),  # supermarkets (OTIF penalties)
    "General-Trade":  (0.33, 0.030, 0.8),  # kirana
    "HoReCa":         (0.12, 0.045, 1.1),  # cafes, bars, QSR
}
ch_names = list(channels.keys())
ch_probs = np.array([channels[c][0] for c in ch_names])
ch_probs = ch_probs / ch_probs.sum()

# customer base
n_customers = 520
cust_channel = rng.choice(ch_names, size=n_customers, p=ch_probs)
cust_depot = rng.choice(depots, size=n_customers)
cust_dist = rng.uniform(4, 45, size=n_customers).round(1)   # km from depot
customers = pd.DataFrame({
    "customer_id": [f"CUST{1000+i}" for i in range(n_customers)],
    "channel": cust_channel, "depot": cust_depot, "distance_km": cust_dist,
})

# --------------------------------------------------------------------------
# 4. ORDER-LINE GENERATION
# --------------------------------------------------------------------------
rows = []
order_seq = 0
sku_ids = sku_master["sku_id"].values

for d in dates:
    csf = float(np.clip(can_supply_factor(d), 0.0, 1.0))
    sf = season_factor(d)
    # number of order lines this day (scaled by season)
    n_lines = int(rng.normal(420, 35) * sf)
    n_lines = max(250, n_lines)

    cust_idx = rng.integers(0, n_customers, size=n_lines)

    for ci in cust_idx:
        cust = customers.iloc[ci]
        ch = cust["channel"]
        _, window_tightness, diet_weight = channels[ch]

        # SKU selection: weight low-sugar SKUs higher for diet-leaning channels
        w = sku_master["base_cases_per_day"].values.astype(float).copy()
        zero_mask = (sku_master["sugar_type"] == "Zero").values
        w[zero_mask] *= diet_weight
        w = w / w.sum()
        sku_i = rng.choice(len(sku_ids), p=w)
        sku = sku_master.iloc[sku_i]

        # ordered cases (small per drop; quick-commerce smaller, GT larger)
        base = {"Quick-Commerce": 6, "Modern-Trade": 14,
                "General-Trade": 22, "HoReCa": 9}[ch]
        ordered = max(1, int(rng.gamma(shape=3.0, scale=base / 3.0) * sf / 1.0))

        # ---------------- IN-FULL logic ----------------
        is_can = sku["pack_format"] == "CAN"
        in_full = True
        delivered = ordered
        primary_reason = "None"

        # (a) supply-shock allocation hits CAN SKUs from mid-April
        if is_can and csf < 0.999:
            # per-line realised allocation around the day's supply factor
            alloc = float(np.clip(rng.normal(csf, 0.10), 0.0, 1.0))
            # diet/zero cans prioritised LAST in real rationing (premium, low base
            # volume) -> slightly worse allocation for Diet Coke cans
            if sku["brand"] in ("Diet Coke", "Coke Zero"):
                alloc *= 0.9
            alloc = float(np.clip(alloc, 0.0, 1.0))
            delivered = int(round(ordered * alloc))
            if delivered < ordered:
                in_full = False
                primary_reason = "Packaging (aluminium can) unavailability"

        # (b) baseline fulfilment errors (independent of crisis), all SKUs
        if in_full and rng.random() < 0.025:
            in_full = False
            delivered = int(ordered * rng.uniform(0.6, 0.95))
            primary_reason = rng.choice(
                ["Order/picking error", "DC stock-out (forecast miss)",
                 "Damage / quality rejection"], p=[0.45, 0.35, 0.20])

        # ---------------- ON-TIME logic ----------------
        on_time = True
        # base lateness driven by channel window tightness + distance + season load
        p_late = window_tightness + 0.0015 * cust["distance_km"] + 0.03 * (sf - 1.0)
        # logistics strain rises during crisis (re-planning, partial loads)
        if csf < 0.999:
            p_late += 0.04
        p_late = float(np.clip(p_late, 0.01, 0.6))
        if rng.random() < p_late:
            on_time = False
            if primary_reason in ("None",):
                primary_reason = rng.choice(
                    ["Late dispatch from DC", "Route / traffic delay",
                     "Vehicle unavailability"], p=[0.45, 0.35, 0.20])

        otif = on_time and in_full
        if otif:
            primary_reason = "None"

        # dates
        req_lead = {"Quick-Commerce": 1, "Modern-Trade": 2,
                    "General-Trade": 2, "HoReCa": 2}[ch]
        requested = d + pd.Timedelta(days=req_lead)
        actual = requested + (pd.Timedelta(days=0) if on_time
                              else pd.Timedelta(days=int(rng.integers(1, 3))))

        order_seq += 1
        rows.append((
            f"SO{200000+order_seq}", d.date(), requested.date(), actual.date(),
            cust["depot"], cust["customer_id"], ch, round(cust["distance_km"], 1),
            sku["sku_id"], sku["sku_name"], sku["brand"], sku["sugar_type"],
            sku["pack_format"], ordered, delivered,
            int(on_time), int(in_full), int(otif), primary_reason,
            int(sku["net_realization_per_case"]), int(sku["contrib_margin_per_case"]),
        ))

orders = pd.DataFrame(rows, columns=[
    "order_id","order_date","requested_delivery_date","actual_delivery_date",
    "depot","customer_id","channel","distance_km",
    "sku_id","sku_name","brand","sugar_type","pack_format",
    "ordered_cases","delivered_cases","on_time","in_full","otif",
    "failure_reason","net_realization_per_case","contrib_margin_per_case"])

# derived business fields
orders["shortfall_cases"] = orders["ordered_cases"] - orders["delivered_cases"]
orders["lost_revenue_inr"] = orders["shortfall_cases"] * orders["net_realization_per_case"]
orders["lost_margin_inr"] = orders["shortfall_cases"] * orders["contrib_margin_per_case"]
orders["order_date"] = pd.to_datetime(orders["order_date"])

sku_master.to_csv(RAW / "sku_master.csv", index=False)
orders.to_csv(RAW / "orders.csv", index=False)

print(f"Generated {len(orders):,} order lines across {orders['order_date'].nunique()} days.")
print(f"Overall OTIF: {orders['otif'].mean()*100:.1f}%")
print(f"Pre-crisis OTIF (<15-Apr): "
      f"{orders.loc[orders.order_date < '2026-04-15','otif'].mean()*100:.1f}%")
print(f"Crisis OTIF (>=15-Apr):    "
      f"{orders.loc[orders.order_date >= '2026-04-15','otif'].mean()*100:.1f}%")
print(f"Diet Coke CAN OTIF in crisis: "
      f"{orders.loc[(orders.order_date>='2026-04-15') & (orders.sku_id=='DC-CAN-300'),'otif'].mean()*100:.1f}%")
print(f"Files written to {RAW}")
