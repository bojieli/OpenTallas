#!/usr/bin/env python3
"""DS-ROM (DeepSeek-V4.1-Flash, S81) one decode token at position 1,048,575 (1M context) with EVERY term of the
critical path taken from a full-shape RTL measurement (owner measurement rule 2026-10-04), composed analytically on
the S81 graph's fixed dependency structure (tools/dsrom_1m_measure.py s58_graph).

Base: the adopted candidate_gather.lat259 composition of tools/dsrom_1m_measure.py (context-dependent terms: index
read, select, CKV gather + q.k, re-index candidate gather).  This tool then replaces the remaining MODELLED terms:

  field   tools/dsrom_1m_field.py      ROM matvecs (projections, router, routed/shared experts)   field.json
  su      tools/dsrom_1m_su.py         norms, quant, rope, softmax, hc, Sinkhorn, MoE SU chain    su.json
  head    tools/dsrom_1m_head.py       lm_head (full vocab) + local argmax                         head.json
  links   tools/dsrom_1m_links.py      stage hop (link_rt endpoint RTL + light-FEC PHY budget),
                                       token return, TP4 collectives                              links.json
  cand    tools/dsrom_1m_cand_select.py  L20 candidate-block select (local + final)              cand_select.json
  window  results/rtl/hbm_path_bandwidth_audit_20261004/dsrom_window_load.json (stream_la, worst phase): the WINDOW
          KV load, added as an explicit node per layer in front of attn.scores -- REQUIRES S81 BINDING OF THE WINDOW
          MODULE (Codex); the as-built S81 prefetch measures 124.5 us a layer and is reported alongside.

Formerly modelled terms, now measured (Claude:dsrom-modelled-terms, each optional; absent -> the old model term):
  engram     tools/dsrom_1m_engram.py     L1/L14 eng.hh/dot/gate/add on the SU, released-checkpoint operands   engram.json
  embed      tools/dsrom_1m_embed.py      embedding row read + TP4 send + 4-copy expand                      embed.json
  su_qdq     tools/dsrom_1m_su_cdcq.py    quantisers with the 22/15 hub stages as RTL stages             su_qdq_wired.json
  su_cdc     tools/dsrom_1m_su_cdcq.py    the domain crossing (meso + 3:4 ratio FIFO) on every slow<->fast edge
                                          (replaces the model's W18 4-slow / 5-fast cycles)                  su_cdc.json
  draft      tools/dsrom_1m_draft_blocks.py  the three DSpark blocks at full shape                         draft_blocks.json

Every critical-path node is classified measured / inside-a-measured-term / modelled; the modelled ones are listed
with their time (never silently dropped).  MTP: wavefront verify (measured rule: a stage takes the next position 46
cycles after it finishes the previous one, results/rtl/dsrom_wavefront_verify_20261004) with the stage busy times of
THIS composition, and the DSpark draft recomposed with the measured head.

    python3 tools/dsrom_1m_allmeasured.py --baseline asbuilt     (-> results/rtl/dsrom_1m_allmeasured_20261004/)
    python3 tools/dsrom_1m_allmeasured.py                        (recovery baseline: + adopted lever records of
                                                                  results/rtl/dsrom_recovery_20261004/levers/*.json,
                                                                  -> results/rtl/dsrom_recovery_20261004/composition.json)
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
import dsrom_1m_measure as M  # noqa: E402
import third_party_tau as TP  # noqa: E402

REC = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004"
BASE = ROOT / "results/rtl/dsrom_1m_measured_20261004"
RC = ROOT / "results/rtl/dsrom_reindex_candidates_20261004"
WINDOW = ROOT / "results/rtl/hbm_path_bandwidth_audit_20261004/dsrom_window_load.json"
WAVE = ROOT / "results/rtl/dsrom_wavefront_verify_20261004/record.json"
DRAFT_REC = ROOT / "results/rtl/dsrom_fused_draft_head_20261004/l1_compose.json"
RECOVERY = ROOT / "results/rtl/dsrom_recovery_20261004"     # microarchitecture-recovery levers (baseline "recovery")
WAVE_PHYSICAL = ROOT / "results/rtl/dsrom_wfc_r12_fanout_20261005/physical_rejection/decision.json"
FULL_FEC_LINKS = REC / "links_full_fec.json"                  # OWNER 2026-10-06 full-FEC baseline (RTL)
FULL_FEC_RACK = ROOT / "results/arch/dsrom_s81_rack_20261006/rack.json"   # hop classes (cable flight beyond 0.3 m)
DEFAULT_HOP_TIER = "full_fec"   # OWNER 2026-10-06: full RS(544,514) on every off-package link; light_fec = history
CLK = 1.2e9
SLOW = 0.9e9
EXTRA_HOPS = M.S81_EXTRA_HOPS


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def bind_wavefront_physical_verdict(rec):
    """Preserve modeled wavefront timing without granting failed hardware credit."""
    if not WAVE_PHYSICAL.exists():
        return rec
    decision = json.loads(WAVE_PHYSICAL.read_text())
    assert not decision['physical_adopted']
    assert decision['three_failed_variants_threshold_met']
    assert not decision['fourth_unchanged_recipe_allowed']
    rec['MTP']['physical_qualified'] = False
    rec['MTP']['qualified_headline_rate'] = None
    rec['MTP']['wavefront_implementation'] = dict(
        decision_record=rel(WAVE_PHYSICAL), decision_sha256=sha(WAVE_PHYSICAL),
        source_commit=decision['source_commit'], verdict=decision['verdict'],
        variants=[dict(utilization=v['utilization'], ss_incontext_ps=v['ss_incontext_ps'],
                       ss_internal_ps=v['ss_internal_ps'], ff_hold_ps=v['ff_hold_ps'],
                       drc=v['drc'], drv=v['drv']) for v in decision['variants']],
        modeled_interval_retained=True, implementation_adopted=False,
        reset_recovery_is_causal=False,
        reason=decision['reason'], redesign_owner='CLAUDE',
        additional_capture_edge_calendar_price=None,
        rule='MTP interval/rate remains modeled composition; any redesign capture edge must be explicitly priced before adoption. No fourth recipe or reset-recovery credit.')
    rec['inputs'][rel(WAVE_PHYSICAL)] = sha(WAVE_PHYSICAL)
    return rec


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT))


class Patcher:
    def __init__(self, g):
        self.g, self.rows = g, {}

    def put(self, name, seconds, src, cls="measured", stream=False, modelled_s=0.0):
        """Replace node `name` by a measured latency (seconds from its last input to its result); `modelled_s` is
        the part of `seconds` that is still a model term (listed, never dropped)."""
        nd = self.g.nodes[name]
        old = (nd["issue"] + nd["depth"] + nd["ctrl"]) * 1e6
        nd.update(issue=seconds, depth=0.0, ctrl=0.0, stream=stream)
        nd.pop("wire_in", None)
        nd.pop("wire_out", None)
        self.rows[name] = dict(node=name, model_us=round(old, 4), measured_us=round(seconds * 1e6, 4), cls=cls,
                               source=src, modelled_part_us=round(modelled_s * 1e6, 4))

    def insert_after(self, after, name, before, seconds, src, cls):
        """Add a node depending on `after`, feeding `before` (insertion order stays topological)."""
        g = self.g
        items = list(g.nodes.items())
        nd = dict(name=name, deps=[after], layer=g.nodes[before]["layer"], issue=seconds, issue_cat="kv_load",
                  depth=0.0, depth_cat="kv_load", ctrl=0.0, stream=False, kind="load", sweep=None, desc=src)
        out = {}
        for k, v in items:
            out[k] = v
            if k == after:
                out[name] = nd
        g.nodes.clear()
        g.nodes.update(out)
        g.nodes[before]["deps"].append(name)
        self.rows[name] = dict(node=name, model_us=0.0, measured_us=round(seconds * 1e6, 4), cls=cls, source=src)


def base_graph():
    """The adopted candidate_gather.lat259 composition (reproduces the committed 394.911 us)."""
    reader = json.loads((BASE / "reader.json").read_text())
    sel = {}
    for f in ("select.json", "select_l24_full.json"):
        sel.update(json.loads((BASE / f).read_text())["layers"])
    rs = json.loads((RC / "select.json").read_text())
    for tag, r in rs["layers"].items():
        sel[f"{tag}_mdrop"] = dict(local=dict(runs=r["drop_dense"]["runs"]), final=r["final"])
        sel[f"{tag}_gather"] = dict(local=dict(runs=r["gather"]["runs"]), final=r["final"])
    ck = M._ckv_cycles(json.loads((BASE / "ckv_lat259.json").read_text()))
    gather = json.loads((RC / "gather.json").read_text())
    g0, T0, _ = M.s58_graph()
    g = copy.deepcopy(g0)
    patches, modelled, *_ = M._apply(g, reader, sel, ck, "candidate_gather", gather)
    t, _ = M.layer_times(g)
    ar = t * 1e6 + EXTRA_HOPS * M.HOP_US
    assert abs(ar - 394.911) < 0.01, ar
    return g0, g, patches


def suffix_nodes(g, suf):
    return [n for n in g.nodes if n.endswith("." + suf) or n == suf]


def full_fec_inputs():
    """(links_full_fec.json, rack.json): the owner's full-FEC baseline (2026-10-06)."""
    return json.loads(FULL_FEC_LINKS.read_text()), json.loads(FULL_FEC_RACK.read_text())


