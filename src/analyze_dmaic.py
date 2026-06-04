"""
analyze_dmaic.py
================
Runs the full Lean Six Sigma DMAIC analysis on the simulated Bangalore
Diet Coke distribution data and produces:
  - reports/figures/*.png      (8 publication-style charts)
  - data/processed/*.csv       (aggregated tables)
  - reports/results.json       (every headline number, machine-readable)

Phases: Define -> Measure -> Analyze -> Improve -> Control.
Run:  python src/analyze_dmaic.py
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"; PROC.mkdir(parents=True, exist_ok=True)
FIG = ROOT / "reports" / "figures"; FIG.mkdir(parents=True, exist_ok=True)
PROC.mkdir(parents=True, exist_ok=True)

CRISIS_START = pd.Timestamp("2026-04-15")
TARGET_OTIF = 0.95            # FMCG "good" benchmark (see docs/references.md)

# ---- style ----------------------------------------------------------------
RED, DARK, GREY, GREEN, AMBER = "#D6202B", "#1A1A2E", "#9AA0A6", "#1B998B", "#F2A93B"
plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 13,
    "axes.grid": True, "grid.alpha": 0.25, "figure.autolayout": True,
})

df = pd.read_csv(RAW / "orders.csv", parse_dates=["order_date"])
sku = pd.read_csv(RAW / "sku_master.csv")
results = {}

pre = df[df.order_date < CRISIS_START]
crisis = df[df.order_date >= CRISIS_START]
# Low-sugar focus portfolio (the project's scope = Diet Coke + Coke Zero)
lowsugar = df[df.sugar_type == "Zero"]
ls_pre = lowsugar[lowsugar.order_date < CRISIS_START]
ls_crisis = lowsugar[lowsugar.order_date >= CRISIS_START]

def sigma_from_otif(p):
    """Convert OTIF (yield) to process sigma via DPMO."""
    p = min(max(p, 1e-6), 1 - 1e-6)
    dpmo = (1 - p) * 1_000_000
    z = stats.norm.ppf(1 - dpmo / 1_000_000)
    return dpmo, z + 1.5   # 1.5-sigma shift convention

# ===========================================================================
# DEFINE / MEASURE
# ===========================================================================
results["measure"] = {
    "n_order_lines": int(len(df)),
    "n_days": int(df.order_date.nunique()),
    "date_range": [str(df.order_date.min().date()), str(df.order_date.max().date())],
    "overall_otif": round(df.otif.mean(), 4),
    "pre_crisis_otif": round(pre.otif.mean(), 4),
    "crisis_otif": round(crisis.otif.mean(), 4),
    "lowsugar_pre_otif": round(ls_pre.otif.mean(), 4),
    "lowsugar_crisis_otif": round(ls_crisis.otif.mean(), 4),
    "target_otif": TARGET_OTIF,
    "baseline_gap_vs_target_pp": round((TARGET_OTIF - pre.otif.mean()) * 100, 1),
    "fill_rate_overall": round(df.delivered_cases.sum() / df.ordered_cases.sum(), 4),
    "fill_rate_lowsugar_crisis": round(
        ls_crisis.delivered_cases.sum() / ls_crisis.ordered_cases.sum(), 4),
}
dpmo_pre, sig_pre = sigma_from_otif(ls_pre.otif.mean())
dpmo_cri, sig_cri = sigma_from_otif(ls_crisis.otif.mean())
results["measure"]["lowsugar_pre_sigma"] = round(sig_pre, 2)
results["measure"]["lowsugar_crisis_sigma"] = round(sig_cri, 2)
results["measure"]["lowsugar_crisis_dpmo"] = int(dpmo_cri)

# --- Fig 1: daily OTIF time series (low-sugar portfolio) -------------------
daily = (lowsugar.groupby("order_date")
         .agg(otif=("otif", "mean"),
              fill=("delivered_cases", "sum"),
              ordered=("ordered_cases", "sum")).reset_index())
daily["fill_rate"] = daily.fill / daily.ordered
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.plot(daily.order_date, daily.otif, color=RED, lw=1.8, label="Daily OTIF (Diet Coke + Coke Zero)")
ax.plot(daily.order_date, daily.fill_rate, color=GREY, lw=1.2, ls="--", label="Daily case fill rate")
ax.axhline(TARGET_OTIF, color=GREEN, lw=1.4, ls=":", label="FMCG target (95%)")
ax.axvline(CRISIS_START, color=DARK, lw=1.2, ls="--")
ax.annotate("Aluminium-can supply shock\nonset ~15 Apr 2026",
            xy=(CRISIS_START, 0.2), xytext=(pd.Timestamp("2026-02-20"), 0.18),
            fontsize=9, color=DARK, arrowprops=dict(arrowstyle="->", color=DARK))
ax.yaxis.set_major_formatter(PercentFormatter(1.0))
ax.set_ylim(0, 1.02); ax.set_title("Diet Coke / low-sugar OTIF collapse — Bangalore, Jan–May 2026")
ax.set_ylabel("Service level"); ax.legend(loc="lower left", fontsize=8.5, frameon=False)
fig.savefig(FIG / "01_otif_timeseries.png"); plt.close(fig)

# ===========================================================================
# ANALYZE
# ===========================================================================
# --- Pareto of failure reasons in the crisis window -----------------------
fr = (crisis[crisis.failure_reason != "None"]
      .groupby("failure_reason").size().sort_values(ascending=False))
fr_pct = fr / fr.sum()
cum = fr_pct.cumsum()
results["analyze"] = {}
results["analyze"]["failure_pareto_crisis"] = {k: int(v) for k, v in fr.items()}
results["analyze"]["top_reason"] = fr.index[0]
results["analyze"]["top_reason_share"] = round(float(fr_pct.iloc[0]), 4)

fig, ax = plt.subplots(figsize=(10, 5))
bars = ax.bar(range(len(fr)), fr.values, color=[RED if i == 0 else GREY for i in range(len(fr))])
ax.set_xticks(range(len(fr)))
ax.set_xticklabels([t.replace(" ", "\n", 1) for t in fr.index], fontsize=8.5)
ax.set_ylabel("Failed order lines (crisis window)")
ax2 = ax.twinx(); ax2.plot(range(len(fr)), cum.values * 100, color=DARK, marker="o", lw=1.6)
ax2.axhline(80, color=GREEN, ls=":", lw=1.2); ax2.set_ylim(0, 105)
ax2.yaxis.set_major_formatter(PercentFormatter()); ax2.set_ylabel("Cumulative %")
ax.set_title("Pareto of OTIF failure reasons — crisis window (≥15 Apr 2026)")
ax.bar_label(bars, fmt="%d", fontsize=8, padding=2)
fig.savefig(FIG / "02_pareto_failures.png"); plt.close(fig)

# --- OTIF by pack format (pre vs crisis) ----------------------------------
pf = (df.assign(period=np.where(df.order_date < CRISIS_START, "Pre-crisis", "Crisis"))
      .groupby(["pack_format", "period"]).otif.mean().unstack())[["Pre-crisis", "Crisis"]]
results["analyze"]["otif_by_packformat"] = pf.round(4).to_dict()
fig, ax = plt.subplots(figsize=(7, 4.6))
x = np.arange(len(pf)); w = 0.38
ax.bar(x - w/2, pf["Pre-crisis"], w, label="Pre-crisis", color=GREY)
ax.bar(x + w/2, pf["Crisis"], w, label="Crisis", color=RED)
ax.set_xticks(x); ax.set_xticklabels(pf.index)
ax.yaxis.set_major_formatter(PercentFormatter(1.0)); ax.set_ylim(0, 1.0)
ax.set_title("OTIF by pack format: CAN collapses, PET survives")
ax.set_ylabel("OTIF"); ax.legend(frameon=False)
for i, fmt in enumerate(pf.index):
    ax.text(i - w/2, pf["Pre-crisis"][fmt] + .01, f"{pf['Pre-crisis'][fmt]*100:.0f}%", ha="center", fontsize=8)
    ax.text(i + w/2, pf["Crisis"][fmt] + .01, f"{pf['Crisis'][fmt]*100:.0f}%", ha="center", fontsize=8)
fig.savefig(FIG / "03_otif_by_packformat.png"); plt.close(fig)

# --- Chi-square: is pack format associated with OTIF failure in crisis? ----
ct = pd.crosstab(crisis.pack_format, crisis.otif)
chi2, pval, dofv, _ = stats.chi2_contingency(ct)
results["analyze"]["chi2_packformat_otif"] = {
    "chi2": round(float(chi2), 1), "p_value": float(pval), "dof": int(dofv),
    "interpretation": "pack format is significantly associated with OTIF failure"
                      if pval < 0.05 else "no significant association"}

# --- OTIF by channel (crisis) ---------------------------------------------
ch = crisis.groupby("channel").otif.mean().sort_values()
results["analyze"]["otif_by_channel_crisis"] = ch.round(4).to_dict()
fig, ax = plt.subplots(figsize=(7.5, 4))
ax.barh(ch.index, ch.values, color=[RED if v < ch.mean() else AMBER for v in ch.values])
ax.xaxis.set_major_formatter(PercentFormatter(1.0)); ax.set_xlim(0, 1)
ax.set_title("Crisis OTIF by channel"); 
for i, v in enumerate(ch.values): ax.text(v + .01, i, f"{v*100:.0f}%", va="center", fontsize=9)
fig.savefig(FIG / "04_otif_by_channel.png"); plt.close(fig)

# --- Crisis fill rate by SKU ----------------------------------------------
skufill = (crisis.groupby(["sku_id", "sku_name", "pack_format"])
           .apply(lambda g: g.delivered_cases.sum() / g.ordered_cases.sum())
           .reset_index(name="fill_rate").sort_values("fill_rate"))
results["analyze"]["crisis_fill_rate_by_sku"] = dict(
    zip(skufill.sku_id, skufill.fill_rate.round(4)))
fig, ax = plt.subplots(figsize=(9, 4.8))
colors = [RED if pf == "CAN" else GREEN for pf in skufill.pack_format]
ax.barh(skufill.sku_name, skufill.fill_rate, color=colors)
ax.xaxis.set_major_formatter(PercentFormatter(1.0)); ax.set_xlim(0, 1)
ax.set_title("Crisis case fill rate by SKU (red = CAN, green = PET)")
for i, v in enumerate(skufill.fill_rate): ax.text(v + .01, i, f"{v*100:.0f}%", va="center", fontsize=8)
fig.savefig(FIG / "05_fillrate_by_sku.png"); plt.close(fig)

# --- Lost revenue / margin (crisis) ---------------------------------------
lost_by_reason = (crisis.groupby("failure_reason")
                  .agg(lost_margin=("lost_margin_inr", "sum"),
                       lost_rev=("lost_revenue_inr", "sum"))
                  .drop(index="None", errors="ignore")
                  .sort_values("lost_margin", ascending=False))
results["analyze"]["crisis_lost_margin_inr"] = int(crisis.lost_margin_inr.sum())
results["analyze"]["crisis_lost_revenue_inr"] = int(crisis.lost_revenue_inr.sum())
results["analyze"]["lost_margin_by_reason_inr"] = {
    k: int(v) for k, v in lost_by_reason.lost_margin.items()}

# ===========================================================================
# IMPROVE  (counterfactual: what 3 Green-Belt levers recover)
# ===========================================================================
# Levers act ONLY on can-shortage shortfall (the controllable, dominant loss).
can_short = crisis[(crisis.pack_format == "CAN") &
                   (crisis.failure_reason == "Packaging (aluminium can) unavailability")].copy()
total_can_short_cases = int(can_short.shortfall_cases.sum())
total_can_short_margin = int(can_short.lost_margin_inr.sum())

LEVERS = {
    # lever: (% of can shortfall it recovers, note)
    "PET / glass pack diversification (Diet Coke 750ml PET, 250ml glass)": 0.35,
    "Dynamic substitution playbook (auto-offer Coke Zero PET when can OOS)": 0.25,
    "Strategic can buffer stock (4–6 wk) + qualified 2nd supplier": 0.20,
}
recovered = {}
running = 0.0
for lever, rec in LEVERS.items():
    # diminishing overlap: each lever recovers from the *remaining* shortfall
    rem = 1 - running
    eff = rec * rem if False else rec  # keep additive but cap below
    recovered[lever] = int(total_can_short_margin * rec)
    running += rec
running = min(running, 0.85)  # cannot recover more than 85% of a physical shock
total_recovered_margin = int(total_can_short_margin * running)
results["improve"] = {
    "can_shortfall_cases": total_can_short_cases,
    "can_shortfall_margin_inr": total_can_short_margin,
    "lever_recovered_margin_inr": recovered,
    "total_recoverable_margin_inr": total_recovered_margin,
    "total_recoverable_share": round(running, 2),
}

# Counterfactual crisis OTIF for low-sugar after substitution+PET shift:
# assume levers convert `running` share of can-shortfall lines into fulfilled.
ls_c = ls_crisis.copy()
mask_recover = (ls_c.pack_format == "CAN") & \
               (ls_c.failure_reason == "Packaging (aluminium can) unavailability")
recover_flags = mask_recover & (np.random.default_rng(7).random(len(ls_c)) < running)
ls_c.loc[recover_flags, "otif"] = 1
post_crisis_otif = ls_c.otif.mean()
results["improve"]["lowsugar_crisis_otif_after"] = round(float(post_crisis_otif), 4)
results["improve"]["structural_target_otif"] = TARGET_OTIF

# --- Fig 6: improvement scenario bars -------------------------------------
labels = ["Pre-crisis\nbaseline", "Crisis\n(actual)", "Crisis\n(after levers)", "Structural\ntarget"]
vals = [ls_pre.otif.mean(), ls_crisis.otif.mean(), post_crisis_otif, TARGET_OTIF]
cols = [GREY, RED, GREEN, DARK]
fig, ax = plt.subplots(figsize=(8, 4.6))
b = ax.bar(labels, vals, color=cols)
ax.yaxis.set_major_formatter(PercentFormatter(1.0)); ax.set_ylim(0, 1.0)
ax.set_title("Diet Coke / low-sugar OTIF: baseline → crisis → recovery")
ax.bar_label(b, labels=[f"{v*100:.0f}%" for v in vals], padding=3, fontsize=10, fontweight="bold")
fig.savefig(FIG / "06_improve_scenario.png"); plt.close(fig)

# --- Fig 7: recoverable margin waterfall ----------------------------------
fig, ax = plt.subplots(figsize=(9, 4.8))
items = ["Total can\nshortfall"] + [k.split(" (")[0].replace(" ", "\n", 1) for k in recovered] + ["Residual\n(physical shock)"]
total = total_can_short_margin / 1e7  # in INR crore
recs = [v / 1e7 for v in recovered.values()]
residual = total - sum(recs)
ax.bar(0, total, color=RED, width=0.6)
running_top = total
for i, r in enumerate(recs, start=1):
    ax.bar(i, r, bottom=running_top - r, color=GREEN, width=0.6); running_top -= r
ax.bar(len(recs) + 1, residual, color=GREY, width=0.6)
ax.set_xticks(range(len(items))); ax.set_xticklabels(items, fontsize=8)
ax.set_ylabel("INR crore (contribution margin)")
ax.set_title("Recoverable margin by intervention (crisis window)")
fig.savefig(FIG / "07_recoverable_waterfall.png"); plt.close(fig)

# ===========================================================================
# CONTROL  (p-chart of daily low-sugar OTIF)
# ===========================================================================
dctrl = (lowsugar.groupby("order_date")
         .agg(n=("otif", "size"), defects=("otif", lambda s: (s == 0).sum())).reset_index())
dctrl["p"] = dctrl.defects / dctrl.n
pbar_pre = dctrl[dctrl.order_date < CRISIS_START].defects.sum() / dctrl[dctrl.order_date < CRISIS_START].n.sum()
nbar = dctrl.n.mean()
ucl = pbar_pre + 3 * np.sqrt(pbar_pre * (1 - pbar_pre) / nbar)
lcl = max(0, pbar_pre - 3 * np.sqrt(pbar_pre * (1 - pbar_pre) / nbar))
results["control"] = {
    "pre_crisis_defect_rate": round(float(pbar_pre), 4),
    "ucl": round(float(ucl), 4), "lcl": round(float(lcl), 4),
    "days_out_of_control": int((dctrl.p > ucl).sum()),
    "early_warning_signals": [
        "Aluminium spot price index (LME + India premium) breaching +10% MoM",
        "Inbound can lead-time > 21 days",
        "Can days-of-cover < 14 days at depot",
        "Quick-commerce sell-out (OOS%) > 5% on Diet Coke SKUs",
    ],
}
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.plot(dctrl.order_date, dctrl.p, color=DARK, lw=1.2, marker=".", ms=3)
ax.axhline(pbar_pre, color=GREEN, ls="-", lw=1.2, label=f"Centre line (pre-crisis p̄={pbar_pre*100:.1f}%)")
ax.axhline(ucl, color=RED, ls="--", lw=1.2, label=f"UCL ({ucl*100:.1f}%)")
ax.axvline(CRISIS_START, color=GREY, ls=":", lw=1)
ax.yaxis.set_major_formatter(PercentFormatter(1.0))
ax.set_title("Control chart (p-chart): daily OTIF-failure rate, low-sugar portfolio")
ax.set_ylabel("OTIF failure rate"); ax.legend(fontsize=8.5, frameon=False, loc="upper left")
fig.savefig(FIG / "08_pchart_control.png"); plt.close(fig)

# ===========================================================================
# SAVE PROCESSED TABLES + RESULTS
# ===========================================================================
daily.to_csv(PROC / "daily_otif_lowsugar.csv", index=False)
pf.to_csv(PROC / "otif_by_packformat.csv")
skufill.to_csv(PROC / "crisis_fill_rate_by_sku.csv", index=False)
lost_by_reason.to_csv(PROC / "crisis_lost_margin_by_reason.csv")
fr.rename("failed_lines").to_csv(PROC / "crisis_failure_pareto.csv")

with open(ROOT / "reports" / "results.json", "w") as f:
    json.dump(results, f, indent=2)

print("=== HEADLINE RESULTS ===")
print(json.dumps({
    "pre_crisis_otif": results["measure"]["pre_crisis_otif"],
    "lowsugar_crisis_otif": results["measure"]["lowsugar_crisis_otif"],
    "top_reason": results["analyze"]["top_reason"],
    "top_reason_share": results["analyze"]["top_reason_share"],
    "crisis_lost_margin_cr": round(results["analyze"]["crisis_lost_margin_inr"]/1e7, 2),
    "recoverable_margin_cr": round(results["improve"]["total_recoverable_margin_inr"]/1e7, 2),
    "otif_after_levers": results["improve"]["lowsugar_crisis_otif_after"],
    "crisis_sigma": results["measure"]["lowsugar_crisis_sigma"],
}, indent=2))
print(f"\nFigures -> {FIG}\nResults -> reports/results.json")
