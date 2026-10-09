#!/usr/bin/env python3
"""Token-path export (stream token-path, 2026-10-08): the critical path of ONE decode token for each design, as a
JSON graph the Chip Explorer token views (/explorer/token: flow graph, swimlane timeline, floorplan replay) render.

No new performance model.  Every cycle comes from an existing record or composition tool, driven exactly as the
re-price of 2026-10-08 (results/arch/reprice_20261008/reprice.json, tools/reprice_20261008.py) drives it:

  qwen_rom  Qwen3-8B ROM, 8K, AR.  The measured STREAM4 P8191 full token (results/rtl/qwen_plain_ar_stream4_P8191_
            20261005/terminal.json: 7 + L0 6,044 + 35 x 5,282 + head 2,998 + 36 hand-off edges = 193,955 cycles), each
            layer split into operations at the op-fetch boundaries of the isolated AR L0 RT_OPTRACE (results/rtl/
            qwen_rom_kv_fullbw_20261004/dspark_verify_P8187/optrace + dspark_step_stream4.json), plus the unified
            composition lines (results/arch/unified_composition_20261007/ledger.json qwen_rom: slab MUL_LAT 7, KV
            landing M, r21 relays, crossbar, controller SHIFT) and the 2026-10-08 re-price items (serdes PINREG, band
            integrate), each placed on the operations it is charged per (ME op / link leg / per token).
  ds_rom    DeepSeek-V4.1 ROM S81 array, 1M, AR, 1,792 pairs HALF_PHL (the re-price headline).  tools/s81/
            field_phases_1792.py compose on the measured field phases with the re-price's extra wire and per-node
            items; the composition of tools/dsrom_1m_allmeasured.py is replayed in-process (its graph_hook) so every
            node of its operator graph carries the solver's own start / finish; slack from the same graph.
  hbm_ds    HBM accelerator, DS-V4.1 1M, AR.  The matched-reference critical path (results/rtl/dshbm_matched_reference_
            20261005/composition.json path, 2,291 nodes), re-based to the gate row, plus every unified-composition line
            of 'unified_candidate_contracts_rtl' and the re-price items (upper bound), each spread over the path nodes
            of the class it is charged on (rules in HBM_RULES).

Where a record gives a total but not its placement, the export spreads it and says so on the node (grade
'apportioned').  The totals are asserted against the published re-priced tok/s.

    python3 tools/token_path_export.py                        # writes results/arch/token_path_20261008/*.json
    python3 tools/token_path_export.py --viz-dir DIR          # also copies data + geometry snapshots for the views
"""
from __future__ import annotations

import argparse
import collections
import copy
import fnmatch
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/s81"))
OUT = ROOT / "results/arch/token_path_20261008"
CLK = 1.2e9
REPRICE = "results/arch/reprice_20261008/reprice.json"
UNI = "results/arch/unified_composition_20261007/ledger.json"
GEO = "site/chip_explorer/inputs/geo.json"


def J(p):
    return json.loads((ROOT / p).read_text())


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:16]