def apply_links(P, links, tier="light_fec"):
    h = dict(links["hop"])
    colls = links["collectives"]
    phy = "light-FEC PHY VENDOR BUDGET 130 ns"
    ret_extra = 0
    if tier == "kp4_209ns":     # rack-cable full-KP4 tier (technology.json rom_rack_cable_serdes): sensitivity
        h.update(total_cycles=h["kp4_sensitivity"]["total_cycles"], token_return=h["token_return_kp4_sensitivity"])
    if tier == "full_fec":      # OWNER 2026-10-06: every off-package link on full RS(544,514), all measured in RTL
        lf, rk = full_fec_inputs()
        assert lf["exact"] and lf["status"] == "pass"
        h.update(total_cycles=lf["hop"]["total_cycles"], token_return=lf["token_return"])
        colls = lf["collectives"]
        phy = "full-KP4 PHY VENDOR BUDGET 209 ns"
        ret_extra = rk["hop_summary"]["token_return_extra_cycles_each"]
    hop_s = h["total_cycles"] / CLK
    for n, nd in P.g.nodes.items():
        if nd.get("kind") == "hop" and nd.get("hop_kind") in ("substage", "head", "stage"):
            P.put(n, hop_s, f"stage hop: ot_dsrom_link_rt RTL {h['measured_endpoint_cycles']} cyc (40,976 B, 64-B flits) "
                            f"+ {phy} + UCIe fan-out 10 ns + 2x45 routed wire stages ({h['total_cycles']} cyc)",
                  cls="measured+vendor_phy")
    tr = h["token_return"]
    P.put("token.return", (tr["total_cycles"] + tr["traversals"] * ret_extra) / CLK,
          f"token return: {tr['traversals']} x (link_rt endpoint 6 cyc + {phy}"
          + (f" + {ret_extra} cyc cable flight" if ret_extra else "") + ") + 90 wire",
          cls="measured+vendor_phy")
    for suf, c in colls.items():
        for n in suffix_nodes(P.g, suf):
            if n in P.rows:          # rows_allgather already inside the measured CKV path
                continue
            P.put(n, c["cycles"] / CLK, f"TP4 collective tb_w15b_v41_tp4 at S81 (U_WIRE 34, X_WIRE 45, 1.2 GHz"
                                         f"{', board leg full RS(544,514)' if tier == 'full_fec' else ''}), "
                                         f"{c['op']} {c['payload_B']} B, bit-exact", cls="measured")
    return hop_s


