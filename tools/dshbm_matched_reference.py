#!/usr/bin/env python3
"""MATCHED DS HBM reference for the DS ROM gate (one decode token at position 1,048,575, 1M context).

The inherited reference (tools/dshbm_1m_allmeasured.py -> results/rtl/dshbm_1m_allmeasured_20261004/composition.json:
460.053 us AR, 888.077 us MTP step; the step does not depend on tau) is re-walked on the same executed TP-96 program, with every other
term unchanged, and with:

CORRECTIONS (reports/DeepSeek_ROM_Architecture_Review.md section 1; evidence reports/deepseek_rom_review_evidence/):
  C1 unused issue slots   the inherited SM row is `lines + drain`: weight LINES issued, as if every issue slot were
                          used.  The group-slot issue runs waves of 8 (row, group) items x 8 chunk steps; a partial
                          last wave leaves slots empty (and the start / handshake protocol adds cycles).
  C2 separate op drains   the inherited walk batches consecutive expert slots into one flush group: their lines are
                          summed and ONE drain is charged (dshbm_1m_allmeasured.walk `pend["cyc"] += lines`).  The
                          issue sequencer accepts `start` only when not busy (ot_hbm_accel_issue), so every op drains.
  C3 activation loading   every SM bench writes the x store BEFORE t0; neither `lines + drain` nor start->done contains
                          it.  The inherited walk charges only the barrier's 16-cycle x-broadcast tail (78 = 62 + 16).
  All three are MEASURED together on the minimum component: one SM element (the 1.2 GHz successor
  ot_hbm_accel_sm_v ENABLE = 1, main e1bf44f09, whose own +12 drain / +19..27 start-to-done are therefore inside every
  cycle, and its +4 barrier crossing is added to the barrier) running the busiest SM's op sequence back to back
  (tools/dshbm_matched_sm_seq.py, rtl/test/tb_hbm_accel_sm_v_seq.sv; records in sm_seq/), bit-exact on every result.
  Per op on the path: x-load cycles (if the input is not resident) + start->done + 1 handshake cycle; per flush group
  one barrier of 62 + 4 cycles (the inherited 16-cycle x tail is replaced by the measured load, not added to it).

SHARED EXACT LEVERS credited to HBM (the review: "applicable architectural improvements must also be credited to HBM"):
  L1 expert workgroup     the 12 routed gate/up matrices (6 experts x w1, w3: one x, FP4, K 5,120) as ONE row set:
                          288 rows a die on 24 SMs, 12 contiguous rows of ONE matrix per SM (one static descriptor, no
                          gather), measured as one op (sm_seq wg); per-row arithmetic unchanged.
  L2 SU at 1.2 GHz        the SU chains re-measured at the 1.2 GHz units' in-lane latencies (MLAT 6 / ALAT 5;
                          bd935b346 ot_hdc_fp32_f12, bit-identical) and clocked at 1.2 GHz (su_m6a5/).
  L3 fused SU chains      the DS ROM SU-chain levers (norm + quant, SwiGLU + quant, hc_post) on the HBM SU
                          (su_fused/fused.json), applied only where measured exact.

    python3 tools/dshbm_matched_reference.py --out results/rtl/dshbm_matched_reference_20261005/composition.json
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dshbm_1m_allmeasured as A  # noqa: E402
import dshbm_baseline_measure as DM  # noqa: E402
import dshbm_chain_levers as CL  # noqa: E402
import w19_hbm_token_compose as WC  # noqa: E402

REC = ROOT / "results/rtl/dshbm_matched_reference_20261005"
INH = ROOT / "results/rtl/dshbm_1m_allmeasured_20261004"
SM_CLOSURE = ROOT / "results/rtl/hbm_accel_fmax_inventory_20261004/sm/closure.json"
F_FAST, F_SER = DM.F_FAST, DM.F_SER
BARRIER_SYNC = 62          # gpu_supply_barrier RTL round trip (results/rtl/gpu_supply_barrier.json), inherited
X_TAIL = 16                # the inherited 16-cycle x-broadcast tail (uarch_model H_X_TAIL_B / X_BCAST_BPC)
HANDSHAKE = 1              # busy low at the pins -> next start (one cycle; measured bench protocol)
ROUTED_GU = ("w1", "w3")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT))


# ---------------------------------------------------------------------------------------------------------------------
class SMSeq:
    """Measured per-op SM cycles from the op-sequence records: start->done, x-load, lines, drain, by (P, fmt, K, rows).
    The worst occurrence of a shape is used (conservative), except that a record's FIRST op (issued a few cycles after
    reset, before the bench's weight ring has run ahead: wq_a 160 vs 143 cycles in ar_l20, 144 vs 143 in p6_l20 where its
    longer x load lets the ring fill) is used only when the shape occurs nowhere else."""

    def __init__(self, files):
        self.op, self.files, occ = {}, [], {}
        for f in files:
            r = json.loads(Path(f).read_text())
            assert r["status"] == "pass" and r["mismatching_ops"] == 0, f
            self.files.append(f)
            P = 6 if r["active_columns"] == 6 else 1
            for o in r["ops"]:
                assert o["exact"] and o["mismatches"] == 0 and o["results"] == o["rows"], (f, o["tag"])
                occ.setdefault((P, o["fmt"], o["K"], o["rows"]), []).append((o["op"] == 0, o))
        for k, lst in occ.items():
            use = [o for first, o in lst if not first] or [o for _, o in lst]
            loads = [o for _, o in lst if o["x_load"]]            # x-load cycles do not depend on the stream
            m = [o["rtl"] for o in use]
            self.op[k] = dict(s2d=max(x["start_to_done"] for x in m), s2last=max(x["start_to_last"] for x in m),
                              drain=max(x["drain_last_line_to_last_result"] for x in m), lines=m[0]["lines"],
                              span=use[0]["issue_span_formula"], occurrences=len(lst), used=len(use),
                              load=max(o["rtl"]["load_cycles"] for o in loads) if loads else None,
                              beats=loads[0]["x_beats"] if loads else None)

    def get(self, P, fmt, K, R):
        k = (P, fmt, K, R)
        if k not in self.op:
            raise KeyError(f"SM shape not measured: {k}")
        return self.op[k]


def mv_rows(op):
    return math.ceil(max(r1 - r0 for r0, r1 in op["rows"]) / WC.N_SM)


def is_routed_gu(op):
    t = op["tag"]
    return t.startswith("expert slot") and t.split()[-1] in ROUTED_GU and op["fmt"] == "fp4"


# ---------------------------------------------------------------------------------------------------------------------
def walk(prog, smseq, su, coll, local, hbm, P=1, clk=A.TARGET, use=("coll", "local", "hbm", "mixes"),
         wg=False, fused=None, ledger=None):
    """dshbm_1m_allmeasured.walk with the SM flush groups re-priced from the op-sequence measurement (C1-C3), the
    optional expert workgroup (L1) and fused SU chain replacements (L3).  `ledger` (dict) collects the decomposition
    of the SM correction against the inherited `lines + drain`."""
    rows = []
    R = WC.LOCAL_REPEAT(P)
    m = dict(n_keys=0)
    inh = ledger.setdefault("_inh", None) if ledger is not None else None

    def add(L, node, us, cls, how, budget=0.0, domain=None):
        rows.append(dict(layer=L, node=node, us=round(us, 5), cls=cls, how=how, budget_us=round(budget, 5),
                         domain=domain))
    mix_us, mix_how = A.hc_mixes_us(P, clk)
    if "hbm" in use and hbm.get("embedding"):
        h = hbm.get("embedding")
        rows.append(dict(layer=-2, node="hbm:embedding_row", us=round(h["ns"] / 1e3, 5), cls="measured",
                         how=f"embedding row (10,240 B) at token start ({h['how']})", budget_us=0.0, domain="hbm"))
    for lay in prog["layers"]:
        L = lay["layer"]
        pend, swi = None, False
        mix_open = {}
        prev_mv = None
        wg_done = False

        def flush():
            nonlocal pend
            if pend:
                f = clk["sm"]
                add(L, "xload:" + pend["tag"], pend["load"] / f * 1e6, "measured",
                    f"x-store load, {pend['nload']} op(s) not resident, {pend['beats']} beats + 1 cycle each "
                    "(ot_hbm_accel_sm_v ENABLE=1 sequence bench)", domain="sm")
                add(L, "sm:" + pend["tag"], pend["cyc"] / f * 1e6, "measured",
                    f"{pend['nops']} op(s), each start->done + {HANDSHAKE} handshake, measured back to back on the "
                    "1.2 GHz successor element (warm stream, bit-exact)", domain="sm")
                add(L, "barrier", (BARRIER_SYNC + 4) / f * 1e6, "measured",
                    "gpu_supply_barrier RTL 62 cycles + successor barrier crossing 4 (sm/closure.json); the inherited "
                    "16-cycle x tail is replaced by the measured x load", domain="sm")
                if ledger is not None:
                    lg = ledger.setdefault(P, dict(groups=0, ops=0, loads=0, load_cyc=0, s2d_cyc=0, handshake_cyc=0,
                                                   lines=0, inh_drain=0, holes=0, perop_drain=0, barrier_delta=0,
                                                   inherited_cyc=0, wg_ops_removed=0))
                    lg["groups"] += 1
                    lg["ops"] += pend["nops"]
                    lg["loads"] += pend["nload"]
                    lg["load_cyc"] += pend["load"]
                    lg["s2d_cyc"] += pend["cyc"] - HANDSHAKE * pend["nops"]
                    lg["handshake_cyc"] += HANDSHAKE * pend["nops"]
                    lg["holes"] += pend["holes"]
                    lg["perop_drain"] += pend["drains"]
                    lg["barrier_delta"] += 4 - X_TAIL
            pend = None
        for op in lay["ops"]:
            k = op["kind"]
            if k == "mv":
                Rr = mv_rows(op)
                fmt, K = op["fmt"], op["k"]
                if wg and is_routed_gu(op):
                    if wg_done:
                        if ledger is not None:
                            ledger.setdefault(P, {}).setdefault("wg_ops_removed", 0)
                            ledger[P]["wg_ops_removed"] += 1
                        prev_mv = op
                        continue
                    wg_done = True
                    Rr = 12                                          # 12 rows of one matrix per SM (sm_seq wg)
                reuse = prev_mv is not None and prev_mv["fmt"] == fmt and prev_mv["k"] == K and \
                    not op["tag"].split()[-1] == "w2" and not op["tag"].startswith("engram")
                prev_mv = op
                s = smseq.get(P, fmt, K, Rr)
                load = 0 if reuse else s["load"]
                assert load is not None, ("no measured load for", P, fmt, K, Rr)
                cyc = s["s2d"] + HANDSHAKE
                batch = op["tag"].startswith("expert slot")
                holes = s["span"] - s["lines"]
                if pend and batch and pend["batch"]:
                    pend["cyc"] += cyc
                    pend["load"] += load
                    pend["nload"] += int(load > 0)
                    pend["nops"] += 1
                    pend["holes"] += holes
                    pend["drains"] += s["drain"]
                else:
                    flush()
                    pend = dict(cyc=cyc, load=load, nload=int(load > 0), nops=1, batch=batch, holes=holes,
                                drains=s["drain"], beats=s["beats"],
                                tag=("routed gate/up workgroup" if (wg and is_routed_gu(op)) else op["tag"]))
                continue
            if k == "local" and op["fn"] == "swiglu":
                if not swi:
                    rr = fused_rows(L, op, fused, P, clk) if fused else None
                    if rr is not None:
                        rows.extend(rr)
                    else:
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
                if k == "topk_merge" and op.get("what") == "sel":
                    sel = P * 419 / F_FAST * 1e6
                    add(L, "select:96x512", sel, "measured", "l20_index_topk RTL 419 cycles (exact)", domain="du_fast")
                c = coll.price(op, P) if "coll" in use else None
                assert c is not None
                ep_us = c["endpoint_cycles"] / clk["coll"] * 1e6 + c["ser_ns"] / 1e3
                bud = c["budget_ns"] / 1e3
                add(L, f"coll:{op['tag']}", ep_us + bud, "measured_tu_budget",
                    f"ot_hbm_accel_tu_endpoint RTL {c['endpoint_cycles']:.1f} cyc + port pacing {c['ser_ns']:.1f} ns"
                    f" + TU budget {c['budget_ns']} ns ({c['how']})", budget=bud, domain="coll")
                add(L, f"tail:{op['tag']}", c["tail_us"], "modelled",
                    "Tomahawk striping tail 0.15 us over ~8 switch chips (uarch_model _TAIL_US; RTL ports equal-latency)")
            elif k == "expert_fetch":
                h = hbm.get("expert_fetch")
                add(L, "hbm:expert_fetch", h["ns"] / 1e3, "measured",
                    f"routed-expert first access, timed HBM3E REFpb ({h['how']})", domain="hbm")
            elif k == "local":
                fn = op["fn"]
                if fn == "index_scores":
                    m["n_keys"] = op["n"]
                if fn == "hc_mixes" and "mixes" in use:
                    mix_open[op["which"]] = len(rows)
                    continue
                if fn in WC.OFF_PATH:
                    continue
                if fn in A.DU_FNS:
                    keys = math.ceil(op["n"] / WC.TP) if fn in ("index_scores", "cand_local", "cand_mask") else None
                    r = local.get(fn, L, keys)
                    stream = hbm.get(f"index_keys_{keys}") or hbm.get("index_keys") if fn == "index_scores" else None
                    assert r is not None, fn
                    f = clk["du_fast"] if r["domain"] == "fast" else clk["du_ser"]
                    us = R * r["cycles"] / f * 1e6
                    how = f"RTL {r['cycles']} cyc ({r['how']})"
                    if stream is not None and r.get("stream_cycles") is not None:
                        ing = r["stream_cycles"] / f * 1e6
                        sus = stream["ns"] / 1e3
                        us = (r["cycles"] - r["stream_cycles"]) / f * 1e6 + max(ing, sus)
                        how += (f"; HBM key stream {stream['ns']:.1f} ns {'binds' if sus > ing else 'hidden'} vs "
                                f"ingest {ing * 1e3:.1f} ns")
                    add(L, f"du:{fn}", us, "measured", how, domain="du")
                    continue
                if fn == "attend":
                    h = hbm.get("window_rows")
                    if h and h["on_path"]:
                        add(L, "hbm:window_rows", h["ns"] / 1e3, "measured",
                            f"128 window rows, timed HBM3E REFpb worst phase ({h['how']})", domain="hbm")
                if fn == "hc_post" and op["which"] in mix_open:
                    slack = sum(r["us"] for r in rows[mix_open.pop(op["which"]):])
                    exp = max(0.0, mix_us - slack)
                    add(L, f"hcp:hc_mixes.{op['which']}", exp, "measured",
                        f"{mix_how}; {mix_us:.3f} us beside a {slack:.3f} us body: exposed {exp:.3f}", domain="du")
                rr = fused_rows(L, op, fused, P, clk) if fused else None
                if rr is not None:
                    rows.extend(rr)
                else:
                    rows.extend(A.local_rows(L, op, su, clk, local, P, use, m))
        flush()
    return round(sum(r["us"] for r in rows), 4), rows


# ---------------------------------------------------------------------------------------------------------------------
FUSED_FNS = {"norm hc": ("hc_pre_norm", "final_norm"), "norm q": ("q_norm_kv_row",), "swiglu": ("swiglu",),
             "hc_post": ("hc_post",)}


def load_fused(path, skip=()):
    """su_fused/fused.json (the DS ROM fused SU engines re-run on the HBM SU wiring HUB_IN 6 / HUB_OUT 8, full shape,
    cached golden 1M operands) -> {(fn, None, P): dict(cycles, clock_hz, replaces, how)}.  P1 only: the fused benches
    run one position, so the MTP verify (P6) keeps the measured SU chains (no fused credit at P6)."""
    p = Path(path)
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    out = {}
    for r in d["rows"]:
        key = next(k for k in FUSED_FNS if r["lever"].startswith(k))
        if key in skip:
            continue
        ex = r["exactness"]
        errs = sum(v["errors"] for v in ex.values() if isinstance(v, dict)) if "errors" not in ex else ex["errors"]
        assert errs == 0, (key, ex)
        how = (f"{r['lever']}: {r['fused']['cycles']} cyc at 1.2 GHz, exact ({ex.get('record', '')}); "
               f"HBM wiring HUB_IN 6 / HUB_OUT 8 (su_fused/fused.json)")
        if key == "hc_post":
            how += "; M5A4 lane REJECT_SS (-52.47 ps), M6A5 not exact: lever-favouring latency"
        for fn in FUSED_FNS[key]:
            out[(fn, None, 1)] = dict(cycles=r["fused"]["cycles"], clock_hz=r["fused"]["clock_hz"],
                                      replaces=r["replaces"], how=how)
    return out


def fused_rows(L, op, fused, P, clk):
    fn, which = op["fn"], op.get("which")
    f = fused.get((fn, None, P))
    if f is None:
        return None
    hz = clk.get("su_fused", f["clock_hz"])
    return [dict(layer=L, node=f"sufused:{fn}", us=round(f["cycles"] / hz * 1e6, 5), cls="measured",
                 how=f"fused SU chain (replaces {', '.join(f['replaces'])}): {f['how']}", budget_us=0.0, domain="su")]


def finite_q_candidate_price(rec=REC):
    """Price the actual finite-provider Q component without inventing a baseline.

    Retain the historical wide-provider paper comparison, but do not transfer
    its fusion saving or its clock qualification to this different service.
    """
    folder = Path(rec)/"su_fused"/"finite_q_component"
    result_path, calendar_path = folder/"result.json", folder/"calendar.json"
    if not result_path.exists() or not calendar_path.exists():
        return None
    result = json.loads(result_path.read_text())
    calendar = json.loads(calendar_path.read_text())
    actual = next(r for r in result['runs'] if r['name'] == 'actual')
    m = actual['metrics']
    assert result['terminal'] and result['pass_exact'] and actual['rc'] == 0
    assert m == calendar['metrics'] and m['errors'] == 0 and m['checked'] == 1280 and m['debt'] == 0
    assert m['requests'] == m['read_sectors']+m['write_sectors']+m['publication_sectors']
    assert result['binary_sha256'] == calendar['binary_sha256']
    accepted_event = next(e for e in actual['events'] if e.startswith('FINITE_EVENT accept '))
    accepted_ns = float(accepted_event.split('time_ns=')[1])
    elapsed = (m['time_ns']-accepted_ns)/1000
    assert abs(elapsed-calendar['observed_command_to_completion_us']) < 1e-9
    assert abs(sum(calendar['segments_us'].values())-elapsed) < 1e-9
    wait = m['request_response_wait_edges']*calendar['clock_period_ns_resolved']/1000
    assert 0 < wait <= elapsed
    historical_path = Path(rec)/'su_fused'/'fused.json'
    historical = json.loads(historical_path.read_text())
    q = next(r for r in historical['rows'] if r['lever'].startswith('norm q'))
    paper_saving = q['on_path_P1_us']['saving']
    return dict(scope='one Q norm component, different finite provider; not original seven-op Q/KV/RoPE/quant program',
        source_records={rel(p):sha(p) for p in (result_path,calendar_path,historical_path)},
        measured_RTL_source=calendar['measurement_source'],
        selected_RTL_source=calendar['selected_source'],
        numerical_exact=True, checked_Q_words=m['checked'],
        accepted_to_observed_completion_us=elapsed,
        completion_observation=calendar['completion_observation'],
        request_counts=dict(read=m['read_sectors'], write=m['write_sectors'],
                            ordered_publication_readback=m['publication_sectors'], total=m['requests']),
        response_wait_edges=m['request_response_wait_edges'],
        resolved_simulation_period_ns=calendar['clock_period_ns_resolved'],
        response_wait_us_including_CDC_backend=wait,
        response_wait_fraction=wait/elapsed,
        remaining_control_engine_observation_us=elapsed-wait,
        critical_segments_us=calendar['segments_us'],
        extra_CDC_charge_us=0,
        extra_CDC_charge_basis='already measured inside these request/response waits; unmeasured parent crossings remain unknown, not zero',
        parent_extra_crossing_and_borrower_cost_us=None,
        historical_wide_provider_Q_KV_pair_us=q['fused']['us'],
        historical_wide_provider_40_P1_saving_us=paper_saving,
        cost_over_historical_total_saving=elapsed/paper_saving,
        historical_comparison_scope='budget mismatch only; neither a same-provider regression nor an all-layer extrapolation',
        effect_on_original_benefit='historical Q/KV fused benefit cannot be credited to this finite candidate; its single Q cost exceeds the entire old 40-occurrence saving',
        native_same_provider_baseline_us=None,
        native_provider_cost='original native wide ports also unpriced; retain neither as a physically guaranteed baseline',
        architecture_risk='one-outstanding sector service and dependent response/publication waits dominate; engine fusion alone does not remove that exposed movement path',
        remaining_engineering='bind actual program borrower/admission and read/write lease, remaining KV/RoPE/quant, actual owner publication and dependent consumer; then measure paired same-provider program',
        parent_program_bound=calendar['parent_program_integration'],
        installed_borrower_lease=calendar['installed_client_borrower_lease'],
        mixed_native_fused_program_measured=calendar['mixed_native_fused_program_measured'],
        physical_clock_qualified=calendar['physical_clock_qualified'],
        whole_program_composed_delta_us=None, headline_acceleration_credit_us=None,
        candidate_adopted=False)


# ---------------------------------------------------------------------------------------------------------------------
def mtp(prog, smseq, su6, coll, local, hbm, clk, use, wg, fused):
    from hbm_accelerator_model import _load_study
    mstudy, _, _, _ = _load_study(ROOT)
    V1, V6 = mstudy.VERIFY_PARTS[1], mstudy.VERIFY_PARTS[6]
    union = dict(sm=round(V6["sm"] - V1["sm"], 3), fetch=round(V6["fetch"] - V1["fetch"], 3))
    led = {}
    t6, rows6 = walk(prog, smseq, su6, coll, local, hbm, P=6, clk=clk, use=use, wg=wg, fused=fused, ledger=led)
    dr = json.loads(A.DRAFT.read_text())
    row = {r["design"]: r for r in dr["rows"] if r["ctx"] == "1M" and r["scenario"] == "tomahawk_ultra_protocol"}
    ab = row["ablation_w19"]
    draft, seed = ab["as_built"]["draft_us"], ab["seed_commit_us"]
    tau, tsrc = A.tau_source()
    verify = t6 + union["sm"] + union["fetch"]
    step = verify + draft + seed
    return dict(tau_source=tsrc, verify_p6_us=round(verify, 3), walk_p6_us=t6, union_model_us=union, draft_us=draft,
                seed_commit_us=seed, step_us=round(step, 3), tau=tau, mtp_tok_s=round(tau * 1e6 / step, 1),
                verify_by_term=A.by_term(rows6), sm_ledger=led.get(6)), rows6


def ledger_us(lg, f_sm):
    """The SM correction decomposed (cycles at the SM clock -> us)."""
    if not lg:
        return None
    c = lambda x: round(x / f_sm * 1e6, 3)  # noqa: E731
    return dict(flush_groups=lg["groups"], ops=lg["ops"], x_loads=lg["loads"], x_load_us=c(lg["load_cyc"]),
                op_start_to_done_us=c(lg["s2d_cyc"]), handshake_us=c(lg["handshake_cyc"]),
                analytic_issue_holes_us=c(lg["holes"]), measured_per_op_drains_us=c(lg["perop_drain"]),
                barrier_delta_us=c(lg["barrier_delta"]), workgroup_ops_removed=lg.get("wg_ops_removed", 0))


UNVALIDATED = [
    dict(term="inherited modelled / vendor terms (unchanged)", why="Tomahawk-Ultra PHY + switch + cable per crossing "
         "(vendor budget, 115.168 us AR), striping tail 0.15 us a collective (39.75 us AR), MTP routed-expert union SM / "
         "fetch increments (47.74 + 28.45 us, W19 model), LOCAL_REPEAT issue fraction at P6, DSpark draft 45.28 us and "
         "seed 3.567 us (draft record), hc_mixes / compressor / cand_apply off-path judgement: see the inherited record"),
    dict(term="MTP union SM increment priced inherited-style", why="the 47.74 us union SM term is the W19 lines-style "
         "price; it does NOT carry C1-C3, so the MTP correction is a lower bound (HBM-favourable)"),
    dict(term="x-broadcast network depth (root -> 32 SM x stores)", why="not priced: the measured load is at the "
         "element's write port (2,048 b/cycle, one beat a cycle, + 1 cycle); the die-level broadcast tree's pipeline "
         "depth (~22 stages if it follows the barrier tree's 13 + 9) is unmodelled. HBM-favourable"),
    dict(term="P6 x load through the as-built port", why="10 beats an address (6 x 3,152 bits, zero-padded fields); a "
         "format-masked write port is not credited (not built)"),
    dict(term="expert workgroup source layout", why="each SM streams 12 contiguous rows of ONE expert matrix: requires "
         "the expert weights laid out for a 12-row-per-SM split (static, one descriptor per SM, no gather) and the "
         "router's expert ids steering 24 of 32 SMs; descriptor/steering logic not built; expert fetch kept as measured"),
    dict(term="SM element clock", why="leaves (tc16, bd_col, stack), issue and bulk copy close at 0.833 ns, the element "
         "route is OPEN (sm/closure.json); today's rows keep the inherited 1,030.9 MHz"),
    dict(term="SU at 1.2 GHz", why="the f12 units close standalone; no m6a5 lane closes (light lane r2r -4.76 ps, side "
         "lane -167.45 ps, softplus -112.85 ps; su_m6a5/lane_clock.json); today's rows use 999.2 MHz (r2r basis)"),
    dict(term="first-op stream warm-up", why="a record's first op is excluded when the shape recurs (the bench ring had "
         "not run ahead); every token op is preceded by other work, so the warm figure applies"),
    dict(term="index path blocks are shared (ROM/W11) RTL, not HBM-die instances", why="du:index_q (HBM SU chain + "
         "the shared ot_hdc_actquant), du:index_scores (ot_hdc_v41x_idx_array W11), du:topk_local / du:cand_local "
         "(ot_hdc_v41x_sel / _sel_cand) and select:96x512 (l20_index_topk) are measured on the SHARED ot_hdc_v41x_* "
         "blocks (results/rtl/dshbm_1m_allmeasured_20261004/local.json); no HBM-accelerator RTL instantiates them "
         "(results/rtl/hbm_accel_fmax_inventory_20261004/attn/closure.json, main 96ed22b21), so they are borrowed "
         "component measurements priced at 1.2 GHz whose 1.2 GHz closure on the HBM side is OPEN; per-row totals in "
         "composition.json index_path"),
    dict(term="GU x load under routing", why="the routed gate/up x (the ffn-norm output) is ready before the router; its "
         "49-cycle load could hide under router_act/route/expert_fetch.  NOT credited (charged serially)"),
]


INDEX_NODES = {"du:index_q": "HBM SU chain (N1024/M256) + shared ot_hdc_actquant FP4 quantiser",
               "du:index_scores": "shared ot_hdc_v41x_idx_array (W11), 1.2 GHz, max(HBM key stream, ingest)",
               "du:topk_local": "shared ot_hdc_v41x_sel (tail after the scorer's last beat), 1.2 GHz",
               "du:cand_local": "shared ot_hdc_v41x_sel_cand, 1.2 GHz",
               "select:96x512": "shared l20_index_topk RTL 419 cycles, 1.2 GHz"}


def index_path(rows_head, rows_corr):
    """The indexer terms on the path: measured on SHARED (ROM/W11) blocks, not HBM-die instances; 1.2 GHz open."""
    out = {}
    for n, how in INDEX_NODES.items():
        out[n] = dict(us_headline=round(sum(r["us"] for r in rows_head if r["node"] == n), 3),
                      us_corrected=round(sum(r["us"] for r in rows_corr if r["node"] == n), 3), block=how,
                      hardware="borrowed shared ot_hdc_v41x_* block (no HBM-accelerator instance)",
                      closure_1p2GHz_on_HBM="OPEN")
    out["total_us_headline"] = round(sum(v["us_headline"] for v in out.values()), 3)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rec", type=Path, default=REC)
    ap.add_argument("--out", type=Path, default=REC / "composition.json")
    a = ap.parse_args()
    prog = json.loads((A.BASE / "program.json").read_text())
    sm_inh = WC.SMTable([json.loads((ROOT / "results/rtl/w19_sm_real_ops.json").read_text()),
                         json.loads((A.BASE / "sm_real_ops.json").read_text())], "ar")
    su1, su6, _, _ = A.su_tables()
    coll = A.Coll(A.load(INH / "collectives.json"))
    local = A.Local(A.load(INH / "local.json"))
    hbm = A.Hbm(A.load(INH / "hbm_streams.json"))
    use = ("coll", "local", "hbm", "mixes")
    # 0. the inherited reference, reproduced exactly
    t_inh, rows_inh = A.walk(prog, sm_inh, su1, coll, local, hbm, use=use)
    m_inh = A.mtp(prog, sm_inh, su6, coll, local, hbm, A.TARGET, None, use)
    assert abs(t_inh - 460.053) < 0.01 and abs(m_inh["step_us"] - 888.077) < 0.01, (t_inh, m_inh["step_us"])
    sm_files = sorted((a.rec / "sm_seq").glob("*_nc8_a*.json"))
    smseq = SMSeq(sm_files)
    # SU at 1.2 GHz: the m6a5 chain records (same cases, same levers il + dr + ov).  Headline: BCAST 7 / RET 8, the
    # hbm-fmax-su owner's hub wire stages at 1.2 GHz (the 0.9 GHz 4 / 5 do not reach at 1.2 GHz); 4 / 5 = sensitivity.
    m6 = a.rec / "su_m6a5"
    su12, su12_files = {}, {}
    for wires in ("b7r8", "b4r5"):
        f1 = m6 / f"su_N1024_M256_{wires}m6a5_dpi_beh_su_cases_v2_ildr.json"
        f6 = m6 / f"su_N1024_M256_{wires}m6a5_dpi_beh_su_cases_p6om_ildr.json"
        if f1.exists() and f6.exists():
            s1 = CL.best_of([("dr", json.loads(f1.read_text()))])
            s6 = CL.best_of([("dr", json.loads(f6.read_text()))])
            assert all(DM.su_exact(c) for c in s1["chains"] + s6["chains"])
            su12[wires] = (CL.su_table_overlap(s1), CL.su_table_overlap(s6))
            su12_files[wires] = [f1, f6]
    fused = load_fused(a.rec / "su_fused" / "fused.json")
    fused_no_hcpost = load_fused(a.rec / "su_fused" / "fused.json", skip=("hc_post",))
    cc = A.closing_clocks()
    clk_today = dict(sm=cc["sm"]["mhz"] * 1e6, su=cc["su"]["mhz"] * 1e6, attn=cc["attn"]["mhz"] * 1e6,
                     du_fast=min(cc["sm"]["mhz"], 1200) * 1e6, du_ser=cc["su"]["mhz"] * 1e6,
                     coll=cc["coll"]["mhz"] * 1e6, hbm=min(cc["hbm"]["mhz"], 1200) * 1e6,
                     router=cc["router"]["mhz"] * 1e6)
    su_today_12 = json.loads((a.rec / "su_m6a5" / "lane_clock.json").read_text()) \
        if (a.rec / "su_m6a5" / "lane_clock.json").exists() else None

    def run(name, clk, su_pair, wg, fz, what):
        led = {}
        t, rows = walk(prog, smseq, su_pair[0], coll, local, hbm, P=1, clk=clk, use=use, wg=wg, fused=fz, ledger=led)
        mm, _ = mtp(prog, smseq, su_pair[1], coll, local, hbm, clk, use, wg, fz)
        return dict(name=name, what=what, AR_us=round(t, 3), AR_tok_s=round(1e6 / t, 1), MTP_step_us=mm["step_us"],
                    MTP_tok_s=mm["mtp_tok_s"], AR_by_term=A.by_term(rows), AR_summary=A.summarise(t, rows),
                    sm_ledger_ar=ledger_us(led.get(1), clk["sm"]), MTP=dict(mm, sm_ledger=ledger_us(mm["sm_ledger"], clk["sm"]))), rows

    T = dict(A.TARGET)
    T12 = dict(T, su=1.2e9, du_ser=F_SER)                 # SU lanes at 1.2 GHz; the quantisers / serial DUs stay 0.9
    steps, paths, today = [], {}, []
    r, p = run("corrected", T, (su1, su6), False, None, "inherited + C1 issue slots + C2 per-op drains + C3 x loading "
               "(all measured on the successor SM element); nothing else changed")
    steps.append(r); paths["corrected"] = p
    r, p = run("corrected+wg", T, (su1, su6), True, None, "+ L1 expert workgroup")
    steps.append(r); paths["corrected+wg"] = p
    sens = []
    if "b7r8" in su12:
        r, p = run("corrected+wg+su12", T12, su12["b7r8"], True, None,
                   "+ L2 SU at 1.2 GHz (m6a5 chains, hub wire stages BCAST 7 / RET 8)")
        steps.append(r); paths["corrected+wg+su12"] = p
        if fused:
            r, p = run("matched", T12, su12["b7r8"], True, fused, "+ L3 fused SU chains (DS ROM levers on the HBM SU)")
            steps.append(r); paths["matched"] = p
    if "b4r5" in su12:
        r, _ = run("sens:corrected+wg+su12_b4r5", T12, su12["b4r5"], True, None,
                   "SENSITIVITY: L2 with the 0.9 GHz hub wire stages BCAST 4 / RET 5 kept at 1.2 GHz (unreachable)")
        sens.append(r)
    if fused and "b7r8" in su12:
        r, _ = run("sens:matched_without_hc_post_fusion", T12, su12["b7r8"], True, fused_no_hcpost,
                   "SENSITIVITY: matched without the hc_post fusion (its exact M5A4 lane is REJECT_SS)")
        sens.append(r)
    if fused:
        r, p = run("corrected+wg+fused_su0.9", T, (su1, su6), True, fused,
                   "+ L1 workgroup + L3 fused SU chains, the remaining SU chains left at 0.9 GHz / MLAT 4 ALAT 3 "
                   "(L2 slows AR with its 1.2 GHz wire stages, so an AR-optimised HBM keeps the 0.9 GHz SU)")
        steps.append(r); paths[r["name"]] = p
        r, _ = run("corrected+wg+fused_su0.9@today", clk_today, (su1, su6), True, fused,
                   "workgroup + fused chains, SU chains 0.9 GHz-class at today's 638.6 MHz; fused units at 1.2 GHz "
                   "(their lanes are not closed either)")
        today.append(r)
    r, _ = run("corrected@today", clk_today, (su1, su6), False, None, "corrected, at the clocks the blocks close at today")
    today.append(r)
    r, _ = run("corrected+wg@today", clk_today, (su1, su6), True, None, "+ workgroup, today's clocks")
    today.append(r)
    if "b7r8" in su12 and su_today_12:
        ct = dict(clk_today, su=su_today_12["mhz"] * 1e6)
        r, _ = run("corrected+wg+su12@today", ct, su12["b7r8"], True, None,
                   f"+ m6a5 SU chains at the m6a5 lane's clock today ({su_today_12['mhz']} MHz: {su_today_12['evidence']})")
        today.append(r)
        if fused:
            r, _ = run("matched@today", dict(ct, su_fused=su_today_12["mhz"] * 1e6), su12["b7r8"], True, fused,
                       "+ fused SU chains at the same SU clock today")
            today.append(r)
    head = next(x for x in steps if x["name"] == "matched") if any(x["name"] == "matched" for x in steps) \
        else steps[-1]
    credited = [x for x in steps if x["name"] != "corrected"]
    best_ar = min(credited, key=lambda x: x["AR_us"])
    best_mtp = min(credited, key=lambda x: x["MTP_step_us"])
    tcred = [x for x in today if x["name"] != "corrected@today"]
    gate = dict(
        rule="ROM target (owner 2026-10-05: a measured checkpoint, not a kill switch): ROM AR <= gate AR_us AND ROM MTP "
             f"step <= gate MTP_step_us (the step is tau-independent; MTP_tok_s at tau {best_mtp['MTP']['tau']:g}).  Each figure is the best credited HBM configuration for that mode (a lever that slows one mode is "
             "not forced on it), i.e. the harder bar for ROM",
        AR_us=best_ar["AR_us"], AR_row=best_ar["name"], MTP_step_us=best_mtp["MTP_step_us"], MTP_row=best_mtp["name"],
        MTP_tok_s=best_mtp["MTP_tok_s"], tau=best_mtp["MTP"]["tau"], tau_source=best_mtp["MTP"]["tau_source"],
        MTP_tok_s_tau_sensitivity=A._tau_sens(best_mtp["MTP_step_us"]),
        today_AR_us=min(x["AR_us"] for x in tcred), today_MTP_step_us=min(x["MTP_step_us"] for x in tcred),
        corrected_only_AR_us=steps[0]["AR_us"], corrected_only_MTP_step_us=steps[0]["MTP_step_us"],
        inherited_AR_us=round(t_inh, 3), inherited_MTP_step_us=m_inh["step_us"])
    rec = dict(
        schema="opentallas.dshbm.matched_reference.v1", context=1048576, position=1048575,
        purpose="DS ROM gate reference (~2026-10-07): the HBM accelerator with the review's three corrections measured "
                "and the shared exact levers credited; ROM must beat AR and MTP step of the headline row",
        inherited=dict(record=rel(INH / "composition.json"), AR_us=round(t_inh, 3), MTP_step_us=m_inh["step_us"],
                       MTP_tok_s=m_inh["mtp_tok_s"], reproduced=True),
        headline=dict(row=head["name"], AR_us=head["AR_us"], AR_tok_s=head["AR_tok_s"], MTP_step_us=head["MTP_step_us"],
                      MTP_tok_s=head["MTP_tok_s"], tau=head["MTP"]["tau"], tau_source=head["MTP"]["tau_source"],
                      MTP_tok_s_tau_sensitivity=A._tau_sens(head["MTP_step_us"]),
                      scope='paper-credited target-clock comparison; not measured integrated finite-provider performance',
                      physical_qualified=False),
        finite_provider_measured_candidate=finite_q_candidate_price(a.rec),
        gate=gate, unvalidated=UNVALIDATED,
        index_path=index_path(paths[head["name"]], paths["corrected"]),
        ladder_target_clocks=steps, ladder_today_clocks=today, sensitivities=sens,
        clocks=dict(target=dict(T12, note="SM / attention / DU-fast / collective endpoint / HBM 1.2 GHz; SU 0.9 GHz "
                                            "before L2, 1.2 GHz from L2; quantisers and serial DUs 0.9 GHz throughout"),
                    today=cc, su_m6a5_today=su_today_12),
        sm_sequence_records=[rel(f) for f in sm_files],
        sm_shapes={f"P{k[0]} {k[1]} K{k[2]} R{k[3]}": v for k, v in sorted(smseq.op.items())},
        path=paths[head["name"]],
        inputs={rel(p): sha(p) for p in sm_files + [INH / "composition.json", INH / "collectives.json",
                                                    INH / "local.json", INH / "hbm_streams.json", A.BASE / "program.json",
                                                    SM_CLOSURE] + [f for v in su12_files.values() for f in v]
                + ([a.rec / "su_fused" / "fused.json"] if fused else [])},
        tool_sha256={rel(Path(__file__)): sha(Path(__file__)), "tools/dshbm_1m_allmeasured.py":
                     sha(ROOT / "tools/dshbm_1m_allmeasured.py")})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    for s in steps + today + sens:
        print(f"{s['name']:28s} AR {s['AR_us']:8.3f} us  MTP step {s['MTP_step_us']:8.3f} us  {s['MTP_tok_s']:7.1f} tok/s"
              f"  sm-ledger {s['sm_ledger_ar']}")
    return rec


if __name__ == "__main__":
    main()
