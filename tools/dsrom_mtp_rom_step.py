#!/usr/bin/env python3
"""DS-ROM MTP step from the mtp-rom RTL (stream mtp-rom, 2026-10-08; NOT PUBLISHED: input to the next reprice).

    python3 tools/dsrom_mtp_rom_step.py --bench DIR/summary.json [--out results/uarch/dsrom_mtp_rom_step_20261008/step.json]

What it composes (on the 85-stage ledger basis the closure-cost ledger and tools/reprice_20261008.py use):
  1. the published composition (tools/dsrom_1m_allmeasured.compose on the ledger lever set = LED.compose's TOTAL);
  2. + the WFC credit: the closed controller's measured charges switched ON (handoff 49 cycles instead of the
     reference 46, +13 cycles on every stage hop: dsrom_1m_allmeasured.apply_wfc_hop) -- in-process, with the closure
     record's integration_qualified forced true in memory ONLY (the committed closure.json stays unqualified until
     the shim routes close and die-level link STA binds them);
  3. + the integration-shim cycles measured in the mtp-rom benches on every stage hop and in every stage's
     occupancy: link bridge in / out (dsfd_wfc_lnk), the 3:4 start crossing and the outbound prefetch
     (dsfd_wfc_vmx, native VM: write ACK 4 / read valid 5 edges);
  4. the MTP step as the new RTL sequences it (dsfd_mtp_seq): the draft starts at the CLOSING result (after a
     accepted drafts, i.e. a x II after the block's first result) and the release waits for the draft chain AND the
     g - a squashed results:  step(a) = AR + max(a II + D + seed, 5 II) + ctl,  D = 3 DSpark blocks + 5 draft-head
     steps, ctl = the sequencer's measured event cycles (seed, 5 head round trips, DRAFT flit + release);
     against the composition's  step = AR + 5 II + D + seed  (verify of all 6 positions before the draft starts).
     a is distributed per class from the measured owner-mix classes (c_coding, f_agentic, g_assistant_fc of
     results/speculative/v41_mtp_acceptance_qualified_20261003/blend_owner6.json: P(a >= k) = tau(k) - tau(k-1)),
     blended harmonically; the transferable output is the RTL / model step ratio at equal tau.
The 1,792 HALF_PHL / full-rate rows of tools/reprice_20261008.py are shifted by the same per-hop and per-step terms,
scaled to their stage counts (120 / 98 stages; approximate: the per-hop shim cycles x stage hops).
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
CLK = 1.2e9
BLEND = ROOT / "results/speculative/v41_mtp_acceptance_qualified_20261003/blend_owner6.json"
REPRICE = ROOT / "results/arch/reprice_20261008/reprice.json"
OUT = ROOT / "results/uarch/dsrom_mtp_rom_step_20261008/step.json"


def bench_cycles(summary):
    s = json.loads(Path(summary).read_text())
    d = Path(summary).parent
    out = {}
    for case, tag in (("stg_vmnat", "MTP_STG_CYC"), ("s0_tr_forced", "MTP_S0_CYC")):
        log = (d / case / "run.log").read_text()
        m = re.search(rf"^{tag} (.*)$", log, re.M)
        out[case] = {k: float(v) for k, v in re.findall(r"(\w+)=([0-9.]+)", m.group(1))}
    out["all_ok"] = s["all_ok"]
    return out


def compose_ledger(wfc_on: bool, shim_hop_cyc: float, shim_stage_cyc: float):
    import dsrom_closure_cost_ledger as LED
    import dsrom_1m_allmeasured as AM
    with tempfile.TemporaryDirectory(prefix=".mtprom-", dir=LED.OUT) as td:
        scratch = Path(td)
        shutil.copytree(LED.LEV.parent, scratch / "levers")
        (scratch / "levers" / LED.LEV.name).write_text(json.dumps(LED.lever([it for it, _, _ in LED.ITEMS]), indent=1) + "\n")
        a = SimpleNamespace(rec=AM.REC, out=scratch / "composition.json", baseline="recovery", recovery=scratch,
                            window="s81", hop_tier=AM.DEFAULT_HOP_TIER)
        orig = AM.wfc_closure
        if wfc_on:
            c = json.loads(AM.WFC_CLOSURE.read_text())
            c = copy.deepcopy(c)
            c["integration_qualified"] = True            # IN MEMORY ONLY: the credit as it would apply once qualified
            if shim_hop_cyc:
                c["charge"] = dict(c["charge"], hop_delta_cycles=c["charge"]["hop_delta_cycles"] + shim_hop_cyc)
            if shim_stage_cyc:
                # stage occupancy: the shims hold a stage for its start crossing + outbound prefetch; charged on the
                # interval overhead (busy x (1 + ovh)) as the equivalent fraction of the worst stage's busy time
                c["_stage_cyc"] = shim_stage_cyc
            AM.wfc_closure = lambda: c
        try:
            rec = AM.compose(a, write_output=False)
        finally:
            AM.wfc_closure = orig
    m = rec["MTP"]
    return dict(AR_us=rec["AR_us"], AR_tok_s=rec["AR_tok_s"], II_us=m["II_us"], verify_us=m["verify_us"],
                draft_us=m["draft_us"], seed_us=m["seed_commit_us"], step_us=m["step_us"], MTP_tok_s=m["MTP_tok_s"],
                tau=m["tau"], worst_stage=m["worst_stage"].get("hop"), worst_busy_us=m["worst_stage"]["busy_us"],
                wfc=rec["info"].get("wfc"))


def a_dist(tau):
    """P(a = k), k = 0..5, from tau(gamma) gamma = 1..5 (greedy prefix acceptance, the same drafts truncated)"""
    t = [1.0] + [tau[g] for g in range(1, 6)]
    ge = [1.0] + [max(0.0, t[k] - t[k - 1]) for k in range(1, 6)] + [0.0]      # P(a >= k)
    return [max(0.0, ge[k] - ge[k + 1]) for k in range(6)]


OWNER6 = ("a_chat", "b_reasoning", "c_coding", "f_agentic", "g_assistant_fc", "h_creative")   # workload-mix-six-classes


def classes():
    """the owner-6 classes that carry a measured tau(gamma) curve (a_chat / b_reasoning / h_creative are published
    verify-window values only: no accept-length distribution); long-doc / multilingual are not in the owner mix"""
    b = json.loads(BLEND.read_text())
    out = {}
    for c, v in b["classes"].items():
        if c not in OWNER6:
            continue
        g = v.get("greedy") or {}
        if not all(str(k) in g for k in range(1, 6)):
            continue
        tau = {k: g[str(k)]["tau_pooled"] for k in range(1, 6)}
        out[c] = dict(tau=tau, p=a_dist(tau))
    return out


def step_rows(base, ctl_us, cls):
    """per class: the composition's constant step and the RTL-sequenced step expectation; harmonic blend"""
    AR, II, D, S = base["AR_us"], base["II_us"], base["draft_us"], base["seed_us"]
    model_step = AR + 5 * II + D + S
    rows = {}
    for c, v in cls.items():
        e = sum(p * (AR + max(a * II + D + S + ctl_us, 5 * II)) for a, p in enumerate(v["p"]))
        tau5 = v["tau"][5]
        rows[c] = dict(tau5=round(tau5, 4), p_a=[round(x, 4) for x in v["p"]], model_step_us=round(model_step, 3),
                       rtl_step_us=round(e, 3), model_tok_s=round(tau5 * 1e6 / model_step, 1),
                       rtl_tok_s=round(tau5 * 1e6 / e, 1))
    hm = lambda xs: len(xs) / sum(1.0 / x for x in xs)
    blend = dict(model_tok_s=round(hm([r["model_tok_s"] for r in rows.values()]), 1),
                 rtl_tok_s=round(hm([r["rtl_tok_s"] for r in rows.values()]), 1))
    blend["rtl_over_model"] = round(blend["rtl_tok_s"] / blend["model_tok_s"], 4)
    return rows, blend, model_step


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bench", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    bc = bench_cycles(a.bench)
    st, s0 = bc["stg_vmnat"], bc["s0_tr_forced"]
    lnk_cyc = 3 + 3                                       # dsfd_wfc_lnk: +3 in, +3 out (structure: skid out flop + ltx; lrx + skid)
    hop_shim = lnk_cyc                                    # on every stage hop (with the WFC's +13)
    stage_shim = st["start_mean"] + st["done_mean"]       # start crossing + outbound prefetch, per stage job
    # the shim's stage cycles sit between a stage's core done and its outbound flit (on the hop path) and before
    # its core start (on the hop path): charged as hop cycles too (conservative: also in the interval below)
    hop_total = hop_shim + stage_shim
    # sequencer control per step (bench means minus the bench's own adapters: +2 in / +1 out each crossing)
    ctl_cyc = s0["seed_after_close"] + 5 * s0["dh_result_to_next"] + s0["last_dh_to_draft_flit"] + 3 + 6
    ctl_us = ctl_cyc / CLK * 1e6
    base = compose_ledger(False, 0, 0)
    wfc = compose_ledger(True, 0, 0)
    shim = compose_ledger(True, hop_total, 0)
    # II: the worst stage's busy grows by the shim's stage cycles (the stage cannot take the next position until its
    # outbound payload left through the staging buffer)
    shim_ii = dict(shim)
    shim_ii["II_us"] = round(shim["II_us"] + stage_shim / CLK * 1e6, 4)
    shim_ii["step_us"] = round(shim["AR_us"] + 5 * shim_ii["II_us"] + shim["draft_us"] + shim["seed_us"], 3)
    shim_ii["MTP_tok_s"] = round(shim["tau"] * 1e6 / shim_ii["step_us"], 1)
    cls = classes()
    rows, blend, model_step = step_rows(shim_ii, ctl_us, cls)
    # the 1,792 rows (reprice_20261008 'after' totals), shifted by the per-hop / per-step deltas scaled to the stage
    # counts; tau 4.159 with the composition's constant step, and the RTL-sequenced blend ratio
    rp = json.loads(REPRICE.read_text())["ds_rom"]
    after = rp.get("after") or {}
    stages = dict(half_phl=120, full_rate_shared98=98, full_rate_dedicated120=120)
    d_ar_85 = shim_ii["AR_us"] - base["AR_us"]
    d_step_85 = shim_ii["step_us"] - base["step_us"]
    r1792 = {}
    for k, v in after.items():
        if k not in stages or not isinstance(v, dict) or "AR_tok_s" not in v:
            continue
        sc = stages[k] / 85.0
        ar_us = 1e6 / v["AR_tok_s"] + d_ar_85 * sc
        step_us = base["tau"] * 1e6 / v["MTP_tok_s"] + d_step_85 * sc + 5 * (stage_shim / CLK * 1e6) * 0
        r1792[k] = dict(before=v, AR_tok_s=round(1e6 / ar_us, 1), MTP_tok_s_model_step=round(base["tau"] * 1e6 / step_us, 1),
                        MTP_tok_s_rtl_sequenced=round(base["tau"] * 1e6 / step_us * blend["rtl_over_model"], 1),
                        stage_scale=round(sc, 4))
    rec = dict(
        schema="opentallas.dsrom.mtp_rom_step.v1", tool="tools/dsrom_mtp_rom_step.py", published=False,
        note="NOT PUBLISHED: the MTP-step cycles as computed from the mtp-rom RTL, for the next reprice; the WFC "
             "credit is applied in memory only (closure.json integration_qualified stays false until the shim routes "
             "close and the die-level link STA binds them)",
        bench=dict(summary=str(a.bench), all_ok=bc["all_ok"], stg_vmnat=st, s0_tr_forced=s0),
        cycles=dict(lnk_per_hop=lnk_cyc, vmx_start=st["start_mean"], vmx_done_prefetch=st["done_mean"],
                    hop_total=hop_total, stage_occupancy_add=stage_shim, seq_ctl_per_step=round(ctl_cyc, 1),
                    seq_ctl_us=round(ctl_us, 4)),
        compositions=dict(published_ledger=base, wfc_credit_on=wfc, wfc_on_plus_shims=shim_ii),
        step_model=dict(rule_model="step = AR + 5 II + D + seed (the composition)",
                        rule_rtl="step(a) = AR + max(a II + D + seed + ctl, 5 II) (dsfd_mtp_seq: draft from the closing "
                                 "result; release after the draft chain and the g - a squashed results)",
                        model_step_us=round(model_step, 3), per_class=rows, blend_harmonic=blend,
                        tau_basis=str(BLEND.relative_to(ROOT))),
        rows_1792=r1792)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=str) + "\n")
    print(json.dumps(dict(cycles=rec["cycles"], base=dict((k, base[k]) for k in ("AR_us", "II_us", "draft_us", "step_us", "MTP_tok_s")),
                          wfc=dict((k, wfc[k]) for k in ("AR_us", "II_us", "step_us", "MTP_tok_s")),
                          shim=dict((k, shim_ii[k]) for k in ("AR_us", "II_us", "step_us", "MTP_tok_s")),
                          blend=blend, rows_1792=r1792), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