def apply_cand(P, cand, links):
    # as built: the local unit overflows and asks for the rank's 262,144 scores twice more; the re-streams come
    # from the index reader + scorer at the reader's MEASURED rate (5,821 cycles a rank, results/rtl/
    # dsrom_1m_measured_20261004/reader.json), not the select's 4,096-cycle ingest
    reader = json.loads((BASE / "reader.json").read_text())
    rd = max((r for r in reader["runs"] if r["name"].startswith("csa1_full_L20") and "clk833" in r["name"]),
             key=lambda r: r["cycles"])
    w = cand["local"]["worst_rank"]
    ingest = 4096
    replays = 2
    tail_after_first = w["cycles"] - ingest + replays * (rd["cycles"] - ingest)
    P.put("L20.attn.cand.topk_local", tail_after_first / CLK,
          f"ot_hdc_v41x_sel_cand on the golden 1M L20 scores ({w['cycles']} cyc incl. 2 overflow re-streams; "
          f"re-streams priced at the measured reader rate {rd['cycles']} cyc)", cls="measured")
    P.put("L20.attn.cand.final", cand["final"]["cycles"] / CLK,
          "ot_hdc_v41x_sel final top-2048 of 4 x 2048 block maxima (golden-equal)", cls="measured")
    return dict(local_after_scan_cycles=tail_after_first, reader_cycles=rd["cycles"])


def apply_head(P, head):
    lm = head["lm_head"]
    P.put("head.lm_head", lm["us_1p2GHz"] * 1e-6,
          f"one S81 head return group (8 BP=2 element pairs, 408 real rows, packed), scaled 409.6/408, +34 wire cyc",
          cls="measured")
    a = head["argmax"]
    drain_rows = 32320 - 408
    t = (drain_rows + a["cycles"]) / SLOW
    P.put("head.argmax", t, "S81 native ordered-root terminal, as built: rows contiguous per group, so 31,912 rows "
                            "drain after the sweep at 1 row / 0.9 GHz cycle + 12-cycle tail (all 32,320 exact)",
          cls="measured")
    return dict(lm_head_us=lm["us_1p2GHz"], argmax_drain_us=t * 1e6,
                stage_occupancy_us=head["wavefront"]["head_stage_occupancy_us_per_position"])


S81_WINDOW = ROOT / "results/rtl/dsrom_s81_window_bind_20261004/window_load.json"


def apply_window_s81(P, win):
    """S81-BOUND WINDOW terms (tools/dsrom_s81_window_la.py, claude/dsrom-s81-window-bind-20261004): the S81 die's
    window HBM service measured with the bound full-bandwidth load (per-PC issue, stack REFpb pull-in) on the 1M
    token's golden rows, in the S81 die's order: the token's own packed row is written through the as-built writer
    after kv_rope_qdq (own_row_write), the 128-row job starts at the attention issue (after the own row, q_rope and,
    in an indexed layer, the final select) and its rows are staged before the scores (window_load); means over the
    refresh phases, per layer type (window-only, scan, re-index, re-use)."""
    import dsrom_1m_measure as M
    terms = win["composition_terms"]["la"]
    g = P.g
    out = {}
    for name, nd in list(g.nodes.items()):
        if name.endswith(".attn.scores"):
            L = int(name.split(".")[0][1:])
            pre = f"L{L}.attn."
            t = terms[M._window_type(L)]
            wr = dict(name=pre + "own_row_write", deps=[pre + "kv_rope_qdq"], layer=nd["layer"],
                      issue=t["own_row_write_cycles"] / CLK, issue_cat="kv_load", depth=0.0, depth_cat="kv_load",
                      ctrl=0.0, stream=False, kind="load", sweep=None, desc="S81 own-row write (measured)")
            deps = [pre + "own_row_write", pre + "q_rope"] + ([pre + "idx.topk_final"] if pre + "idx.topk_final" in g.nodes else [])
            ld = dict(name=pre + "window_load", deps=deps, layer=nd["layer"], issue=t["window_cycles"] / CLK,
                      issue_cat="kv_load", depth=0.0, depth_cat="kv_load", ctrl=0.0, stream=False, kind="load",
                      sweep=None, desc="S81-bound WINDOW job (measured)")
            out[wr["name"]], out[ld["name"]] = wr, ld
            nd = dict(nd, deps=nd["deps"] + [pre + "window_load"])
            for n in (wr, ld):
                P.rows[n["name"]] = dict(node=n["name"], model_us=0.0, measured_us=round(n["issue"] * 1e6, 4),
                                         cls="measured", source=f"{t['source']} ({rel(S81_WINDOW)})")
        out[name] = nd
    g.nodes.clear()
    g.nodes.update(out)
    return dict(mode="s81", terms_cycles=terms, record=rel(S81_WINDOW))


def apply_window(P, win, mode="stream_la"):
    s = win["summary"]["stream_la"]
    t = s["cycles"]["max"] / CLK if mode == "stream_la" else win["summary"]["asbuilt_c1"]["us_max"] * 1e-6
    for L in range(40):
        before = f"L{L}.attn.scores"
        after = f"L{L}.attn.hc_pre"
        if before in P.g.nodes and after in P.g.nodes:
            P.insert_after(after, f"L{L}.attn.window_load", before, t,
                           "WINDOW 128 rows x 17 sectors, ot_dsrom_window_stream_la on timed HBM3E, worst of 64 phases "
                           f"({s['cycles']['max']} cyc; {100 * s['sustained_after_first_access_frac']:.1f}% of peak sustained) "
                           "-- REQUIRES S81 BINDING OF THE WINDOW MODULE (Codex)", cls="measured_requires_binding")
    return dict(per_layer_us=t * 1e6, asbuilt_c1_us=win["summary"]["asbuilt_c1"]["us_median"],
                fraction_of_peak_sustained=s["sustained_after_first_access_frac"])


def apply_table(P, rows, label):
    """rows: {node name: (seconds, source)} from the field / SU adapters."""
    for n, (t, src, cls, mod) in rows.items():
        if n in P.g.nodes and n not in P.rows:
            P.put(n, t, f"{label}: {src}", cls=cls, modelled_s=mod)


