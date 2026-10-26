#!/usr/bin/env python3
"""DS HBM accelerator (DeepSeek-V4.1-Flash, TP-96, 32 SMs a die, static schedule, Tomahawk-Ultra tier + our protocol)
one decode token at position 1,048,575 (1M context) with every critical-path term taken from a full-shape RTL
measurement where one exists (owner measurement rule 2026-10-04), composed on the executed TP-96 program's fixed
serial order -- the DS-HBM counterpart of tools/dsrom_1m_allmeasured.py.

Base: the adopted measured accelerator rate (results/rtl/dshbm_local_chains_20261004, N1024 SU, levers il + dr + ov:
2,313.0 AR / 5,225.8 MTP).  Its walk (tools/dshbm_baseline_measure.compose_program) prices SM matvecs, the barrier and
the SU chains from RTL, and the rest from the model.  This tool re-walks the same program and replaces:

  coll    results/rtl/dshbm_1m_allmeasured_20261004/collectives.json   (tools/dshbm_1m_coll.py)
          collective endpoint RTL issue -> on-wire, receive -> consume (+ owner reduce for the all-reduce); only the
          PHY + Tomahawk switch + cable traversal stays a labelled Tomahawk-protocol VENDOR BUDGET
  local   results/rtl/dshbm_1m_allmeasured_20261004/local.json         (tools/dshbm_1m_local.py)
          the dedicated-unit steps the baseline priced from the model (index q / scores / local top-k, candidates,
          Engram, the FP8 quantisers, the router top-6 select)
  hbm     results/rtl/dshbm_1m_allmeasured_20261004/hbm_streams.json   (tools/dshbm_1m_hbm.py)
          the token's HBM loads on the timed HBM3E model with the corrected REFpb rules (main c217afff7): index keys,
          window rows, selected compressed-KV source reads, Engram rows, routed-expert fetch, and the SM weight stream
          check (SM time is stretched where the measured stream cannot feed the measured SM demand)

Every term on the path is classified measured / measured_tu_budget (the labelled vendor part of a collective) /
modelled, and the modelled ones are listed with their time.  The same walk is repeated at the clocks the blocks close
at today (results/rtl/hbm_accel_fmax_inventory_20261004/inventory.json + the routed collective endpoint and the SU lane
screen), and for the MTP verify pass (P = 6) with the measured DSpark draft.

    python3 tools/dshbm_1m_allmeasured.py --out results/rtl/dshbm_1m_allmeasured_20261004/composition.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dshbm_baseline_measure as DM  # noqa: E402
import dshbm_chain_levers as CL  # noqa: E402
import w19_hbm_token_compose as WC  # noqa: E402

REC = ROOT / "results/rtl/dshbm_1m_allmeasured_20261004"
BASE = ROOT / "results/rtl/dshbm_baseline_measured_20261004"
CHAINS = ROOT / "results/rtl/dshbm_local_chains_20261004"
FMAX = ROOT / "results/rtl/hbm_accel_fmax_inventory_20261004/inventory.json"
HA3_VERDICT = ROOT / "results/rtl/hbm_accel_ha3_20261004/verdict.json"
DRAFT = ROOT / "results/rtl/dshbm_dspark_draft_20261004/composition.json"
F_FAST, F_SER = DM.F_FAST, DM.F_SER

# the adopted SU configuration (N1024, il + dr + ov): best exact chain among the variant records, attention pipelined
SU1 = [("base", BASE / "su_N1024_M256_b4r5m4a3_dpi_beh_su_cases_v2.json"),
       ("il", CHAINS / "su/su_N1024_M256_b4r5m4a3_dpi_beh_su_cases_v2_il.json"),
       ("dr", CHAINS / "su/su_N1024_M256_b4r5m4a3_dpi_beh_su_cases_v2_ildr.json")]
SU6 = [("base", BASE / "su_N1024_M256_b4r5m4a3_dpi_beh_su_cases_p6om.json"),
       ("il", CHAINS / "su/su_N1024_M256_b4r5m4a3_dpi_beh_su_cases_p6om_il.json"),
       ("dr", CHAINS / "su/su_N1024_M256_b4r5m4a3_dpi_beh_su_cases_p6om_ildr.json")]
# hc_mixes (projection + norm scale + pre/post + Sinkhorn), consumed at the same sublayer's hc_post (post, comb) and
# by the NEXT sublayer's pre-norm (pre): it runs beside the sublayer body; only its excess over the body is exposed.
# HCP: ot_hdc_v41x_hcp spec W 256 (2,048 FP32 lanes), shipped size K 20,480 x 24 rows, golden-exact (DPI FP stand-ins),
# results/rtl/hdc_v41x_hcp_campaign.json benches.spec_w256 "shipped typical x1/x6": 328 / 1,578 cycles (it computes
# its own sum of squares and rsqrt, cmd_scale 1).  pre/post + Sinkhorn: the same N1024/M256 SU element, measured
# golden-exact at full shape in the DS-ROM 1M record (results/rtl/dsrom_1m_allmeasured_20261004/su.json node_us
# attn.hc.pre_post 0.16556 us + attn.hc.sinkhorn 0.52778 us incl. ot_hdc_sinkhorn 41 clocks at routed 151.9 MHz;
# wired at the ROM hub's 22/15 stages, conservative for the HBM SU's 4/5).
HCP_REC = ROOT / "results/rtl/hdc_v41x_hcp_campaign.json"
ROM_SU = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004/su.json"


def hc_mixes_us(P, clk):
    hcp = json.loads(HCP_REC.read_text())["benches"]["spec_w256"]["run"]["cases"]
    name = "shipped typical x1" if P == 1 else "shipped typical x6 (MTP verify)"
    c = next(x for x in hcp if x["name"] == name)
    assert c["errors"] == 0
    su = json.loads(ROM_SU.read_text())["node_us"]
    pp = 0.16556                                       # attn.hc.pre_post wired RTL (patch in the ROM composition)
    sk = su["attn.hc.sinkhorn"]["us"] - 0.0           # front + unit, as composed in the ROM record (0.8822 incl.
    sk = 0.52778                                      # the chain's sumsq/rsqrt: take the sinkhorn node alone)
    return c["last_result_cycles"] / clk["du_fast"] * 1e6 + WC.LOCAL_REPEAT(P) * (pp + sk) * F_SER / clk["su"], \
        f"HCP RTL {c['last_result_cycles']} cyc (spec W256, K 20,480, exact) + SU pre/post 0.166 + Sinkhorn 0.528 us"


DU_FNS = ("index_q", "index_scores", "topk_local", "cand_local", "cand_mask", "engram_fetch", "engram_mix")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT))


def load(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else None


# ---------------------------------------------------------------------------------------------------------------------
# clocks: the target (1.2 GHz streaming, 0.9 GHz serial) and the clocks the blocks close at today
# ---------------------------------------------------------------------------------------------------------------------
TARGET = dict(sm=F_FAST, su=F_SER, attn=F_FAST, du_fast=F_FAST, du_ser=F_SER, coll=F_FAST, hbm=F_FAST)


def closing_clocks():
    """Per domain, the clock the blocks on the token path close at today (SS 60 ps / FF 25 ps), with the evidence.
    A domain runs at its slowest on-path block; a block with only a screen counts at its screen fmax; a block never
    measured keeps the target and is listed (it cannot make the rate faster, only unknown)."""
    inv = json.loads(FMAX.read_text())
    b = {r["module"]: r for r in inv["blocks"]}

    def mhz(name):
        r = b[name]
        return r.get("fmax_mhz_equiv_ss")
    ha3 = json.loads(HA3_VERDICT.read_text())["G_timing"]["baseline_ha3_0"]
    coll_mhz = 1e3 / (0.833333 + (-ha3["ss_setup_wns_ns"]))
    rows = dict(
        sm=(min(mhz("ot_gpu_tc_col"), mhz("ot_gpu_stack"), mhz("ot_gpu_tc16"),
                1e3 / (0.833333 + 0.1367)),     # issue output ports -136.7 ps (closes_signoff false)
            "SM element: min(ot_gpu_tc_col routed -102.66 ps 1,068.8 MHz, ot_gpu_stack screen 1,042.4, ot_gpu_tc16 "
            "routed 1,157.3, ot_hbm_accel_issue output ports -136.7 ps 1,031); bulk copy r12 closes 1,220; the whole "
            "SM element was never routed"),
        su=(638.6, "SU light lane MLAT4/ALAT3 one-lane placed+repaired screen r2r 638.6 MHz "
                   "(results/rtl/dshbm_local_chains_20261004/record.json timing_screen lane_k0_kr0; SFU lane 520.9)"),
        su_sfu=(520.9, "SU SFU lane k1 screen 520.9 MHz (same record)"),
        attn=(min(mhz("ot_hdc_fastfp LAT3 add/mul (SU + attention as built)"), 881.0),
              "attention tile as built on ot_hdc_fastfp LAT3: the multiplier routes 881 MHz at SS (add 975); the tile itself "
              "never routed)"),
        coll=(coll_mhz, f"collective endpoint clk_sm side: routed ot_gpu_coll_endpoint (HA3=0 baseline, in context, "
                        f"540 um) SS setup {ha3['ss_setup_wns_ns']} ns on the RX CDC -> asmb path "
                        f"(results/rtl/hbm_accel_ha3_20261004/verdict.json, main 53ebc1219)"),
        hbm=(mhz("ot_hbm_r14_stream_pc/stack r8b (WR_EN=0)"), "HBM stream PC r8b routed SS +6.28 ps"),
        router=(mhz("ot_gpu_router_topk"), "ot_gpu_router_topk screen 621.5 MHz"),
    )
    return {k: dict(mhz=round(v[0], 1), evidence=v[1]) for k, v in rows.items()}


# ---------------------------------------------------------------------------------------------------------------------
# measured-record adapters (each returns None when its record is absent: the term then stays modelled)
# ---------------------------------------------------------------------------------------------------------------------
class Coll:
    """collectives.json (tools/dshbm_1m_coll.py, ot_hbm_accel_tu_endpoint one-die RTL + labelled TU stub) -> per
    on-path collective: endpoint cycles (TX + RX + owner reduce, at the endpoint clock), serialisation (port pacing,
    clock-independent), the labelled vendor budget (PHY + switch + cable per crossing) and the 0.15 us striping tail
    (budget: equal-latency ports in RTL, inter-chip skew not captured)."""
    HUB = "ha2hub"

    def __init__(self, rec):
        self.rec = rec

    def price(self, op, P):
        if self.rec is None or "classes" not in self.rec:
            return None
        import dshbm_1m_coll as DC
        kind = op["kind"]
        for c in self.rec["classes"]:
            if c["hub"] != self.HUB or c["P"] != P or not c["exact"]:
                continue
            hit = (kind == "all_reduce" and c["kind"] == "all_reduce") or \
                  (kind != "all_reduce" and c["kind"] != "all_reduce" and
                   c["flits_per_rank"] == DC.gather_pf(op["bytes"], P))
            if hit:
                ser = c.get("serialisation_cycles", 0.0)
                return dict(endpoint_cycles=c["endpoint_only_cycles"] - ser, ser_ns=ser / F_FAST * 1e9,
                            budget_ns=c["tu_budget_ns"], tail_us=DC.TU_TAIL_US, cls=c["kind"],
                            how=f"{c['kind']} {c['crossings']} crossing(s), {c['n_runs']} exact runs")
        raise KeyError((kind, op["bytes"], P))


class Local:
    """local.json (tools/dshbm_1m_local.py: RTL on the executor's real operands of L1/L2/L20/L24, bit-exact) ->
    measured cycles + clock per dedicated-unit step.  Layer types share shapes, so a step is taken from the measured
    layer of its type: index layers ratio 2 (L2, L8, L14) <- L2; ratio 1 (L20 .. L36) <- L24 (L20 for its own
    candidates); Engram (L1, L14) <- L1; quantisers have the same widths in every layer."""
    TYPE = {2: 2, 8: 2, 14: 2, 20: 20, 24: 24, 28: 24, 32: 24, 36: 24, 1: 1}

    def __init__(self, rec):
        self.rec = rec

    def _row(self, key):
        r = self.rec["rows"].get(key)
        if r is None or not r.get("exact"):
            return None
        dom = "fast" if r["clock_hz"] > 1.0e9 else "ser"
        out = dict(cycles=r["cycles"], domain=dom, how=r.get("source", ""), fixed=r.get("fixed_cycles"),
                   ingest=r.get("ingest_keys_per_cycle"))
        if r.get("tail_after_last_input") is not None:
            # the select units ingest the scorer's 64-score stream directly (as the DS-ROM composition prices its L20
            # candidate select): only the tail after the last score sits on the chain
            out.update(cycles=r["tail_after_last_input"], how=out["how"] + f" (tail after last score; full "
                       f"{r['cycles']} cyc incl. {r['ingest_cycles']} ingest under the scan)")
        return out

    def get(self, fn, layer=None, keys=None):
        if self.rec is None or "rows" not in self.rec:
            return None
        if fn == "router_top6":
            return self._row("router_top6")
        if fn in ("attn.quant", "ffn.quant", "q_quant", "kv_row_qdq"):
            return self._row(f"L2.{fn}")
        if fn == "engram_mix":
            return self._row("L1.engram_mix")
        if fn == "engram_fetch":
            return dict(cycles=0, domain="fast", how="off path: the Engram row read is issued at token start "
                        "(hashed ids depend only on the history; HBM fork engram_1row_notice 74 ns)", fixed=None,
                        ingest=None)
        if fn == "cand_mask":
            return dict(cycles=0, domain="fast", how="inside index_scores (the indexer array applies the keep bit)",
                        fixed=None, ingest=None)
        t = self.TYPE.get(layer)
        if fn == "topk_local" and layer == 14:
            t = 14
        r = self._row(f"L{t}.{fn}") if t is not None else None
        if r is not None and fn == "index_scores" and keys is not None and r["fixed"] is not None:
            r["cycles"] = r["fixed"] + math.ceil(keys / r["ingest"])
            r["stream_cycles"] = math.ceil(keys / r["ingest"])
        return r


class Hbm:
    """hbm_streams.json (tools/dshbm_1m_hbm.py: ot_hbm_accel_expert_stream_pc on one HBM3E stack, 32 PCs, corrected
    REFpb, 64 refresh phases, data-checked) -> on-path load times (worst phase).

    DEFAULT (owner >= 90 % bandwidth rule, 2026-10-04): the index-key scans and the window rows are issued with the
    stream PC's static-schedule NOTICE (the program is static, so the next scan / window descriptor and its notice
    are posted ahead of the query; measured 1.0 of peak steady at the worst of 64 refresh phases, 0 violations on
    the per-PC DRAM checker).  Token-dependent loads (CKV gather, embedding row) stay as built.  MODE = "as_built"
    gives the earlier everything-as-built walk (a sensitivity); MODE = "notice" puts notice on every load."""
    MODE = "default"
    NOTICE_KINDS = ("window_rows", "index_keys")

    def __init__(self, rec):
        self.rec = rec

    def _s(self, key):
        r = self.rec["streams"][key]
        assert r["exact"] and r["dram_violations"] == 0, key
        return dict(cycles=r["complete_cycles_1p2GHz"]["max"], ns=r["complete_ns"]["max"],
                    how=f"{key}: {r['cases']} phases, {r['complete_ns']['max']:.1f} ns worst", on_path=True,
                    frac=r.get("fraction_of_peak_steady_min"))

    def get(self, name, layer=None):
        if self.rec is None:
            return None
        m = self.MODE
        if m == "default":
            m = "notice" if name.startswith(self.NOTICE_KINDS) else "as_built"
        if name == "window_rows":
            return self._s(f"window_{m}")
        if name.startswith("index_keys"):
            keys = int(name.rsplit("_", 1)[1])
            return self._s(f"scan_L20_{m}" if keys > 6000 else f"scan_L2_{m}")
        if name == "ckv_source_rows":
            sel = self.rec["ckv_selection"]["layers"].get(str(layer))
            n = sel["max_rows_per_stack"] if sel else 7
            k = 2 if n <= 2 else (7 if n <= 7 else 18)
            r = self._s(f"gather_{k}rows_{'notice' if m == 'notice' else 'as_built'}")
            r["how"] += f" (L{layer} worst stack {n} rows -> {k}-row case)"
            return r
        if name == "embedding":
            return self._s("embedding_row_post_at_go" if m == "as_built" else "embedding_row_notice")
        if name == "expert_fetch":
            f = self.rec["routed_expert_fetch"]
            return dict(cycles=f["first_access_ns"]["max"] * 1.2, ns=f["first_access_ns"]["max"], on_path=True,
                        how="sel90 post-REFpb first access worst (per-token 5.212 us worst / 4.974 mean)")
        return None


# ---------------------------------------------------------------------------------------------------------------------
# the walk: the executed TP-96 program, op by op, in its fixed serial order
# ---------------------------------------------------------------------------------------------------------------------
TAU_REC = ROOT / "results/speculative/third_party_acceptance_20261004"


def _tau_sens(step_us):
    import third_party_tau as TP
    return TP.mtp_sensitivity(step_us)


def tau_source():
    """Acceptance tau from tools/third_party_tau.py, DSpark block 5 for DeepSeek-V4.1: default the owner 6-class
    workload blend 4.159 (owner decision 2026-10-05); the published V4.1 3.8879 is the sensitivity."""
    import third_party_tau as TP
    return TP.tau_ds_v41(5), TP.tau_src("deepseek_v41", 5)


# N2048 SU option (+1,024 light lanes, +7.5 mm2/die): only with its measured wire stages (rule-derived BCAST 6 /
# RET 6 for the 2x lane span); records under REC/su_n2048/
W2048 = dict(p1="su_N2048_M256_b6r6m4a3_dpi_beh_su_cases_v2_ildr.json",
             p6="su_N2048_M256_b6r6m4a3_dpi_beh_su_cases_p6om_ildr.json")


def su_tables(variant="n1024", rec=REC):
    if variant == "n2048":
        f1, f6 = rec / "su_n2048" / W2048["p1"], rec / "su_n2048" / W2048["p6"]
        if not (f1.exists() and f6.exists()):
            return None
        a1, a6 = [("w2048", json.loads(f1.read_text()))], [("w2048", json.loads(f6.read_text()))]
        s1, s6 = CL.best_of(a1), CL.best_of(a6)
        t1 = CL.su_table_overlap(s1)
        return t1, CL.su_table_overlap(s6), s1, s6
    a1 = [(t, json.loads(p.read_text())) for t, p in SU1]
    a6 = [(t, json.loads(p.read_text())) for t, p in SU6]
    s1, s6 = CL.best_of(a1), CL.best_of(a6)
    t1 = CL.su_table_overlap(s1)
    reps = s6["chains"][0].get("reps", 2)
    t6 = CL.su_table_overlap(s6) if reps == 6 else DM.su_table(s1, s6, 6)   # as the adopted compose
    return t1, t6, s1, s6


def walk(prog, sm, su, coll, local, hbm, P=1, clk=TARGET, use=("coll", "local", "hbm", "mixes")):
    """Returns (total_us, path rows).  Each row: layer, node, us, cls, budget_us (vendor part), modelled_us."""
    rows = []
    R = WC.LOCAL_REPEAT(P)
    m = dict(n_keys=0)

    def add(L, node, us, cls, how, budget=0.0, domain=None):
        rows.append(dict(layer=L, node=node, us=round(us, 5), cls=cls, how=how, budget_us=round(budget, 5),
                         domain=domain))
    mix_us, mix_how = hc_mixes_us(P, clk)
    if "hbm" in use and hbm.get("embedding"):
        h = hbm.get("embedding")
        rows.append(dict(layer=-2, node="hbm:embedding_row", us=round(h["ns"] / 1e3, 5), cls="measured",
                         how=f"embedding row (10,240 B) at token start ({h['how']})", budget_us=0.0, domain="hbm"))
    for lay in prog["layers"]:
        L = lay["layer"]
        pend, swi = None, False
        mix_open = {}

        def flush():
            nonlocal pend
            if pend:
                us = pend["cyc"] / clk["sm"] * 1e6
                add(L, pend["tag"], us, "measured", "ot_gpu_sm_v RTL lines + drain on real operands", domain="sm")
                add(L, "barrier", DM.BARRIER_CYC / clk["sm"] * 1e6, "measured",
                    "gpu_supply_barrier RTL 78 cycles (62 + 16)", domain="sm")
            pend = None
        for op in lay["ops"]:
            k = op["kind"]
            if k == "mv":
                rows_die = max(r1 - r0 for r0, r1 in op["rows"])
                Rr = math.ceil(rows_die / WC.N_SM)
                lines, drain, hw = sm.op(op["fmt"], op["k"], Rr)
                batch = op["tag"].startswith("expert slot")
                if pend and batch and pend["batch"]:
                    pend["cyc"] += lines
                else:
                    flush()
                    pend = dict(cyc=lines + drain, batch=batch, tag=f"sm:{op['tag']}")
                continue
            if k == "local" and op["fn"] == "swiglu":
                if not swi:
                    us, how = DM.price_local(op, su, clk["su"], set(), WC, m, P)
                    add(L, "swiglu", us, "measured", how, domain="su")
                    swi = True
                continue
            flush()
            if k in ("all_gather", "all_reduce", "topk_merge", "kv_gather"):
                if op["tag"].startswith(WC.OFF_PATH_COLL):
                    continue
                if k == "kv_gather" and "hbm" in use:
                    h = hbm.get("ckv_source_rows", L)
                    if h and h["on_path"]:
                        add(L, "hbm:ckv_source_rows", h["ns"] / 1e3, "measured",
                            f"selected compressed-KV source reads, timed HBM3E REFpb ({h['how']})", domain="hbm")
                sel = 0.0
                if k == "topk_merge" and op.get("what") == "sel":
                    sel = P * 419 / F_FAST * 1e6           # l20_index_topk exact 96 x 512 select, RTL 419 cycles
                    add(L, "select:96x512", sel, "measured", "l20_index_topk RTL 419 cycles (exact)", domain="du_fast")
                elif k == "topk_merge" and op.get("what") == "cand":
                    pass                                       # candidate merge is off-path (OFF_PATH_COLL)
                c = coll.price(op, P) if "coll" in use else None
                if c is not None:
                    ep_us = c["endpoint_cycles"] / clk["coll"] * 1e6 + c["ser_ns"] / 1e3
                    bud = c["budget_ns"] / 1e3
                    add(L, f"coll:{op['tag']}", ep_us + bud, "measured_tu_budget",
                        f"ot_hbm_accel_tu_endpoint RTL {c['endpoint_cycles']:.1f} cyc + port pacing {c['ser_ns']:.1f} ns"
                        f" + TU budget {c['budget_ns']} ns ({c['how']})", budget=bud, domain="coll")
                    add(L, f"tail:{op['tag']}", c["tail_us"], "modelled",
                        "Tomahawk striping tail 0.15 us over ~8 switch chips (uarch_model _TAIL_US; RTL ports equal-latency)")
                else:
                    import uarch_model as U
                    us = U.tu_transport_us(k, P * op["bytes"], "tomahawk_ultra_protocol")
                    if k == "topk_merge" and op.get("what") == "argmax":
                        pass
                    add(L, f"coll:{op['tag']}", us, "modelled", "uarch_model.tu_transport_us (vendor budget)",
                        domain=None)
            elif k == "expert_fetch":
                h = hbm.get("expert_fetch") if "hbm" in use else None
                if h:
                    add(L, "hbm:expert_fetch", h["ns"] / 1e3, "measured",
                        f"routed-expert first access, timed HBM3E REFpb ({h['how']})", domain="hbm")
                else:
                    add(L, "hbm:expert_fetch", DM.FETCH_POSTPONED_NS / 1e3, "modelled", "W19 fetch model 133.2 ns")
            elif k == "local":
                fn = op["fn"]
                if fn == "index_scores":
                    m["n_keys"] = op["n"]
                if fn == "hc_mixes" and "mixes" in use:
                    mix_open[op["which"]] = len(rows)
                    continue
                if fn in WC.OFF_PATH:
                    continue
                if fn in DU_FNS:
                    keys = math.ceil(op["n"] / WC.TP) if fn in ("index_scores", "cand_local", "cand_mask") else None
                    r = local.get(fn, L, keys) if "local" in use else None
                    stream = None
                    if fn == "index_scores" and "hbm" in use:
                        stream = hbm.get(f"index_keys_{keys}") or hbm.get("index_keys")
                    if r is not None:
                        f = clk["du_fast"] if r["domain"] == "fast" else clk["du_ser"]
                        us = R * r["cycles"] / f * 1e6
                        how = f"RTL {r['cycles']} cyc ({r['how']})"
                        if stream is not None and r.get("stream_cycles") is not None:
                            # fixed part + max(the array's 64-key/cycle ingest, the measured HBM key stream)
                            ing = r["stream_cycles"] / f * 1e6
                            sus = stream["ns"] / 1e3
                            us = (r["cycles"] - r["stream_cycles"]) / f * 1e6 + max(ing, sus)
                            how += (f"; HBM key stream {stream['ns']:.1f} ns (as built, worst phase) "
                                    f"{'binds' if sus > ing else 'hidden'} vs ingest {ing * 1e3:.1f} ns")
                        add(L, f"du:{fn}", us, "measured", how, domain="du")
                    else:
                        ns, _ = WC.local_cycles(op, m)
                        add(L, f"du:{fn}", R * ns / 1e3, "modelled", "W19 NODE_NS / local_cycles model price")
                    continue
                if fn == "attend" and "hbm" in use:
                    h = hbm.get("window_rows")
                    if h and h["on_path"]:
                        add(L, "hbm:window_rows", h["ns"] / 1e3, "measured",
                            f"128 window rows, timed HBM3E REFpb worst phase ({h['how']})", domain="hbm")
                if fn == "hc_post" and op["which"] in mix_open:
                    slack = sum(r["us"] for r in rows[mix_open.pop(op["which"]):])
                    exp = max(0.0, mix_us - slack)
                    add(L, f"hcp:hc_mixes.{op['which']}", exp, "measured",
                        f"{mix_how}; {mix_us:.3f} us beside a {slack:.3f} us body: exposed {exp:.3f}", domain="du")
                rows.extend(local_rows(L, op, su, clk, local, P, use, m))
        flush()
    return round(sum(r["us"] for r in rows), 4), rows


def local_rows(L, op, su, clk, local, P, use, m):
    """An SU step (measured chain) plus its model-priced add-ons (FP8 quantiser, top-6, attention tile)."""
    out = []
    fn = op["fn"]
    R = WC.LOCAL_REPEAT(P)

    def row(node, us, cls, how, domain):
        out.append(dict(layer=L, node=node, us=round(us, 5), cls=cls, how=how, budget_us=0.0, domain=domain))
    if fn in ("hc_pre_norm", "final_norm", "q_norm_kv_row"):
        q = None
        if "local" in use:
            if fn == "q_norm_kv_row":
                a_, b_ = local.get("q_quant"), local.get("kv_row_qdq")
                q = dict(cycles=a_["cycles"] + b_["cycles"], domain="ser") if a_ and b_ else None
            else:
                q = local.get("ffn.quant" if op.get("which") == "ffn" else "attn.quant")
        if fn == "q_norm_kv_row":
            k = "q_norm_kv_row"
        elif fn == "hc_pre_norm":
            k = "hc_pre_norm." + op.get("which", "attn")
            k = k if k in su else "hc_pre_norm.attn"
        else:
            k = "final_norm" if "final_norm" in su else "hc_pre_norm.attn"
        row(f"su:{fn}", su[k] / clk["su"] * 1e6, "measured", "SU RTL chain (N1024/M256, exact)", "su")
        if q is not None:
            f = clk["du_fast"] if q["domain"] == "fast" else clk["du_ser"]
            row(f"quant:{fn}", R * q["cycles"] / f * 1e6, "measured",
                f"ot_hdc_actquant RTL {q['cycles']} cyc (exact; q + kv-row QDQ serial on one instance)", "du")
        else:
            row(f"quant:{fn}", R * DM.QUANT_NS * F_FAST / F_SER / 1e3, "modelled", "FP8 quantiser model node 40.6 ns",
                None)
        return out
    if fn == "hc_post":
        row("su:hc_post", su["hc_post." + op["which"]] / clk["su"] * 1e6, "measured", "SU RTL chain", "su")
        return out
    if fn in ("q_rope", "router_act", "moe_sum", "argmax_local"):
        row(f"su:{fn}", su[fn] / clk["su"] * 1e6, "measured", "SU RTL chain", "su")
        return out
    if fn == "route":
        row("su:route", su["route"] / clk["su"] * 1e6, "measured", "SU RTL chain", "su")
        t = local.get("router_top6", L) if "local" in use else None
        if t is not None:
            f = clk.get("router", clk["du_fast"])
            row("du:router_top6", R * t["cycles"] / f * 1e6, "measured", f"router top-6 RTL {t['cycles']} cyc", "du")
        else:
            row("du:router_top6", R * (31.9 + 25.1) * F_FAST / F_SER / 1e3, "modelled", "model node top6 + order",
                None)
        return out
    if fn == "attend":
        T = 640 if op.get("yarn") else 128
        row("su:attend", su[f"attend.T{T}"] / clk["su"] * 1e6, "measured", "SU RTL chain (pipelined with the tile)",
            "su")
        row(f"attn:tile_T{T}", DM.TILE_JOBS(P) * DM.ATT_TILE[T] / clk["attn"] * 1e6, "measured",
            f"attention tile RTL {DM.ATT_TILE[T]} cyc (results/rtl/v41_full_attention_numeric)", "attn")
        return out
    raise KeyError(fn)


# ---------------------------------------------------------------------------------------------------------------------
def summarise(total, rows, extra_us=0.0):
    by = {}
    for r in rows:
        by[r["cls"]] = by.get(r["cls"], 0.0) + r["us"]
    budget = sum(r["budget_us"] for r in rows)
    modelled = by.get("modelled", 0.0)
    fam = {}
    for r in rows:
        if r["cls"] == "modelled":
            f = r["node"].split(":")[0] + ":" + r["node"].split(":")[-1].split(" ")[0]
            fam[f] = round(fam.get(f, 0.0) + r["us"], 3)
    T = total + extra_us
    return dict(total_us=round(T, 3), tok_s=round(1e6 / T, 1),
                us_by_class={k: round(v, 3) for k, v in by.items()},
                tu_budget_us=round(budget, 3), modelled_us=round(modelled + extra_us, 3),
                measured_share_incl_tu_budget=round((total - modelled) / T, 4),
                measured_share_excl_tu_budget=round((total - modelled - budget) / T, 4),
                modelled_by_family=dict(sorted(fam.items(), key=lambda x: -x[1])))


def by_term(rows):
    t = {}
    for r in rows:
        k = r["node"].split(":")[0] if ":" in r["node"] else r["node"]
        t[k] = round(t.get(k, 0.0) + r["us"], 3)
    return t


def mtp(prog, sm, su6, coll, local, hbm, clk, ar, use, tau_override=None):
    """verify(P = 6) on the same walk + the union increments the walk does not carry (model, listed) + the measured
    DSpark draft + seed commit; tau from tau_source()."""
    from hbm_accelerator_model import _load_study
    mstudy, _, _, _ = _load_study(ROOT)
    V1, V6 = mstudy.VERIFY_PARTS[1], mstudy.VERIFY_PARTS[6]
    union = dict(sm=round(V6["sm"] - V1["sm"], 3), fetch=round(V6["fetch"] - V1["fetch"], 3))
    t6, rows6 = walk(prog, sm, su6, coll, local, hbm, P=6, clk=clk, use=use)
    dr = json.loads(DRAFT.read_text())
    row = {r["design"]: r for r in dr["rows"] if r["ctx"] == "1M" and r["scenario"] == "tomahawk_ultra_protocol"}
    ab = row["ablation_w19"]
    draft, seed, tau = ab["as_built"]["draft_us"], ab["seed_commit_us"], dr["tau"]
    if tau_override is None:
        tau, tsrc = tau_source()
    else:
        tau, tsrc = tau_override, f"tau {tau_override:g} fixed (base reproduction only)"
    verify = t6 + union["sm"] + union["fetch"]
    step = verify + draft + seed
    return dict(tau_source=tsrc, verify_p6_us=round(verify, 3), walk_p6_us=t6, union_model_us=union, draft_us=draft,
                seed_commit_us=seed, step_us=round(step, 3), tau=tau, mtp_tok_s=round(tau * 1e6 / step, 1),
                verify_summary=summarise(t6, rows6, union["sm"] + union["fetch"]), verify_by_term=by_term(rows6))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rec", type=Path, default=REC)
    ap.add_argument("--out", type=Path, default=REC / "composition.json")
    a = ap.parse_args()
    prog = json.loads((BASE / "program.json").read_text())
    sm = WC.SMTable([json.loads((ROOT / "results/rtl/w19_sm_real_ops.json").read_text()),
                     json.loads((BASE / "sm_real_ops.json").read_text())], "ar")
    su1, su6, _, _ = su_tables()
    ins = {k: a.rec / f"{k}.json" for k in ("collectives", "local", "hbm_streams")}
    coll, local, hbm = Coll(load(ins["collectives"])), Local(load(ins["local"])), Hbm(load(ins["hbm_streams"]))
    # 0. reproduce the adopted base (nothing replaced): must equal the published 2,313.0 / 432.33 us
    t0, r0 = walk(prog, sm, su1, coll, local, hbm, use=())
    assert abs(t0 - 432.33) < 0.02, t0
    m0 = mtp(prog, sm, su6, coll, local, hbm, TARGET, None, (), tau_override=4.159)
    assert abs(m0["mtp_tok_s"] - 5225.8) < 0.2, m0["mtp_tok_s"]
    use = ("coll", "local", "hbm", "mixes")
    t, rows = walk(prog, sm, su1, coll, local, hbm, use=use)
    ar = summarise(t, rows)
    m = mtp(prog, sm, su6, coll, local, hbm, TARGET, ar, use)
    cc = closing_clocks()
    clk_today = dict(sm=cc["sm"]["mhz"] * 1e6, su=cc["su"]["mhz"] * 1e6, attn=cc["attn"]["mhz"] * 1e6,
                     du_fast=min(cc["sm"]["mhz"], 1200) * 1e6, du_ser=cc["su"]["mhz"] * 1e6,
                     coll=cc["coll"]["mhz"] * 1e6, hbm=min(cc["hbm"]["mhz"], 1200) * 1e6,
                     router=cc["router"]["mhz"] * 1e6)
    tt, rows_t = walk(prog, sm, su1, coll, local, hbm, clk=clk_today, use=use)
    ar_today = summarise(tt, rows_t)
    m_today = mtp(prog, sm, su6, coll, local, hbm, clk_today, ar_today, use)
    still = [dict(term=k, us=v) for k, v in ar["modelled_by_family"].items()]
    sens = {}
    Hbm.MODE = "notice"
    ts, _ = walk(prog, sm, su1, coll, local, hbm, use=use)
    sens["hbm_loads_with_notice"] = dict(AR_us=round(ts, 3), AR_tok_s=round(1e6 / ts, 1),
                                         note="stream PC notice mode on every load (index keys, window, CKV gather, "
                                              "embedding); the headline already has it on the index keys and window")
    Hbm.MODE = "as_built"
    ts, _ = walk(prog, sm, su1, coll, local, hbm, use=use)
    sens["hbm_loads_as_built_no_notice"] = dict(AR_us=round(ts, 3), AR_tok_s=round(1e6 / ts, 1),
                                                note="index keys and window WITHOUT notice (scans 0.617 / 0.506, window "
                                                     "0.198 of peak at the worst refresh phase): the superseded default")
    Hbm.MODE = "default"
    Coll.HUB = "matched"
    ts, _ = walk(prog, sm, su1, coll, local, hbm, use=use)
    sens["collective_hub_port_matched"] = dict(AR_us=round(ts, 3), AR_tok_s=round(1e6 / ts, 1),
                                               note="TU endpoint hub 8 in / 10 out flits a cycle (port-matched) "
                                                    "instead of HA2's 2 / 4")
    Coll.HUB = "ha2hub"
    w = su_tables("n2048", a.rec)
    if w is not None:
        tw, rows_w = walk(prog, sm, w[0], coll, local, hbm, use=use)
        mw = mtp(prog, sm, w[1], coll, local, hbm, TARGET, None, use)
        n2048 = dict(status="measured with rule-derived wire stages BCAST 6 / RET 6", AR_us=round(tw, 3),
                     AR_tok_s=round(1e6 / tw, 1), MTP_tok_s=mw["mtp_tok_s"],
                     ar_gain_pct=round(100 * (t / tw - 1), 2), mtp_gain_pct=round(100 * (mw["mtp_tok_s"] /
                                                                                    m["mtp_tok_s"] - 1), 2),
                     area="+1,024 light lanes ~ +7.5 mm2/die pre-layout (dshbm_local_chains wide lever)",
                     wire_stages=rel(a.rec / "su_n2048" / "wire_stages.json"))
        n2048["verdict"] = ("REJECT (not in the headline): with its real wire stages AR %+.2f%%; MTP %+.2f%% alone, "
                            "and the wider lane array has no area/route/SS-FF (the N1024 lane itself screens 638.6 MHz)"
                            % (n2048["ar_gain_pct"], n2048["mtp_gain_pct"]))
    else:
        n2048 = dict(status="NOT INCLUDED: N2048 with its real wire stages not measured yet")
    rec = dict(
        schema="opentallas.dshbm-1m.allmeasured.composition.v1", context=1048576, position=1048575,
        design="DS-V4.1 HBM accelerator (TP-96, 32 SMs/die, static schedule, Tomahawk-Ultra tier + our protocol); "
               "adopted SU levers il+dr+ov (N1024)",
        base=dict(record="results/rtl/dshbm_local_chains_20261004/record.json (headline measured_adopted_no_new_hardware)",
                  ar_us=t0, ar_tok_s=round(1e6 / t0, 1), mtp_tok_s=m0["mtp_tok_s"], reproduced=True),
        AR_us=ar["total_us"], AR_tok_s=ar["tok_s"], AR=ar, AR_by_term=by_term(rows),
        MTP=m, MTP_tok_s=m["mtp_tok_s"],
        at_closing_clocks=dict(clocks=cc, AR_us=ar_today["total_us"], AR_tok_s=ar_today["tok_s"], AR=ar_today,
                               AR_by_term=by_term(rows_t), MTP_tok_s=m_today["mtp_tok_s"], MTP=m_today),
        option_su_n2048=n2048, sensitivities=sens,
        still_modelled_ar=still,
        tau_sensitivity=_tau_sens(m["step_us"]),
        still_modelled_other=[
            dict(term="Tomahawk-Ultra PHY + switch + cable per crossing", us=ar["tu_budget_us"],
                 why="VENDOR BUDGET (Broadcom SUE RM104 App. A); inside the measured_tu_budget collective rows"),
            dict(term="MTP verify: routed-expert union SM lines / fetch increments", us=m["union_model_us"],
                 why="W19 composer's union pricing, not re-measured"),
            dict(term="MTP verify: LOCAL_REPEAT issue fraction for dedicated-unit steps", us=None,
                 why="W19 model issue fraction applied to the measured unit cycles at P = 6"),
            dict(term="DSpark draft", us=m["draft_us"], why="results/rtl/dshbm_dspark_draft_20261004 (RTL chain + "
                                                            "full-shape; its collectives are the TU model)"),
            dict(term="seed commit", us=m["seed_commit_us"], why="draft record"),
            dict(term="acceptance tau", us=None, why=f"{m['tau_source']}; not an RTL quantity (published V4.1 3.8879 "
                                                     "and range 3.43-4.32 in tau_sensitivity)"),
            dict(term="hc_mixes, compressor, cand_apply, Engram/candidate-merge collectives", us=0.0,
                 why="off the critical path in the program's dependency order (model judgement, unchanged)")],
        path=rows,
        inputs={rel(p): sha(p) for p in list(ins.values()) + [BASE / "program.json", BASE / "sm_real_ops.json",
                                                              FMAX, HA3_VERDICT, DRAFT] + [p for _, p in SU1 + SU6]
                if Path(p).exists()},
        tool_sha256={rel(ROOT / "tools/dshbm_1m_allmeasured.py"): sha(ROOT / "tools/dshbm_1m_allmeasured.py")})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    print(json.dumps(dict(base=t0, AR_us=ar["total_us"], AR_tok_s=ar["tok_s"], by_class=ar["us_by_class"],
                          share=ar["measured_share_incl_tu_budget"], share_x=ar["measured_share_excl_tu_budget"],
                          MTP=m["mtp_tok_s"], today_AR=ar_today["tok_s"], today_MTP=m_today["mtp_tok_s"],
                          by_term=by_term(rows), modelled=ar["modelled_by_family"]), indent=1))
    return rec


if __name__ == "__main__":
    main()
