# Control Plan (DMAIC — Control phase)

Goal: hold the gains, detect the next shock early, and keep OTIF in statistical control.

## 1. SPC monitoring
- **p-chart** of daily OTIF-failure rate, low-sugar portfolio (`reports/figures/08_pchart_control.png`).
- Pre-crisis centre line p̄ = **11.2%**; **UCL = 17.1%**, LCL = 5.2%.
- Crisis window shows **46 days out of control** — exactly what the chart should flag.
- Rule: any point above UCL, or 7 consecutive rising points, triggers the response playbook.

## 2. Early-warning supply-risk dashboard (leading indicators)
| Signal | Threshold (amber → red) | Action |
|---|---|---|
| Aluminium spot index (LME + India premium) | +10% MoM | Review can buffer; alert procurement |
| Inbound can lead-time | > 21 days | Activate 2nd supplier; raise buffer |
| Can days-of-cover at depot | < 14 days | Pre-position substitution; cap promotions |
| Quick-commerce OOS% (Diet Coke SKUs) | > 5% | Trigger substitution playbook |

## 3. Response playbook (when red)
1. Activate **substitution rules** (auto-offer Coke Zero PET when can OOS).
2. Re-allocate available cans by margin × strategic-account priority.
3. Accelerate **PET/glass** production for affected SKUs.
4. Communicate revised fill commitments to key accounts (protect OTIF penalties).

## 4. Standardisation & ownership
- OTIF measurement **SOP** (multiplication method: OT% × IF%; order-line granularity).
- Quarterly **FMEA** review of packaging & ingredient supply risk.
- RACI: Supply Planning (owns buffer & dashboard), Sales Ops/KAM (substitution & accounts), Procurement (2nd supplier), Quality/Green Belt (control plan & audit).

## 5. Control metrics & cadence
| Metric | Target | Cadence |
|---|---|---|
| OTIF (low-sugar) | ≥ 95% structural | Daily (p-chart) |
| Can days-of-cover | ≥ 14 days | Weekly |
| Substitution capture rate | ≥ 25% during OOS | Weekly |
| Recovered margin vs plan | ≥ ₹1.45 cr per comparable shock | Per event |