def apply_levers(P, info, lever_dir, excluded=()):
    """Recovery baseline: every ADOPTED lever record in `lever_dir`/levers/*.json replaces the measured terms it
    re-measured on its successor RTL.  Record schema (opentallas.dsrom-recovery.lever.v1):
      lever, verdict ("ADOPT" | "REJECT" | ...), exact (bool), ss_ff (signoff summary),
      nodes  {"<node name>" | "*.<suffix>": {"us": float, "source": str, "cls": "measured",
              "kind": optional graph kind, e.g. "fused_fast" for a node moved to the 1.2 GHz domain (not in
              uarch_model.SLOW_KINDS), so the measured CDC is charged on the edges the move creates or removes}}
      info   {"hop_us": all stage hops + extra S81 hops, "head_stage_occupancy_us", "head_argmax_drain_us",
              "draft_blocks_total_us" + "draft_blocks_source": the three DSpark blocks re-measured with the recovery
              levers (ONE lever record owns it, normally levers/draft.json; the 5 draft head sweeps follow
              head_stage_occupancy_us)}
    Only verdict ADOPT with exact true is applied; the others are listed."""
    applied, skipped = [], []
    for f in sorted((lever_dir / "levers").glob("*.json")):
        r = json.loads(f.read_text())
        if r.get("schema") != "opentallas.dsrom-recovery.lever.v1":      # an analysis record kept beside the levers
            continue
        row = dict(lever=r["lever"], record=rel(f), sha256=sha(f), verdict=r.get("verdict"))
        if r["lever"] in excluded or r.get("verdict") != "ADOPT" or r.get("exact") is not True:
            skipped.append(row)
            continue
        for key, v in r.get("nodes", {}).items():
            names = suffix_nodes(P.g, key[2:]) if key.startswith("*.") else [key]
            assert names and all(n in P.g.nodes for n in names), (f, key)
            for n in names:
                P.put(n, v["us"] * 1e-6, f"{r['lever']}: {v['source']}", cls=v.get("cls", "measured"))
                if "kind" in v:
                    P.g.nodes[n]["kind"] = v["kind"]
        li = r.get("info", {})
        if "hop_us" in li:
            for n, nd in P.g.nodes.items():
                if nd.get("kind") == "hop" and nd.get("hop_kind") in ("substage", "head", "stage"):
                    P.put(n, li["hop_us"] * 1e-6, f"{r['lever']}: {li.get('hop_source', 'stage hop')}",
                          cls=li.get("hop_cls", "measured+vendor_phy"))
            info["hop_us"] = li["hop_us"]
        h = info.setdefault("head", {})
        if "head_stage_occupancy_us" in li:
            h["stage_occupancy_us"] = li["head_stage_occupancy_us"]
        if "head_argmax_drain_us" in li:
            h["argmax_drain_us"] = li["head_argmax_drain_us"]
        if "draft_blocks_total_us" in li:
            assert "draft_blocks" not in info, f"two lever records set draft_blocks_total_us ({f})"
            info["draft_blocks"] = dict(us=li["draft_blocks_total_us"], lever=r["lever"],
                                        source=li.get("draft_blocks_source", rel(f)))
        applied.append(row)
    return dict(applied=applied, not_applied=skipped)


def apply_candidate(P, record):
    """Conditional decision study only; never changes a lever's adoption record.

    Uses the same node replacement semantics as apply_levers. Candidate costs exclude
    the independently inserted CDC terms, which the composer adds exactly once.
    """
    if record.get("exact") is not True:
        raise ValueError("candidate must have a positive exactness measurement")
    seen = set()
    for key, value in record.get("nodes", {}).items():
        names = suffix_nodes(P.g, key[2:]) if key.startswith("*.") else [key]
        if not names or any(n not in P.g.nodes for n in names):
            raise ValueError(f"candidate node not in the baseline: {key}")
        for name in names:
            if name in seen:
                raise ValueError(f"candidate replaces a node twice: {name}")
            seen.add(name)
            seconds = float(value["us"]) * 1e-6
            if not math.isfinite(seconds) or seconds < 0:
                raise ValueError(f"invalid candidate latency: {name}")
            if seconds == 0 and not value.get("covered_by"):
                raise ValueError(f"zero candidate latency requires a measured covering node: {name}")
            P.put(name, seconds, f"conditional {record['lever']}: {value['source']}",
                  cls=value.get("cls", "measured"))
            if "kind" in value:
                P.g.nodes[name]["kind"] = value["kind"]
    return sorted(seen)


def apply_engram(P, eng):
    """engram.json: the Engram nodes on the stream unit (wired variant), operands rebuilt from the released checkpoint."""
    n = 0
    for name, e in eng["nodes"].items():
        if name in P.g.nodes and name not in P.rows:
            P.put(name, e["us"] * 1e-6, f"Engram SU chain: {e['source']}", cls="measured" if e["exact"] else
                  "measured_not_exact")
            n += 1
    return dict(nodes=n, exact=eng["exact"])


def apply_embed(P, emb, tier="light_fec"):
    e = emb["nodes"]["embed"]
    us, note = e["us"], ""
    if tier == "full_fec":      # the embed's TP4 owner->4 ranks all-gather moves by the measured full-FEC shift
        lf, _ = full_fec_inputs()
        assert lf["collective_delta_cycles"]["constant"]
        d = lf["collective_delta_cycles"]["values"][0]
        us += d / CLK * 1e6
        note = f" + {d} cyc full-FEC board leg (links_full_fec.json, constant over every measured TP4 payload)"
    P.put("embed", us * 1e-6, f"embed: {e['source']}{note}", cls="measured" if e["exact"] else "measured_not_exact")
    return dict(us=round(us, 4), parts={k: round(v["us"], 4) for k, v in e["parts"].items()}, exact=e["exact"])


def draft_full_fec_delta(blocks_record, links):
    """Full-FEC increment of the DSpark draft blocks (us): every board hop on a block's critical path (cls
    measured+vendor_phy, us > 0) moves by the measured hop shift (+ the draft-link cable flight from the rack record);
    every TP4 collective by the measured collective shift per issue (issues = node us / the S81 single-issue us)."""
    lf, rk = full_fec_inputs()
    dh = lf["hop"]["delta_cycles"] + rk["hop_summary"]["draft_link_extra_cycles_each"]
    dc = lf["collective_delta_cycles"]["values"][0]
    single = {k: v["us"] for k, v in links["collectives"].items()}
    cyc, n_hop, n_coll = 0, 0, 0
    for b in json.loads(Path(blocks_record).read_text())["stages"].values():
        for x in b["critical_path"]:
            if x["cls"] == "measured+vendor_phy" and x["us"] > 0:
                cyc += dh
                n_hop += 1
            elif x["node"] in single:
                k = max(1, round(x["us"] / single[x["node"]]))
                cyc += k * dc
                n_coll += k
    return dict(us=cyc / CLK * 1e6, cycles=cyc, board_hops=n_hop, collective_issues=n_coll, hop_delta_cycles=dh,
                collective_delta_cycles=dc, record=rel(blocks_record))