def head():
    return subprocess.run(["git", "rev-parse", "--short=9", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def src(grade, record, pointer=None, note=None):
    d = dict(grade=grade, record=record)
    if pointer:
        d["pointer"] = pointer
    if note:
        d["note"] = note
    return d


# ======================================================================================== shared schedule helpers
class Design:
    def __init__(self, key, title, unit):
        self.key, self.title, self.unit = key, title, unit
        self.nodes, self.edges, self.order = {}, [], []
        self.items = {}        # adder item -> {grade, record, note}: per-node adders are [item, cycles]

    def add(self, nid, label, group, cls, cycles, source, *, op=None, elements=(), instances=(), adders=(), deps=None,
            start=None, critical=True, bytes_in=None, link_in=None, edge_cycles=0, kind="op"):
        assert nid not in self.nodes, nid
        base = cycles
        tot = cycles + sum(a["cycles"] for a in adders)
        for a in adders:
            self.items.setdefault(a["item"], {k: v for k, v in a.items() if k not in ("item", "cycles")})
        if source.get("note") and len(source["note"]) > 320:
            source = dict(source, note=source["note"][:317] + "...")
        n = dict(id=nid, label=label, group=group, cls=cls, op=op or label, kind=kind, base_cycles=r1(base),
                 cycles=r1(tot), adders=[[a["item"], r1(a["cycles"])] for a in adders], src=source,
                 elements=list(elements), instances=list(instances), critical=critical)
        if start is not None:
            n["start"] = r1(start)
            n["end"] = r1(start + tot)
        self.nodes[nid] = n
        if critical:
            prev = self.order[-1] if self.order else None
            self.order.append(nid)
            if prev is not None and deps is None:
                deps = [prev]
        for d in deps or ():
            self.edges.append(dict(src=d, dst=nid, bytes=bytes_in, link=link_in, cycles=edge_cycles))
        return n

    def chain_schedule(self):
        """serial critical chain: start = previous end + the edge's cycles"""
        t = 0.0
        ein = {(e["src"], e["dst"]): e for e in self.edges}
        prev = None
        for nid in self.order:
            n = self.nodes[nid]
            if prev is not None:
                t += ein.get((prev, nid), {}).get("cycles", 0) or 0
            n["start"], n["end"] = r1(t), r1(t + n["cycles"])
            t += n["cycles"]
            prev = nid
        return t


def r1(x):
    return round(float(x), 1)


def distribute(total, keys, weights=None):
    """split `total` over keys (weights default equal) in 0.1-cycle units, largest remainder: the parts sum to the
    total exactly and keep its sign"""
    if not keys:
        return {}
    w = weights or [1.0] * len(keys)
    sw = sum(w) or 1.0
    sign = -1 if total < 0 else 1
    units = round(abs(total) * 10)
    raw = [units * x / sw for x in w]
    q = [int(v) for v in raw]
    rest = units - sum(q)
    for i in sorted(range(len(keys)), key=lambda k: raw[k] - q[k], reverse=True)[:rest]:
        q[i] += 1
    return {k: sign * v / 10 for k, v in zip(keys, q)}


def finish(d, headline, groups_def, classes, drill, notes, extra=None, tau=None):
    """slack, groups, shares, totals check; returns the record.  tau (MTP): the record is one verify step and the rate
    is tau accepted tokens a step"""
    N, E = d.nodes, d.edges
    crit = [n for n in d.order]
    total = max(N[c]["end"] for c in crit)
    # slack: latest allowed end for off-critical nodes = earliest start of their consumers (+ consumer slack)
    succ = collections.defaultdict(list)
    for e in E:
        succ[e["src"]].append(e)
    for nid in reversed(list(N)):
        n = N[nid]
        if n["critical"]:
            n["slack"] = 0.0
            continue
        if "slack" in n:
            continue
        outs = succ.get(nid)
        if not outs:
            n["slack"] = r1(total - n["end"])
            continue
        n["slack"] = r1(min(N[e["dst"]]["start"] - (e["cycles"] or 0) - n["end"] + N[e["dst"]].get("slack", 0.0) for e in outs))
    cpairs = set(zip(crit, crit[1:]))
    for e in E:
        e["critical"] = (e["src"], e["dst"]) in cpairs
    for nid, n in N.items():
        n["share"] = round(n["cycles"] / total, 6) if n["critical"] else 0.0
    # groups
    gl = collections.OrderedDict()
    for nid in crit:
        gl.setdefault(N[nid]["group"], []).append(nid)
    for nid, n in N.items():
        if not n["critical"]:
            gl.setdefault(n["group"], [])
    groups = []
    for g, ids in gl.items():
        meta = groups_def.get(g, {})
        cc = collections.Counter()
        for i in ids:
            cc[N[i]["cls"]] += N[i]["cycles"]
        allids = [i for i, n in N.items() if n["group"] == g]
        st = min(N[i]["start"] for i in allids)
        en = max(N[i]["end"] for i in allids)
        cyc = sum(N[i]["cycles"] for i in ids)
        groups.append(dict(id=g, label=meta.get("label", g), kind=meta.get("kind", "stage"), start=r1(st), end=r1(en),
                           cycles=r1(cyc), share=round(cyc / total, 6), critical=bool(ids), n_nodes=len(allids),
                           cls_cycles={k: r1(v) for k, v in cc.most_common()}, **{k: v for k, v in meta.items() if k not in ("label", "kind")}))
    gedges, prev = [], None
    for g in groups:
        if prev is not None and g["critical"]:
            first = gl[g["id"]][0]
            e = next((x for x in E if x["dst"] == first and N[x["src"]]["group"] == prev["id"]), None)
            gedges.append(dict(src=prev["id"], dst=g["id"], bytes=e["bytes"] if e else None, link=e["link"] if e else None,
                               cycles=e["cycles"] if e else 0, critical=True))
        if g["critical"]:
            prev = g
    cls_tot = collections.Counter()
    grade_tot = collections.Counter()
    for nid in crit:
        cls_tot[N[nid]["cls"]] += N[nid]["cycles"]
        grade_tot[N[nid]["src"]["grade"]] += N[nid]["base_cycles"]
        for it, cy in N[nid]["adders"]:
            grade_tot[d.items[it].get("grade", "priced")] += cy
    edge_cyc = sum(e["cycles"] or 0 for e in E if e["critical"])
    if edge_cyc:
        grade_tot["measured"] += edge_cyc
    # element / instance lists live on the class; a node keeps its own only when it differs
    cdef = {c["id"]: c for c in classes}
    for n in N.values():
        c = cdef.get(n["cls"], {})
        if n["elements"] == c.get("elements"):
            del n["elements"]
        if n["instances"] == c.get("instances"):
            del n["instances"]
    tok_s = (tau or 1.0) * CLK / total
    pub = headline["tok_s"]
    assert abs(round(tok_s, 1) - pub) <= 0.1 + 1e-9, (d.key, tok_s, pub)
    repro = (f"{total:,.1f} cycles x (1 / {CLK / 1e9:g} GHz) = {total / CLK * 1e6:,.3f} us = {tok_s:,.2f} tok/s; "
             f"published {pub:,.1f} (within rounding)") if not tau else (
             f"one verify step {total:,.1f} cycles = {total / CLK * 1e6:,.3f} us; tau {tau:g} accepted tokens a step -> "
             f"{total / tau:,.1f} cycles ({total / tau / CLK * 1e6:,.3f} us) an accepted token = {tok_s:,.2f} tok/s; "
             f"published {pub:,.1f} (within rounding)")
    rec = dict(
        schema="opentallas.token_path.v1", design=d.key, title=d.title, clock_hz=CLK, tool="tools/token_path_export.py",
        repo_head=head(), headline=headline, mode="mtp" if tau else "ar",
        totals=dict(cycles=r1(total), us=round(total / CLK * 1e6, 3), tok_s=round(tok_s, 2), tok_s_published=pub,
                    reproduces=repro,
                    by_grade={k: r1(v) for k, v in grade_tot.most_common()},
                    by_class=[dict(cls=k, cycles=r1(v), share=round(v / total, 6)) for k, v in cls_tot.most_common()]),
        classes=classes, groups=groups, group_edges=gedges, drill=drill, critical_path=crit,
        adder_items=d.items, nodes=list(N.values()), edges=E, notes=notes)
    if tau:
        rec["totals"].update(tau=tau, step_cycles=r1(total), per_accepted_cycles=r1(total / tau),
                             per_accepted_us=round(total / tau / CLK * 1e6, 3))
    if extra:
        rec.update(extra)
    return rec


# ======================================================================================== Qwen ROM 8K
QWEN_CLASSES = [
    dict(id="embed", label="Embedding ROM", elements=["qfd_io_emb_root", "qfd_io_emb_tap", "qfd_embed_code_bank",
         "qfd_embed_ingress_code", "qfd_embed_ingress_scale", "qfd_embed_scale_bank"], instances=["io_embedding_rom"]),
    dict(id="su", label="Spine SU / SFU + vector memory", elements=["qfd_sp_su64_sfu", "qfd_sp_vector_memory",
         "qfd_sp_constants_sequencer", "qfd_sp_res_ser", "qfd_vm_bank_checked", "ot_qwen_rom_core_core_p",
         "ot_qwen_rom_core_core_pu"], instances=["sp_su*_sfu", "sp_vector_memory", "sp_constants_sequencer"]),
    dict(id="me", label="ROM tiles (matrix engine)", elements=["qfd_tile", "qfd_tile_e", "qfd_sp_tree_lane",
         "qfd_sp_tree_top", "qfd_sp_tree_top_b", "qfd_sp_band_lanes", "ot_qwen_slab_port_group_m3_m8",
         "ot_qwen_slab_port_group_s14_die", "qfd_rly", "qfd_lst_c", "qfd_lst_h", "qfd_lst_v", "ot_qwen_rom_core_meif_idle_capture"],
         instances=["t_*", "s_*", "h_*", "sp_tree_top", "sp_port_tiles_*"]),
    dict(id="kv", label="HBM KV (controller, CDC, landing)", elements=["qfd_ctrl_pc_00", "qfd_ctrl_shift_00",
         "qfd_ctrl_ready_00", "qfd_ctrl_protected_00", "ot_qwen_stream4_cdc_pc", "qfd_kvc_decode_pc", "qfd_kvc_decode_map_pc",
         "ot_qwen_rom_core_core_kv_banked", "ot_qwen_hbm_code_pair_margin", "qfd_cst"],
         instances=["phy_*", "ctrl_*", "cdc_*"]),
    dict(id="link", label="TP4 collective (SerDes link + hub)", elements=["qfd_io_collective", "qfd_io_serdes", "qfd_io_xfifo",
         "qfd_io_ucie", "qfd_link_rx128", "qfd_hub", "ot_qwen_link_fwd_cx_station", "ot_qwen_link_forwarded_tmr_pair"],
         instances=["io_collective", "io_serdes", "io_ucie", "hub_el", "lfifo_*", "lh_*", "lv_*", "lc_*"]),
    dict(id="head", label="LM head + argmax", elements=["qfd_chead", "qfd_tile", "qfd_sp_tree_top"],
         instances=["h_*", "t_*", "sp_tree_top", "sp_su*_sfu"]),
]
QCLS = {c["id"]: c for c in QWEN_CLASSES}

# isolated AR L0 (P8187, np1) RT_OPTRACE op-fetch boundaries (cycle in the stage); the segment breakdown of
# dspark_step_stream4.json names attention [0,4404) / MLP [4404,6243) / residual [6243,6489)
Q_OPS = [  # id, label, cls, lo, hi, me_ops, ar_legs, note
    ("rmsnorm1", "RMSNorm (pre-attention)", "su", 0, 15, 0, 0, "op 0 SU nin=4096 issued at 0; next fetch at 15"),
    ("qkv", "QKV matvec on the ROM tiles (1,536 rows a die)", "me", 15, 171, 1, 0, "op 1 ME nout=1536 (q 1,024 + k 256 + v 256 a die); 152 weight-stream cycles (verify_op_breakdown)"),
    ("qknorm_rope", "q/k RMSNorm + RoPE + KV append", "su", 171, 272, 0, 0, "ops 2-10 SU / SFU"),
    ("attn_kv", "Attention QK, softmax, PV over 8,191 keys (KV streamed from HBM)", "me", 272, 1427, 2, 0,
     "ops 11-13: ME k=128 wsrc=1 (QK) + SFU exp + ME nout=128 wsrc=1 (PV); 1,155 cycles = attention_kv_passes.ar"),
    ("softmax_norm", "Softmax normalise + attention-output staging", "su", 1427, 1822, 0, 0, "ops 14-15 SU / SFU"),
    ("o_proj", "O projection matvec (4,096 rows)", "me", 1822, 2101, 1, 0, "op 16 ME nout=4096 k=2; ~40 weight-stream cycles + tree / ordering return"),
    ("allreduce1", "All-reduce #1 (TP4, one-stream AR256)", "link", 2101, 3195, 0, 1, "END b barrier; 1,094 cycles = all_reduces.ar[0]"),
    ("attn_tail", "Post-attention residual / KV write-back drain", "su", 3195, 4404, 0, 0,
     "ops 18-21 fetched; the isolated run's posted-write drain (MEMSTAT stall_drain 1,243) sits here and is hidden in the chain"),
    ("rmsnorm2", "RMSNorm (pre-MLP)", "su", 4404, 4495, 0, 0, "MLP block from pc18 (4,404)"),
    ("gate_up", "Gate/up matvec (6,144 rows a die) + SwiGLU", "me", 4495, 5024, 1, 0, "ME nout=6144 k=32; 278 weight-stream cycles; SwiGLU SFU op"),
    ("down", "Down matvec (4,096 rows)", "me", 5024, 5291, 1, 0, "ME nout=4096 k=6; 118 weight-stream cycles"),
    ("allreduce2", "All-reduce #2 (TP4, one-stream AR256)", "link", 5291, 6243, 0, 1, "949 cycles = all_reduces.ar[1] (+3 to the residual pc)"),
    ("residual", "Residual add + layer output hand-off", "su", 6243, 6489, 0, 0, "residual_pc26 246 cycles"),
]
Q_BYTES = dict(rmsnorm1=16384, qkv=16384, qknorm_rope=6144, attn_kv=6144, softmax_norm=4096, o_proj=4096, allreduce1=16384,
               attn_tail=16384, rmsnorm2=16384, gate_up=16384, down=12288, allreduce2=16384, residual=16384)
Q_LINK = dict(rmsnorm1="VM -> SU", qkv="VM -> tile band broadcast (tree)", qknorm_rope="tree top -> SU",
              attn_kv="SU -> tiles (q) | HBM -> landing -> tiles (KV)", softmax_norm="tiles -> SU", o_proj="VM -> tile band",
              allreduce1="hub -> SerDes TP4 ring", attn_tail="link -> VM", rmsnorm2="VM -> SU", gate_up="VM -> tile band",
              down="VM -> tile band", allreduce2="hub -> SerDes TP4 ring", residual="link -> VM")


def qwen():
    T = "results/rtl/qwen_plain_ar_stream4_P8191_20261005/terminal.json"
    DS4 = "results/rtl/qwen_rom_kv_fullbw_20261004/dspark_step_stream4.json"
    OPT = "results/rtl/qwen_rom_kv_fullbw_20261004/dspark_verify_P8187/optrace/k_AR_op.trace.log"
    KVM = "results/rtl/qwen_rom_kv_fullbw_20261004/model.json"
    REL = "results/rtl/qwen_rom_die_r17_20261005/relays_r21/relay_token_cost.json"
    t, ds4, rel, kvm = J(T), J(DS4), J(REL), J(KVM)
    uni = J(UNI)["targets"]["qwen_rom"]
    lines = {l["id"]: l for l in uni["lines"]}
    rp = J(REPRICE)["qwen_rom"]["rows"]["unified_candidate:lower"]
    # the trace anchors must agree with the committed breakdown
    seg = ds4["verify_segment_breakdown"]["ar"]
    ob = ds4["verify_op_breakdown"]
    assert seg["attention_block_pc0"]["cycles"] == 4404 and seg["mlp_block_pc18"]["cycles"] == 1839 and seg["residual_pc26"]["cycles"] == 246
    assert ob["all_reduces"]["ar"] == [1094, 949] and ob["attention_kv_passes"]["ar"] == 1155
    trace = (ROOT / OPT).read_text()
    for cyc in (15, 171, 272, 1427, 1822, 2101, 3195, 4404, 4495, 5024, 5291, 6243):
        assert f"cyc={cyc} " in trace, cyc
    stages = {s["stage"]: s for s in t["stages"]}
    L_iso = seg["attention_block_pc0"]["cycles"] + seg["mlp_block_pc18"]["cycles"] + seg["residual_pc26"]["cycles"]   # 6,489
    chained = stages["L1"]["cycles"]
    drain = L_iso - chained          # 1,207: removed from attn_tail (posted write-back hides the drain in the chain)
    L0_extra = stages["L0"]["cycles"] - chained
    # per-op adders (unified lines + today's re-price)
    me_ops = rel["me_ops_per_ar_token"]
    assert me_ops == 36 * sum(o[5] for o in Q_OPS) + 1
    d_me = rel["delta_per_me_op"]; d_link = rel["delta_link_per_traversal"]
    assert d_me * me_ops + d_link * 72 == lines["die_relays_430um"]["effect"]["AR"]
    assert lines["slab_mul_lat7"]["effect"]["AR"] == me_ops
    rpi = {i["item"]: i for i in rp["items"]}
    band = rpi["band_integrate"]["cycles"]; assert band == 7 * me_ops
    pin = rpi["serdes_pinreg"]["cycles"]; assert pin == 72
    ME_ADD = [dict(item="slab_mul_lat7", cycles=1, grade="measured", record=lines["slab_mul_lat7"]["source"][0]["file"], note=lines["slab_mul_lat7"]["item"]),
              dict(item="die_relays_430um", cycles=d_me, grade="priced", record=REL + " delta_per_me_op", note=lines["die_relays_430um"]["item"]),
              dict(item="band_integrate (re-price 10-08)", cycles=7, grade="priced", record=REPRICE + " qwen_rom band_integrate (+5 + 2 LNK, LNK 1)")]
    AR_ADD = [dict(item="die_relays_430um", cycles=d_link, grade="priced", record=REL + " delta_link_per_traversal"),
              dict(item="serdes_pinreg (re-price 10-08)", cycles=1, grade="priced", record=REPRICE + " qwen_rom serdes_pinreg")]
    TOKEN_KV = [(k, lines[k]) for k in ("kv_map_m", "kv_crossbar_model", "ctrl_shift")]
    d = Design("qwen_rom", "Qwen3-8B ROM, 8K context, AR (TP4 dies)", "cycles")
    gdef = collections.OrderedDict()
    gdef["embed"] = dict(label="Embed", kind="embed")
    d.add("embed", "Embedding ROM row read + broadcast", "embed", "embed", t["stages"][0]["start_cycle"],
          src("measured", T, "stages[0].start_cycle (7 initial edges)"), elements=QCLS["embed"]["elements"],
          instances=QCLS["embed"]["instances"])
    prev_group_last = "embed"
    for L in range(36):
        g = f"L{L}"
        gdef[g] = dict(label=f"Layer {L}", kind="layer", measured_cycles=stages[g]["cycles"])
        for i, (oid, lab, cls, lo, hi, nme, nar, note) in enumerate(Q_OPS):
            cyc = hi - lo
            if oid == "attn_tail":
                cyc -= drain
            if oid == "residual":
                cyc = L_iso - lo
            adders = []
            for _ in range(nme):
                adders += [dict(a) for a in ME_ADD]
            for _ in range(nar):
                adders += [dict(a) for a in AR_ADD]
            # merge same-item adders
            m = collections.OrderedDict()
            for a in adders:
                if a["item"] in m:
                    m[a["item"]]["cycles"] += a["cycles"]
                else:
                    m[a["item"]] = dict(a)
            adders = list(m.values())
            grade = "measured" if oid in ("attn_kv", "allreduce1", "allreduce2") else "apportioned"
            s_note = f"isolated AR L0 RT_OPTRACE op-fetch window [{lo}, {hi}) of the measured {L_iso}-cycle trace; {note}"
            if oid == "attn_tail":
                s_note += f"; chained layer {chained} = isolated {L_iso} - {drain} drain cycles (all taken here)"
            if L == 0 and oid == "attn_kv":
                cyc += L0_extra
                s_note += f"; + {L0_extra} cold-layer cycles (L0 {stages['L0']['cycles']} vs chained {chained}: no earlier layer hides its KV prefetch)"
                for k, ln in TOKEN_KV:
                    adders.append(dict(item=k, cycles=ln["effect"]["AR"], grade="measured" if ln["status"] == "measured" else "priced",
                                       record=ln["source"][0]["file"], note="per-token KV-path constant, placed on the cold layer"))
            li = Q_LINK[oid] if i else ("embedding row -> VM" if L == 0 else "layer hand-off (registered, 1 cycle)")
            deps = [prev_group_last] if i == 0 else None
            n = d.add(f"{g}.{oid}", lab, g, cls, cyc,
                      src(grade, f"{T} stages[{g}] + {OPT}", note=s_note + f"; layer total measured {stages[g]['cycles']} cycles"),
                      op=oid, elements=QCLS[cls]["elements"], instances=QCLS[cls]["instances"], adders=adders, deps=deps,
                      bytes_in=Q_BYTES[oid] if i else 16384, link_in=li, edge_cycles=1 if (i == 0 and L > 0) else 0)
            n["layer"] = L
        prev_group_last = f"{g}.residual"
        # parallel KV prefetch for the next layer, inside this layer's MLP window
        if L < 35:
            fill = 1362
            st = None  # placed after the chain is scheduled
            n = d.add(f"{g}.kv_prefetch", f"KV prefetch for layer {L + 1} (HBM -> landing, 4.19 MB a die)", g, "kv", fill,
                      src("measured", "results/rtl/qwen_rom_kv_fullbw_20261004/dspark_verify_P8187/optrace/k_AR_op.trace.log",
                          "MEMSTAT fill_cycles", note=f"measured fill 1,362 cycles a layer a die (131,072 sectors, 4 stacks); "
                          f"model {kvm['S4_P8191']['fill_cycles']['plus_first_latency']} ({KVM} S4_P8191); hidden behind "
                          f"the MLP window (kv_fill_hidden_with_prefetch_if_mlp_window_ge)"),
                      op="kv_prefetch", elements=QCLS["kv"]["elements"], instances=QCLS["kv"]["instances"],
                      critical=False, deps=[], kind="parallel")
            n["layer"] = L
    gdef["head"] = dict(label="LM head + argmax", kind="head", measured_cycles=stages["head"]["cycles"])
    hn = d.add("head.lm_head", "Final RMSNorm -> LM head matvec (151,936 rows over 4 dies) -> argmax merge", "head", "head",
               stages["head"]["cycles"], src("measured", T, "stages[head]", note="RTL head; next token 18, exact on all ranks"),
               elements=QCLS["head"]["elements"], instances=QCLS["head"]["instances"],
               adders=[dict(a) for a in ME_ADD], deps=[prev_group_last], bytes_in=16384, link_in="layer hand-off (registered, 1 cycle)",
               edge_cycles=1)
    total = d.chain_schedule()
    # place the prefetch nodes: start at this layer's rmsnorm2 (MLP window), feed the next layer's attn_kv
    for L in range(35):
        n = d.nodes[f"L{L}.kv_prefetch"]
        st = d.nodes[f"L{L}.rmsnorm2"]["start"]
        n["start"], n["end"] = r1(st), r1(st + n["cycles"])
        d.edges.append(dict(src=n["id"], dst=f"L{L + 1}.attn_kv", bytes=4194304, link="HBM3E x4 stacks -> PC landing FIFOs (CK/2 -> core)", cycles=0))
    measured_total = t["total_cycles"]
    adders_total = sum(c for n in d.nodes.values() if n["critical"] for _, c in n["adders"])
    assert abs(total - rp["after"]["cycles"]) < 0.5, (total, rp["after"]["cycles"])
    assert abs(total - adders_total - measured_total) < 0.5
    headline = dict(tok_s=rp["after"]["AR_tok_s"], cycles=rp["after"]["cycles"], mode="AR (DSpark off), position 8,191",
                    basis=f"{UNI} qwen_rom unified_candidate ({rp['before']['cycles']:,} cycles, {rp['before']['AR_tok_s']} tok/s) "
                          f"+ the 2026-10-08 re-price (serdes PINREG +{pin}, band integrate +{band}) = {rp['after']['cycles']:,} cycles",
                    source=REPRICE + " qwen_rom.rows['unified_candidate:lower']", status="priced candidate (not a closed rate)",
                    measured_cycles=measured_total, priced_cycles=r1(adders_total))
    drill = dict(group="L1", why="a chained layer (L1-L35 are identical: 5,282 measured cycles); L0 carries the cold KV fill")
    notes = [
        f"Operation boundaries inside a layer are the op-fetch cycles of the isolated AR L0 RT_OPTRACE ({OPT}); the attention-KV "
        "and both all-reduce windows match the committed breakdown exactly; the other windows are attributed by program order "
        "(grade 'apportioned').",
        f"The chained layer is {chained} cycles against {L_iso} isolated: the {drain}-cycle difference is the isolated run's "
        "posted KV write-back drain (MEMSTAT stall_drain 1,243), hidden in the chain; it is removed from the attention tail window.",
        f"Priced adders sit on the operations they are charged per: {d_me + 1 + 7} cycles a ME op (relays {d_me}, MUL_LAT 7 +1, band integrate +7) "
        f"x {me_ops} ME ops, {d_link + 1} a link leg x 72 legs, and the per-token KV constants (+54 KV map, +24 crossbar, +144 SHIFT) on L0.",
        "Every die of the TP4 group runs the same schedule in lockstep; the views show one die.",
    ]
    return finish(d, headline, gdef, QWEN_CLASSES, drill, notes,
                  extra=dict(geometry=dict(source=GEO, key="qwen_rom", die="Qwen ROM die (r17b snapshot; one of 4 TP dies)")))


# ======================================================================================== DS ROM S81 1,792 HALF_PHL
DS_CLASSES = [
    dict(id="field", label="ROM field (q / BF elements, VM, gather, capture, PQ root)", elements=[
        "ot_v41_rom_elem_q_qxpq_w10", "ot_s81_bf_native", "dsfd_vm_bg", "dsfd_vm_bgh", "dsfd_vm_bgq", "dsfd_capt_ctl",
        "dsfd_capt_g2", "dsfd_capt_grp", "dsfd_capt_x", "ot_s81_pq_ret_root_cam_p", "ot_s81ph_root_tile", "dsfd_cfifo",
        "dsfd_l2r_vr_564x1__hx_W", "dsfd_l2r_vr_564x1__hx_E", "dsfd_l2r_vr_512x1__hq_SW", "dsfd_r2l_vr_1024x1__ha_SW",
        "dsfd_m2l_raw_512x1__hl_E0", "dsfd_m2l_vr_68x11__hr_E1", "dsfd_stnh_512x1", "dsfd_stnv_512x1", "ot_meso_fifo_w512d8g1",
        "ot_v41_pqc_spine_screen"],
        instances=["e*", "n*_*", "sp_vm", "sp_gather", "sp_capture", "mf_*", "fb_*", "wh_*", "wv_*"]),
    dict(id="hbm", label="HBM service column (scan / window / KV)", elements=["dsfd_svc_pc", "dsfd_svc_stn", "dsfd_svcio_ad",
         "dsfd_svcio_od", "dsfd_svcio_q", "dsfd_svcio_x", "dsfd_ctrl_ctr", "dsfd_ctrl_pc", "ot_dsrom_window_column_128",
         "ot_dsrom_window_column_256", "ot_dsrom_window_column_halfwrite", "ot_dsrom_window_source_ctl"],
         instances=["svc_*", "ctrl_*", "phy_*"]),
    dict(id="su", label="SU / softmax / HC (hub slab)", elements=["ot_dsrom_su_softmax_exp_tile", "ot_dsrom_su_softmax_div_tile",
         "ot_dsrom_su_softmax_exp_hr", "ot_dsrom_su_fdiv_tile", "ot_dsrom_su_fdiv_hr", "ot_dsrom_su_swiglu_lane"],
         instances=["sp_su_n", "sp_su_s", "sp_hc"]),
    dict(id="select", label="Selector / collector band", elements=["dsfd_selt_c", "dsfd_selt_q", "dsfd_selt_q2",
         "dsfd_r2l_vr_512x1__hsel", "dsfd_r2l_vr_512x1__hcol", "dsfd_colt_mrg"], instances=["bk_selector", "bk_collector"]),
    dict(id="coll", label="TP4 collective (slab v4 + links)", elements=["dsfd_coll_core", "dsfd_coll_ck", "dsfd_coll_lane_e",
         "dsfd_coll_lane_w", "dsfd_colt_lane"], instances=["sp_collective", "lk_*"]),
    dict(id="hop", label="Stage hop (SerDes, full-KP4 FEC)", elements=[], instances=["lk_E*", "lk_W*"]),
    dict(id="head", label="Head die (LM head bundle, argmax)", elements=["ot_dsrom_head_elem_A", "ot_dsrom_head_elem_B",
         "ot_dsrom_head_bundle_glue", "ot_s81_head_delay8x32", "ot_hdc_v41_fh_head_top"], instances=[]),
    dict(id="embed", label="Embed ROM / Engram lookup (HBM-resident tables, design 2026-10-08)",
         elements=["ot_dsrom_engram_idwin", "ot_dsrom_engram_lookup", "ot_dsrom_engram_rowsink", "ot_hdc_engram_hash_shipped"],
         instances=["eng_SE", "ctrl_SE", "phy_SE"]),
]
FIELD_SUF = ("a_proj", "wq_b", "cmp.wk", "wo_a", "wo_b", "ffn.router", "shared_gu", "experts_gu", "ffn.down", "idx.q", "eng.dot")
HBM_SUF = ("idx.score", "attn.scores", "attn.pv", "window_load", "own_row_write", "ckv")
SEL_SUF = ("topk_local", "topk_final", "top6", "attn.gather")
COLL_SUF = ("allreduce", "allgather", "topk_merge", "cand.merge", "argmax_merge")
BF_SUF = ("wo_a", "a_proj", "ffn.router", "cmp.wk")


def ds_cls(node):
    s = re.sub(r"^(L|E)\d+\.", "", node)
    if node in ("embed",) or s.startswith("eng."):
        return "embed" if node == "embed" else ("field" if s == "eng.dot" else "su")
    if node.startswith("head.") and node != "head.hop":
        return "coll" if "merge" in s else "head"
    if "hop" in s or node == "token.return":
        return "hop"
    if any(k in s for k in COLL_SUF):
        return "coll"
    if any(k in s for k in SEL_SUF):
        return "select"
    if any(k in s for k in HBM_SUF):
        return "hbm"
    if any(k in s for k in FIELD_SUF):
        return "field"
    return "su"


_DS_CAP = {}
DS_TARGETS = {"field1792_half_dedicated_ksplit_half_rate": ("half_dedicated_ksplit", "half_rate", "half_phl"),
              "field1792_full_shared_full_rate_bf": ("full_shared", "full_rate_bf", "full_rate_shared98")}


def ds_capture():
    """field_phases_1792 compose exactly as the re-price's final cumulative state, with the allmeasured runs of the
    HALF_PHL (half_dedicated_ksplit / half_rate) and full-rate (full_shared / full_rate_bf) compositions replayed
    in-process (graph_hook) to keep their operator graphs.  Cached: the AR and MTP exports share one run."""
    if _DS_CAP:
        return _DS_CAP["cap"], _DS_CAP["fp"], _DS_CAP["rp"], _DS_CAP["ew"]
    import dsrom_closure_cost_ledger as LED
    import field_phases_1792 as FP
    import dsrom_1m_allmeasured as A
    rp = J(REPRICE)["ds_rom"]
    BASE_EXTRA_WIRE = 2           # reprice basis: composition_basis_39e424990 extra_wire 2 (2 PQ root-row return stations)
    assert "extra_wire 2" in rp["basis"]
    ew = BASE_EXTRA_WIRE + sum(i["per_field_phase"] for i in rp["items"])
    rows = [tuple(r) for i in rp["items"] for r in i["per_node"]]
    cap = {"all": {}}
    orig = LED.compose

    def compose(items, pending=False, extra=()):
        names = [e[0] for e in extra]
        if len(names) != 1 or names[0] not in DS_TARGETS:
            return orig(items, pending, extra)
        with tempfile.TemporaryDirectory(prefix=".tokenpath-", dir=LED.OUT) as td:
            s = Path(td)
            shutil.copytree(LED.LEV.parent, s / "levers")
            (s / "levers" / LED.LEV.name).write_text(json.dumps(LED.lever(items, pending, extra), indent=1) + "\n")
            ns = argparse.Namespace(rec=A.REC, out=s / "composition.json", baseline="recovery", recovery=s, window="s81",
                                    hop_tier=A.DEFAULT_HOP_TIER)
            c1 = {}

            def hook(g, P, base_patches, info):
                c1["g"], c1["P"], c1["base"] = g, P, base_patches
            rec = A.compose(ns, graph_hook=hook, write_output=False)
        c1["rec"] = rec
        cap["all"][names[0]] = c1
        return rec["AR_tok_s"], rec["MTP"]["MTP_tok_s"]

    LED.ITEMS.append(("reprice_20261008", "today's per-node closure items (results/arch/reprice_20261008)", rows))
    LED.compose = compose
    try:
        with tempfile.TemporaryDirectory(prefix="tokenpath-") as td:
            out = Path(td) / "fp.json"
            a = argparse.Namespace(regions_dir=FP.OUT / "regions", geo_dir=FP.OUT / "geometry",
                                   variants=",".join(sorted({v for v, _, _ in DS_TARGETS.values()})), extra_wire=ew, out=out)
            FP.cmd_compose(a)
            fp = json.loads(out.read_text())
    finally:
        LED.compose = orig
        LED.ITEMS.pop()
    cap.update(cap["all"]["field1792_half_dedicated_ksplit_half_rate"])
    _DS_CAP.update(cap=cap, fp=fp, rp=rp, ew=ew)
    return cap, fp, rp, ew


def ds_rom():
    cap, fp, rp, ew = ds_capture()
    v = fp["variants"]["half_dedicated_ksplit"]
    comp = v["compositions"]["half_rate"]
    assert comp["AR_tok_s"] == rp["after"]["half_phl"]["AR_tok_s"], (comp, rp["after"]["half_phl"])
    rec, g, P = cap["rec"], cap["g"], cap["P"]
    hop_us = fp["basis"]["hop_us"]
    extra_hops = v["extra_hops"]
    fin = g.solve(True)
    path = rec["critical_path"]
    onpath = [p["node"] for p in path]
    assert abs(sum(p["us"] for p in path) - fin[onpath[-1]] * 1e6) < 0.01
    rows = {r["node"]: r for r in P.rows.values()}
    base = {p["node"]: p for p in cap["base"]}
    CY = CLK / 1e6
    d = Design("ds_rom", "DeepSeek-V4.1 ROM array (S81 die, 1,792 pairs, HALF_PHL BF), 1M context, AR", "cycles")
    pq = rp["items"]
    today_phase = sum(i["per_field_phase"] for i in pq)
    pernode = collections.defaultdict(list)
    for i in pq:
        for pat, c, _f in i["per_node"]:
            pernode[pat].append((i["item"], c))

    def reprice_note(nid):
        out = []
        for pat, lst in pernode.items():
            if fnmatch.fnmatch(nid, pat):
                out += [f"{it} +{c}" for it, c in lst]
        if ds_cls(nid) == "field" and not nid.startswith("E"):
            out.append(f"+{today_phase} a field phase (capture KST1 +4, hub PINREG +3, PQ root CAM a0 +8) inside the measured-field term")
        return out

    def source_of(nid, us):
        r = rows.get(nid)
        if r is not None:
            gr = {"measured": "measured", "measured+vendor_phy": "measured+vendor", "measured_not_exact": "measured"}.get(r["cls"], r["cls"])
            return src(gr, "tools/dsrom_1m_allmeasured.py patch", note=r["source"][:600])
        b = base.get(nid)
        if b is not None:
            return src("measured", "results/rtl/dsrom_reindex_candidates_20261004 (base graph candidate_gather.lat259)",
                       note=json.dumps({k: b[k] for k in b if k != "node"})[:400])
        return src("zero" if us == 0 else "modelled", "tools/dsrom_1m_measure.py s58 graph", note="no measured patch")

    # stage groups: split the critical path at hop nodes
    stage, gdef, grp_of = 0, collections.OrderedDict(), {}
    cur_layers = []
    for nid in onpath:
        if nid == "token":
            continue
        kind = g.nodes[nid].get("kind")
        gid = f"S{stage:03d}"
        grp_of[nid] = gid
        lay = nid.split(".")[0]
        if gid not in gdef:
            gdef[gid] = dict(label="", kind="stage", stage=stage, layers=[])
        if lay not in gdef[gid]["layers"] and kind != "hop":
            gdef[gid]["layers"].append(lay)
        if kind == "hop":
            stage += 1
    for gid, gd in gdef.items():
        ls = gd["layers"]
        first = next(n for n in onpath if grp_of.get(n) == gid)
        part = ".attn" if ".attn." in first else ".ffn" if ".ffn." in first else ""
        gd["label"] = (f"Stage {gd['stage']}: " + (", ".join(ls[:3]) + ("..." if len(ls) > 3 else "")) + part) if ls else f"Stage {gd['stage']}"
        if "embed" in ls:
            gd["kind"] = "embed"
        if any(x.startswith("head") for x in ls):
            gd["kind"] = "head"; gd["label"] = f"Stage {gd['stage']}: head die (LM head, argmax)"
    # all graph nodes: start / finish from the solver; critical chain from the composition's own path
    prev = None
    for nid in onpath:
        if nid == "token":
            continue
        us = sum(g.contrib[nid].values()) * 1e6
        st = fin[nid] * 1e6 - us
        c = ds_cls(nid)
        nn = d.add(nid, nid, grp_of[nid], c, us * CY, source_of(nid, us), op=re.sub(r"^(L|E)\d+\.", "", nid),
                   elements=DSC[c]["elements"], instances=DSC[c]["instances"], start=st * CY, deps=[],
                   kind=g.nodes[nid].get("kind", "op"))
        rn = reprice_note(nid)
        if rn:
            nn["reprice_10_08"] = rn
        if c == "field" and any(k in nid for k in BF_SUF):
            nn["bf16"] = True
        nn["layer"] = g.nodes[nid].get("layer")
    crit_set = set(onpath)
    # off-critical nodes: solver start / finish; group = the stage of their critical consumer (or their layer's stage)
    layer_stage = collections.defaultdict(list)
    for nid in onpath:
        if nid in grp_of:
            layer_stage[nid.split(".")[0]].append((d.nodes[nid]["start"], grp_of[nid]))
    # slack on the operator graph with the solver's own semantics: an operator may slip until it becomes the
    # last-arriving input of a consumer (that consumer's critical dependency finishes at fin[crit[s]])
    succ = collections.defaultdict(list)
    for nid, nd in g.nodes.items():
        for dd in nd["deps"]:
            succ[dd].append(nid)
    gslack = {}
    t_end = fin[onpath[-1]]
    for nid in reversed(list(g.nodes)):
        ss = succ.get(nid)
        if not ss:
            gslack[nid] = t_end - fin[nid]
            continue
        gslack[nid] = max(0.0, min(fin[g.crit[s]] - fin[nid] + gslack[s] for s in ss))
    for nid, nd in g.nodes.items():
        if nid in crit_set or nid == "token" or nd.get("kind") == "join":
            continue
        f = fin[nid] * 1e6
        dur = min(f, (nd["issue"] + nd["depth"] + nd["ctrl"] + nd.get("wire_in", 0.0) + nd.get("wire_out", 0.0)) * 1e6)
        st = f - dur
        lay = nid.split(".")[0]
        cands = layer_stage.get(lay)
        if not cands:
            continue
        gid = cands[0][1]
        for cst, cg in cands:
            if cst <= st * CY + 1e-6:
                gid = cg
        c = ds_cls(nid)
        nn = d.add(nid, nid, gid, c, dur * CY, source_of(nid, dur), op=re.sub(r"^(L|E)\d+\.", "", nid),
                   elements=DSC[c]["elements"], instances=DSC[c]["instances"], start=st * CY, deps=[], critical=False,
                   kind="parallel")
        nn["layer"] = nd.get("layer")
        nn["slack"] = r1(gslack[nid] * 1e6 * CY)
    # edges from the operator graph (deps), through joins
    def real_deps(n, seen=None):
        out = []
        for dd in g.nodes[n]["deps"]:
            if g.nodes[dd].get("kind") == "join":
                out += real_deps(dd)
            else:
                out.append(dd)
        return out
    HOPB = 40976
    for nid in d.nodes:
        for dd in real_deps(nid):
            if dd in d.nodes:
                cdd = ds_cls(nid)
                link = {"hop": "ot_dsrom_link_rt full-KP4 stage hop (board / cable)", "coll": "TP4 slab v4 collective",
                        "hbm": "HBM3E -> service column", "field": "VM -> hub l2r -> field -> PQ root -> gather -> capture",
                        "select": "hub -> selector band", "su": "hub slab"}.get(cdd, "on die")
                d.edges.append(dict(src=dd, dst=nid, bytes=HOPB if g.nodes[nid].get("kind") == "hop" else None, link=link, cycles=0))
    # unplaced hops (S81 extra + q-element + 1,792 mapping): one aggregate node before the head hop
    by = rec["critical_path_us_by_class"]
    t_path = fin[onpath[-1]] * 1e6
    # the 1,792 compose adds the mapping's extra hops to 1e6 / (allmeasured AR tok/s rounded to 0.1): the published
    # AR_us carries that rounding (<= 0.03 us); the aggregate node absorbs it so the total equals the published AR_us
    assert abs(rec["AR_us"] + extra_hops * hop_us - comp["AR_us"]) < 0.05
    unplaced_us = comp["AR_us"] - t_path
    n_s81 = round(by.get("extra_S81_hops", 0.0) / rec["info"]["hop_us"])
    # shift: insert before head.hop
    hh = d.nodes["head.hop"]["start"]
    dt = unplaced_us * CY
    for n in d.nodes.values():
        if n["start"] >= hh - 1e-6:
            n["start"], n["end"] = r1(n["start"] + dt), r1(n["end"] + dt)
    gdef["SX"] = dict(label=f"{n_s81 + extra_hops} stage hops not placed by the record", kind="hops")
    # keep insertion order: unplaced group goes before the head stage in the chain
    ix = d.order.index("head.hop")
    un = dict(id="unplaced_hops", label=f"{n_s81 + extra_hops} more stage hops + cable flight (not placed in the record)",
              group="SX", cls="hop", op="unplaced_hops", kind="hop", base_cycles=r1(dt), cycles=r1(dt), adders=[],
              src=src("measured+vendor", "tools/s81/field_phases_1792.py compose + tools/dsrom_1m_allmeasured.py",
                      note=f"{n_s81} hops of the S81 / q-element frame over the S58 graph ({by.get('extra_S81_hops')} us) + "
                           f"{extra_hops} hops of the 1,792 HALF mapping (120 vs 85 stages) x {hop_us:.4f} us + cable flight "
                           f"{by.get('cable_flight', 0)} us (+ the composition's tok/s rounding, < 0.03 us); where they fall between stages is "
                           "not in the composition record"),
              elements=[], instances=DSC["hop"]["instances"], critical=True, start=r1(hh), end=r1(hh + dt))
    d.nodes["unplaced_hops"] = un
    d.order.insert(ix, "unplaced_hops")
    prevn = d.order[ix - 1]
    d.edges.append(dict(src=prevn, dst="unplaced_hops", bytes=HOPB, link="stage hops", cycles=0))
    d.edges.append(dict(src="unplaced_hops", dst="head.hop", bytes=HOPB, link="stage hops", cycles=0))
    total_us = t_path + unplaced_us
    assert abs(total_us - comp["AR_us"]) < 0.002, (total_us, comp["AR_us"])
    ds_engram_nodes(d)
    # slack for off-critical nodes is computed in finish(); order groups so SX precedes the head stage
    headline = dict(tok_s=comp["AR_tok_s"], us=comp["AR_us"], cycles=r1(comp["AR_us"] * CY), mode="AR, position 1,048,575",
                    mtp_tok_s=comp["MTP_tok_s"], tau=4.159,
                    basis="1,792-pair S81 measured field phases (19,312 region runs exact), BF HALF_PHL, 120 stages / 480 layer "
                          f"dies, field extra wire {ew} a phase (basis 2 + today's {today_phase}), + every DS closure-cost "
                          "ledger item + today's per-node items",
                    source=REPRICE + " ds_rom.after.half_phl", status="measured field + composed (not an adopted or closed rate)",
                    by_class_us=by, extra_hops_1792=extra_hops, hop_us=hop_us)
    # the drill-down stage: the slowest layer stage (the MTP II limiter)
    worst = rec["MTP"]["worst_stage"]["hop"]
    wg = grp_of.get(worst)
    drill = dict(group=wg, why=f"the busiest stage ({rec['MTP']['worst_stage']['busy_us']} us busy, the wavefront II limiter): "
                               f"{rec['MTP']['worst_stage']['first']} .. {worst}")
    notes = [
        "Critical path = tools/dsrom_1m_allmeasured.py's own longest path (Graph.solve) on the composition the 2026-10-08 "
        "re-price builds for HALF_PHL; off-critical operators carry the same solver's start / finish; slack is the delay an "
        "operator can absorb before it becomes the last input of a consumer.",
        f"Each stage group is one TP4 layer-die group of the pipeline (split at stage hops); {n_s81 + extra_hops} further stage "
        "hops exist in the mapping but the composition does not place them: they are one aggregate node before the head hop.",
        "Field operators are the measured 1,792 field phases (HALF_PHL: BF16 phases at 2 x (go->idle) + 2, upper bound).",
        "Engram (E1.* / E14.*, off the critical path): the HBM-resident table design of results/arch/engram_20261008/design.json "
        "(lead flit from S0 -> HBM row lookup on the home stage's rank dies -> TP4 row all-gather -> wkv + key norm), "
        "grade modelled until the blocks close; it replaces the composition's ROM-table gather / deliver placeholders and "
        "the 36 table dies.",
    ]
    return finish(d, headline, gdef, DS_CLASSES, drill, notes,
                  extra=dict(geometry=dict(source=GEO, key="ds_s81_layer", die="S81 layer die (snapshot; one of 4 TP dies per stage)")))


DSC = {c["id"]: c for c in DS_CLASSES}
ENGRAM = "results/arch/engram_20261008/design.json"


def ds_engram_nodes(d):
    """The Engram side branch of the HBM-resident design (stream engram, 2026-10-08): lead flit -> HBM row lookup ->
    TP4 row all-gather -> wkv + key norm, from token start, ending at the L{L}.eng.dot consumer.  The composition's
    own E{L}.gather / E{L}.deliver (ROM-table placeholders) are not exported; these nodes replace them.  Off the
    critical path (slack from the design record); grade 'modelled' until the blocks close."""
    if not (ROOT / ENGRAM).exists():
        return
    rec = J(ENGRAM)
    for L in (1, 14):
        t = rec["timeline_cycles"][f"L{L}"]
        cons = f"L{L}.eng.dot"
        if cons not in d.nodes:
            continue
        grp = d.nodes[cons]["group"]
        steps = [("lead_flit", "hop", t["lead_flit_cycles"], t["lead_flit_note"]),
                 ("hash", "embed", t["hash_cycles"], t["hash_note"]),
                 ("hbm_read", "embed", t["hbm_read_cycles"], t["hbm_read_note"] + "; " + t["lookup_local_src"]),
                 ("rows_allgather", "coll", t["allgather_cycles"] - 4, t["allgather_note"]),
                 ("wkv", "field", t["wkv_cycles"], t["wkv_note"]),
                 ("knorm", "su", t["knorm_cycles"], t["wkv_knorm_src"])]
        st, prev = 0.0, None
        for k, cls, cyc, note in steps:
            nid = f"E{L}.{k}"
            n = d.add(nid, nid, grp, cls, cyc, src("modelled", ENGRAM, f"timeline_cycles.L{L}", note=note), op=k,
                      elements=DSC[cls]["elements"], instances=DSC[cls]["instances"], start=st, deps=[prev] if prev else [],
                      critical=False, kind="parallel")
            n["layer"] = L
            n["slack"] = r1(t["slack_cycles"])
            n["engram"] = True
            st += cyc
            prev = nid
        d.edges.append(dict(src=prev, dst=cons, bytes=6 * 264 * 4, link="on die (key / value to the SU)", cycles=0))


# ======================================================================================== HBM accelerator DS 1M
HBM_CLASSES = [
    dict(id="hbm", label="HBM loader / stream service", elements=["hfd_loader", "hfd_svc_SE_s0", "hfd_svc_SW_s0", "hfd_cmdproc_n",
         "hfd_cmdproc_s"], instances=["svc_*", "phy_*", "hb_loader"]),
    dict(id="xload", label="VM x-broadcast to the SMs", elements=["hfd_vm", "hfd_vm_ne", "hfd_vm_nw", "hfd_vm_se", "hfd_vm_sw",
         "hfd_mcast_r6a", "hfd_mcast_r6b", "hfd_mcast_r7", "hfd_stn_r33", "hfd_meso_r35"], instances=["hb_vm", "w*_xt_*", "w*_xm*"]),
    dict(id="sm", label="SM array (weight matvec, HBM-streamed)", elements=["ot_hbm_accel_smh_tile_e", "ot_hbm_accel_smh_tile_w",
         "ot_hbm_accel_smh_front_c", "ot_hbm_accel_smh_front_n", "ot_hbm_accel_smh_front_s", "hfd_router"],
         instances=["sm*", "svc_*", "hb_cmdproc", "hb_router"]),
    dict(id="barrier", label="Barrier + SM -> SU result gather", elements=["hfd_gath_r25", "hfd_gath_r9", "hfd_result_relay64_ew",
         "hfd_result_relay64_ns", "hfd_su_result_ingress"], instances=["hb_barrier", "w*_wl_sm*"]),
    dict(id="su", label="SU / fused SU chains + SFU", elements=["hfd_su", "hfd_sfu", "hfd_quant", "ot_su12_full", "ot_su12_sfu",
         "ot_su64_full64", "ot_hbm_norm_grp8", "ot_hbm_norm_grp16", "ot_hbm_norm_engine_view", "ot_hdc_v41x_vred_top1024"],
         instances=["hb_su_*", "hb_sfu_*", "hb_quant"]),
    dict(id="attn", label="Attention tiles (near-HBM)", elements=["hfd_attn_tile_b", "hfd_attn_half_hi", "hfd_attn_half_lo",
         "ot_attn_tile_m6h1q", "ot_attn_bank_ew544", "ot_attn_bank_sn544"], instances=["at_*"]),
    dict(id="du", label="Index / router DU", elements=["hfd_index_q_b0", "hfd_index_q_b1", "hfd_index_q_b2", "hfd_index_q_b3",
         "hfd_index_q_b5", "hfd_router"], instances=["hb_router", "at_*"]),
    dict(id="hc", label="Hyper-connection mix (HC, Sinkhorn)", elements=["hfd_hc"], instances=["hb_hc_*"]),
    dict(id="coll", label="Collective endpoint (TU, SerDes)", elements=["hfd_coll", "hfd_coll_credit_prod", "hfd_coll_idle_tx",
         "hfd_coll_pkt_fifo_ii1", "ot_hcoll_port", "ot_ha2_truecredit_rx_phys", "ot_ha2_truecredit_tx_phys",
         "ot_ha2_relay_tx_internal", "ot_ha2_tu_owner_banked_half"], instances=["hb_coll", "sd_*", "lk_*"]),
    dict(id="switch", label="Switch tier (off die, Tomahawk Ultra)", elements=[], instances=["lk_*"]),
]
HBC = {c["id"]: c for c in HBM_CLASSES}


def hbm_cls(n):
    p = n["node"].split(":")[0]
    return {"hbm": "hbm", "xload": "xload", "sm": "sm", "barrier": "barrier", "su": "su", "sufused": "su", "attn": "attn",
            "du": "du", "select": "du", "hcp": "hc", "coll": "coll", "tail": "switch"}.get(p, "su")


# unified line -> (classes it is spread over, weight): wire-like lines over the r05 wire-class shares
WIRE_SHARES = dict(xload="x_broadcast", barrier="barrier_wire_delta", coll=("su_coll_endpoint", "endpoint_serdes"),
                   sm="expert_fetch_wire", hbm="kv_rows_wire", du="index_keys_wire", attn=("attn_out_wire", "attn_q_wire"))
HBM_RULES = {
    "die_wire_r16j": "wire", "closure_00": "wire", "closure_01": "wire", "closure_02": ["barrier"], "closure_03": ["xload"],
    "closure_04": ["barrier"], "closure_05": ["coll"], "closure_06": ["coll"], "closure_07": ["xload"], "closure_08": ["sm"],
    "closure_09": ["sm"], "closure_10": ["sm"], "closure_11": ["du"], "closure_12": ["du"], "closure_13": ["du"],
    "closure_14": ["sm"], "closure_15": ["xload", "barrier"], "closure_16": ["sm"], "closure_17": [], "closure_18": ["attn"],
    "closure_19": ["sm"], "closure_20": ["sm"], "closure_21": ["du"], "closure_22": "wire", "closure_23": [],
    "closure_24": "wire", "closure_25": ["attn"], "closure_26": "wire", "closure_27": "wire",
    "full_fec": "fec", "lever_joint_PQ_XMAP": ["sm", "xload"], "lever_paired_W2_PACK": ["sm"],
    "ha2_truecredit": ["coll"], "cdc_refill_ii1": ["coll"], "sm_su_native_edge_proposed": ["barrier"],
}


def hbm():
    M = "results/rtl/dshbm_matched_reference_20261005/composition.json"
    HWS = "results/rtl/hbm_accel_die_floorplan_20261005/wire_stages.json"
    m = J(M)
    uni = J(UNI)["targets"]["hbm_ds"]
    lines = {l["id"]: l for l in uni["lines"]}
    comp = uni["compositions"]["unified_candidate_contracts_rtl"]
    rp = J(REPRICE)["hbm_ds"]
    gate = m["gate"]
    row = {r["name"]: r for r in m["ladder_target_clocks"]}
    path = m["path"]
    assert abs(sum(n["us"] for n in path) - m["headline"]["AR_us"]) < 0.01
    # gate row differs from the headline row only in the SU term: re-base the su: nodes pro rata
    hd, gr = row["matched"]["AR_by_term"], row[gate["AR_row"]]["AR_by_term"]
    diff = {k: round(gr.get(k, 0) - hd.get(k, 0), 3) for k in set(hd) | set(gr) if abs(gr.get(k, 0) - hd.get(k, 0)) > 0.0005}
    assert set(diff) == {"su"}, diff
    su_nodes = [i for i, n in enumerate(path) if n["node"].startswith("su:")]
    su_sum = sum(path[i]["us"] for i in su_nodes)
    target_su = su_sum + (gate["AR_us"] - m["headline"]["AR_us"])
    scale = target_su / su_sum
    # the composition lines of unified_candidate_contracts_rtl
    use = [l for l in uni["lines"] if l["role"] in ("base", "published", "candidate", "lever") and l["effect"]]
    use = [l for l in use if l["id"] != "collective_sram_protected"] + [lines["cdc_refill_ii1"], lines["sm_su_native_edge_proposed"]]
    assert abs(sum(l["effect"]["AR"] for l in use) - comp["AR_us"]) < 0.002, (sum(l["effect"]["AR"] for l in use), comp["AR_us"])
    wt = J(HWS)["compositions"]["ds_matched"]["terms"]
    wsh = {}
    for c, keys in WIRE_SHARES.items():
        keys = keys if isinstance(keys, tuple) else (keys,)
        wsh[c] = sum(wt[k]["us"] for k in keys)
    serial = [n for n in path if not n["node"].startswith("hcp:")]
    hcp = [n for n in path if n["node"].startswith("hcp:")]
    assert all(n["us"] == 0 for n in hcp)
    CY = CLK / 1e6
    idx_by_cls = collections.defaultdict(list)
    for i, n in enumerate(serial):
        idx_by_cls[hbm_cls(n)].append(i)
    adders = collections.defaultdict(list)

    def spread(item, us, classes, grade, record, weight=None, note=None):
        if not us:
            return
        keys = [i for c in classes for i in idx_by_cls[c]]
        w = [weight(serial[i]) for i in keys] if weight else None
        for i, v in distribute(us * CY, keys, w).items():
            a = dict(item=item, cycles=v, grade=grade, record=record)
            if note:
                a["note"] = note
            adders[i].append(a)

    for l in use:
        if l["id"] == "matched_gate":
            continue
        rule = HBM_RULES[l["id"]]
        rec_ = l["source"][0]["file"] if isinstance(l["source"], list) and l["source"] else UNI
        gr_ = "lever" if l["role"] == "lever" else "priced"
        if rule == "wire":
            tot = sum(wsh.values())
            for c, s in wsh.items():
                spread(l["id"], l["effect"]["AR"] * s / tot, [c], gr_, rec_,
                       note=f"{l['item'][:160]}; spread over the r05 wire-class shares ({HWS} compositions.ds_matched.terms)")
        elif rule == "fec":
            spread(l["id"], l["effect"]["AR"], ["coll"], gr_, rec_, weight=lambda n: n.get("budget_us") or 0.0,
                   note=f"{l['item'][:160]}; per switch crossing, weighted by each collective's TU budget (crossings)")
        else:
            spread(l["id"], l["effect"]["AR"], rule, gr_, rec_, note=f"{l['item'][:160]}; spread over the {'/'.join(rule)} nodes")
    # re-price items (upper bound), placed per occurrence
    RPR = REPRICE + " hbm_ds (upper bound)"
    for i, n in enumerate(serial):
        if n["node"].startswith("coll:"):
            ar = "all_reduce" in n["how"]
            adders[i].append(dict(item="collective_sr_endpoint (re-price 10-08)", cycles=17 if ar else 14, grade="priced", record=RPR))
            adders[i].append(dict(item="truecredit_rx_pin (re-price 10-08)", cycles=1, grade="priced", record=RPR))
        if n["node"].startswith("sufused:") and "norm" in n["node"]:
            adders[i].append(dict(item="norm_split (re-price 10-08)", cycles=2, grade="priced", record=RPR))
    pk = next(x for x in rp["items"] if x["item"] == "packet_sram_ii1rw")["cycles_hi"]
    spread("packet_sram_ii1rw (re-price 10-08)", pk / CY, ["coll"], "priced", RPR, note="+4 a packet pass x 610 passes, spread over the collectives")
    d = Design("hbm_ds", "HBM accelerator (TP-96 dies, Tomahawk Ultra tier), DeepSeek-V4.1 1M, AR", "cycles")
    gdef = collections.OrderedDict()

    def gname(n):
        L = n["layer"]
        if L == -2:
            return "embed"
        if isinstance(L, str):
            return "head"
        return f"L{L}"
    for i, n in enumerate(serial):
        gid = gname(n)
        if gid not in gdef:
            gdef[gid] = dict(label={"embed": "Embed", "head": "LM head + argmax"}.get(gid, f"Layer {gid[1:]}"),
                             kind="embed" if gid == "embed" else "head" if gid == "head" else "layer")
        us = n["us"] * (scale if n["node"].startswith("su:") else 1.0)
        c = hbm_cls(n)
        grade = {"measured": "measured", "measured_tu_budget": "measured+vendor", "modelled": "modelled"}[n["cls"]]
        note = n["how"]
        if n["node"].startswith("su:"):
            note += f" | re-based to the gate row {gate['AR_row']} (su term {gr['su']} vs {hd['su']} us: x{scale:.5f})"
        nn = d.add(f"n{i:04d}", n["node"], gid, c, us * CY, src(grade, M, f"path[{path.index(n)}]", note=note[:600]),
                   op=n["node"].split(":")[0], elements=HBC[c]["elements"], instances=HBC[c]["instances"], adders=adders.get(i, []),
                   bytes_in=None, link_in={"coll": "SU -> endpoint -> SerDes -> switch", "switch": "switch tier (8 chips striped)",
                                           "xload": "VM -> SM x faces", "sm": "HBM -> stream service -> SM", "barrier": "SM -> SU result tree"}.get(c, "on die"))
        nn["layer"] = n["layer"]
        if n.get("budget_us"):
            nn["vendor_budget_cycles"] = r1(n["budget_us"] * CY)
    d.chain_schedule()
    # HC mixes run beside the layer body (exposed 0): parallel nodes with their measured duration
    first_of = {}
    for nid in d.order:
        first_of.setdefault(d.nodes[nid]["group"], nid)
    for k, n in enumerate(hcp):
        mm = re.search(r"([\d.]+) us beside a ([\d.]+) us body", n["how"])
        dur, body = float(mm.group(1)), float(mm.group(2))
        gid = gname(n)
        part = n["node"].split(".")[-1]
        grp_nodes = [x for x in d.order if d.nodes[x]["group"] == gid]
        # attn mix starts with the layer; ffn mix with the layer's second half (first node after the attention out gather)
        if part == "ffn":
            k0 = next((j for j, x in enumerate(grp_nodes) if d.nodes[x]["label"].startswith("sufused:hc_post")), None)
            anchor = grp_nodes[k0 + 1] if k0 is not None and k0 + 1 < len(grp_nodes) else grp_nodes[0]
        else:
            anchor = grp_nodes[0]
        st = d.nodes[anchor]["start"]
        nn = d.add(f"hcp{k:03d}", n["node"], gid, "hc", dur * CY, src("measured", M, f"path[{path.index(n)}]", note=n["how"]),
                   op="hcp", elements=HBC["hc"]["elements"], instances=HBC["hc"]["instances"], critical=False, deps=[],
                   start=st, kind="parallel")
        nn["layer"] = n["layer"]
        nn["slack"] = r1((body - dur) * CY)
    after = rp["upper"]["after"]
    total = d.nodes[d.order[-1]]["end"]
    exp_us = comp["AR_us"] + sum(x["cycles_hi"] for x in rp["items"]) / CY
    assert abs(total / CY - exp_us) < 0.01, (total / CY, exp_us)
    headline = dict(tok_s=after["AR_tok_s"], us=round(exp_us, 3), cycles=r1(exp_us * CY), mode="AR, position 1,048,575",
                    mtp_tok_s=after["MTP_tok_s"], tau=comp["tau"],
                    basis=f"{UNI} hbm_ds unified_candidate_contracts_rtl ({comp['AR_us']} us, {comp['AR_tok_s']} tok/s) + the "
                          "2026-10-08 re-price upper bound (collective SR endpoint, norm split, true-credit rx, packet SRAM ii1rw)",
                    source=REPRICE + " hbm_ds.upper.after", status="priced candidate (not a closed rate)",
                    gate_row=gate["AR_row"], gate_AR_us=gate["AR_us"])
    worst = max((g for g in gdef if g.startswith("L")), key=lambda g: sum(d.nodes[x]["cycles"] for x in d.order if d.nodes[x]["group"] == g))
    drill = dict(group=worst, why="the longest layer on the token path")
    notes = [
        f"Measured path: {M} path[] (2,291 operators; the 80 HC-mix operators are exposed 0 and are drawn as parallel "
        "operators beside their layer body with their measured duration).",
        f"Every line of unified_candidate_contracts_rtl ({len(use) - 1} lines over the gate) is spread over the operators of the "
        "class it is charged on (HBM_RULES in the tool; die-wire lines over the r05 wire-class shares, full FEC over the switch "
        "crossings by TU budget). Those adders are grade 'priced' or 'lever' (negative: exact levers).",
        "Each die of the TP-96 group runs the same schedule; collectives cross the off-die switch tier ('switch' class).",
    ]
    return finish(d, headline, gdef, HBM_CLASSES, drill, notes,
                  extra=dict(geometry=dict(source=GEO, key="hbm_ds", die="HBM accelerator DS die (r14b snapshot; one of 96)")))


# ======================================================================================== MTP (speculative) step
# One MTP step = draft (the MTP head proposes 5 tokens) -> verify (6 positions through the layers: the fixed
# latency is paid once, then one wavefront interval / multi-position walk) -> accept / commit (tau accepted tokens a
# step, on average) -> the next step.  No new model: every term is the existing MTP pricing of the composition the
# re-price drives (DS ROM: tools/dsrom_1m_allmeasured.py MTP + field_phases_1792 compose; HBM: the matched reference's
# mtp() walk at P = 6 + the unified composition's MTP_step lines + the re-price upper bound).
# hw: the hardware status of each MTP-only operator (verify-pass operators are the AR path's, as in the AR view):
#   built   = runs on closed elements / the same hardware as the AR path
#   partial = its element closed as a block but is not integrated / not adopted on the die
#   none    = no closed hardware element: FLAGGED (modelled, or measured RTL with no die / route)
MTP_FLAG_NONE = "modelled — no RTL/route"
QWEN_VERDICT = "results/rtl/qwen_rom_kv_fullbw_20261004/dspark_verdict.json"
DS_DRAFT_REC = "results/rtl/dsrom_recovery_20261004/draft/draft_blocks_recovery.json"
DS_SLICES = "results/rtl/dsrom_dspark_step_slices_20261004/composition.json"
WFC_CLOSURE = "results/rtl/dsrom_wfc_split_20261006/closure.json"
WAVE_REJECT = "results/rtl/dsrom_wfc_r12_fanout_20261005/physical_rejection/decision.json"
HBM_CTL = "results/rtl/hbm_accel_fmax_inventory_20261004/ctl_takeover_20261005/closure.json"
HBM_DRAFT = "results/rtl/dshbm_dspark_draft_20261004/composition.json"
PHASES = [("draft", "Draft (MTP head)"), ("verify", "Verify (6 positions)"), ("accept", "Accept / commit")]
MTP_CLASSES_EXTRA = [
    dict(id="wave", label="Wavefront verify positions (slowest stage)", elements=["ot_rom_pkg_ctrl_wfc", "ot_rom_pkg_ctrl_wf"],
         instances=["e*", "n*_*", "sp_vm", "sp_su_n", "sp_su_s"]),
    dict(id="ctl", label="Accept / commit control (spec state, accept)", elements=["ot_hdc_accept", "ot_dshbm_dspark_ctl",
         "ot_dshbm_spec_state", "ot_dshbm_accept_port"], instances=["hb_cmdproc", "ctrl_*"]),
]


def hw(status, note, evidence=None):
    assert status in ("built", "partial", "none")
    d = dict(status=status, note=note)
    if evidence:
        d["evidence"] = evidence
    return d


def mark(n, phase, hwd=None):
    n["phase"] = phase
    if hwd:
        n["hw"] = hwd
        if hwd["status"] == "none":
            n["flag"] = hwd.get("flag", MTP_FLAG_NONE)
    return n


def phase_spans(d, total):
    out = []
    for pid, lab in PHASES:
        ns = [n for n in d.nodes.values() if n.get("phase") == pid and n["critical"]]
        if not ns:
            continue
        st, en = min(n["start"] for n in ns), max(n["end"] for n in ns)
        cyc = sum(n["cycles"] for n in ns)
        out.append(dict(id=pid, label=lab, start=r1(st), end=r1(en), cycles=r1(cyc), share=round(cyc / total, 6)))
    return out


def hw_summary(d):
    s = collections.defaultdict(lambda: dict(nodes=0, cycles=0.0))
    for n in d.nodes.values():
        if n["critical"] and n.get("hw"):
            s[n["hw"]["status"]]["nodes"] += 1
            s[n["hw"]["status"]]["cycles"] += n["cycles"]
    return {k: dict(nodes=v["nodes"], cycles=r1(v["cycles"])) for k, v in s.items()}


def accounting(total, tau, ar_cycles, phases, tau_source):
    return dict(tau=tau, tau_source=tau_source, drafted_tokens=5, verified_positions=6,
                accepted_tokens_per_step=tau, step_cycles=r1(total), per_accepted_cycles=r1(total / tau),
                per_accepted_us=round(total / tau / CLK * 1e6, 3), ar_token_cycles=r1(ar_cycles),
                speedup_over_ar=round(ar_cycles * tau / total, 4),
                per_accepted_by_phase={p["id"]: r1(p["cycles"] / tau) for p in phases},
                rule="one verify step emits tau tokens on average (accepted drafts + the verify pass's own next token); "
                     "per-accepted-token cost = step / tau")


def ds_rom_mtp(ar=None):
    import dsrom_1m_measure as M
    ar = ar or ds_rom()
    cap, fp, rp, ew = ds_capture()
    CY = CLK / 1e6
    npos = M.WAVEFRONT["positions"]
    # ---- both BF cases at phase level (the reproduction of the re-priced MTP tok/s)
    variants = {}
    for tgt, (v, key, rkey) in DS_TARGETS.items():
        m = cap["all"][tgt]["rec"]["MTP"]
        comp = fp["variants"][v]["compositions"][key]
        assert comp["MTP_tok_s"] == rp["after"][rkey]["MTP_tok_s"], (rkey, comp, rp["after"][rkey])
        parts = dict(draft_us=m["draft_us"], verify_first_position_us=comp["AR_us"], wavefront_us=round(npos * m["II_us"], 3),
                     seed_commit_us=m["seed_commit_us"])
        rnd = comp["MTP_step_us"] - sum(parts.values())
        assert abs(rnd) < 0.05, (rkey, rnd)
        variants[rkey] = dict(
            label={"half_phl": "BF HALF_PHL (120 stages, accepted closure path)",
                   "full_rate_shared98": "BF full rate (full_shared, 98 stages; no BF cost)"}[rkey],
            AR_tok_s=comp["AR_tok_s"], AR_us=comp["AR_us"], MTP_tok_s=comp["MTP_tok_s"], step_us=comp["MTP_step_us"],
            tau=m["tau"], II_us=m["II_us"], positions_after_first=npos, worst_stage=m["worst_stage"], **parts,
            rounding_us=round(rnd, 4), extra_hops_1792=fp["variants"][v]["extra_hops"],
            reproduces=f"draft {parts['draft_us']} + verify ({comp['AR_us']} AR pass + {npos} x II {m['II_us']}) + seed/commit "
                       f"{parts['seed_commit_us']} (+ {rnd:+.3f} composition rounding) = {comp['MTP_step_us']} us; "
                       f"{m['tau']} x 1e6 / {comp['MTP_step_us']} = {m['tau'] * 1e6 / comp['MTP_step_us']:,.2f} tok/s "
                       f"(published {comp['MTP_tok_s']:,.1f})",
            source=REPRICE + f" ds_rom.after.{rkey}.MTP_tok_s")
    hv = variants["half_phl"]
    m = cap["rec"]["MTP"]
    dt = m["draft_terms"]
    dr = J(DS_DRAFT_REC)
    sl = J(DS_SLICES)["measured_reduced"]
    wfc = J(WFC_CLOSURE)
    d = Design("ds_rom", "DeepSeek-V4.1 ROM array (S81, 1,792 pairs, HALF_PHL BF), 1M context, MTP (DSpark, gamma 5)", "cycles")
    gdef = collections.OrderedDict()
    HW_DRAFTDIE = hw("none", "not built: mtp.* weights sit on no die of the S81 binding (the DSpark stage placement DP1-EP5, "
                     f"{dr['placement']['dies']['total']} S81 layer-class dies, +{dr['placement']['dies']['added_silicon_mm2']:,.0f} mm2, "
                     "is stated, not bound); the elements were measured exact in full-shape RTL on the released mtp.* weights",
                     evidence=DS_DRAFT_REC + " still_modelled['DSpark stage placement'] / placement")
    HW_DRAFTDIE["flag"] = "not built — no die / route (elements measured in RTL)"
    # ---- draft: three DSpark blocks (node level, the record's own critical paths)
    ff = cap["rec"]["info"]["draft_blocks"]["full_fec"]
    blk_nodes = []
    for k, (st, s) in enumerate(dr["stages"].items()):
        gid = f"D{k}"
        gdef[gid] = dict(label=f"Draft block {st} (DSpark stage {k})", kind="draft", phase="draft")
        for p in s["critical_path"]:
            blk_nodes.append((gid, st, p))
    fec_keys = [i for i, (_, _, p) in enumerate(blk_nodes) if "hop" in p["node"] or "all" in p["node"]]
    fec_w = [99.0 if "hop" in blk_nodes[i][2]["node"] else 100.0 for i in fec_keys]
    fec = distribute(ff["cycles"], fec_keys, fec_w)
    for i, (gid, st, p) in enumerate(blk_nodes):
        c = ds_cls(p["node"])
        gr = {"measured": "measured", "measured+vendor_phy": "measured+vendor", "placement": "measured"}.get(p["cls"], "modelled")
        ad = [dict(item="draft full-KP4 FEC delta", cycles=fec[i], grade="measured+vendor", record=ff["record"],
                   note=f"{ff['cycles']} cycles ({ff['board_hops']} board hops x {ff['hop_delta_cycles']} + {ff['collective_issues']} "
                        f"collectives x {ff['collective_delta_cycles']}), spread over the hop / collective operators")] if i in fec else []
        n = d.add(f"{st}.{p['node']}", f"{st} {p['node']}", gid, c, p["us"] * CY,
                  src(gr, DS_DRAFT_REC, f"stages['{st}'].critical_path", note=f"{p['cls']}; " + dr["basis"][:200]),
                  op=p["node"], elements=DSC[c]["elements"], instances=DSC[c]["instances"], adders=ad)
        mark(n, "draft", HW_DRAFTDIE)
    assert abs(sum(n["cycles"] for n in d.nodes.values()) - dt["blocks_us"] * CY) < 1.0
    # ---- draft: 5 serial head steps on the head die (lm_head sweep) + the Markov embedding head
    gdef["DH"] = dict(label="Draft head x 5 (LM head + Markov, serial chain)", kind="draft", phase="draft")
    head_hw = hw("built", "the head die's lm_head bundle (ot_dsrom_head_elem_A / _B SAFE closed 2026-10-08), the verify pass's own head")
    mk_hw = hw("none", "Markov bigram head (d_i's embedding row x the lm_head MAC ratio 0.00781): a transfer ratio from the reduced "
               "vehicle, no full-shape Markov RTL and no element", evidence=DS_SLICES + " transfer_ratios.markov_over_head_macs_full")
    for k in range(5):
        n = d.add(f"draft.head{k}", f"draft head step {k + 1}: LM head sweep + argmax", "DH", "head", dt["head_occ_us"] * CY,
                  src("measured", "tools/dsrom_1m_allmeasured.py info.head.stage_occupancy_us",
                      note=f"head stage occupancy {dt['head_occ_us']} us (the measured lm_head bundle sweep), one per drafted token"),
                  op="draft.head", elements=DSC["head"]["elements"], instances=DSC["head"]["instances"])
        mark(n, "draft", head_hw)
        n = d.add(f"draft.markov{k}", f"draft step {k + 1}: Markov embedding head", "DH", "head",
                  dt["head_occ_us"] * dt["r_markov"] * CY,
                  src("modelled", DS_SLICES, "transfer_ratios.markov_over_head_macs_full",
                      note=f"head occupancy x {dt['r_markov']} (Markov MACs / lm_head MACs at full shape)"),
                  op="draft.markov", elements=[], instances=[])
        mark(n, "draft", mk_hw)
    n = d.add("draft.fixed", "draft fixed overhead: head element SAFE (+39 x 5 sweeps)", "DH", "head", dt["fixed_overhead_us"] * CY,
              src("priced", REPRICE, "ds_rom.items[head_elem_safe] draft.total +195", note="lm_head element A/B SAFE +39 cycles a bundle "
                  "sweep on the 5 draft head sweeps (dshead-elemA/elemB-safe CLOSED 10-08)"),
              op="draft.fixed", elements=DSC["head"]["elements"], instances=DSC["head"]["instances"])
    mark(n, "draft", head_hw)
    t_draft = d.chain_schedule()
    assert abs(t_draft - m["draft_us"] * CY) < 1.0, (t_draft, m["draft_us"] * CY)
    # ---- verify, position 1: the AR pass (the AR record's own critical path, shifted)
    an = {n["id"]: n for n in ar["nodes"]}
    ag = {g["id"]: g for g in ar["groups"]}
    for nid in ar["critical_path"]:
        n0 = an[nid]
        gid = "V." + n0["group"]
        if gid not in gdef:
            g0 = ag[n0["group"]]
            gdef[gid] = dict(label="verify " + g0["label"], kind=g0["kind"], phase="verify")
        n = d.add("V." + nid, n0["label"], gid, n0["cls"], n0["base_cycles"], n0["src"], op=n0["op"],
                  elements=n0.get("elements", DSC[n0["cls"]]["elements"]), instances=n0.get("instances", DSC[n0["cls"]]["instances"]),
                  adders=[dict(item=a, cycles=c, **ar["adder_items"].get(a, {})) for a, c in n0["adders"]],
                  start=t_draft + n0["start"], kind=n0["kind"])
        for k in ("reprice_10_08", "bf16", "layer"):
            if k in n0:
                n[k] = n0[k]
        mark(n, "verify")
    t_v1 = t_draft + ar["totals"]["cycles"]
    assert abs(ar["totals"]["cycles"] - hv["verify_first_position_us"] * CY) < 1.0
    # ---- verify, positions 2..6: wavefront intervals through the slowest stage
    ws = m["worst_stage"]
    ovh = 46 / 11271
    busy = ws["busy_us"] * (1 + ovh)
    hopx = m["II_us"] - busy
    gdef["W"] = dict(label=f"verify positions 2-6 (wavefront II {m['II_us']} us at {ws['first']} .. {ws['hop']})", kind="wave",
                     phase="verify")
    wave_hw = hw("partial", f"wavefront controller: the split ot_rom_pkg_ctrl_wfc closed as blocks ({wfc['verdict'][:90]}...) "
                 "but integration_qualified = false, so the composition charges the reference ot_rom_pkg_ctrl_wf handoff "
                 "(46 / 11,271), whose physical route was rejected (three variants)",
                 evidence=f"{WFC_CLOSURE} accepted/exact true, integration_qualified false; {WAVE_REJECT}")
    t = t_v1
    prev = d.order[-1]
    for k in range(npos):
        n = d.add(f"wave.p{k + 2}", f"position {k + 2}: slowest stage busy ({ws['first']} .. {ws['hop']}) + handoff", "W", "wave",
                  busy * CY, src("measured", "tools/dsrom_1m_allmeasured.py MTP.worst_stage",
                                 note=f"busy {ws['busy_us']} us x (1 + measured handoff 46/11271) (wavefront verify rule, "
                                      "results/rtl/dsrom_wavefront_verify_20261004: a stage takes the next position 46 cycles "
                                      "after it finishes the previous one)"),
                  op="wave.busy", start=t, deps=[prev], elements=MTP_CLASSES_EXTRA[0]["elements"],
                  instances=MTP_CLASSES_EXTRA[0]["instances"])
        mark(n, "verify", wave_hw)
        t += busy * CY
        n = d.add(f"wave.h{k + 2}", f"position {k + 2}: stage hop (full-KP4) out of the slowest stage", "W", "hop", hopx * CY,
                  src("measured+vendor", "tools/dsrom_1m_allmeasured.py MTP.II_us", note=f"II {m['II_us']} - busy x (1 + ovh) = "
                      f"{hopx:.4f} us: the measured stage hop + its cable flight"), op="wave.hop", start=t,
                  elements=[], instances=DSC["hop"]["instances"])
        mark(n, "verify", hw("built", "the stage-hop link (ot_dsrom_link_rt, measured; PHY = vendor budget), as AR"))
        t += hopx * CY
        prev = n["id"]
    # ---- accept / commit: seed (next step's DSpark seed) + commit, then the composition's rounding
    gdef["A"] = dict(label="accept / commit + seed of the next step", kind="accept", phase="accept")
    seed_c, com_c = sl["dspark_seed_cycles"], sl["commit_cycles"]
    sc = m["seed_commit_us"]
    note_sc = (f"seed_commit {sc} us = the reduced-vehicle ratio (seed {seed_c} + commit {com_c} cycles) / verify, "
               f"x the full-shape verify pass (dsrom_1m_measure DRAFT.seed_commit_us); split seed / commit by the reduced cycles")
    n = d.add("accept.seed", "seed: main_proj + wkv window rows of the 3 DSpark stages (next step)", "A", "field",
              sc * seed_c / (seed_c + com_c) * CY, src("modelled", DS_SLICES, "transfer_ratios.seed_commit_over_verify", note=note_sc),
              op="accept.seed", start=t, deps=[prev], elements=[], instances=[])
    mark(n, "accept", dict(HW_DRAFTDIE, note="the seed runs on the DSpark stage dies: " + HW_DRAFTDIE["note"]))
    t += n["cycles"]
    n = d.add("accept.commit", "accept / commit: compare drafts vs targets, emit accepted tokens, roll back KV", "A", "ctl",
              sc * com_c / (seed_c + com_c) * CY, src("modelled", DS_SLICES, "measured_reduced.commit_cycles", note=note_sc),
              op="accept.commit", start=t, elements=MTP_CLASSES_EXTRA[1]["elements"][:1], instances=[])
    mark(n, "accept", hw("partial", "ot_hdc_accept closed as a block (accept_a0, SS +55.27 / FF +13.99 ps in the HBM control "
                         "inventory) but is on no S81 die; the ROM commit path is ISA-level (ot_hdc_accept + CTL ACCEPT)",
                         evidence=HBM_CTL + " rows[accept_a0]"))
    t += n["cycles"]
    if (ROOT / ENGRAM).exists():
        er = J(ENGRAM)["mtp_history_restore"]
        n = d.add("accept.engram_rewind", "Engram history restore: rewind the user's n-gram history by the rejected drafts",
                  "A", "embed", er["cycles"], src("modelled", ENGRAM, "mtp_history_restore", note=er["how"]),
                  op="accept.engram_rewind", start=t, deps=["accept.commit"], critical=False, kind="parallel",
                  elements=["ot_dsrom_engram_idwin"], instances=[])
        mark(n, "accept", hw("partial", "RTL rewind port of ot_dsrom_engram_idwin, bench-exact vs the official cache "
                             "truncation; not routed", evidence="results/rtl/dsrom_engram_lookup_campaign.json"))
    n = d.add("accept.round", "composition rounding (MTP tok/s rounded to 0.1 before the 1,792 hops are added)", "A", "ctl",
              hv["step_us"] * CY - t, src("zero", "tools/s81/field_phases_1792.py compose", note=f"MTP_step_us = tau x 1e6 / "
              f"round(MTP_tok_s, 1) + extra hops: {hv['rounding_us'] * CY:+.1f} cycles against the sum of the terms "
              "(+ the 0.1-cycle rounding of the operators)"), op="accept.round", start=t,
              elements=[], instances=[])
    mark(n, "accept")
    total = t + n["cycles"]
    assert abs(total - hv["step_us"] * CY) < 0.6, (total, hv["step_us"] * CY)
    phases = phase_spans(d, total)
    headline = dict(tok_s=hv["MTP_tok_s"], us=hv["step_us"], cycles=r1(hv["step_us"] * CY), tau=m["tau"],
                    mode=f"MTP (DSpark gamma 5, tau {m['tau']}), position 1,048,575", ar_tok_s=hv["AR_tok_s"],
                    mtp_over_ar=round(hv["MTP_tok_s"] / hv["AR_tok_s"], 3),
                    basis=f"{m['rule']}; 1,792 HALF mapping adds {hv['extra_hops_1792']} hops once a step",
                    source=REPRICE + " ds_rom.after.half_phl.MTP_tok_s", status="measured field + composed MTP rule "
                    "(wavefront and draft placement not physically qualified)", physical_qualified=m.get("physical_qualified"))
    drill = dict(group="W", why="the wavefront: positions 2-6 at the slowest stage's interval")
    notes = [
        "One MTP step: the DSpark draft (3 blocks + 5 serial head steps) -> verify (position 1 is the whole AR pass, the "
        f"fixed latency paid once; positions 2-6 follow it through the pipeline at one interval II = slowest stage busy x "
        f"(1 + 46/11,271) + hop = {m['II_us']} us each) -> accept / commit + the next step's seed.",
        f"Rate = tau {m['tau']} accepted tokens / step ({hv['step_us']} us) = {hv['MTP_tok_s']:,.1f} tok/s; full-rate BF "
        f"(98 stages): {variants['full_rate_shared98']['MTP_tok_s']:,.1f} tok/s (phase split in mtp_variants).",
        "Hatched operators have no closed hardware: the three DSpark stages and the seed run on dies the S81 binding does not "
        "contain (mtp.* weights are unowned there); the Markov head is a transfer ratio. The wavefront controller and the "
        "accept unit closed as blocks but are not integrated (dashed).",
        "The verify pass's operators are the AR view's critical path (off-critical operators: see the AR view).",
    ]
    rec = finish(d, headline, gdef, DS_CLASSES + MTP_CLASSES_EXTRA, drill, notes, tau=m["tau"],
                 extra=dict(geometry=ar["geometry"], mtp_variants=variants))
    rec.update(phases=phases, hw_summary=hw_summary(d),
               accounting=accounting(total, m["tau"], ar["totals"]["cycles"], phases, m["tau_source"]))
    return rec


def hbm_p6():
    """the matched reference's MTP walk at P = 6 for its MTP gate row (corrected+wg+su12), replayed in-process"""
    import dshbm_matched_reference as MR
    A, CL = MR.A, MR.CL
    prog = json.loads((A.BASE / "program.json").read_text())
    _, su6, _, _ = A.su_tables()
    coll, local = A.Coll(A.load(MR.INH / "collectives.json")), A.Local(A.load(MR.INH / "local.json"))
    hbm_ = A.Hbm(A.load(MR.INH / "hbm_streams.json"))
    smseq = MR.SMSeq(sorted((MR.REC / "sm_seq").glob("*_nc8_a*.json")))
    f6 = MR.REC / "su_m6a5" / "su_N1024_M256_b7r8m6a5_dpi_beh_su_cases_p6om_ildr.json"
    s6 = CL.best_of([("dr", json.loads(f6.read_text()))])
    T12 = dict(A.TARGET, su=1.2e9, du_ser=MR.F_SER)
    return MR.mtp(prog, smseq, CL.su_table_overlap(s6), coll, local, hbm_, T12, ("coll", "local", "hbm", "mixes"), True, None)


def hbm_mtp(ar=None):
    M_ = "results/rtl/dshbm_matched_reference_20261005/composition.json"
    HWS = "results/rtl/hbm_accel_die_floorplan_20261005/wire_stages.json"
    ar = ar or hbm()
    m = J(M_)
    gate = m["gate"]
    row = {r["name"]: r for r in m["ladder_target_clocks"]}[gate["MTP_row"]]["MTP"]
    mm, rows6 = hbm_p6()
    assert abs(mm["step_us"] - gate["MTP_step_us"]) < 0.001 and abs(mm["step_us"] - row["step_us"]) < 0.001, (mm["step_us"], gate)
    uni = J(UNI)["targets"]["hbm_ds"]
    lines = {l["id"]: l for l in uni["lines"]}
    comp = uni["compositions"]["unified_candidate_contracts_rtl"]
    rp = J(REPRICE)["hbm_ds"]
    tau = comp["tau"]
    use = [l for l in uni["lines"] if l["role"] in ("base", "published", "candidate", "lever") and l["effect"]]
    use = [l for l in use if l["id"] != "collective_sram_protected"] + [lines["cdc_refill_ii1"], lines["sm_su_native_edge_proposed"]]
    assert abs(sum(l["effect"]["MTP_step"] for l in use) - comp["MTP_step_us"]) < 0.002
    assert abs(lines["matched_gate"]["effect"]["MTP_step"] - mm["step_us"]) < 0.001
    CY = CLK / 1e6
    wt = J(HWS)["compositions"]["ds_matched"]["terms"]
    wsh = {c: sum(wt[k]["us"] for k in (keys if isinstance(keys, tuple) else (keys,))) for c, keys in WIRE_SHARES.items()}
    serial = [n for n in rows6 if not n["node"].startswith("hcp:")]
    hcp = [n for n in rows6 if n["node"].startswith("hcp:")]
    assert all(n["us"] == 0 for n in hcp)
    idx_by_cls = collections.defaultdict(list)
    for i, n in enumerate(serial):
        idx_by_cls[hbm_cls(n)].append(i)
    adders = collections.defaultdict(list)

    def spread(item, us, classes, grade, record, weight=None, note=None):
        if not us:
            return
        keys = [i for c in classes for i in idx_by_cls[c]]
        w = [weight(serial[i]) for i in keys] if weight else None
        for i, v in distribute(us * CY, keys, w).items():
            a = dict(item=item, cycles=v, grade=grade, record=record)
            if note:
                a["note"] = note
            adders[i].append(a)

    for l in use:
        if l["id"] == "matched_gate":
            continue
        rule = HBM_RULES[l["id"]]
        rec_ = l["source"][0]["file"] if isinstance(l["source"], list) and l["source"] else UNI
        gr_ = "lever" if l["role"] == "lever" else "priced"
        eff = l["effect"]["MTP_step"]
        if rule == "wire":
            tot = sum(wsh.values())
            for c, s_ in wsh.items():
                spread(l["id"], eff * s_ / tot, [c], gr_, rec_, note=f"{l['item'][:160]}; MTP_step effect, spread over the r05 wire-class shares")
        elif rule == "fec":
            spread(l["id"], eff, ["coll"], gr_, rec_, weight=lambda n: n.get("budget_us") or 0.0,
                   note=f"{l['item'][:160]}; MTP_step effect per switch crossing, weighted by TU budget")
        else:
            spread(l["id"], eff, rule, gr_, rec_, note=f"{l['item'][:160]}; MTP_step effect over the {'/'.join(rule)} nodes")
    # re-price (upper bound): the same cycles a step as the AR walk (unified convention), placed per occurrence
    RPR = REPRICE + " hbm_ds (upper bound)"
    items = {x["item"]: x["cycles_hi"] for x in rp["items"]}
    n_ar = n_g = 0
    for i, n in enumerate(serial):
        if n["node"].startswith("coll:"):
            a_ = "all_reduce" in n["how"]
            n_ar += a_; n_g += not a_
            adders[i].append(dict(item="collective_sr_endpoint (re-price 10-08)", cycles=17 if a_ else 14, grade="priced", record=RPR))
            adders[i].append(dict(item="truecredit_rx_pin (re-price 10-08)", cycles=1, grade="priced", record=RPR))
    assert 17 * n_ar + 14 * n_g == items["collective_sr_endpoint"] and n_ar + n_g == items["truecredit_rx_pin"], (n_ar, n_g)
    norm_keys = [i for i, n in enumerate(serial) if n["node"].startswith("su:") and "norm" in n["node"]]
    for i, v in distribute(items["norm_split"], norm_keys).items():
        adders[i].append(dict(item="norm_split (re-price 10-08)", cycles=v, grade="priced", record=RPR,
                              note=f"+2 x the AR path's fused norm nodes = {items['norm_split']} cycles a step, spread over the "
                                   f"{len(norm_keys)} SU norm nodes of the P6 walk (unfused SU chains at P6)"))
    spread("packet_sram_ii1rw (re-price 10-08)", items["packet_sram_ii1rw"] / CY, ["coll"], "priced", RPR,
           note="+4 a packet pass x 610 passes, spread over the collectives")
    d = Design("hbm_ds", "HBM accelerator (TP-96 dies, Tomahawk Ultra tier), DeepSeek-V4.1 1M, MTP (DSpark, gamma 5)", "cycles")
    gdef = collections.OrderedDict()
    # ---- draft
    drw = [x for x in J(HBM_DRAFT)["rows"] if x["ctx"] == "1M" and x["scenario"] == "tomahawk_ultra_protocol"
           and x["design"] == "ablation_w19"][0]
    ab = drw["as_built"]
    assert abs(ab["draft_us"] - mm["draft_us"]) < 1e-6 and abs(drw["seed_commit_us"] - mm["seed_commit_us"]) < 1e-6
    gdef["D"] = dict(label="Draft: 3 DSpark stages + LM head + 5-step Markov chain", kind="draft", phase="draft")
    ctl_hw = hw("built", "SM array (as the AR path) + the DSpark controller ot_dshbm_dspark_ctl (ctl_f2) and the SM argmax "
                "epilogue ot_dshbm_argmax (argmax_f1), both closed blocks", evidence=HBM_CTL)
    n = d.add("draft.compute", "draft compute: embed + 3 DSpark stages (5 slots) + batched LM head pass + 5-step Markov chain",
              "D", "sm", (ab["draft_us"] - ab["draft_transport_us"]) * CY,
              src("measured", HBM_DRAFT, "rows[1M, tomahawk_ultra_protocol, ablation_w19].as_built",
                  note="stage SM ops measured 5-column on the SM element (exact), head 5-col pass, chain step measured; "
                       "composed per the record's definition (draft_us - draft_transport_us)"),
              op="draft.compute", elements=HBC["sm"]["elements"] + ["ot_dshbm_argmax"], instances=HBC["sm"]["instances"])
    mark(n, "draft", ctl_hw)
    n = d.add("draft.transport", "draft collectives / transport (18 stage collectives + cross-die argmax merges)", "D", "coll",
              ab["draft_transport_us"] * CY, src("modelled", HBM_DRAFT, "as_built.draft_transport_us",
                                                  note="w15 collective time; o-group tree reduce + multicast extrapolated (record flag)"),
              op="draft.transport", elements=HBC["coll"]["elements"], instances=HBC["coll"]["instances"])
    mark(n, "draft", hw("built", "the collective endpoint + switch tier of the AR path; its time is extrapolated, not the hardware"))
    # ---- verify: the P6 walk
    def gname(n):
        L = n["layer"]
        return "embed" if L == -2 else "head" if isinstance(L, str) else f"L{L}"
    for i, n in enumerate(serial):
        gid = "V." + gname(n)
        if gid not in gdef:
            b = gname(n)
            gdef[gid] = dict(label="verify " + {"embed": "embed", "head": "LM head + argmax"}.get(b, f"layer {b[1:]}"),
                             kind="embed" if b == "embed" else "head" if b == "head" else "layer", phase="verify")
        c = hbm_cls(n)
        grade = {"measured": "measured", "measured_tu_budget": "measured+vendor", "modelled": "modelled"}[n["cls"]]
        nn = d.add(f"v{i:04d}", n["node"], gid, c, n["us"] * CY,
                   src(grade, "tools/dshbm_matched_reference.py mtp() walk P=6", f"row {gate['MTP_row']}", note=n["how"][:600]),
                   op=n["node"].split(":")[0], elements=HBC[c]["elements"], instances=HBC[c]["instances"], adders=adders.get(i, []))
        nn["layer"] = n["layer"]
        if n.get("budget_us"):
            nn["vendor_budget_cycles"] = r1(n["budget_us"] * CY)
        mark(nn, "verify")
    gdef["VU"] = dict(label="verify: routed-expert union over 6 positions (W19 model)", kind="union", phase="verify")
    un_hw = hw("partial", "ot_dshbm_expert_union closed as a block (union_f3, SS +9.52 / FF +10.79 ps) but not adopted "
               "(adopted_system false); the SM / fetch increment itself is the W19 lines-style model, no RTL walk",
               evidence=HBM_CTL + " rows[union_f3]")
    for k, c, lab in (("sm", "sm", "union: extra expert SM work (6 positions' union of routed experts)"),
                      ("fetch", "hbm", "union: extra expert weight fetch (union of routed experts)")):
        n = d.add(f"union.{k}", lab, "VU", c, mm["union_model_us"][k] * CY,
                  src("modelled", "hbm_accelerator_model VERIFY_PARTS[6] - [1]", note="W19 model increment (verify P6 over P1); "
                      "the matched reference keeps it unchanged (an HBM-favourable lower bound)"),
                  op=f"union.{k}", elements=HBC[c]["elements"] + ["ot_dshbm_expert_union"], instances=HBC[c]["instances"])
        mark(n, "verify", un_hw)
    # ---- accept / commit + seed
    gdef["A"] = dict(label="accept / commit + seed of the next step", kind="accept", phase="accept")
    sp = J(HBM_DRAFT)["elements"]["seed"]["parts_us"]
    rest = mm["seed_commit_us"] - sum(sp.values())
    seed_hw = hw("built", "SM / SU / barrier of the AR path")
    for k, c, lab, gr in (("sm", "sm", "seed: main_proj (6 columns) on the SMs", "measured"),
                          ("local", "su", "seed: main_x gather + main_norm + 3 stages' wkv window rows", "measured"),
                          ("barrier", "barrier", "seed: barrier", "measured"),
                          ("collective", "coll", "seed: 1 collective (the record's remainder)", "apportioned"),
                          ("commit", "ctl", "accept / commit: compare, emit accepted tokens, roll back spec state", "measured")):
        us = rest if k == "collective" else sp[k]
        n = d.add(f"accept.{k}", lab, "A", c, us * CY,
                  src(gr, HBM_DRAFT, "elements.seed.parts_us" if k != "collective" else "seed_commit_us - sum(parts)",
                      note=f"seed_commit {mm['seed_commit_us']} us = parts {sp} + 1 collective"),
                  op=f"accept.{k}", elements=(MTP_CLASSES_EXTRA[1]["elements"] if c == "ctl" else HBC[c]["elements"]),
                  instances=(MTP_CLASSES_EXTRA[1]["instances"] if c == "ctl" else HBC[c]["instances"]))
        mark(n, "accept", hw("partial", "ot_dshbm_dspark_ctl (ctl_f2) and ot_hdc_accept (accept_a0) closed as blocks; "
                             "ot_dshbm_spec_state NOT adopted (spec3_s8 terminal: 2 mismatches; route positive) and the "
                             "accelerator is not qualified as a whole", evidence=HBM_CTL + " blocked.spec_state")
             if k == "commit" else seed_hw)
    total = d.chain_schedule()
    # HC mixes beside the layer body (exposed 0)
    first_of = {}
    for nid in d.order:
        first_of.setdefault(d.nodes[nid]["group"], nid)
    for k, n in enumerate(hcp):
        mo = re.search(r"([\d.]+) us beside a ([\d.]+) us body", n["how"])
        dur, body = float(mo.group(1)), float(mo.group(2))
        gid = "V." + gname(n)
        grp_nodes = [x for x in d.order if d.nodes[x]["group"] == gid]
        if n["node"].split(".")[-1] == "ffn":
            k0 = next((j for j, x in enumerate(grp_nodes) if d.nodes[x]["label"].startswith("su:hc_post")), None)
            anchor = grp_nodes[k0 + 1] if k0 is not None and k0 + 1 < len(grp_nodes) else grp_nodes[0]
        else:
            anchor = grp_nodes[0]
        nn = d.add(f"hcp{k:03d}", n["node"], gid, "hc", dur * CY, src("measured", "tools/dshbm_matched_reference.py mtp() walk P=6",
                   note=n["how"]), op="hcp", elements=HBC["hc"]["elements"], instances=HBC["hc"]["instances"], critical=False,
                   deps=[], start=d.nodes[anchor]["start"], kind="parallel")
        nn["layer"] = n["layer"]
        nn["slack"] = r1((body - dur) * CY)
        mark(nn, "verify")
    after = rp["upper"]["after"]
    exp_us = comp["MTP_step_us"] + sum(x["cycles_hi"] for x in rp["items"]) / CY
    assert abs(total / CY - exp_us) < 0.01, (total / CY, exp_us)
    phases = phase_spans(d, total)
    headline = dict(tok_s=after["MTP_tok_s"], us=round(exp_us, 3), cycles=r1(exp_us * CY), tau=tau,
                    mode=f"MTP (DSpark gamma 5, tau {tau}), position 1,048,575", ar_tok_s=after["AR_tok_s"],
                    mtp_over_ar=round(after["MTP_tok_s"] / after["AR_tok_s"], 3),
                    basis=f"{UNI} hbm_ds unified_candidate_contracts_rtl MTP step ({comp['MTP_step_us']} us, {comp['MTP_tok_s']} "
                          f"tok/s) + the 2026-10-08 re-price upper bound; step = draft + verify (P6 walk + expert union) + seed/commit "
                          f"(gate row {gate['MTP_row']}, {gate['MTP_step_us']} us)",
                    source=REPRICE + " hbm_ds.upper.after.MTP_tok_s", status="priced candidate (not a closed rate)",
                    gate_row=gate["MTP_row"])
    worst = max((g for g in gdef if g.startswith("V.L")), key=lambda g: sum(d.nodes[x]["cycles"] for x in d.order if d.nodes[x]["group"] == g))
    drill = dict(group=worst, why="the longest verify layer (6 positions on one weight fetch)")
    notes = [
        "One MTP step: draft (as-built DSpark draft on the SMs) -> verify (the 6 positions walk the layers together: one weight "
        "fetch, the MMA columns carry the positions; the SU, attention and collectives scale with the positions) + the routed-"
        "expert union increment -> accept / commit + the next step's seed.",
        f"Verify walk: tools/dshbm_matched_reference.py mtp() at P = 6 on the gate's MTP row {gate['MTP_row']} ({len(rows6)} "
        "operators, replayed in-process); the unified composition's MTP_step line effects are spread as in the AR view "
        "(the joint PQ/XMAP lever credits -77.1 us here vs -36.4 AR; W2_PACK credits 0 at MTP).",
        f"Rate = tau {tau} / step = {after['MTP_tok_s']:,.1f} tok/s (re-price upper bound; lower bound in reprice.json).",
        "Hatched: no closed hardware; dashed: a closed block not adopted / integrated (expert union, spec state).",
    ]
    rec = finish(d, headline, gdef, HBM_CLASSES + MTP_CLASSES_EXTRA[1:], drill, notes, tau=tau,
                 extra=dict(geometry=ar["geometry"]))
    rec.update(phases=phases, hw_summary=hw_summary(d),
               accounting=accounting(total, tau, ar["totals"]["cycles"], phases, row["tau_source"]))
    return rec


def qwen_mtp_note():
    v = J(QWEN_VERDICT)
    return dict(available=False, verdict=v["verdict"], source=QWEN_VERDICT,
                reason=f"AR only by the owner's decision (2026-10-05, {QWEN_VERDICT} verdict {v['verdict']}): the Qwen3-8B ROM is "
                       "compute-balanced (weight read rate = MAC rate), so a multi-position verify costs about as much per "
                       "position as an AR layer and DSpark measured below AR (best np3: "
                       f"{v['best']['speedup_vs_ar_upper']}-{v['best']['speedup_vs_ar_lower']}x AR). DSpark stays built and "
                       "exact but off; speculation pays only where the dominant per-token cost is shared across positions "
                       "(the DS ROM and the HBM accelerator).")


# ======================================================================================== geometry snapshots (views)
def geo_snapshot(key):
    """neutral geometry for the views' harness: {w, h, instances: [[name, kind, x, y, w, h, master]]} (y up)"""
    g = J(GEO)[key]
    ms = g["meta"].get("masters", {})
    return dict(schema="opentallas.token_path.geometry.v1", source=GEO + f" [{key}]", w=g["w"], h=g["h"],
                instances=[[r[5], g["kinds"][r[0]], r[1], r[2], r[3], r[4], ms.get(r[5], "")] for r in g["rects"]])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--viz-dir", type=Path, default=None, help="also write data/ + geometry snapshots for the views here")
    ap.add_argument("--only", default="qwen_rom,ds_rom,hbm_ds")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    fns = dict(qwen_rom=qwen, ds_rom=ds_rom, hbm_ds=hbm)
    mtps = dict(ds_rom=ds_rom_mtp, hbm_ds=hbm_mtp)
    index = []

    def write(name, rec):
        rec["inputs"] = {p: sha(p) for p in sorted({REPRICE, UNI, GEO})}
        p = a.out / f"{name}.json"
        p.write_text(json.dumps(rec, separators=(",", ":")) + "\n")
        if a.viz_dir:
            dd = a.viz_dir / "data"
            dd.mkdir(parents=True, exist_ok=True)
            shutil.copy(p, dd / p.name)
        return p

    for k in a.only.split(","):
        rec = fns[k]()
        mrec = mtps[k](rec) if k in mtps else None
        if mrec:
            t = mrec["totals"]
            rec["mtp"] = dict(available=True, file=f"{k}_mtp.json", tok_s=t["tok_s_published"], tau=t["tau"],
                              step_cycles=t["cycles"], per_accepted_cycles=t["per_accepted_cycles"])
            mrec["ar"] = dict(file=f"{k}.json", tok_s=rec["totals"]["tok_s_published"], cycles=rec["totals"]["cycles"])
            write(f"{k}_mtp", mrec)
            print(f"{k} MTP: step {t['cycles']:,.1f} cycles = {t['us']} us, tau {t['tau']} -> {t['tok_s']} tok/s (published "
                  f"{t['tok_s_published']}); per accepted {t['per_accepted_cycles']:,.1f} cycles; phases "
                  f"{[(x['id'], x['cycles']) for x in mrec['phases']]}; hw {mrec['hw_summary']}")
            for vk, vv in (mrec.get("mtp_variants") or {}).items():
                print(f"   {vk}: {vv['reproduces']}")
        else:
            rec["mtp"] = qwen_mtp_note()
        p = write(k, rec)
        t = rec["totals"]
        print(f"{k}: {t['cycles']:,.1f} cycles = {t['us']} us = {t['tok_s']} tok/s (published {t['tok_s_published']}); "
              f"{len(rec['nodes'])} nodes, {len(rec['critical_path'])} on the critical path, {len(rec['groups'])} groups")
        index.append(dict(design=k, title=rec["title"], file=p.name, tok_s=t["tok_s_published"], cycles=t["cycles"],
                          mtp=dict(rec["mtp"], reason=None) if mrec else rec["mtp"]))
        if a.viz_dir:
            gk = rec["geometry"]["key"]
            (a.viz_dir / "data" / f"geo_{k}.json").write_text(json.dumps(geo_snapshot(gk), separators=(",", ":")) + "\n")
    (a.out / "index.json").write_text(json.dumps(dict(schema="opentallas.token_path.index.v1", designs=index), indent=1) + "\n")
    if a.viz_dir:
        shutil.copy(a.out / "index.json", a.viz_dir / "data" / "index.json")


if __name__ == "__main__":
    main()
