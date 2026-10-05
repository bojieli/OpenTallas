"""Headline accepted-token rate vs per-position acceptance alpha, using the repo's MTP rate formula:
   rate = tau / (T_verify(P) + T_draft),  T_draft = V41_DRAFT_FRACTION x T_AR (ASSUMED 3/40),  P = gamma + 1 = 6,
   tau(alpha) = sum_{i=0..gamma} alpha^i  (i.i.d. per-position acceptance; the measured chain is NOT i.i.d.).
At gamma 5 this is exactly uarch_model.cons_tau_sweep (rate_mtp x tau / 3.649).  The gamma < 5 rows (DSpark block
truncation, a 'derived' grade) take the verify-time shape Tv(P)/T_AR from the model's own v41_verify_T (ROM, proposal
preset, m=1) and v41_hbm_chain (HBM), anchored so that P = 6 reproduces each headline step."""
import json
V41_TAU = 3.649
DRAFT = 3 / 40
# model shape, measured above in this session from tools/uarch_model.py at origin/main 7b4d51a08 (us)
ROM_TV = {1: 266.8, 2: 332.6, 3: 401.0, 4: 469.5, 5: 537.9, 6: 607.9}   # v41_verify_T(proposal, P, lm=1)
HBM_TV = {1: 356.9, 2: 411.9, 3: 466.9, 4: 521.9, 5: 577.0, 6: 632.0}   # v41_hbm_chain(True, P)
HEAD = {
 "v41_rom_product (consolidation.json headline_table.v41[0])": dict(ar=2786.8, mtp=4588.9, shape=ROM_TV,
     basis="per_user_ar / per_user_mtp; tau 3.649, P 6, m=1 time-multiplexed; draft 3/40 of AR (ASSUMED)"),
 "v41_hbm_w19 (consolidation.json headline_table.v41[1..3], uarch_model HBM_W19)": dict(ar=2261.7, mtp=4765.4, shape=HBM_TV,
     basis="AR 442.14 us; MTP pass 715.82 us + drafter 49.9 us; tau 3.649"),
 "v41_hbm_groupslot_TT (hbm_gpu.json 2801.8 / MICROARCH_MODEL.md 5,673)": dict(ar=2801.8, mtp=5673.0, shape=HBM_TV,
     basis="T_us 356.9 TT; MTP 5,673 at tau 3.649 (MICROARCH_MODEL.md speculation table)"),
}
ALPHAS = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
def tau(a, g): return sum(a ** i for i in range(g + 1))
out = dict(formula=__doc__, alphas=ALPHAS, designs={})
for name, h in HEAD.items():
    Tar = 1e6 / h["ar"]; step6 = V41_TAU * 1e6 / h["mtp"]          # us
    sh = h["shape"]; k = (step6 - DRAFT * Tar) / Tar / (sh[6] / sh[1])  # anchor: P=6 reproduces the headline step
    steps = {g: Tar * (k * sh[g + 1] / sh[1] + DRAFT) for g in range(1, 6)}
    rows = []
    for a in ALPHAS:
        r = dict(alpha=a, tau_g5=round(tau(a, 5), 3), mtp_g5_tok_s=round(tau(a, 5) * 1e6 / steps[5], 1),
                 speedup_g5=round(tau(a, 5) * 1e6 / steps[5] / h["ar"], 3))
        best = max(range(1, 6), key=lambda g: tau(a, g) / steps[g])
        r.update(best_gamma_derived=best, best_gamma_tok_s_derived=round(tau(a, best) * 1e6 / steps[best], 1))
        rows.append(r)
    out["designs"][name] = dict(ar_tok_s=h["ar"], mtp_tok_s_at_tau_3649=h["mtp"], basis=h["basis"],
        T_ar_us=round(Tar, 1), step_us_g5=round(step6, 1), step_over_ar_g5=round(step6 / Tar, 3),
        breakeven_tau_g5=round(step6 / Tar, 3), anchor_k=round(k, 4),
        step_us_by_gamma_derived={g: round(s, 1) for g, s in steps.items()}, rows=rows)
out["tau_reference_points"] = {
  "agentic committed pooled (20 prompts)": 4.654, "agentic committed median of prompts": 4.684,
  "overall mixed headline (36 prompts, 9 workloads)": 3.649, "chat mt_bench": 2.458,
  "InferenceX V4.1-Flash T=1 thinking-on / off (acceptance_tau.json)": [3.51, 4.07]}
json.dump(out, open("sensitivity.json", "w"), indent=1)
for n, d in out["designs"].items():
    print(n, "AR", d["ar_tok_s"], "step/AR", d["step_over_ar_g5"], "breakeven tau", d["breakeven_tau_g5"], d["step_us_by_gamma_derived"])
    for r in d["rows"]: print("  ", r)