def su_with_qdq(su, q):
    """su.json with every quantiser's wired time replaced by the SIMULATED hub stages (su_qdq_wired.json); the
    arithmetic +37 cycles of su.json are dropped.  Returns (su copy, replaced count)."""
    su = copy.deepcopy(su)
    n = 0
    for key, r in q["nodes"].items():
        L, suf = key.split(".", 1)
        if r["part"] == "whole" and key in su["nodes"]:
            su["nodes"][key]["wired_us"] = r["qdq_wired_us"]
            su["nodes"][key]["qdq_wired_simulated"] = True
            n += 1
        lay = su.get("node_us_by_layer", {}).get(L, {})
        if r["part"] != "whole" and suf in lay and "qdq" in lay[suf]:
            lay[suf]["qdq"] = dict(lay[suf]["qdq"], wired_us=r["qdq_wired_us"], exact=r["exact"], simulated=True)
            n += 1
    return su, n


def su_without_model_cdc(su):
    su = copy.deepcopy(su)
    for x in su["nodes"].values():
        x["model_cdc_us"] = 0.0
    return su


def apply_cdc(P, cdc):
    """Every non-hop node with a dependency in the other clock domain pays the MEASURED crossing once (f2s on a
    0.9 GHz consumer, s2f on a 1.2 GHz consumer), as uarch_model charges CDC_W18: a patched node gets it added; an
    unpatched node's model depth already holds CDC_W18, which is swapped for the measured value."""
    import uarch_model as u
    g = P.g
    f2s, s2f = cdc["crossing"]["f2s"]["us"] * 1e-6, cdc["crossing"]["s2f"]["us"] * 1e-6
    mf2s = u.CDC_W18["fast_to_slow_slow_cycles"] / SLOW
    ms2f = u.CDC_W18["slow_to_fast_fast_cycles"] / CLK
    added, swapped = {}, 0
    for n, nd in g.nodes.items():
        if nd.get("kind") in ("hop", "join"):
            continue
        sl = nd["kind"] in u.SLOW_KINDS
        if not any((g.nodes[d]["kind"] in u.SLOW_KINDS) != sl for d in nd["deps"] if g.nodes[d]["kind"] != "join"):
            continue
        x = f2s if sl else s2f
        if n in P.rows:
            nd["issue"] += x
            P.rows[n]["cdc_measured_us"] = round(x * 1e6, 5)
        else:
            nd["depth"] = max(0.0, nd["depth"] - (mf2s if sl else ms2f)) + x
            swapped += 1
        added[n] = x
    return dict(edges=len(added), f2s_us=round(f2s * 1e6, 5), s2f_us=round(s2f * 1e6, 5),
                model_f2s_us=round(mf2s * 1e6, 5), model_s2f_us=round(ms2f * 1e6, 5), unpatched_swapped=swapped), added


def classify(g, P, base_patches):
    fin = g.solve(True)
    sink = [n for n in g.nodes if n.endswith("token.return")][0]
    base = {p["node"]: p for p in base_patches}
    out, tot = [], 0.0
    for n in g.path(sink):
        c = sum(g.contrib[n].values()) * 1e6
        tot += c
        if n in P.rows:
            k = P.rows[n]["cls"]
        elif n in base:
            k = "measured" if base[n]["measured_us"] > 0 or base[n]["measured_cycles"] > 0 else "inside_measured"
        elif c == 0:
            k = "zero"
        else:
            k = "modelled"
        out.append(dict(node=n, us=round(c, 4), cls=k))
    return fin[sink] * 1e6, out


def stage_busy(g):
    """Busy time of each stage for one position: from the stage's first input to the hop that leaves it (the
    wavefront RTL shows a stage takes the next position only after finishing the current one)."""
    fin = g.solve(True)
    sink = [n for n in g.nodes if n.endswith("token.return")][0]
    segs, start, first = [], 0.0, None
    for n in g.path(sink):
        first = first or n
        if g.nodes[n].get("kind") == "hop":
            hop_t = sum(g.contrib[n].values())
            segs.append(dict(first=first, hop=n, busy_us=round((fin[n] - hop_t - start) * 1e6, 4)))
            start, first = fin[n], None
    return segs


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rec", type=Path, default=REC)
    ap.add_argument("--out", type=Path, default=None,
                    help="default: <rec>/composition.json (asbuilt) or <recovery>/composition.json (recovery)")
    ap.add_argument("--baseline", default="recovery", choices=("asbuilt", "recovery"),
                    help="recovery (default): apply the adopted lever records of --recovery on top of as-built")
    ap.add_argument("--recovery", type=Path, default=RECOVERY)
    ap.add_argument("--window", default="s81", choices=("s81", "stream_la", "asbuilt_c1"),
                    help="s81 (default): the S81-bound window record; stream_la / asbuilt_c1: the audit's component")
    ap.add_argument("--hop-tier", default=DEFAULT_HOP_TIER, choices=("full_fec", "light_fec", "kp4_209ns"),
                    help="full_fec (default, OWNER 2026-10-06): every off-package link on full RS(544,514) -- stage "
                         "hops, token return, TP4 collectives, embed and draft links, measured in RTL, + cable flight "
                         "per hop class; light_fec: the superseded 130 ns board budget (history)")
    a = ap.parse_args()
    return compose(a)


# CLAUDE DS-REPRICE 2026-10-06: wired S81 r8 die geometry (results/rtl/dsrom_field_reprice_r8_20261006/reprice.json).
# FIELD_GEOM (adapters) picks the element frame: field wire per region, the hub-slab stations, and -- for the taller
# q-element frames -- the extra layer dies' stage hops (each at the measured full-FEC stage hop + mean cable flight).
SU_FUSED_LEVERS = ("su_norm", "su_swiglu", "su_hcpost", "su_softmax")
FIELD_LEVER_CFG = {"field_spine_pq": "pq", "field_spine": "baseline"}


