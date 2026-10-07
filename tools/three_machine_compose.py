#!/usr/bin/env python3
"""Recompose the three machines from committed lever records, with an adoption guard (one command).

  DS ROM   DeepSeek-V4.1 1M (P1,048,575): tools/dsrom_1m_allmeasured.compose() over the lever records
           results/rtl/dsrom_recovery_20261004/levers/*.json (ADOPT + exact applied; PENDING_SSFF recomposed
           separately as CONDITIONAL, never in the headline).  MTP at the adopted owner-blend tau (4.159),
           published 3.8879 as the sensitivity (tools/third_party_tau.py).
  Qwen ROM Qwen3-8B 8K (P8191): the measured STREAM4 full36+HEAD token (terminal.json, 193,955 cycles) plus the
           adopted in-context core closure's added cycles (claude_context_20261005/verdict.json) and the closed
           slab's MUL_LAT 7 (+217/token, VERDICT_r11c.json) and the ADOPT+exact Qwen lever records (QWEN_LEVERS:
           KV_MAP=1 Option M, its measured cold-layer cost; modelled costs only as a labelled sensitivity).  KV guard: the token's MEMSTAT landing sectors must equal
           the config's full FP8 window (36 x 8 x 128 x 2 x 8,192 B = 576 MiB/token), else refused.
           MTP mode = AR (DSpark verdict AR_MODE: below AR on STREAM4).
  LINKS    OWNER 2026-10-06: FULL RS(544,514) FEC on every off-package link of both machines (DS ROM: RTL-measured
           full-KP4 hops / collectives, links_full_fec.json, + cable flight per hop class from the S81 rack record;
           HBM: the SUE endpoint PHY at the full-KP4 channel on every switch crossing).  Light FEC = superseded row.
  HBM      DS HBM accelerator 1M: the matched reference gate (dshbm_matched_reference_20261005) + the exact HBM
           levers (joint PQ+XMAP, paired W2 PACK; tools/dshbm_hbm_opt_compose.py output joint_r2) + the die
           wire stages priced at floor / median / bound (hbm_accel_die_floorplan_20261005/wire_stages.json).

GUARD (refuses to publish, exit 2):
  * an ADOPT lever record that is not exact, or an unknown verdict;
  * a lever applied in the published DS ROM composition that is not ADOPT+exact now (or whose record changed /
    disappeared), or an ADOPT+exact lever the published composition does not apply (missing);
  * the same two checks on the fresh recomposition;
  * Qwen: core closure not SS/FF >= 0, or its token_cycles_before != the measured terminal token;
  * HBM: a non-exact lever (e.g. the analytic item-3 x map) included, a lever input whose sha256 drifted, or a
    basis that is not the matched gate.

    python3 tools/three_machine_compose.py            # recompose, guard, write record + table, scoreboard --check
    python3 tools/three_machine_compose.py --check    # guard + recompose, compare with the committed record only
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

RECOVERY = ROOT / "results/rtl/dsrom_recovery_20261004"
QWEN_TERMINAL = ROOT / "results/rtl/qwen_plain_ar_stream4_P8191_20261005/terminal.json"
QWEN_CORE = ROOT / "results/rtl/qwen_core_decode_closure_20261004/claude_context_20261005/verdict.json"
QWEN_DSPARK = ROOT / "results/rtl/qwen_rom_kv_fullbw_20261004/dspark_verdict.json"
QWEN_SLAB = ROOT / "results/rtl/qwen_slab_share_20261005/structural_route_20261005/VERDICT_r11c.json"
QWEN_CONFIG = ROOT / "compiler/models/qwen3-8b/config.json"
# Qwen lever records (schema opentallas.qwen-rom.lever.v1): ADOPT + exact are composed with their measured token_cost;
# any modelled cost is reported as a labelled sensitivity, never in the headline.
QWEN_LEVERS = [ROOT / "results/rtl/qwen_stream4_kvmap_m_20261006/lever.json"]
QWEN_CLOSURE = ROOT / "results/rtl/qwen_rom_closed_20261006/closure.json"
QWEN_LEVER_SCHEMA = "opentallas.qwen-rom.lever.v1"
QWEN_P0_CAPACITY = ROOT / "results/rtl/qwen_rom_combined_p0_20261005/stream4_capacity_r1/result.json"
# r18g die-level routed wire bound (claude/qwen-die-rebuild-20261005 279518cd0, path_sta r18g_i50_*): NOT composed --
# GRT i50 11,534 overflow (route not closed) and the r18 frame's tiles have the KV slice / fill port removed (KV over a
# 1,056-track stack link), so it is not yet a die that carries the measured STREAM4 landing.  Reported as PENDING only.
QWEN_WIRE_PENDING = dict(record="claude/qwen-die-rebuild-20261005@279518cd0 results/rtl/qwen_rom_die_r17_20261005/"
                                "path_sta/r18g_i50_wire8k_skew{0,65}.json (STREAM4 deltas per CLAUDE QWEN-PHYS 08:29Z)",
                         penalty_cycles=dict(skew0=13305, skew65=16268), grt_overflow=11534,
                         status="PENDING: die-top route not done (r20c GRT i50 overflow 7,972; flat and region pilots did not "
                                "complete, results/rtl/qwen_rom_closed_20261006/closure.json); r18g bound kept as the last priced wire bound")
HBM_MATCHED = ROOT / "results/rtl/dshbm_matched_reference_20261005/composition.json"
HBM_OPT = ROOT / "results/rtl/dshbm_hbm_opt_20261005/joint_r2/composition.json"
WIRE = ROOT / "results/rtl/hbm_accel_die_floorplan_20261005/wire_stages.json"
OUT = ROOT / "results/arch/three_machine_compose"
WIRE_BASES = (("floor", "stages_430_manhattan"), ("median", "stages_430_median_bundle"), ("bound", "stages_430"))
LEVER_SCHEMA = "opentallas.dsrom-recovery.lever.v1"
# OWNER 2026-10-06: full RS(544,514) FEC on every off-package link of BOTH machines.  HBM accelerator: the SUE RM104
# crossing's endpoint "Ethernet link + PHY Tx+Rx < 100 ns" (dshbm_1m_coll.TU_PHY_NS) becomes the full-KP4 channel the
# ROM hop is measured with (technology.json links.rom_board_serdes full_kp4_fec_s: 200 ns channel incl. ~0.3 m = 2 ns
# of board flight; the HBM cable is priced separately in TU_CABLE_NS) = 198 ns.  The switch's 250 ns already
# "includes its PHY/FEC" (RM104).  The DS ROM side is measured in RTL (links_full_fec.json).
HBM_FULL_FEC_PHY_NS = 200.0 - 2.0
KNOWN_VERDICTS = {"ADOPT", "REJECT", "PENDING_SSFF"}


class Refused(Exception):
    pass


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    p = Path(p).resolve()
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


def load(p):
    return json.loads(Path(p).read_text())


# ------------------------------------------------------------------------------------------------- DS ROM levers
def read_levers(lever_dir: Path):
    """All lever records (schema v1) with their adoption class; refuses inconsistent records."""
    out, errs = {}, []
    for f in sorted(lever_dir.glob("*.json")):
        r = load(f)
        if r.get("schema") != LEVER_SCHEMA:
            continue
        v, ex = r.get("verdict"), r.get("exact")
        if v not in KNOWN_VERDICTS:
            errs.append(f"{r['lever']}: unknown verdict {v!r}")
        if v == "ADOPT" and ex is not True:
            errs.append(f"{r['lever']}: verdict ADOPT but exact={ex!r} (an ADOPT lever must be exact)")
        cls = ("adopted" if v == "ADOPT" and ex is True else
               "conditional" if v == "PENDING_SSFF" and ex is True else "excluded")
        out[r["lever"]] = dict(lever=r["lever"], verdict=v, exact=ex, cls=cls, record=rel(f), path=f,
                               sha256=sha(f), note=r.get("verdict_reason") or r.get("note") or "")
    if errs:
        raise Refused("lever records: " + "; ".join(errs))
    return out


def guard_applied(levers: dict, applied: list, what: str):
    """`applied` = info.levers.applied of a DS ROM composition.  Refuse unless it is exactly the ADOPT+exact set
    with the current record bytes."""
    errs = []
    adopted = {k for k, v in levers.items() if v["cls"] == "adopted"}
    seen = set()
    for row in applied:
        k = row["lever"]
        seen.add(k)
        if k not in levers:
            errs.append(f"{what} applies lever {k!r} whose record is gone (ADOPT lever missing)")
        elif levers[k]["cls"] != "adopted":
            errs.append(f"{what} includes lever {k!r} with verdict {levers[k]['verdict']} exact={levers[k]['exact']} "
                        "(only ADOPT + exact may be included)")
        elif row.get("sha256") != levers[k]["sha256"]:
            errs.append(f"{what} applied lever {k!r} from a different record version (stale composition)")
    for k in sorted(adopted - seen):
        errs.append(f"{what} is missing ADOPT lever {k!r}")
    if errs:
        raise Refused("; ".join(errs))


def _args(recovery: Path, hop_tier=None):
    import dsrom_1m_allmeasured as D
    return argparse.Namespace(rec=D.REC, out=Path("/dev/null"), baseline="recovery", recovery=recovery,
                              window="s81", hop_tier=hop_tier or D.DEFAULT_HOP_TIER)


def _row(rec):
    m = rec["MTP"]
    return dict(AR_us=rec["AR_us"], AR_tok_s=rec["AR_tok_s"], MTP_step_us=m["step_us"], MTP_tok_s=m["MTP_tok_s"],
                MTP_tok_s_tau_published=m["tau_sensitivity"]["published"]["MTP_tok_s"], II_us=m["II_us"],
                measured_share=rec["measured_share"])


def _delta(new, base):
    return {k: round(new[k] - base[k], 3) for k in ("AR_us", "AR_tok_s", "MTP_step_us", "MTP_tok_s")}


def ds_rom(recovery: Path, levers: dict, deltas=True):
    import dsrom_1m_allmeasured as D
    base = D.compose(_args(recovery), write_output=False)
    guard_applied(levers, base["info"]["levers"]["applied"], "fresh DS ROM recomposition")
    b = _row(base)
    per = {}
    if deltas:
        for k, v in levers.items():
            if v["cls"] == "adopted":       # delta = headline - headline without this lever
                r = _row(D.compose(_args(recovery), excluded_levers=(k,), write_output=False))
                per[k] = dict(cls="adopted", verdict=v["verdict"], record=v["record"], delta=_delta(b, r))
        with tempfile.TemporaryDirectory() as td:
            for k, v in levers.items():
                if v["cls"] != "conditional":
                    continue
                r = _row(_with_flipped(recovery, Path(td), [k]))
                per[k] = dict(cls="conditional", verdict=v["verdict"], record=v["record"], delta=_delta(r, b),
                              if_adopted=r)
            # alternatives: conditional levers replacing the same nodes (e.g. field_spine vs field_spine_pq) are
            # not stacked; the joint keeps the one with the larger individual AR gain and lists the other
            cond = [k for k, v in levers.items() if v["cls"] == "conditional"]
            nodes = {k: set(load(levers[k]["path"]).get("nodes", {})) for k in cond}
            dropped = {}
            for x in cond:
                for y in cond:
                    if x < y and nodes[x] & nodes[y]:
                        lo, hi = sorted((x, y), key=lambda k: per[k]["delta"]["AR_us"], reverse=True)
                        dropped[lo] = f"overlaps {hi} on {len(nodes[x] & nodes[y])} nodes; {hi} kept in the joint"
            cond = [k for k in cond if k not in dropped]
            joint = _row(_with_flipped(recovery, Path(td), cond)) if cond else None
        for k, v in levers.items():
            if v["cls"] == "excluded":
                per[k] = dict(cls="excluded", verdict=v["verdict"], exact=v["exact"], record=v["record"],
                              note=v["note"][:240])
    else:
        joint, cond, dropped = None, [], {}
    m = base["MTP"]
    light = _row(D.compose(_args(recovery, "light_fec"), write_output=False))
    link_fec = dict(hop_tier=base["info"]["hop_tier"], full_fec=base["info"].get("full_fec"),
                    draft_full_fec=base["info"].get("draft_blocks", {}).get("full_fec"),
                    light_fec_superseded=light, delta_vs_light_fec=_delta(b, light),
                    rule="OWNER 2026-10-06: full RS(544,514) on every off-package link (stage hops, token return, TP4 "
                         "collectives, embed and draft links, all re-measured in RTL) + cable flight per hop class "
                         "(results/arch/dsrom_s81_rack_20261006/rack.json); light FEC kept only as the superseded row")
    return base, dict(
        tool="tools/dsrom_1m_allmeasured.py compose() (recovery baseline)", link_fec=link_fec,
        **b, tau=m["tau"], tau_source=m["tau_source"], tau_sensitivity=m["tau_sensitivity"],
        MTP_physical_qualified=m.get("physical_qualified"), MTP_qualified_headline_rate=m.get("qualified_headline_rate"),
        still_modelled_total_us=base["still_modelled_total_us"],
        levers=per, conditional_all=dict(levers=cond, alternatives_not_stacked=dropped, composed=joint,
                                         note="all PENDING_SSFF levers (alternatives resolved) flipped to ADOPT together; not a headline"))


def _with_flipped(recovery: Path, td: Path, names):
    """Compose as if the named PENDING_SSFF levers were ADOPT (same apply_levers semantics), in a scratch copy."""
    import dsrom_1m_allmeasured as D
    tmp = td / ("r_" + "_".join(names))
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(recovery / "levers", tmp / "levers")
    for n in names:
        for f in (tmp / "levers").glob("*.json"):
            r = load(f)
            if r.get("lever") == n:
                r["verdict"] = "ADOPT"
                f.write_text(json.dumps(r))
    old_rel, D.rel = D.rel, rel          # the scratch copy lives outside the repository
    try:
        return D.compose(_args(tmp), write_output=False)
    finally:
        D.rel = old_rel


# ------------------------------------------------------------------------------------------------------ Qwen ROM
def qwen_rom():
    t, core, dsp = load(QWEN_TERMINAL), load(QWEN_CORE), load(QWEN_DSPARK)
    if not (t["status"] == "PASS" and t["process_exit"] == 0 and t["total_cycles"] == t["total_edges"]):
        raise Refused("Qwen terminal.json is not a PASS full token")
    ad = core["adopted"]
    if not (ad["setup_ss_ref_ps"] >= 0 and ad["hold_ff_ref_ps"] >= 0 and ad["drc_errors"] == 0):
        raise Refused(f"Qwen core-context lever {ad['variant']} does not close SS60/FF25")
    if ad["token_cycles_before"] != t["total_cycles"]:
        raise Refused(f"Qwen core-context added cycles composed on {ad['token_cycles_before']}, "
                      f"terminal token is {t['total_cycles']} (stale)")
    clk = ad["tok_per_s_before"] * ad["token_cycles_before"]
    if abs(clk - 1.2e9) > 1e6:
        raise Refused(f"Qwen clock basis {clk:.4g} Hz is not 1.2 GHz")
    clk = 1.2e9
    # ---- KV traffic audit (QWEN-KV-RECONCILE 2026-10-06): the measured token must carry the WHOLE mandatory FP8 KV
    # window of every layer (config: layers x KV heads x head_dim x {K,V} x 8,192 positions x 1 B), read from the
    # runtime's own MEMSTAT counters (one 32 B landing sector per count), else the headline is refused.
    import re
    cfg = load(QWEN_CONFIG)
    tp = 4
    kv_sys_token = cfg["num_hidden_layers"] * cfg["num_key_value_heads"] * cfg["head_dim"] * 2 * (t["position"] + 1)
    log = QWEN_TERMINAL.parent / "runtime.log"
    per_die, steady = {}, []
    for ln in log.read_text().splitlines():
        m = re.match(r"MEMSTAT (\S+) die(\d) fill_cycles=(\d+) fill_sectors=(\d+).*fill_exposed=(\d+)", ln)
        if m:
            d = per_die.setdefault(m[2], dict(sectors=0, exposed=0))
            d["sectors"] += int(m[4]); d["exposed"] += int(m[5])
            if m[2] == "0" and int(m[4]) == 131072 and int(m[5]) == 0:
                steady.append(int(m[3]))
    if len(per_die) != tp or any(d["sectors"] * 32 * tp != kv_sys_token for d in per_die.values()):
        raise Refused(f"Qwen token does not carry the full KV window: per-die sectors "
                      f"{ {k: v['sectors'] for k, v in per_die.items()} } vs {kv_sys_token // 32 // tp} expected")
    peak_die = 4 * 32 * 32 / 1.024e-9
    win = kv_sys_token // tp // cfg["num_hidden_layers"]
    mean_fill = sum(steady) / len(steady)
    p0 = load(QWEN_P0_CAPACITY)
    sc = p0["source_capacity"]
    kv = dict(
        bytes_system_token=kv_sys_token, MiB_system_token=kv_sys_token / 2**20, bytes_per_rank_layer=win,
        sectors_per_die_token={k: v["sectors"] for k, v in per_die.items()},
        exposed_fill_cycles_per_die=per_die["0"]["exposed"],
        steady_window_fill_cycles=dict(n=len(steady), min=min(steady), mean=round(mean_fill, 1), max=max(steady)),
        landing_bytes_per_core_cycle_per_rank=dict(mean=round(win / mean_fill, 1), best=round(win / min(steady), 1)),
        achieved_TBps_per_die=dict(mean=round(win / mean_fill * clk / 1e12, 3), best=round(win / min(steady) * clk / 1e12, 3)),
        pct_of_4stack_peak=dict(mean=round(100 * win / mean_fill * clk / peak_die, 1),
                                best=round(100 * win / min(steady) * clk / peak_die, 1)),
        token_average_system_TBps=None,
        record=rel(log),
        not_this_vehicle=dict(
            record=rel(QWEN_P0_CAPACITY),
            P0_return_bytes_per_core_cycle_per_rank=sc["return_records_per_stack_core_max"]
            * sc["payload_bytes_per_record"] * sc["stacks_per_rank"],
            P0_payload_floor_us=p0["floor"]["at_assumed_1p2GHz_us"],
            verdict="the Codex P0 integration vehicle serialises each stack's 32 PC landings through ONE 288-bit sealed "
                    "frame per core edge (ot_qwen_s4_stack_transport); the measured headline token lands every PC in "
                    "parallel (ot_qwen_rt_kv_stream4_service l_v[127:0]). P0's floor describes P0's transport, not the "
                    "measured machine; P0 must adopt the per-PC landing (ot_qwen_stream4_cdc_pc RSEL=1 per PC)"))
    # slab MUL_LAT 7 (closed r11c SS60/FF25): +1 cycle per ME op, 217 ME ops / AR token
    slab = load(QWEN_SLAB)
    sg = slab["signoff"]
    if not (sg["SS60_setup_ps"] >= 0 and sg["FF25_hold_ps"] >= 0 and sg["violating_endpoints"] == 0 and sg["drc"] == 0
            and sg["pins_over_liberty_320ps"] == 0):
        raise Refused(f"Qwen slab {slab['adopted']} does not close SS60/FF25")
    m = re.search(r"\+(\d+) cycles/token \(([\d,]+) cycles", slab["cost"])
    slab_add = int(m[1])
    if int(m[2].replace(",", "")) != t["total_cycles"] + ad["added_cycles_per_token"] + slab_add:
        raise Refused(f"Qwen slab cost composed on another base: {slab['cost']}")
    cyc = t["total_cycles"] + ad["added_cycles_per_token"] + slab_add
    # ---- Qwen lever records (KV_MAP=1 Option M, owner ADOPT 2026-10-06)
    qlev, mod_add = {}, 0
    for f in QWEN_LEVERS:
        r = load(f)
        if r.get("schema") != QWEN_LEVER_SCHEMA or r.get("verdict") not in KNOWN_VERDICTS:
            raise Refused(f"Qwen lever record {rel(f)}: bad schema/verdict")
        if r["verdict"] == "ADOPT" and r.get("exact") is not True:
            raise Refused(f"Qwen lever {r['lever']}: verdict ADOPT but exact={r.get('exact')!r}")
        if r["verdict"] != "ADOPT":
            qlev[r["lever"]] = dict(cls="excluded", verdict=r["verdict"], record=rel(f), sha256=sha(f))
            continue
        add = int(r["token_cost"]["cycles_composed"])
        mc = int(r["token_cost"].get("modelled_not_composed", {}).get("cycles", 0))
        before = cyc
        cyc += add
        mod_add += mc
        qlev[r["lever"]] = dict(cls="adopted", verdict="ADOPT (exact, %s)" % r["exactness"]["KV_MAP_1"], record=rel(f), sha256=sha(f),
                                basis=r["token_cost"]["basis"],
                                modelled_not_composed=r["token_cost"].get("modelled_not_composed"),
                                delta=dict(cycles=add, AR_tok_s=round(clk / cyc - clk / before, 3)))
    ar = clk / cyc
    kv["token_average_system_TBps"] = round(kv_sys_token / (cyc / clk) / 1e12, 3)
    sp = dsp["variants"]["baseline_np4"]
    mtp_mode = dsp["verdict"] == "AR_MODE"
    return dict(
        position=t["position"], clock_hz=clk, token_cycles_measured=t["total_cycles"],
        levers={"core_context": dict(cls="adopted", verdict="ADOPT (closed SS60/FF25, exact 5/5)", record=rel(QWEN_CORE),
                                     variant=ad["variant"], ss_ps=ad["setup_ss_ref_ps"], ff_ps=ad["hold_ff_ref_ps"],
                                     delta=dict(cycles=ad["added_cycles_per_token"],
                                                AR_tok_s=round(clk / (t["total_cycles"] + ad["added_cycles_per_token"])
                                                               - clk / t["total_cycles"], 3))),
                "slab_mul_lat7": dict(cls="adopted", verdict="ADOPT (closed SS60 %+.2f / FF25 %+.2f ps, 0 slew/DRC)"
                                      % (sg["SS60_setup_ps"], sg["FF25_hold_ps"]), record=rel(QWEN_SLAB),
                                      variant=slab["adopted"],
                                      delta=dict(cycles=slab_add, AR_tok_s=round(clk / (t["total_cycles"] + ad["added_cycles_per_token"]
                                                                                      + slab_add)
                                                                                 - clk / (t["total_cycles"] + ad["added_cycles_per_token"]), 3))),
                **qlev},
        modelled_sensitivity=dict(cycles=mod_add, token_cycles=cyc + mod_add, AR_tok_s=round(clk / (cyc + mod_add), 1),
                                  note="adopted levers' MODELLED (not RTL) costs added on top of the measured headline; not a headline"),
        physical_closure=dict(status=load(QWEN_CLOSURE)["status"], bar=load(QWEN_CLOSURE)["physical"]["bar"], record=rel(QWEN_CLOSURE),
                              die_top_route=load(QWEN_CLOSURE)["physical"]["die_r20c"]["die_top_route"]["status"]),
        kv_traffic=kv,
        pending_not_composed=dict(r18g_die_wire_bound=dict(
            **QWEN_WIRE_PENDING, bound_tok_s=dict(skew0=round(clk / (cyc + 13305), 1), skew65=round(clk / (cyc + 16268), 1)))),
        token_cycles=cyc, AR_us=round(cyc / clk * 1e6, 3), AR_tok_s=round(ar, 1),
        MTP_mode="AR (DSpark OFF)" if mtp_mode else "DSpark", MTP_tok_s=round(ar, 1) if mtp_mode else sp["tok_s_upper"],
        dspark_reference=dict(tok_s=sp["tok_s_upper"], speedup_vs_ar=sp["speedup_vs_ar_upper"], tau=sp["tau"],
                              verdict=dsp["verdict"], record=rel(QWEN_DSPARK)),
        physical_qualified_full_system=False,
        inputs={rel(p): sha(p) for p in (QWEN_TERMINAL, QWEN_CORE, QWEN_DSPARK, QWEN_SLAB, QWEN_CONFIG,
                                          QWEN_TERMINAL.parent / "runtime.log", QWEN_P0_CAPACITY, QWEN_CLOSURE, *QWEN_LEVERS)})


# ---------------------------------------------------------------------------------------------------------- HBM
def hbm_ds():
    import third_party_tau as TP
    mref, opt, wire = load(HBM_MATCHED), load(HBM_OPT), load(WIRE)
    gate = mref["gate"]
    b = opt["basis"]
    if b["record"] != rel(HBM_MATCHED) or abs(b["gate_AR_us"] - gate["AR_us"]) > 1e-6 \
            or abs(b["gate_MTP_step_us"] - gate["MTP_step_us"]) > 1e-6:
        raise Refused("HBM lever composition is not on the matched gate basis")
    tau = gate["tau"]
    j, w2 = opt["joint_PQ_XMAP"], opt["paired_W2_increment"]
    drift = [p for blk in (j["inputs"], w2["inputs"], w2["combined_measurement"]["inputs"]) for p, s in blk.items()
             if not (ROOT / p).exists() or sha(ROOT / p) != s]
    if drift:
        raise Refused(f"HBM lever inputs drifted: {drift}")
    term = load(ROOT / next(p for p in j["inputs"] if p.endswith("terminal.json")))
    levers = {
        "joint_PQ_XMAP": dict(exact=term["status"] == "pass" and j["negative_expected_failure"] is True,
                              AR_us=-j["target_clock_projection"]["AR"]["total_replacement_saved_us"],
                              MTP_step_us=-j["target_clock_projection"]["MTP"]["total_replacement_saved_us"],
                              scope=j["measured_scope"], ss_ff=j["SS_FF_admitted"],
                              note="pipelined issue (item 1) + format-masked x map measured together; replaces the "
                                   "PQ groups once (item 1 alone is not added again)"),
        "paired_W2_PACK": dict(exact=bool(w2["actual_combined_PQ_XMAP_PACK_measured"]
                                          and w2["combined_measurement"]["exact_rows"] == 86
                                          and w2["combined_measurement"]["exact_activation_beats"]),
                               AR_us=-w2["incremental_AR_projection_us"], MTP_step_us=0.0,
                               scope=w2["combined_measurement"]["scope"], ss_ff=w2["physical_ss_ff_qualified"],
                               note="P1 combined measurement; P6 (MTP) increment unmeasured -> 0"),
    }
    excluded = {"item3_activation_delivery_standalone": "analytic beat-law sensitivity (not an exact measurement; "
                                                        "joint_PQ_XMAP carries the measured x map)",
                "item2_partial_wave / item4_workgroup_layout": "estimates (design notes), not credited",
                "item5_head": "REJECT"}
    bad = [k for k, v in levers.items() if v["exact"] is not True]
    if bad:
        raise Refused(f"HBM non-exact lever included: {bad}")
    ar0, st0 = gate["AR_us"], gate["MTP_step_us"]
    ar1 = ar0 + sum(v["AR_us"] for v in levers.values())
    st1 = st0 + sum(v["MTP_step_us"] for v in levers.values())
    # full FEC: switch crossings on the AR path (the P6 verify walks the same ops, so the same crossings)
    import dshbm_1m_coll as DC
    tu = sum(n.get("budget_us", 0.0) for n in mref["path"] if n["cls"] == "measured_tu_budget")
    n_x = round(tu / (DC.BUDGET_NS / 1e3))
    assert abs(n_x * DC.BUDGET_NS / 1e3 - tu) < 1e-6, (tu, n_x)
    d_x = HBM_FULL_FEC_PHY_NS - DC.TU_PHY_NS
    fec_us = n_x * d_x / 1e3
    full_fec = dict(crossings_AR=n_x, crossings_MTP_verify=n_x, per_crossing_ns=round(d_x, 3), AR_us=round(fec_us, 3),
                    MTP_step_us=round(fec_us, 3), endpoint_phy_ns=dict(was=DC.TU_PHY_NS, now=HBM_FULL_FEC_PHY_NS),
                    basis="OWNER 2026-10-06 full FEC on every off-package link: SUE endpoint link+PHY 100 ns -> full-KP4 "
                          "channel 198 ns (configs/hardware/technology.json links.rom_board_serdes full_kp4_fec_s 200 ns "
                          "less 2 ns of board flight); crossings counted from " + rel(HBM_MATCHED) + " path "
                          "(measured_tu_budget rows / 377.6 ns); switch 250 ns unchanged (RM104: includes its PHY/FEC)",
                    not_charged="the HBM DSpark draft (45.28 us, W19 estimate) carries no crossing count: not re-priced "
                                "(HBM-favourable)")
    ar_lev, st_lev = ar1, st1
    ar1 += fec_us
    st1 += fec_us
    pub = TP.sensitivity_ds_v41()["published"]["tau"]
    rows = {}
    for name, key in WIRE_BASES:
        add = wire["bases"][key]["ds_matched_added_us"]
        ar, st = ar1 + add, st1 + add
        rows[name] = dict(wire_basis=key, wire_added_us=add, full_fec_added_us=round(fec_us, 3), AR_us=round(ar, 3), AR_tok_s=round(1e6 / ar, 1),
                          MTP_step_us=round(st, 3), MTP_tok_s=round(tau * 1e6 / st, 1),
                          MTP_tok_s_tau_published=round(pub * 1e6 / st, 1))
    # cross-check: the wire record's own gate-row pricing at each basis reproduces gate + wire
    for name, key in WIRE_BASES:
        assert abs(wire["bases"][key]["ds_gate_AR_priced_us"] - (ar0 + wire["bases"][key]["ds_matched_added_us"])) < 2e-3
    return dict(
        basis=dict(record=rel(HBM_MATCHED), gate_AR_us=ar0, gate_MTP_step_us=st0, tau=tau, gate_AR_tok_s=round(1e6 / ar0, 1),
                   gate_MTP_tok_s=gate["MTP_tok_s"]),
        levers={k: dict(cls="exact_credited", record=rel(HBM_OPT), exact=v["exact"], ss_ff_admitted=v["ss_ff"],
                        delta=dict(AR_us=round(v["AR_us"], 3), MTP_step_us=round(v["MTP_step_us"], 3)), scope=v["scope"],
                        note=v["note"]) for k, v in levers.items()},
        not_credited=excluded,
        levers_AR_us=round(ar_lev, 3), levers_MTP_step_us=round(st_lev, 3),
        full_fec_AR_us=round(ar1, 3), full_fec_MTP_step_us=round(st1, 3),
        rows=rows, headline_row="median", full_fec=full_fec,
        unvalidated=["wire stages priced on the matched-reference walk's crossing counts; the PQ levers merge some "
                     "barriers / x loads, so the barrier and x-broadcast wire terms are an upper charge on the lever row",
                     "HBM levers are exact on minimum components; SS60/FF25 not admitted (comparator credit)",
                     "inherited vendor terms (Tomahawk-Ultra PHY + switch + cable) as in the matched reference, with "
                     "the endpoint PHY raised to the full-KP4 channel (full_fec)"],
        inputs={rel(p): sha(p) for p in (HBM_MATCHED, HBM_OPT, WIRE)})


# ------------------------------------------------------------------------------------------------------- output
def table(rec):
    d, q, h = rec["ds_rom"], rec["qwen_rom"], rec["hbm_ds"]
    L = ["THREE-MACHINE COMPOSITION (per user, target context)", "",
         f"{'machine':34s} {'AR tok/s':>10s} {'MTP tok/s':>10s} {'MTP@3.8879':>11s}  note",
         "(links: FULL RS(544,514) FEC on every off-package link, owner 2026-10-06)"]
    L.append(f"{'DS ROM 1M (adopted levers)':34s} {d['AR_tok_s']:>10,.1f} {d['MTP_tok_s']:>10,.1f} "
             f"{d['MTP_tok_s_tau_published']:>11,.1f}  tau {d['tau']:g}; MTP physical_qualified={d['MTP_physical_qualified']}")
    cj = d["conditional_all"]["composed"]
    if cj:
        L.append(f"{'  + all PENDING_SSFF (CONDITIONAL)':34s} {cj['AR_tok_s']:>10,.1f} {cj['MTP_tok_s']:>10,.1f} "
                 f"{cj['MTP_tok_s_tau_published']:>11,.1f}  not a headline")
    L.append(f"{'Qwen ROM 8K (P8191)':34s} {q['AR_tok_s']:>10,.1f} {q['MTP_tok_s']:>10,.1f} {'-':>11s}  "
             f"{q['token_cycles']:,} cycles; MTP mode {q['MTP_mode']} (DSpark {q['dspark_reference']['speedup_vs_ar']}x)")
    k = q["kv_traffic"]
    L.append(f"{'  KV (all 36 layers, FP8, in token)':34s} {k['MiB_system_token']:,.0f} MiB/token; landing "
             f"{k['landing_bytes_per_core_cycle_per_rank']['mean']:,.0f} B/cyc/rank = {k['achieved_TBps_per_die']['mean']} TB/s/die "
             f"({k['pct_of_4stack_peak']['mean']}% peak), exposed {k['exposed_fill_cycles_per_die']} cyc")
    ms = q["modelled_sensitivity"]
    L.append(f"{'  + modelled costs (not RTL)':34s} {ms['AR_tok_s']:>10,.1f} {'':>10s} {'':>11s}  "
             f"+{ms['cycles']} cyc (KV_MAP=1 die crossbar, cold layer); not a headline")
    pc = q["physical_closure"]
    L.append(f"{'  physical':34s} {pc['status']}; prior Qwen bar (SS60/FF25 >= 0); die-top route {pc['die_top_route']}")
    pw = q["pending_not_composed"]["r18g_die_wire_bound"]
    L.append(f"{'  r18g die wire bound (PENDING)':34s} {pw['bound_tok_s']['skew0']:>10,.1f} {'':>10s} {'':>11s}  "
             f"65 ps skew {pw['bound_tok_s']['skew65']:,.1f}; GRT {pw['grt_overflow']:,} overflow; not a headline")
    for name, r in h["rows"].items():
        L.append(f"{('HBM accel DS 1M, wire ' + name):34s} {r['AR_tok_s']:>10,.1f} {r['MTP_tok_s']:>10,.1f} "
                 f"{r['MTP_tok_s_tau_published']:>11,.1f}  +{r['wire_added_us']} us wire")
    lf = d["link_fec"]["delta_vs_light_fec"]
    L.append(f"{'full FEC vs light FEC (superseded)':34s} DS ROM dAR {lf['AR_tok_s']:+,.1f} tok/s ({lf['AR_us']:+.3f} us), "
             f"dMTP {lf['MTP_tok_s']:+,.1f} tok/s ({lf['MTP_step_us']:+.3f} us step); HBM +{h['full_fec']['AR_us']} us AR "
             f"and MTP step ({h['full_fec']['crossings_AR']} crossings x {h['full_fec']['per_crossing_ns']} ns)")
    L += ["", f"DS ROM / HBM (wire median): AR {rec['ratios']['ds_rom_over_hbm_ar']:.4f}x  "
              f"MTP {rec['ratios']['ds_rom_over_hbm_mtp']:.4f}x", "",
          "PER-LEVER DELTAS (adopted: headline minus headline-without; conditional: if-adopted minus headline)",
          f"{'machine':9s} {'lever':22s} {'class':12s} {'dAR us':>9s} {'dAR tok/s':>10s} {'dMTP step':>10s} {'dMTP tok/s':>11s}"]
    for k, v in sorted(d["levers"].items(), key=lambda kv: (kv[1]["cls"], kv[0])):
        if v["cls"] == "excluded":
            L.append(f"{'DS ROM':9s} {k:22s} {'excluded':12s} {v['verdict']}")
            continue
        x = v["delta"]
        L.append(f"{'DS ROM':9s} {k:22s} {v['cls']:12s} {x['AR_us']:>9.3f} {x['AR_tok_s']:>10.1f} "
                 f"{x['MTP_step_us']:>10.3f} {x['MTP_tok_s']:>11.1f}")
    for k, v in q["levers"].items():
        if "delta" not in v:
            L.append(f"{'Qwen ROM':9s} {k:22s} {v['cls']:12s} {v['verdict']}")
            continue
        L.append(f"{'Qwen ROM':9s} {k:22s} {v['cls']:12s} {'+' + str(v['delta']['cycles']) + ' cyc':>9s} "
                 f"{v['delta']['AR_tok_s']:>10.1f}")
    for k, v in h["levers"].items():
        L.append(f"{'HBM':9s} {k:22s} {'exact':12s} {v['delta']['AR_us']:>9.3f} {'':>10s} {v['delta']['MTP_step_us']:>10.3f}")
    return "\n".join(L) + "\n"


def compose_all(recovery: Path, committed: Path, deltas=True):
    levers = read_levers(recovery / "levers")
    guard_applied(levers, load(committed)["info"]["levers"]["applied"], f"published DS ROM composition ({rel(committed)})")
    _, ds = ds_rom(recovery, levers, deltas=deltas)
    q, h = qwen_rom(), hbm_ds()
    hm = h["rows"][h["headline_row"]]
    rec = dict(
        schema="opentallas.three-machine-compose.v1",
        rule="ADOPT + exact levers only in headlines; PENDING_SSFF reported as conditional; refuses otherwise",
        ds_rom=ds, qwen_rom=q, hbm_ds=h,
        ratios=dict(ds_rom_over_hbm_ar=round(ds["AR_tok_s"] / hm["AR_tok_s"], 4),
                    ds_rom_over_hbm_mtp=round(ds["MTP_tok_s"] / hm["MTP_tok_s"], 4),
                    hbm_row=h["headline_row"],
                    by_wire_basis={n: dict(ar=round(ds["AR_tok_s"] / r["AR_tok_s"], 4),
                                           mtp=round(ds["MTP_tok_s"] / r["MTP_tok_s"], 4))
                                   for n, r in h["rows"].items()}),
        lever_summary=dict(
            ds_rom_adopted=sorted(k for k, v in ds["levers"].items() if v["cls"] == "adopted"),
            ds_rom_conditional=sorted(k for k, v in ds["levers"].items() if v["cls"] == "conditional"),
            ds_rom_excluded=sorted(k for k, v in ds["levers"].items() if v["cls"] == "excluded"),
            qwen_rom_adopted=sorted(q["levers"]), hbm_exact_credited=sorted(h["levers"])),
        inputs=dict(levers={v["record"]: v["sha256"] for v in levers.values()},
                    ds_rom_composition={rel(committed): sha(committed)}, **q["inputs"], **h["inputs"]),
        tool_sha256={rel(Path(__file__)): sha(Path(__file__))})
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--recovery", type=Path, default=RECOVERY, help="directory holding levers/*.json")
    ap.add_argument("--composition", type=Path, default=None,
                    help="published DS ROM composition (default <recovery>/composition.json)")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--check", action="store_true", help="do not write; fail if the committed record differs")
    ap.add_argument("--guard-only", action="store_true", help="lever guard against the published composition only")
    ap.add_argument("--no-scoreboard", action="store_true")
    a = ap.parse_args(argv)
    committed = a.composition or a.recovery / "composition.json"
    try:
        if a.guard_only:
            levers = read_levers(a.recovery / "levers")
            guard_applied(levers, load(committed)["info"]["levers"]["applied"], f"published DS ROM composition ({rel(committed)})")
            print("GUARD PASS:", sorted(k for k, v in levers.items() if v["cls"] == "adopted"))
            return 0
        rec = compose_all(a.recovery, committed)
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    tab = table(rec)
    print(tab)
    out_json, out_tab = a.out / "compose.json", a.out / "table.txt"
    text = json.dumps(rec, indent=1, default=str) + "\n"
    if a.check:
        old = out_json.read_text() if out_json.exists() else ""
        strip = lambda s: {k: v for k, v in json.loads(s).items() if k != "tool_sha256"} if s else None
        if strip(old) != strip(text):
            print(f"STALE: {rel(out_json)} differs from the recomposition", file=sys.stderr)
            return 1
        print("CHECK PASS")
        return 0
    a.out.mkdir(parents=True, exist_ok=True)
    out_json.write_text(text)
    out_tab.write_text(tab)
    print(f"wrote {rel(out_json)}, {rel(out_tab)}")
    if not a.no_scoreboard:
        for args in ([], ["--check"]):
            r = subprocess.run([sys.executable, str(ROOT / "tools/measured_scoreboard.py"), *args], cwd=ROOT)
            if r.returncode:
                print(f"measured_scoreboard.py {' '.join(args)} failed ({r.returncode})", file=sys.stderr)
                return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
