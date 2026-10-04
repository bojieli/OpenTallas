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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_1m_measure as M  # noqa: E402

REC = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004"
BASE = ROOT / "results/rtl/dsrom_1m_measured_20261004"
RC = ROOT / "results/rtl/dsrom_reindex_candidates_20261004"
WINDOW = ROOT / "results/rtl/hbm_path_bandwidth_audit_20261004/dsrom_window_load.json"
WAVE = ROOT / "results/rtl/dsrom_wavefront_verify_20261004/record.json"
DRAFT_REC = ROOT / "results/rtl/dsrom_fused_draft_head_20261004/l1_compose.json"
RECOVERY = ROOT / "results/rtl/dsrom_recovery_20261004"     # microarchitecture-recovery levers (baseline "recovery")
CLK = 1.2e9
SLOW = 0.9e9
EXTRA_HOPS = M.S81_EXTRA_HOPS


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


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


def apply_links(P, links, tier="light_fec"):
    h = dict(links["hop"])
    if tier == "kp4_209ns":     # rack-cable full-KP4 tier (technology.json rom_rack_cable_serdes): sensitivity
        h.update(total_cycles=h["kp4_sensitivity"]["total_cycles"], token_return=h["token_return_kp4_sensitivity"])
    hop_s = h["total_cycles"] / CLK
    for n, nd in P.g.nodes.items():
        if nd.get("kind") == "hop" and nd.get("hop_kind") in ("substage", "head", "stage"):
            P.put(n, hop_s, f"stage hop: ot_dsrom_link_rt RTL {h['measured_endpoint_cycles']} cyc (40,976 B, 64-B flits) "
                            f"+ light-FEC PHY VENDOR BUDGET 130 ns + UCIe fan-out 10 ns + 2x45 routed wire stages",
                  cls="measured+vendor_phy")
    tr = h["token_return"]
    P.put("token.return", tr["total_cycles"] / CLK,
          f"token return: {tr['traversals']} x (link_rt endpoint 6 cyc + light-FEC PHY VENDOR BUDGET 156 cyc) + 90 wire",
          cls="measured+vendor_phy")
    for suf, c in links["collectives"].items():
        for n in suffix_nodes(P.g, suf):
            if n in P.rows:          # rows_allgather already inside the measured CKV path
                continue
            P.put(n, c["cycles"] / CLK, f"TP4 collective tb_w15b_v41_tp4 at S81 (U_WIRE 34, X_WIRE 45, 1.2 GHz), "
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


def apply_levers(P, info, lever_dir):
    """Recovery baseline: every ADOPTED lever record in `lever_dir`/levers/*.json replaces the measured terms it
    re-measured on its successor RTL.  Record schema (opentallas.dsrom-recovery.lever.v1):
      lever, verdict ("ADOPT" | "REJECT" | ...), exact (bool), ss_ff (signoff summary),
      nodes  {"<node name>" | "*.<suffix>": {"us": float, "source": str, "cls": "measured"}}
      info   {"hop_us": all stage hops + extra S81 hops, "head_stage_occupancy_us", "head_argmax_drain_us"}
    Only verdict ADOPT with exact true is applied; the others are listed."""
    applied, skipped = [], []
    for f in sorted((lever_dir / "levers").glob("*.json")):
        r = json.loads(f.read_text())
        row = dict(lever=r["lever"], record=rel(f), sha256=sha(f), verdict=r.get("verdict"))
        if r.get("verdict") != "ADOPT" or r.get("exact") is not True:
            skipped.append(row)
            continue
        for key, v in r.get("nodes", {}).items():
            names = suffix_nodes(P.g, key[2:]) if key.startswith("*.") else [key]
            assert names and all(n in P.g.nodes for n in names), (f, key)
            for n in names:
                P.put(n, v["us"] * 1e-6, f"{r['lever']}: {v['source']}", cls=v.get("cls", "measured"))
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
        applied.append(row)
    return dict(applied=applied, not_applied=skipped)


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
    ap.add_argument("--window", default="stream_la", choices=("stream_la", "asbuilt_c1"))
    ap.add_argument("--hop-tier", default="light_fec", choices=("light_fec", "kp4_209ns"))
    a = ap.parse_args()
    if a.out is None:
        a.out = (a.rec if a.baseline == "asbuilt" else a.recovery) / "composition.json"
    ins = {k: a.rec / f"{k}.json" for k in ("field", "su", "head", "links", "cand_select")}
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
    info["window"] = apply_window(P, json.loads(WINDOW.read_text()), a.window)
    info["window"]["mode"] = a.window
    info["hop_tier"] = a.hop_tier
    if "field" in recs:
        import dsrom_1m_allmeasured_adapters as AD
        apply_table(P, AD.field_rows(g, recs["field"]), "ROM field")
    if "su" in recs:
        import dsrom_1m_allmeasured_adapters as AD
        apply_table(P, AD.su_rows(g, recs["su"]), "SU")
    if a.baseline == "recovery":
        info["levers"] = apply_levers(P, info, a.recovery)
    t, path = classify(g, P, base_patches)
    hop_extra = info.get("hop_us", M.HOP_US)
    ar = t + EXTRA_HOPS * hop_extra
    # ---- MTP: wavefront verify with this composition's stage busy times (measured handoff rule) + DSpark draft
    wave = json.loads(WAVE.read_text())["composition"]
    segs = stage_busy(g)
    head_occ = info.get("head", {}).get("stage_occupancy_us", M.WAVEFRONT["head_occ_us"])
    for s in segs:
        if s["hop"] == "token.return":          # the head stage: lm_head sweep is its occupancy (terminal overlaps)
            s["busy_us"] = max(s["busy_us"] - info.get("head", {}).get("argmax_drain_us", 0.0), head_occ)
    worst = max(segs, key=lambda s: s["busy_us"])
    ii = worst["busy_us"] * (1 + wave["measured_interval_overhead"]) + hop_extra
    verify = ar + M.WAVEFRONT["positions"] * ii
    dr = json.loads(DRAFT_REC.read_text())["result"]
    r_markov = dr["transfer_ratios"]["markov_over_head_macs_full"]
    draft = 3 * dr["block5_us"] + 5 * head_occ * (1 + r_markov)
    step = verify + draft + M.DRAFT["seed_commit_us"]
    mtp = M.DRAFT["tau"] * 1e6 / step
    modelled = [p for p in path if p["cls"] == "modelled"]
    by = {}
    for p in path:
        by[p["cls"]] = round(by.get(p["cls"], 0.0) + p["us"], 3)
    by["extra_S81_hops"] = round(EXTRA_HOPS * hop_extra, 3)
    fam = {}
    for p in modelled:
        f = p["node"].split(".", 1)[1] if p["node"].startswith(("L", "E")) else p["node"]
        fam[f] = round(fam.get(f, 0.0) + p["us"], 3)
    onpath = {p["node"] for p in path}
    sub = {n: r.get("modelled_part_us", 0.0) for n, r in P.rows.items() if n in onpath and r.get("modelled_part_us")}
    sub_us = round(sum(sub.values()), 3)
    meas = sum(v for k, v in by.items() if k not in ("modelled", "zero")) - sub_us
    rec = dict(
        schema="opentallas.dsrom-1m.allmeasured.composition.v1", context=M.CTX, position=M.POS,
        baseline=a.baseline,
        base="candidate_gather.lat259 (results/rtl/dsrom_reindex_candidates_20261004/composition.json, 394.911 us)",
        AR_us=round(ar, 3), AR_tok_s=round(1e6 / ar, 1),
        critical_path_us_by_class=by, measured_share=round(meas / ar, 4),
        modelled_on_path_us=round(sum(p["us"] for p in modelled), 3), modelled_on_path_by_family=fam,
        modelled_inside_measured_nodes_us=sub_us,
        modelled_inside_measured_note="CDC fast->slow ratio-FIFO crossings (4 slow cycles a crossing edge, W18) charged "
                                      "on SU nodes as the model does; no CDC bench",
        still_modelled_total_us=round(sum(p["us"] for p in modelled) + sub_us, 3),
        MTP=dict(rule="II = slowest stage busy x (1 + measured handoff 46/11271) + measured hop; verify = AR + 5 II; "
                      "draft = 3 x block5 + 5 x head occupancy x (1 + Markov/lm_head MACs); tau 4.159",
                 stage_busy_top=sorted(segs, key=lambda s: -s["busy_us"])[:6], worst_stage=worst,
                 II_us=round(ii, 3), verify_us=round(verify, 3), draft_us=round(draft, 3),
                 draft_terms=dict(block5_us=dr["block5_us"], block5_basis="reduced-vehicle slice x transfer ratio "
                                  "(results/rtl/dsrom_dspark_step_slices_20261004) -- NOT full shape",
                                  head_occ_us=head_occ, r_markov=r_markov),
                 seed_commit_us=M.DRAFT["seed_commit_us"], step_us=round(step, 3), MTP_tok_s=round(mtp, 1),
                 tau=M.DRAFT["tau"], mtp_over_ar=round(mtp * ar / 1e6, 3)),
        still_modelled=[
            dict(term="Engram eng.dot / eng.gate / eng.add (L1, L14)", us=round(sum(v for k, v in fam.items() if k.startswith("eng.")), 3),
                 why="golden shard holds only h_in and the Engram output, not hashed rows / key / value"),
            dict(term="embed (embedding ROM row read + 4-copy expand)", us=fam.get("embed", 0.0), why="no bench"),
            dict(term="CDC fast->slow crossings on SU nodes", us=sub_us, why="W18 ratio-FIFO latency, no CDC bench"),
            dict(term="light-FEC PHY (130 ns a board hop) and UCIe PHY (10 ns)", us=None,
                 why="VENDOR BUDGET (no PHY RTL); inside the measured+vendor_phy hop terms"),
            dict(term="quantiser hub network stages (22 + 15 slow cycles)", us=None,
                 why="added arithmetically to the RTL quantiser (other SU nodes ran them in RTL)"),
            dict(term="MTP draft block5 (3 DSpark blocks)", us=round(3 * dr["block5_us"], 3),
                 why="reduced-vehicle slice x transfer ratio (dsrom_dspark_step_slices_20261004), not full shape"),
            dict(term="tau 4.159", us=None, why="6-class mix acceptance, not an RTL quantity")],
        requires_binding=["WINDOW load: ot_dsrom_window_stream_la measured 93.9% of peak; the as-built S81 prefetch "
                          "measures 124.5 us a layer -- composition REQUIRES S81 BINDING OF THE WINDOW MODULE (Codex)"],
        info=info, patches=list(P.rows.values()), base_patches=base_patches, critical_path=path,
        inputs={rel(p): sha(p) for p in list(ins.values()) + sorted((a.recovery / "levers").glob("*.json")) + [WINDOW, WAVE, DRAFT_REC, BASE / "reader.json",
                                                             BASE / "ckv_lat259.json", RC / "gather.json",
                                                             RC / "select.json"] if Path(p).exists()},
        tool_sha256={rel(ROOT / "tools/dsrom_1m_allmeasured.py"): sha(ROOT / "tools/dsrom_1m_allmeasured.py"),
                     rel(ROOT / "tools/dsrom_1m_measure.py"): sha(ROOT / "tools/dsrom_1m_measure.py")})
    a.out.write_text(json.dumps(rec, indent=1, default=str) + "\n")
    print(json.dumps(dict(AR_us=rec["AR_us"], AR_tok_s=rec["AR_tok_s"], by=by, share=rec["measured_share"],
                          modelled=rec["still_modelled_total_us"], II=rec["MTP"]["II_us"], worst=worst["hop"],
                          draft=rec["MTP"]["draft_us"], MTP=rec["MTP"]["MTP_tok_s"]), indent=0))
    return rec


if __name__ == "__main__":
    main()