def apply_r8_reprice(P, info, geom):
    """Re-patch lever-applied field nodes at a non-default geometry, and add the hub-slab stations the r8 die
    wires as direct nets (SU out path through HC, collective -> VM) beyond what each node already charges."""
    import dsrom_1m_allmeasured_adapters as AD
    if not AD.REPRICE.exists():
        return None
    rp = json.loads(AD.REPRICE.read_text())
    G = rp["geoms"].get(geom) or {}
    out = dict(record=rel(AD.REPRICE), geom=geom, label=G.get("label", "old charge: 80 cycles a field phase"),
               field_lever_nodes=0, su_fused_nodes=0, su_wired_nodes=0, collective_nodes=0)
    if geom != rp["default_geom"]:       # lever records carry the default geometry; re-price (geom None = old 80)
        cache = {}
        for n, row in list(P.rows.items()):
            lev = next((k for k in FIELD_LEVER_CFG if row["source"].startswith(k + ":")), None)
            if lev is None:
                continue
            if lev not in cache:
                lr = json.loads((RECOVERY / "levers" / f"{lev}.json").read_text())
                cache[lev] = AD.field_rows(P.g, json.loads((ROOT / lr["measurement"]["record"]).read_text()), geom=geom)
            sec, src, cls, _m = cache[lev][n]
            tag = row["source"].split(": ", 1)[0]
            P.put(n, sec, f"{tag}: {src}", cls=row["cls"])
            out["field_lever_nodes"] += 1
    if geom is None:
        out.update(extra_stage_hops=0, stages=81, layer_dies=324)
        return out
    hub = G["hub"]
    su_ex = {k: max(v["su"][sl]["excess_ns"][k] for v in hub.values() for sl in v["su"]) for k in ("fused", "wired")}
    coll = max(v["collective_vm_added"] for v in hub.values())
    out.update(su_excess_ns=su_ex, collective_vm_stations=coll)
    for n, row in list(P.rows.items()):
        src = row["source"]
        add_ns = 0.0
        if src.split(":", 1)[0] in SU_FUSED_LEVERS and row["measured_us"] > 0:
            add_ns, key = su_ex["fused"], "su_fused_nodes"
        elif (src.startswith("SU:") or src.startswith("Engram SU chain")) and row["measured_us"] > 0:
            add_ns, key = su_ex["wired"], "su_wired_nodes"
        elif src.startswith("TP4 collective") and row["measured_us"] > 0:
            add_ns, key = coll / CLK * 1e9, "collective_nodes"
        if add_ns > 0:
            P.g.nodes[n]["issue"] += add_ns * 1e-9
            row["measured_us"] = round(row["measured_us"] + add_ns * 1e-3, 4)
            row["source"] += f" + r8 hub-slab stations {add_ns:.3f} ns"
            out[key] += 1
    out["extra_stage_hops"] = G["extra_stage_hops"]
    out["stages"] = G["stages"]
    out["layer_dies"] = G["layer_dies"]
    return out


