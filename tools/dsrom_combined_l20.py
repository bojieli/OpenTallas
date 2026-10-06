#!/usr/bin/env python3
"""CLAUDE DS-INTEGRATION: the DS-ROM combined-lever L20 bench.

One DeepSeek-V4.1 L20 layer stage (position 1,048,575, rank-0 die) with every adopted-or-exact recovery lever ON
together, bit-exact against the golden, as a lever matrix (all-ON / all-OFF / one-at-a-time).  No new simulator:
the per-unit benches (tools/dsrom_su_*.py, tools/dsrom_field_spine.py) are re-invoked unchanged from ONE pinned
source snapshot; this tool adds the checks a per-unit bench cannot make.

    static   (any host, light)  the lever source sets and the matrix's source unions: every module defined once per
             configuration (a duplicate definition with a different body is an integration conflict), the lever
             records' source pins against the snapshot, two lever records claiming one composition node, and the
             q-element x field-spine structural compatibility.  -> W/static.json
    edges    (compute host)     the L20 stage's data edges between the fused units, on the shared golden case set
             (su_cases.pkl): the producer's checked output bits == the consumer's input bits, so units proven exact
             alone are exact chained.  Includes a negative control (one flipped word must be caught).  -> W/edges.json
    field    (compute host)     the v9 field spine on L20 (every node, every region of the rank-0 die, bit-exact):
             PQ 0, PQ 1, PQ 0 + the DS q-element (QX 9, segtree5) through the pair FILE SWAP
             rtl/v41die/swap/ot_v41_pair_pq_w17w10_qelem.sv, and PQ 1 + q-element (expected NOT buildable).
             -> W/field_<cfg>/..., W/field.json
    units    (compute host)     collect the per-unit bench runs (driven by the shell plan in the record README) into
             rows.  -> W/units.json
    compose  (compute host)     the lever matrix through tools/dsrom_1m_allmeasured.compose (the timing authority,
             imported unchanged): all-OFF, all-ON, each lever alone and all-ON minus each lever.  -> W/compose.json
    record                      join everything -> results/rtl/dsrom_recovery_20261004/combined/combined.json.
                                EXIT 1 on any mismatch, unresolved conflict or missing run.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pickle
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
LEVERS_DIR = ROOT / "results/rtl/dsrom_recovery_20261004/levers"
OUT = ROOT / "results/rtl/dsrom_recovery_20261004/combined"
LA6 = ROOT / "results/rtl/dsrom_recovery_20261004/su_fusion_takeover/la6_inputs"
SWAP_PAIR = ROOT / "rtl/v41die/swap/ot_v41_pair_pq_w17w10_qelem.sv"


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p) -> str:
    p = Path(p)
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


# ------------------------------------------------------------------------------------------------ lever source sets
SU_LIB = ["rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
          "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fastfp.sv",
          "rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv",
          "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv"]


def lever_sources():
    """{lever: [repo-relative source paths of the RTL the lever's measurement elaborated]} (synthesizable RTL only;
    test benches and DPI stand-ins excluded), from the owning tools' own lists."""
    import dsrom_su_hcpost as H
    import dsrom_su_softmax as SX
    import dsrom_su_swiglu as SW
    import dsrom_su_routeract as RA
    import dsrom_1m_field as F1
    import dsrom_field_spine as FS
    r = lambda ps: sorted({rel(p) for p in ps})
    norm_common = ["rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fpu.sv",
                   "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
                   "rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/v41/ot_hdc_fsqrt.sv", "rtl/hdc/v41/ot_hdc_fdiv.sv",
                   "rtl/hdc/v41/ot_hdc_softplus.sv", "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv", "rtl/hdc/v41/ot_hdc_actquant.sv",
                   "rtl/hdc/v41x/ot_dsrom_aq12.sv", "rtl/hdc/v41x/ot_dsrom_divc.sv", "rtl/hdc/ot_hdc_fastfp.sv",
                   "rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
                   "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv"]
    field_die = [p for p in FS.DIE]
    return dict(
        su_hcpost=r(H.RTL),
        su_norm=sorted(set(norm_common)) + [rel(LA6 / "ot_dsrom_su_norm.sv")],
        su_swiglu=sorted(set(SU_LIB + list(SW.RTL) + [SW.ADD6, "rtl/hdc/v41/ot_hdc_actquant.sv"])),
        su_softmax=sorted(set(SX.RTL)),
        su_routeract=sorted(set(rel(p) for p in RA.SP_SRCS)) if hasattr(RA, "SP_SRCS") else
        sorted(set(SU_LIB + ["rtl/hdc/v41/ot_hdc_fsqrt.sv", "rtl/hdc/v41/ot_hdc_fdiv.sv",
                             "rtl/hdc/v41x/ot_hdc_v41x_spshort.sv", rel(RA.SP_RTL)])),
        field_spine=r(field_die + F1.RTL + [ROOT / "rtl/v41rom/ot_v41_rom_elem_pq_w10.sv",
                                            ROOT / "rtl/v41rom/ot_v41_elem_pq_tags.sv"]),
        qelem=r([p for p in field_die if p.name != "ot_v41_pair_pq_w17w10.sv"] + [SWAP_PAIR] + F1.RTL + F1.QRTL +
                [ROOT / "rtl/v41rom/ot_v41_rom_elem_pq_w10.sv", ROOT / "rtl/v41rom/ot_v41_elem_pq_tags.sv"]),
    )


# the 0.9 GHz SU vehicle that every lever-OFF SU node runs on (results/rtl/dsrom_1m_allmeasured_20261004/su.json)
BASELINE_SU = ["rtl/hdc/v41x/ot_hdc_v41x_sfu.sv", "rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv",
               "rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv", "rtl/hdc/v41x/ot_hdc_v41x_vec_red.sv",
               "rtl/hdc/v41x/ot_hdc_v41x_vec.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fpu.sv",
               "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_sfu.sv",
               "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fastfp_lat.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv",
               "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/v41/ot_hdc_fsqrt.sv",
               "rtl/hdc/v41/ot_hdc_fdiv.sv", "rtl/hdc/v41/ot_hdc_softplus.sv"]
# the 1.2 GHz FILE SWAP: same modules, same latency at every LAT the SU instantiates (ALAT 3/4, MLAT 3/4/5), bit-exact
# (c464d70f1, rtl/test/tb_su_fp32_f12.sv); a die that carries any fused unit names the swap die-wide.
SWAPS = {"rtl/hdc/ot_hdc_fastfp_lat.sv": "rtl/hdc/ot_hdc_fastfp_lat_f12.sv",
         "rtl/v41die/ot_v41_pair_pq_w17w10.sv": rel(SWAP_PAIR)}

SU_LEVERS = ("su_hcpost", "su_norm", "su_swiglu", "su_softmax", "su_routeract")
FIELD_LEVERS = ("field_spine", "qelem")
ALL = SU_LEVERS + FIELD_LEVERS
# lever records that are ALTERNATIVES for one set of nodes (the composition must apply at most one of each group)
ALTERNATIVES = [("field", "field_spine", "field_spine_pq")]

_MOD = re.compile(r"^\s*module\s+(\w+)", re.M)
_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


def modules(path: Path) -> dict:
    """{module name: sha256 of its comment-stripped, whitespace-normalised body}."""
    txt = _COMMENT.sub("", path.read_text(errors="ignore"))
    out = {}
    starts = [(m.group(1), m.start()) for m in _MOD.finditer(txt)]
    for i, (name, s) in enumerate(starts):
        e = txt.find("endmodule", s)
        body = re.sub(r"\s+", " ", txt[s:e if e >= 0 else len(txt)])
        out[name] = hashlib.sha256(body.encode()).hexdigest()
    return out


def union_check(srcs: list) -> dict:
    defs = {}
    for s in srcs:
        for m, h in modules(ROOT / s).items():
            defs.setdefault(m, []).append((s, h))
    dup = {m: v for m, v in defs.items() if len(v) > 1}
    conflicts = {m: [s for s, _ in v] for m, v in dup.items() if len({h for _, h in v}) > 1}
    same = {m: [s for s, _ in v] for m, v in dup.items() if len({h for _, h in v}) == 1}
    return dict(n_files=len(srcs), n_modules=len(defs), conflicts=conflicts, identical_duplicates=same)


def config_sources(on, srcs, swap=True):
    """Source union of one matrix configuration: the ON levers' sources + the baseline SU (any SU node whose lever
    is OFF still runs on it) + the field vehicle the config implies."""
    s = set()
    for lv in on:
        s |= set(srcs[lv])
    if any(lv not in on for lv in SU_LEVERS):
        s |= set(BASELINE_SU)
    if "field_spine" not in on and "qelem" not in on:
        s |= set(srcs["field_spine"])
    if "qelem" in on:
        s -= set(srcs["field_spine"]) - set(srcs["qelem"])
    if swap and any(lv in on for lv in SU_LEVERS):
        s = {SWAPS.get(p, p) if p == "rtl/hdc/ot_hdc_fastfp_lat.sv" else p for p in s}
    return sorted(s)


def matrix_configs():
    cfgs = {"all_off": (), "all_on": ALL}
    for lv in ALL:
        cfgs[f"only_{lv}"] = (lv,)
        cfgs[f"all_on_minus_{lv}"] = tuple(x for x in ALL if x != lv)
    return cfgs


def pin_currency(records: dict) -> dict:
    out = {}
    for lv, paths in records.items():
        rows = []
        for p in paths:
            f = ROOT / p
            if not f.exists():
                rows.append(dict(record=p, missing=True))
                continue
            d = json.loads(f.read_text())
            pins = {}
            def walk(x):
                if isinstance(x, dict):
                    for k, v in x.items():
                        if k in ("source_sha256", "rtl_sha256") and isinstance(v, dict):
                            pins.update({kk: vv for kk, vv in v.items() if isinstance(vv, str)})
                        else:
                            walk(v)
                elif isinstance(x, list):
                    for v in x[:200]:
                        walk(v)
            walk(d)
            drift = {}
            for k, h in pins.items():
                kp = ROOT / k
                if not k.startswith(("rtl/", "tools/", "physical/")) or not kp.exists():
                    continue
                cur = sha(kp)
                if cur != h:
                    la6 = LA6 / kp.name
                    drift[k] = dict(pinned=h, current=cur,
                                    matches_la6_preserved_copy=la6.exists() and sha(la6) == h)
            rows.append(dict(record=p, pins=len(pins), drifted=drift))
        out[lv] = rows
    return out


LEVER_RECORDS = dict(
    su_hcpost=["results/rtl/dsrom_recovery_20261004/su_hcpost/runs/run_ng256_w33_23_m5a5_h.json"],
    su_norm=["results/rtl/dsrom_recovery_20261004/su_norm/measure.json",
             "results/rtl/dsrom_recovery_20261004/su_fusion_takeover/la6_transport_terminal.json"],
    su_swiglu=["results/rtl/dsrom_recovery_20261004/su_swiglu/r4/run_rtl_W64_NB32_m5a4q5_swiglu.json",
               "results/rtl/dsrom_recovery_20261004/su_swiglu/r4/run_rtl_NB32_m5a4q5_z_quant.json"],
    su_softmax=["results/rtl/dsrom_recovery_20261004/su_softmax/r2/run_lph16e54.json"],
    su_routeract=["results/rtl/dsrom_recovery_20261004/su_routeract/sim.json"],
    field_spine=["results/rtl/dsrom_field_spine_20261004/field_baseline.json",
                 "results/rtl/dsrom_field_spine_20261004/field_pq.json"],
    qelem=["results/rtl/dsrom_field_qelem_20261005/field_qelem.json"],
)


def node_claims() -> dict:
    claims, per = {}, {}
    for f in sorted(LEVERS_DIR.glob("*.json")):
        r = json.loads(f.read_text())
        if r.get("schema") != "opentallas.dsrom-recovery.lever.v1":
            continue
        per[r["lever"]] = dict(verdict=r.get("verdict"), exact=r.get("exact"), n_nodes=len(r.get("nodes", {})))
        for k in r.get("nodes", {}):
            claims.setdefault(k, []).append(r["lever"])
    alt = {x for g in ALTERNATIVES for x in g}
    overlaps = {}
    for k, ls in claims.items():
        if len(ls) < 2:
            continue
        # alternatives (field / field_spine / field_spine_pq) are allowed only if the composition applies one
        kind = "alternatives" if set(ls) <= alt else "CONFLICT"
        overlaps.setdefault(kind, {})[k] = ls
    return dict(levers=per, overlaps={k: dict(n=len(v), sample=dict(list(v.items())[:6]))
                                      for k, v in overlaps.items()})


def cmd_static(a):
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    srcs = lever_sources()
    per_lever = {lv: union_check(s) for lv, s in srcs.items()}
    cfgs = matrix_configs()
    mat = {}
    for name, on in cfgs.items():
        noswap = union_check(config_sources(on, srcs, swap=False))
        withswap = union_check(config_sources(on, srcs, swap=True))
        mat[name] = dict(levers_on=list(on), conflicts_without_swap=noswap["conflicts"],
                         conflicts=withswap["conflicts"], n_files=withswap["n_files"],
                         n_modules=withswap["n_modules"])
    # the norm source on main vs the measured LA6 lever
    norm_main = ROOT / "rtl/hdc/v41x/ot_dsrom_su_norm.sv"
    norm_note = dict(main_sha256=sha(norm_main), la6_sha256=sha(LA6 / "ot_dsrom_su_norm.sv"),
                     same=sha(norm_main) == sha(LA6 / "ot_dsrom_su_norm.sv"),
                     main_modules=sorted(modules(norm_main)), la6_modules=sorted(modules(LA6 / "ot_dsrom_su_norm.sv")),
                     tool_main_vs_la6_same=sha(ROOT / "tools/dsrom_su_norm.py") == sha(LA6 / "dsrom_su_norm.py"),
                     tb_main_vs_la6_same=sha(ROOT / "rtl/test/tb_dsrom_su_norm.sv") == sha(LA6 / "tb_dsrom_su_norm.sv"))
    # q-element x PQ: the PQ pair has no QELEM path; the swap adds it for PQ 0 only
    pq_pair = (ROOT / "rtl/v41die/ot_v41_pair_pq_w17w10.sv").read_text()
    qx = dict(pq_pair_has_qelem="QELEM" in _COMMENT.sub("", pq_pair),
              plain_pair_has_qelem="QELEM" in _COMMENT.sub("", (ROOT / "rtl/v41die/ot_v41_pair_w17w10.sv").read_text()),
              q_element_has_pq="PQ" in re.findall(r"parameter\s+integer\s+(\w+)", _COMMENT.sub(
                  "", (ROOT / "rtl/v41rom/ot_v41_rom_elem_q_qx_w10.sv").read_text())),
              swap=rel(SWAP_PAIR))
    rec = dict(schema="opentallas.dsrom-combined.static.v1", generated_utc=now(), lever_sources=srcs,
               per_lever=per_lever, matrix=mat, file_swaps=SWAPS, norm_source=norm_note, qelem_x_pq=qx,
               pin_currency=pin_currency(LEVER_RECORDS), composition_node_claims=node_claims())
    unresolved = {k: v["conflicts"] for k, v in mat.items() if v["conflicts"]}
    rec["unresolved_conflicts"] = unresolved
    (work / "static.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("static: configs", len(mat), "unresolved", {k: list(v) for k, v in unresolved.items()})
    print("static: without the f12 swap", {k: list(v["conflicts_without_swap"]) for k, v in mat.items()
                                           if v["conflicts_without_swap"]})
    print("static: norm main == LA6:", norm_note["same"], " q-element x PQ:", qx)
    return 1 if unresolved else 0


# ------------------------------------------------------------------------------------------------------- edges
def _init(c):
    return {int(a): b for a, b in c["init"]}


def _chk(c, i=0):
    return c["checks"][i][1], c["checks"][i][2]


def _chk_named(c, name):
    return [x for x in c["checks"] if x[0] == name][0][2]


def bits32(x):
    import numpy as np
    return np.asarray(x).astype(np.float32).view(np.uint32) if np.asarray(x).dtype != np.uint32 else np.asarray(x)


def edge_list(cs):
    """(name, producer -> consumer description, producer bits, consumer bits) on the L20 stage."""
    import numpy as np
    E = []
    L = "L20"
    g = lambda n: cs[f"{L}.{n}"]
    # the layer's residual (4 x 5120) enters attn.hc_mix, attn.hc_pre_norm and attn.hc_post identically
    r_mix, r_pre, r_post = _init(g("attn.hc_mix"))[64], _init(g("attn.hc_pre_norm"))[64], _init(g("attn.hc_post"))[64]
    E.append(("residual_in: attn.hc_pre_norm == attn.hc_mix", bits32(r_mix), bits32(r_pre)))
    E.append(("residual_in: attn.hc_post == attn.hc_pre_norm", bits32(r_pre), bits32(r_post)))
    # attn.hc_post (su_hcpost) output h -> ffn.hc_mix / ffn.hc_pre_norm (su_norm hc) / ffn.hc_post residual
    _, h = _chk(g("attn.hc_post"))
    E.append(("su_hcpost(attn) h -> su_norm(ffn.hc_pre_norm) residual", bits32(h), bits32(_init(g("ffn.hc_pre_norm"))[64])))
    E.append(("su_hcpost(attn) h -> ffn.hc_mix residual", bits32(h), bits32(_init(g("ffn.hc_mix"))[64])))
    E.append(("su_hcpost(attn) h -> su_hcpost(ffn) residual", bits32(h), bits32(_init(g("ffn.hc_post"))[64])))
    # hc_mix (baseline SU + Sinkhorn) -> the hc_pre weights and the hc_post post / comb.  The golden's mix order
    # (tools/hdc_golden_v41.Model.layer): a block's hc_mixes give (pre for the NEXT block, post and comb for this
    # block), so ffn.hc_pre collapses with attn.hc_mix's pre and attn.hc_pre with the previous layer's ffn pre
    # (L19, not in the case set).  comb: the hc_mix case stops at the Sinkhorn unit's input exp(comb - max); the
    # golden's own row-softmax + eps + (iters) column/row normalisation (hc_eps 1e-6, 20 iterations, the released
    # config) is applied here with its own arithmetic functions and compared to the hc_post operand.
    import hdc_golden_v41 as G
    F32 = np.float32
    hc_eps, iters = F32(1e-6), 20
    for blk in ("attn", "ffn"):
        mix = g(f"{blk}.hc_mix")
        ck = {c[0]: c for c in mix["checks"]}
        post_init = _init(g(f"{blk}.hc_post"))
        E.append((f"{blk}.hc_mix post -> su_hcpost({blk}) post", bits32(ck["post"][2]), bits32(post_init[25680])))
        e = np.asarray(ck["exp(comb - max): the Sinkhorn unit's input"][2]).view(F32).reshape(4, 4)
        rs = G.seqsum([e[:, k] for k in range(4)])
        cm = G.add(G.div(e, rs[:, None]), hc_eps)

        def cols(c):
            cs_ = G.seqsum([c[j, :] for j in range(4)])
            return G.div(c, G.add(cs_, hc_eps)[None, :])

        def rows(c):
            r_ = G.seqsum([c[:, k] for k in range(4)])
            return G.div(c, G.add(r_, hc_eps)[:, None])
        cm = cols(cm)
        for _ in range(iters - 1):
            cm = cols(rows(cm))
        E.append((f"{blk}.hc_mix exp(comb-max) -> golden Sinkhorn -> su_hcpost({blk}) comb",
                  bits32(np.asarray(cm, F32).reshape(-1)), bits32(post_init[25664])))
    E.append(("attn.hc_mix pre -> su_norm(ffn.hc_pre_norm) pre (golden mix order: next block)",
              bits32(_chk_named(g("attn.hc_mix"), "pre")), bits32(_init(g("ffn.hc_pre_norm"))[20544])))
    # router_act (su_routeract, the die's 96 rows) -> ffn.route input (all 4 dies' 384 rows, die 0 first)
    ra = g("ffn.router_act")
    _, sp = _chk(ra)
    rin = bits32(_init(g("ffn.route"))[64])
    E.append(("su_routeract sqrt(softplus) (die 0, 96 rows) -> ffn.route input rows 0..95", bits32(sp), rin[:len(sp)]))
    # ffn.route weights -> su_swiglu route_w (the 6 routed weights)
    sw = g("ffn.swiglu")
    E.append(("ffn.route weights -> su_swiglu route_w", bits32(_chk_named(g("ffn.route"), "route weights")),
              bits32(_init(sw)[sw["ops"][0]["bbase"]])))
    return E


def cmd_edges(a):
    import numpy as np
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    d = pickle.loads(Path(a.cases).read_bytes())
    cs = {c["name"]: c for c in d["cases"]}
    rows = []
    for name, p, c in edge_list(cs):
        ok = len(p) > 0 and len(p) == len(c) and bool(np.array_equal(p, c))
        nbad = int(np.count_nonzero(p != c)) if len(p) == len(c) else None
        rows.append(dict(edge=name, words=int(len(c)), producer_words=int(len(p)), equal=ok, mismatched=nbad,
                         first_mismatch=(int(np.flatnonzero(p != c)[0]) if nbad else None)))
        print(("PASS " if ok else "FAIL ") + name, len(p), len(c), nbad)
    # negative control: one flipped bit on the first edge must be caught by the same comparison
    name, p, c = edge_list(cs)[2]
    q = p.copy()
    q[len(q) // 2] ^= np.uint32(1)
    neg = dict(edge=name, flipped_word=int(len(q) // 2), caught=not bool(np.array_equal(q, c)))
    rec = dict(schema="opentallas.dsrom-combined.edges.v1", generated_utc=now(), cases=rel(a.cases),
               cases_sha256=sha(a.cases), snapshots_sha256=d.get("snapshots_sha256"), rows=rows,
               negative_control=neg, all_equal=all(r["equal"] for r in rows) and neg["caught"])
    (work / "edges.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("EDGES", "PASS" if rec["all_equal"] else "FAIL", "negative caught", neg["caught"])
    return 0 if rec["all_equal"] else 1


# ------------------------------------------------------------------------------------------------------- field
FIELD_CFGS = {
    "pq0": dict(pq=0, qelem=0, plan="base"),
    "pq1": dict(pq=1, qelem=0, plan="pq"),
    "pq0_q9": dict(pq=0, qelem=9, plan="base"),
    "pq1_q9": dict(pq=1, qelem=9, plan="pq"),        # expected NOT buildable (negative structural control)
}


def cmd_field(a):
    import dsrom_1m_field as F1
    import dsrom_field_spine as FS
    cfg = FIELD_CFGS[a.cfg]
    work = Path(a.work).resolve() / f"field_{a.cfg}"
    work.mkdir(parents=True, exist_ok=True)
    plan = Path(a.plan_base if cfg["plan"] == "base" else a.plan_pq)
    if cfg["qelem"]:
        defs = work / "qelem_defines.sv"
        defs.write_text(f"`define OT_PAIR_PQ_QELEM 1\n`define OT_PAIR_PQ_QXV {cfg['qelem']}\n")
        FS.DIE = [defs] + [SWAP_PAIR if p.name == "ot_v41_pair_pq_w17w10.sv" else p for p in FS.DIE] + list(F1.QRTL)
        FS.SOURCES = sorted(set(FS.SOURCES) | set(F1.QRTL) | {SWAP_PAIR})
    status = dict(cfg=a.cfg, **cfg, plan_dir=str(plan))
    if not (work / "build" / "tb").exists():
        ns = argparse.Namespace(work=work, pq=cfg["pq"], gap=12, guard=180, gslack=6, jobs=a.jobs)
        try:
            FS.cmd_build(ns)
        except SystemExit as e:
            status.update(build="FAILED", build_error=str(e)[-1500:])
            (work / "status.json").write_text(json.dumps(status, indent=1) + "\n")
            print("field", a.cfg, "BUILD FAILED")
            return 2
    status["build"] = "ok"
    rcs = {}
    for mode in ("phase", "node"):          # every L20 phase alone (as-built rule), then nodes back to back
        ns = argparse.Namespace(work=work, plan_dir=plan, mode=mode, single_only=False, layers="20", regions="",
                                only_nodes="", sample=0, keep=False, positions=1, force=False, jobs=a.jobs)
        rcs[mode] = FS.cmd_run(ns)
    status["run_rc"] = rcs
    (work / "status.json").write_text(json.dumps(status, indent=1) + "\n")
    return 0 if not any(rcs.values()) else 1


def field_summary(work: Path, cfg_name: str, plan_dir: Path):
    """L20 nodes of one field configuration: exactness of every phase x region run and every node's back-to-back
    run, and the node time by the as-built rule of tools/dsrom_field_spine.py (sum over the node's phases of
    go -> idle + 1, + go -> last row write of the last; each phase at the max over the die's regions; cycles, no
    floorplan wire)."""
    import dsrom_field_spine as FS
    w = work / f"field_{cfg_name}"
    st = json.loads((w / "status.json").read_text()) if (w / "status.json").exists() else {}
    if st.get("build") != "ok":
        return dict(cfg=cfg_name, build=st.get("build", "missing"), build_error=st.get("build_error"))
    plan = json.loads((plan_dir / "plan.json").read_text())
    g = FS.groups_all(plan)
    nodes, bad, missing = [], 0, 0
    for key, phs in sorted(g.items()):
        if key[0] != 20:
            continue
        stats = [FS.phase_stats(w, key, i, ph) for i, ph in enumerate(phs)]
        ok = all(x["exact"] for x in stats)
        missing += sum(x["regions"] - x["regions_run"] for x in stats)
        tot = None
        if ok:
            tot = sum(x["go_to_idle_cycles"] + 1 for x in stats[:-1]) + stats[-1]["go_to_last_row_cycles"]
        node_ok = None
        if len(phs) >= 2:
            regs = sorted({r for ph in phs for r in ph["regions"]})
            rs = [FS.load(w, key, reg) for reg in regs]
            missing += sum(r is None for r in rs)
            node_ok = all(r is not None and r["pass_"] for r in rs)
            ok = ok and node_ok
        bad += not ok
        nodes.append(dict(node=f"L{key[0]}.{key[1]}", stage=key[2], phases=len(phs),
                          regions=len({r for ph in phs for r in ph["regions"]}), exact=ok, node_runs_exact=node_ok,
                          rows_checked=sum(x["rows_checked"] for x in stats),
                          rows_mismatched=sum(x["rows_mismatched"] for x in stats), total_cycles=tot))
    return dict(cfg=cfg_name, build="ok", params=json.loads((w / "build" / "build.json").read_text()).get("params"),
                nodes=nodes, n_nodes=len(nodes), n_bad=bad, missing_runs=missing,
                exact=(bad == 0 and missing == 0 and bool(nodes)))


# ------------------------------------------------------------------------------------------------------- units
def _rows_json(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def cmd_units(a):
    """Collect the per-unit bench outputs of the shell plan (README) into rows; L20 rows decide the stage."""
    w = Path(a.work)
    rows, missing = [], []
    static = json.loads((w / "static.json").read_text()) if (w / "static.json").exists() else {}
    current = {lv: all(not r.get("missing") and not any(k.startswith("rtl/") for k in r.get("drifted", {}))
                       for r in rows_) for lv, rows_ in static.get("pin_currency", {}).items()}
    sources = {}

    def pick(unit, sub, pattern, committed):
        """A fresh run under W/<sub> if present, else the committed record when its RTL pins are current on this
        snapshot (owner rule 2026-10-06: no same-source replay of an already-PASS run)."""
        rs = sorted((w / sub).glob(pattern))
        if rs:
            sources[unit] = dict(kind="fresh", files=[rel(x) for x in rs])
            return rs
        if current.get(unit):
            rs = [ROOT / c for c in committed if (ROOT / c).exists()]
            sources[unit] = dict(kind="committed, RTL pins current", files=[rel(x) for x in rs])
            return rs
        sources[unit] = dict(kind="missing (no fresh run, committed RTL pins not current)")
        return []

    def add(unit, case, exact, cycles=None, **kw):
        rows.append(dict(unit=unit, case=case, l20=case.startswith("L20"), exact=bool(exact), cycles=cycles, **kw))

    # su_hcpost
    rs = pick("su_hcpost", "hcpost", "run_*.json", LEVER_RECORDS["su_hcpost"])
    for p in rs:
        for r in (_rows_json(p) or {}).get("rows", []):
            add("su_hcpost", r["name"], r.get("pass_") and r.get("errors") == 0 and r.get("fault") == 0,
                r.get("cycles"), errors=r.get("errors"), run=rel(p))
    missing += [] if rs else ["su_hcpost"]
    # su_norm (LA6): per-run json under norm/
    rs = pick("su_norm", "norm", "run_*.json", [])
    for p in rs:
        d = _rows_json(p) or {}
        for r in d.get("rows", []) if isinstance(d.get("rows"), list) else []:
            errs = {k: r.get(k) for k in r if k.startswith("err")}
            add(f"su_norm.{d.get('variant', p.stem)}", r.get("case") or r.get("name"),
                (r.get("ok", r.get("pass_", r.get("exact"))) is True) and not any(errs.values()) and not r.get("fault"),
                r.get("q_last") or r.get("y_last") or r.get("cycles"), errors=errs, fp=d.get("fp"), run=rel(p))
    missing += [] if rs else ["su_norm"]
    # su_softmax
    rs = pick("su_softmax", "softmax", "run_*.json", LEVER_RECORDS["su_softmax"])
    for p in rs:
        for r in (_rows_json(p) or {}).get("rows", []):
            add("su_softmax", r["name"], r.get("exact") and not r.get("fault"), r.get("nodes_cycles"),
                errors={k: r.get(k) for k in ("err_max", "err_es", "err_den", "err_e", "err_o")}, run=rel(p))
    missing += [] if rs else ["su_softmax"]
    # su_swiglu (swiglu + z_quant)
    rs = pick("su_swiglu", "swiglu", "run_*.json", LEVER_RECORDS["su_swiglu"])
    for p in rs:
        for r in (_rows_json(p) or {}).get("rows", []):
            add("su_swiglu", r["case"], r.get("exact"), r.get("cycles"),
                errors={k: r.get(k) for k in ("a_errors", "q_errors", "rope_errors")}, run=rel(p))
    missing += [] if rs else ["su_swiglu"]
    # su_routeract
    rs = pick("su_routeract", "routeract", "sim.json", LEVER_RECORDS["su_routeract"])
    p = rs[0] if rs else w / "routeract" / "sim.json"
    d = _rows_json(p) if rs else None
    if d:
        for impl, v in (d.get("spsqrt") or {}).items():
            for case, r in ((v.get("runs") or {}).items() if isinstance(v, dict) else []):
                if isinstance(r, dict) and "pass" in r:
                    add(f"su_routeract.{impl}", "L20.die" if case == "die_L20" else case,
                        r.get("pass") and r.get("errors") == 0 and r.get("faults") == 0, r.get("span0"),
                        errors=r.get("errors"), run=rel(p))
    else:
        missing.append("su_routeract")
    l20 = [r for r in rows if r["l20"]]
    rec = dict(schema="opentallas.dsrom-combined.units.v1", generated_utc=now(), row_sources=sources, rows=rows,
               missing_units=missing,
               n_rows=len(rows), n_bad=sum(not r["exact"] for r in rows), n_l20=len(l20),
               l20_units=sorted({r["unit"].split(".")[0] for r in l20}),
               all_exact=bool(rows) and all(r["exact"] for r in rows) and not missing)
    (w / "units.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("UNITS", "PASS" if rec["all_exact"] else "FAIL", rec["n_rows"], "rows,", rec["n_bad"], "bad, L20 rows",
          rec["n_l20"], "missing", missing)
    return 0 if rec["all_exact"] else 1


# ----------------------------------------------------------------------------------------------------- compose
COMPOSE_LEVERS = ("field_spine_pq", "su_hcpost", "su_routeract", "su_norm", "su_swiglu", "su_softmax")


def cmd_compose(a):
    """Lever matrix through the timing authority, on its own adoption code path (apply_levers): each configuration
    composes from a scratch copy of levers/*.json in which the matrix levers ON read verdict ADOPT and the OFF ones
    read OFF_FOR_MATRIX; every other record (draft, head, router, hop, field) is copied unchanged.  The committed
    records are never modified."""
    import shutil
    import dsrom_1m_allmeasured as AM
    recs = {lv: json.loads((LEVERS_DIR / f"{lv}.json").read_text()) for lv in COMPOSE_LEVERS}
    adopted_main = {lv for lv, r in recs.items() if r.get("verdict") == "ADOPT"}

    def run(on, label):
        tmp = ROOT / ".combined_matrix" / label          # under ROOT: the authority's rel() needs repo paths
        if tmp.exists():
            shutil.rmtree(tmp)
        (tmp / "levers").mkdir(parents=True)
        for f in LEVERS_DIR.glob("*.json"):
            r = json.loads(f.read_text())
            if r.get("lever") in COMPOSE_LEVERS:
                r["verdict"] = "ADOPT" if r["lever"] in on else "OFF_FOR_MATRIX"
            (tmp / "levers" / f.name).write_text(json.dumps(r))
        ns = argparse.Namespace(rec=AM.REC, out=tmp / "composition.json", baseline="recovery",
                                recovery=tmp, window="s81", hop_tier="light_fec")
        AM.compose(ns, write_output=True)
        excluded, cands = [lv for lv in COMPOSE_LEVERS if lv not in on], []
        d = json.loads(ns.out.read_text())
        cp = d.get("critical_path", [])
        l20 = [c for c in cp if str(c.get("node", "")).startswith("L20.")]
        keep = dict(AR_us=d.get("AR_us"), AR_tok_s=d.get("AR_tok_s"), MTP_tok_s=(d.get("MTP") or {}).get("MTP_tok_s"),
                    II_us=(d.get("MTP") or {}).get("II_us"), L20_on_critical_path_us=round(sum(c.get("us", 0) for c in l20), 4),
                    L20_nodes=len(l20), applied=[x["lever"] for x in (d.get("info", {}).get("levers", {}) or {}).get("applied", [])])
        return dict(levers_on=list(on), excluded=list(excluded), candidates=cands, **keep,
                    output=rel(ns.out))

    m = {"all_off": run((), "all_off"), "all_on": run(COMPOSE_LEVERS, "all_on")}
    for lv in COMPOSE_LEVERS:
        m[f"only_{lv}"] = run((lv,), f"only_{lv}")
        m[f"all_on_minus_{lv}"] = run(tuple(x for x in COMPOSE_LEVERS if x != lv), f"minus_{lv}")
    base = m["all_off"].get("AR_us")
    if base:
        sep = sum(base - m[f"only_{lv}"]["AR_us"] for lv in COMPOSE_LEVERS)
        joint = base - m["all_on"]["AR_us"]
        m["additivity"] = dict(sum_of_single_lever_savings_us=round(sep, 3), all_on_saving_us=round(joint, 3),
                               interaction_us=round(joint - sep, 3))
    (Path(a.work) / "compose.json").write_text(json.dumps(dict(schema="opentallas.dsrom-combined.compose.v1",
                                                               generated_utc=now(), adopted_on_main=sorted(adopted_main),
                                                               matrix=m), indent=1) + "\n")
    print(json.dumps({k: (v.get("AR_us"), v.get("MTP_tok_s")) if isinstance(v, dict) and "AR_us" in v else v
                      for k, v in m.items()}, indent=0))
    return 0


# ------------------------------------------------------------------------------------------------------ record
def crosscheck(w: Path, parts: dict, field: dict) -> list:
    """Run-vs-composition at L20: (1) every L20 node a matrix lever owns: the lever record's us vs the all-ON
    composition's applied value (+ its measured CDC) -- an application or double-charge error shows here; (2) the
    unit runs' L20 cycles vs the lever record; (3) the field: PQ 0 fresh vs the committed v9 baseline (harness
    reproduction) and PQ 0 + q-element vs PQ 0 (the q-element's cycle effect, not in any lever record)."""
    out = []
    comp = Path(w) / "compose_all_on.json"
    pat = {}
    allon = (parts.get("compose") or {}).get("matrix", {}).get("all_on", {})
    cpath = ROOT / allon["output"] if allon.get("output") else None
    if cpath and cpath.exists():
        d = json.loads(cpath.read_text())
        for x in d.get("patches", []):
            pat[x["node"]] = x
    for lv in COMPOSE_LEVERS:
        r = json.loads((LEVERS_DIR / f"{lv}.json").read_text())
        for k, v in r.get("nodes", {}).items():
            n = "L20." + k[2:] if k.startswith("*.") else k
            if not n.startswith("L20.") or n not in pat:
                if n.startswith("L20."):
                    out.append(dict(kind="lever node absent from the all-ON composition", lever=lv, node=n))
                continue
            got = pat[n].get("measured_us")
            if got is None or abs(got - v["us"]) > 5e-4:
                out.append(dict(kind="composition applies a different value than the lever record", lever=lv, node=n,
                                lever_us=v["us"], composition_us=got, source=pat[n].get("source", "")[:120]))
            cdc = pat[n].get("cdc_measured_us")
            if cdc and v.get("kind") == "fused_fast":
                out.append(dict(kind="CDC still charged on a fused 1.2 GHz node with all levers ON", lever=lv, node=n,
                                cdc_us=cdc))
    # unit cycles vs lever records (1.2 GHz units; routeract's short lane runs at 0.9 GHz)
    unit_node = {"su_hcpost": {"L20.attn.hc_post": ["L20.attn.hc_post"], "L20.ffn.hc_post": ["L20.ffn.hc_post"]}}
    for row in (parts.get("units") or {}).get("rows", []):
        if not row["l20"]:
            continue
        nodes = unit_node.get(row["unit"], {}).get(row["case"])
        if nodes and isinstance(row.get("cycles"), (int, float)):
            us = row["cycles"] / 1.2e3
            lev = sum(pat.get(n, {}).get("measured_us") or 0 for n in nodes)
            if abs(us - lev) > 5e-4:
                out.append(dict(kind="unit run vs composition", unit=row["unit"], case=row["case"], run_us=round(us, 5),
                                composition_us=lev))
    # field
    base = json.loads((ROOT / "results/rtl/dsrom_field_spine_20261004/field_baseline.json").read_text())
    bmap = {n["node"]: n.get("total_cycles") for n in base.get("node_summary", [])}
    f0 = {n["node"]: n for n in (field.get("pq0") or {}).get("nodes", [])}
    fq = {n["node"]: n for n in (field.get("pq0_q9") or {}).get("nodes", [])}
    for n, x in sorted(f0.items()):
        if bmap.get(n) is not None and x.get("total_cycles") != bmap[n]:
            out.append(dict(kind="field PQ 0 fresh run != committed v9 baseline (harness)", node=n,
                            fresh_cycles=x.get("total_cycles"), committed_cycles=bmap[n]))
        if n in fq and fq[n].get("total_cycles") is not None and x.get("total_cycles") is not None:
            dlt = fq[n]["total_cycles"] - x["total_cycles"]
            if dlt:
                out.append(dict(kind="q-element changes the L20 field node (not in any lever record or composition)",
                                node=n, pq0_cycles=x["total_cycles"], pq0_q9_cycles=fq[n]["total_cycles"],
                                delta_cycles=dlt))
    return out


def cmd_record(a):
    w = Path(a.work)
    out = Path(a.out) if a.out else OUT
    out.mkdir(parents=True, exist_ok=True)
    parts = {}
    for n in ("static", "edges", "units", "compose"):
        p = w / f"{n}.json"
        parts[n] = json.loads(p.read_text()) if p.exists() else None
    field = {c: field_summary(w, c, Path(a.plan_base if FIELD_CFGS[c]["plan"] == "base" else a.plan_pq))
             for c in FIELD_CFGS}
    fails = []
    if not parts["edges"] or not parts["edges"]["all_equal"]:
        fails.append("edges")
    if not parts["units"] or not parts["units"]["all_exact"]:
        fails.append("units")
    for c, s in field.items():
        if c == "pq1_q9":
            if s.get("build") == "ok":
                fails.append("field pq1_q9 built (expected NOT buildable)")
            continue
        if not s.get("exact"):
            fails.append(f"field {c}")
    if parts["static"] and parts["static"]["unresolved_conflicts"]:
        fails.append("static conflicts")
    xc = crosscheck(w, parts, field)
    rec = dict(schema="opentallas.dsrom-combined.record.v1", generated_utc=now(), source_commit=a.source_commit,
               verdict="PASS" if not fails else "FAIL", failures=fails, run_vs_composition=xc, field=field, **parts)
    (out / "combined.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("RECORD", rec["verdict"], fails)
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("static", "edges", "field", "units", "compose", "record"))
    ap.add_argument("--work", required=True)
    ap.add_argument("--cases")
    ap.add_argument("--cfg", choices=tuple(FIELD_CFGS))
    ap.add_argument("--plan-base", default="/srv/opentallas/scratch-overflow/claude/dsrom-allmeas/field/work2")
    ap.add_argument("--plan-pq", default="/mnt/epyc1-scratch/claude/dsrom-field-spine/planv")
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--out")
    ap.add_argument("--source-commit", default="")
    a = ap.parse_args()
    return dict(static=cmd_static, edges=cmd_edges, field=cmd_field, units=cmd_units, compose=cmd_compose,
                record=cmd_record)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