def compose(a, *, candidates=(), excluded_levers=(), graph_hook=None, write_output=True):
    """Replay the timing authority without a CLI subprocess or mutable lever directory.

    The default path is unchanged. Decision-gate callers can hold adopted inputs
    fixed and price preliminary measurements without enabling their hardware.
    """
    if a.out is None:
        a.out = (a.rec if a.baseline == "asbuilt" else a.recovery) / "composition.json"
    ins = {k: a.rec / f"{k}.json" for k in ("field", "su", "head", "links", "cand_select", "engram", "embed",
                                             "su_cdc", "su_qdq_wired", "draft_blocks")}
    recs = {k: json.loads(p.read_text()) for k, p in ins.items() if p.exists()}
    g0, g, base_patches = base_graph()
    P = Patcher(g)
    info = {}
    if "links" in recs:
        info["hop_us"] = apply_links(P, recs["links"], a.hop_tier) * 1e6
    if "cand_select" in recs:
        info["cand"] = apply_cand(P, recs["cand_select"], recs.get("links"))
    if "head" in recs:
        info["head"] = apply_head(P, recs["head"])
    if a.window == "s81":
        info["window"] = apply_window_s81(P, json.loads(S81_WINDOW.read_text()))
    else:
        info["window"] = apply_window(P, json.loads(WINDOW.read_text()), a.window)
        info["window"]["mode"] = a.window
    info["hop_tier"] = a.hop_tier
    if "field" in recs:
        import dsrom_1m_allmeasured_adapters as AD
        apply_table(P, AD.field_rows(g, recs["field"]), "ROM field")
    if "engram" in recs:
        info["engram"] = apply_engram(P, recs["engram"])
    if "embed" in recs:
        info["embed"] = apply_embed(P, recs["embed"], a.hop_tier)
    if "su" in recs:
        import dsrom_1m_allmeasured_adapters as AD
        su = recs["su"]
        if "su_qdq_wired" in recs:
            su, info["qdq_wired_simulated_nodes"] = su_with_qdq(su, recs["su_qdq_wired"])
        if "su_cdc" in recs:
            su = su_without_model_cdc(su)
        apply_table(P, AD.su_rows(g, su), "SU")
    if a.baseline == "recovery":
        info["levers"] = apply_levers(P, info, a.recovery, excluded_levers)
    if "field" in recs:
        import dsrom_1m_allmeasured_adapters as AD
        r8 = apply_r8_reprice(P, info, AD.FIELD_GEOM)
        if r8:
            info["r8_reprice"] = r8
    if candidates:
        info["conditional_candidates"] = [dict(lever=r["lever"], nodes=apply_candidate(P, r)) for r in candidates]
    cdc_nodes = {}
    if "su_cdc" in recs:
        info["cdc"], cdc_nodes = apply_cdc(P, recs["su_cdc"])
    if graph_hook is not None:
        graph_hook(g, P, base_patches, info)
    t, path = classify(g, P, base_patches)
    hop_extra = info.get("hop_us", M.HOP_US)
    cable_us, ii_cable_us = 0.0, 0.0
    if a.hop_tier == "full_fec":   # cable flight beyond the 0.3 m inside the measured hop, per hop class (rack record)
        _, rk = full_fec_inputs()
        hs = rk["hop_summary"]
        cable_us = (hs["stage_hop_extra_cycles"] + hs["head_hop_extra_cycles"]) / CLK * 1e6
        ii_cable_us = max(x["extra_cycles"] for x in rk["stage_hops"]) / CLK * 1e6
        info["full_fec"] = dict(rack=rel(FULL_FEC_RACK), links=rel(FULL_FEC_LINKS), cable_flight_us=round(cable_us, 4),
                                stage_hops_by_class=hs["stage_hops"], head_hop=rk["head_hop"]["cls"],
                                token_return=rk["token_return"]["cls"], ii_hop_cable_us=round(ii_cable_us, 4))
    tall = info.get("r8_reprice", {}).get("extra_stage_hops", 0)
    if tall:        # taller q-element frame: more layer dies -> more pipeline stages, each a full stage hop
        _, rk = full_fec_inputs()
        mean_cable = rk["hop_summary"]["stage_hop_extra_cycles"] / len(rk["stage_hops"]) / CLK * 1e6
        info["r8_reprice"]["extra_stage_hops_us"] = round(tall * (hop_extra + mean_cable), 4)
        cable_us += tall * mean_cable
    ar = t + (EXTRA_HOPS + tall) * hop_extra + cable_us
    # ---- MTP: wavefront verify with this composition's stage busy times (measured handoff rule) + DSpark draft
    wave = json.loads(WAVE.read_text())["composition"]
    segs = stage_busy(g)
    head_occ = info.get("head", {}).get("stage_occupancy_us", M.WAVEFRONT["head_occ_us"])
    for s in segs:
        if s["hop"] == "token.return":          # the head stage: lm_head sweep is its occupancy (terminal overlaps)
            s["busy_us"] = max(s["busy_us"] - info.get("head", {}).get("argmax_drain_us", 0.0), head_occ)
    worst = max(segs, key=lambda s: s["busy_us"])
    ii = worst["busy_us"] * (1 + wave["measured_interval_overhead"]) + hop_extra + ii_cable_us
    verify = ar + M.WAVEFRONT["positions"] * ii
    dr = json.loads(DRAFT_REC.read_text())["result"]
    r_markov = dr["transfer_ratios"]["markov_over_head_macs_full"]
    db = recs.get("draft_blocks")
    blocks_us = db["blocks_total_us"] if db else 3 * dr["block5_us"]
    if "draft_blocks" in info:                  # recovery lever re-measured the three blocks
        blocks_us = info["draft_blocks"]["us"]
        if a.hop_tier == "full_fec":
            src = ROOT / info["draft_blocks"]["source"].split(" ")[0]
            fd = draft_full_fec_delta(src, recs["links"])
            info["draft_blocks"]["full_fec"] = fd
            blocks_us += fd["us"]
    draft = blocks_us + 5 * head_occ * (1 + r_markov)
    step = verify + draft + M.DRAFT["seed_commit_us"]
    mtp = M.DRAFT["tau"] * 1e6 / step
    modelled = [p for p in path if p["cls"] == "modelled"]
    by = {}
    for p in path:
        by[p["cls"]] = round(by.get(p["cls"], 0.0) + p["us"], 3)
    by["extra_S81_hops"] = round((EXTRA_HOPS + tall) * hop_extra, 3)
    if cable_us:
        by["cable_flight"] = round(cable_us, 3)
    fam = {}
    for p in modelled:
        f = p["node"].split(".", 1)[1] if p["node"].startswith(("L", "E")) else p["node"]
        fam[f] = round(fam.get(f, 0.0) + p["us"], 3)
    onpath = {p["node"] for p in path}
    sub = {n: r.get("modelled_part_us", 0.0) for n, r in P.rows.items() if n in onpath and r.get("modelled_part_us")}
    sub_us = round(sum(sub.values()), 3)
    meas = sum(v for k, v in by.items() if k not in ("modelled", "zero")) - sub_us
    eng_us = round(sum(v for k, v in fam.items() if k.startswith("eng.")), 3)
    still, done = [], []
    if "engram" in recs:
        done.append(dict(term="Engram eng.hh / eng.dot / eng.gate / eng.add (L1, L14)", record="engram.json",
                         us_on_path=round(sum(p["us"] for p in path if ".eng." in p["node"]), 3), exact=recs["engram"]["exact"],
                         was="modelled 1.316 us on path"))
    else:
        still.append(dict(term="Engram eng.dot / eng.gate / eng.add (L1, L14)", us=eng_us,
                          why="golden shard holds only h_in and the Engram output, not hashed rows / key / value"))
    if "embed" in recs:
        done.append(dict(term="embed (owner-rank ROM row read + wire + TP4 send + 4-copy expand)", record="embed.json",
                         us_on_path=round(sum(p["us"] for p in path if p["node"] == "embed"), 3),
                         exact=recs["embed"]["exact"], was="modelled 0.032 us"))
    else:
        still.append(dict(term="embed (embedding ROM row read + 4-copy expand)", us=fam.get("embed", 0.0), why="no bench"))
    if "su_cdc" in recs:
        done.append(dict(term="domain crossings (meso FIFO + 3:4 ratio FIFO) on every slow<->fast edge", record="su_cdc.json",
                         us_on_path=round(sum(cdc_nodes.get(p["node"], 0.0) for p in path) * 1e6, 3),
                         exact=recs["su_cdc"]["exact"], was="model W18 4 slow cycles on SU nodes (1.773 us on path); "
                                                            "the s2f charge was lost on patched fast nodes"))
        still.append(dict(term="fast->fast mesochronous region crossings (field region <-> hub / IO regions)", us=None,
                          why="no S81 clock-region map of every 1.2 GHz edge; the clocking decision prices them at "
                              "+661 cycles (0.55 us) a token central (results/uarch/rom_die_clocking_decision_20261003)"))
    else:
        still.append(dict(term="CDC fast->slow crossings on SU nodes", us=sub_us, why="W18 ratio-FIFO latency, no CDC bench"))
    still.append(dict(term=("full-KP4 PHY (209 ns a board or cable hop, OWNER full-FEC baseline 2026-10-06)"
                            if a.hop_tier == "full_fec" else "light-FEC PHY (130 ns a board hop)") + " and UCIe PHY (10 ns)",
                      us=None, why="VENDOR BUDGET (no PHY RTL); inside the measured+vendor_phy hop terms"))
    if "su_qdq_wired" in recs:
        done.append(dict(term="quantiser hub network stages (22 + 15 slow cycles) simulated as RTL stages",
                         record="su_qdq_wired.json", nodes=info.get("qdq_wired_simulated_nodes"),
                         exact=recs["su_qdq_wired"]["exact"], was="added arithmetically"))
    else:
        still.append(dict(term="quantiser hub network stages (22 + 15 slow cycles)", us=None,
                          why="added arithmetically to the RTL quantiser (other SU nodes ran them in RTL)"))
    if db:
        done.append(dict(term="MTP draft: three DSpark blocks at full shape", record="draft_blocks.json",
                         us=round(blocks_us, 3), exact=db["exact"], was=f"{3 * dr['block5_us']:.3f} us reduced-vehicle"))
        still += [dict(term=f"draft blocks: {x['term']}", us=x.get("us"), why=x.get("why")) for x in db.get("still_modelled", [])]
    else:
        still.append(dict(term="MTP draft block5 (3 DSpark blocks)", us=round(3 * dr["block5_us"], 3),
                          why="reduced-vehicle slice x transfer ratio (dsrom_dspark_step_slices_20261004), not full shape"))
    still.append(dict(term=f"tau {M.DRAFT['tau']:g}", us=None,
                      why=f"acceptance, not an RTL quantity: {TP.tau_src('deepseek_v41', 5)}; published V4.1 3.8879 "
                          "and range 3.43-4.32 kept as MTP.tau_sensitivity"))
    rec = dict(
        schema="opentallas.dsrom-1m.allmeasured.composition.v1", context=M.CTX, position=M.POS,
        baseline=a.baseline,
        base="candidate_gather.lat259 (results/rtl/dsrom_reindex_candidates_20261004/composition.json, 394.911 us)",
        AR_us=round(ar, 3), AR_tok_s=round(1e6 / ar, 1),
        critical_path_us_by_class=by, measured_share=round(meas / ar, 4),
        modelled_on_path_us=round(sum(p["us"] for p in modelled), 3), modelled_on_path_by_family=fam,
        modelled_inside_measured_nodes_us=sub_us,
        modelled_inside_measured_note=("none: CDC measured (su_cdc.json)" if "su_cdc" in recs else
                                       "CDC fast->slow ratio-FIFO crossings (4 slow cycles a crossing edge, W18) charged "
                                       "on SU nodes as the model does; no CDC bench"),
        cdc_on_path_us=round(sum(cdc_nodes.get(p["node"], 0.0) for p in path) * 1e6, 3),
        still_modelled_total_us=round(sum(p["us"] for p in modelled) + sub_us, 3),
        MTP=dict(rule="II = slowest stage busy x (1 + measured handoff 46/11271) + measured hop; verify = AR + 5 II; "
                      "draft = 3 DSpark blocks + 5 x head occupancy x (1 + Markov/lm_head MACs); tau " + f"{M.DRAFT['tau']:g} ({TP.tau_src('deepseek_v41', 5)})",
                 stage_busy_top=sorted(segs, key=lambda s: -s["busy_us"])[:6], worst_stage=worst,
                 II_us=round(ii, 3), verify_us=round(verify, 3), draft_us=round(draft, 3),
                 draft_terms=dict(block5_us=db["block5_us"] if db else dr["block5_us"], blocks_us=round(blocks_us, 3),
                                  block5_basis=(db["basis"] if db else "reduced-vehicle slice x transfer ratio "
                                                "(results/rtl/dsrom_dspark_step_slices_20261004) -- NOT full shape"),
                                  head_occ_us=head_occ, r_markov=r_markov),
                 seed_commit_us=M.DRAFT["seed_commit_us"], step_us=round(step, 3), MTP_tok_s=round(mtp, 1),
                 tau=M.DRAFT["tau"], tau_source=TP.tau_src("deepseek_v41", 5), mtp_over_ar=round(mtp * ar / 1e6, 3),
                 tau_sensitivity=TP.mtp_sensitivity(step)),
        still_modelled=still,
        measured_formerly_modelled=done,
        requires_binding=([] if a.window == "s81" else
                          ["WINDOW load: ot_dsrom_window_stream_la measured 93.9% of peak; the as-built S81 prefetch "
                           "measures 124.5 us a layer -- composition REQUIRES S81 BINDING OF THE WINDOW MODULE (Codex)"]),
        info=info, patches=list(P.rows.values()), base_patches=base_patches, critical_path=path,
        inputs={rel(p): sha(p) for p in list(ins.values()) + sorted((a.recovery / "levers").glob("*.json")) + [WINDOW, S81_WINDOW, WAVE, DRAFT_REC, BASE / "reader.json",
                                                             BASE / "ckv_lat259.json", RC / "gather.json",
                                                             RC / "select.json"] if Path(p).exists()},
        tool_sha256={rel(ROOT / "tools/dsrom_1m_allmeasured.py"): sha(ROOT / "tools/dsrom_1m_allmeasured.py"),
                     rel(ROOT / "tools/dsrom_1m_measure.py"): sha(ROOT / "tools/dsrom_1m_measure.py")})
    bind_wavefront_physical_verdict(rec)
    if write_output:
        a.out.write_text(json.dumps(rec, indent=1, default=str) + "\n")
        print(json.dumps(dict(AR_us=rec["AR_us"], AR_tok_s=rec["AR_tok_s"], by=by, share=rec["measured_share"],
                          modelled=rec["still_modelled_total_us"], II=rec["MTP"]["II_us"], worst=worst["hop"],
                          draft=rec["MTP"]["draft_us"], MTP=rec["MTP"]["MTP_tok_s"]), indent=0))
    return rec


if __name__ == "__main__":
    main()
