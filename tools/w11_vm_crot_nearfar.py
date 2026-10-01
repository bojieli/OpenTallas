#!/usr/bin/env python3
"""W11 C_rotate: how often does an SU op need the FAR rotate path? (root request 2026-10-01)

C_rotate's fixed pipeline pays the hub's worst bank -> lane distance on every op (results/floorplan/
v41_vm_crot_stages.json: 42 extra cycles a dependent element op).  A variable-latency strip could charge each op only
the distance its accesses travel.  This tool measures, on the V4.1 programs, the distance each op's accesses need:

  geometry   W18b's compact hub (the stages record): bank column g (elements e with e mod 128 = g) row-aligned with
             lane-group tile g (lanes l with l mod 128 = g; tiles 0-63 in SU_W, 64-127 in SU_E, 4 columns x 16 rows a
             side, column 0 against the strip), in the strip half facing the tile's side.  An access of element e by
             lane l travels |row(e) - row(l)| x 433 um vertically, the tile's offset from the strip edge, and the strip
             half (+ the other half when e and l are on different sides): Manhattan, rectangle-bound.
  near       every access of the op is group-local (e = l mod 128): the row-aligned path (tile -> strip edge only).
  per op     read stages = 1 (macro register) + wire(max read distance) + 2 (rotate mux); write stages = wire(max
             write distance) + 2; extra = CR_LEAD + read + (write | CR_RES for a reduction).

Op sets (each with its layout as the unit lays it out today, VMD_NG = 0):
  vehicle_as_built   the reduced vehicle at position 7, the builder's default 32-alignment
  vehicle_a128       the same built with HDC_V41_VM_ALIGN=128 (aligned bases)
  full_shape_l0      the full-shape L0 program (results/rtl/hdc_v41x_fullshape_program_bind_rope_hbm.json, the
                     builder's 32-alignment), position 65,535
Per set: near ops, the per-op extra distribution, mean extra (variable latency) vs the fixed 42, ops that cannot be
near whatever the allocator does (gathered A, broadcast scalars, strides other than 0 / 1), and cross-half accesses.

Writes results/uarch/w11_vm_crot_nearfar.json.
    python3 tools/w11_vm_crot_nearfar.py
"""
from __future__ import annotations

import collections
import datetime
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import w11_vm_variant  # noqa: E402,F401  (VM-H / C_rotate sources and rules: rtl/w11crot)
import hdc_isa_v41 as I                    # noqa: E402
import rtl_hdc_v41x_vec_campaign as C      # noqa: E402
import w11_vm_h as H                       # noqa: E402

STAGES = ROOT / "results/floorplan/v41_vm_crot_stages.json"
OUT = ROOT / "results/uarch/w11_vm_crot_nearfar.json"
N, M, NG = 1024, 256, 128
MK24 = (1 << 24) - 1


def geometry():
    s = json.loads(STAGES.read_text())
    g = s["geometry"]
    tile = g["tile_um"]
    strip_w = g["strip_um"][0]
    gid = np.arange(NG)
    side = gid // 64
    j = gid % 64
    col, row = j % 4, j // 4
    edge = (col + 0.5) * tile                     # tile centre -> the strip edge it faces
    return s, dict(tile=tile, strip_w=strip_w, side=side, row=row, edge=edge)


def dist(geo, e_grp, l_grp):
    """Bank column e_grp (in the strip half facing its tile) -> lane tile l_grp, um."""
    v = np.abs(geo["row"][e_grp] - geo["row"][l_grp]) * geo["tile"]
    same = geo["side"][e_grp] == geo["side"][l_grp]
    h = geo["edge"][l_grp] + np.where(same, geo["strip_w"] / 2, geo["strip_w"])
    return v + h


def op_need(f, vm, geo):
    lay = C.layout(f, N, M)
    no, ni = f["nout"], f["nin"]
    idx = None
    if f["aind"]:
        cnt = ni if f["aind"] == I.IND_I else no
        idx = np.asarray(vm[f["aibase"]:f["aibase"] + cnt], dtype=np.int64)
    st = {}
    for s, name in zip("abcd", "ABCD"):
        if f[f"{s}src"] == I.SRC_VM:
            st[name] = C.addrs(f, s, no, ni, idx if s == "a" else None)
    if f["cpair"] and f["csrc"] == I.SRC_VM and "A" in st:
        st["C"] = st["A"] ^ 1
    if f["aind"]:
        o, i = np.meshgrid(np.arange(no), np.arange(ni), indexing="ij")
        st["G"] = (f["aibase"] + (i if f["aind"] == I.IND_I else o)).reshape(-1).astype(np.int64)
    if f["dst"] == I.DST_VM:
        st["E"] = C.out_addrs(f).astype(np.int64)
    rd = wr = 0.0
    near = {c: True for c in st}
    cross = collections.Counter()
    acc = collections.Counter()
    bcast = set()
    for oo, ii in lay["vecs"]:
        e = C.elem_index(f, oo, ii)
        lanes = H.phys_lanes(f, lay, oo, ii)
        lg = lanes % NG
        for cls, a in st.items():
            x = (a[e] & MK24)
            if len(x) > 1 and len(np.unique(x)) == 1:
                bcast.add(cls)
            eg = x % NG
            d = dist(geo, eg, lg)
            acc[cls] += len(x)
            cross[cls] += int(np.count_nonzero(geo["side"][eg] != geo["side"][lg]))
            if np.any(eg != lg):
                near[cls] = False
            if cls == "E":
                wr = max(wr, float(d.max()))
            else:
                rd = max(rd, float(d.max()))
    return dict(rd_um=rd, wr_um=wr, near=near, cross=cross, acc=acc, bcast=bcast, red=bool(f["red"]),
                gather=bool(f["aind"]), nv=lay["nv"], has_vm=bool(st))


def measure(ops, geo, p, reach):
    stg = lambda um: math.ceil(um / reach) if um > 0 else 0
    rows = []
    for tag, f, vm in ops:
        if f["nout"] == 0 or f["nin"] == 0 or C.layout(f, N, M)["bad"]:
            continue
        r = op_need(f, vm, geo)
        rd = 1 + stg(r["rd_um"]) + 2 + (p["CR_GX"] if r["gather"] else 0)
        wr = stg(r["wr_um"]) + 2
        tail = p["CR_RES"] if r["red"] else wr
        r["extra"] = p["CR_LEAD"] + rd + tail
        r["fixed_extra"] = p["CR_LEAD"] + p["CR_RD"] + (p["CR_GX"] if r["gather"] else 0) + \
            (p["CR_RES"] if r["red"] else p["CR_WR"])
        r["op_near"] = all(r["near"].values()) and not r["bcast"]
        rows.append(r)
    n = len(rows)
    cls_near = collections.Counter()
    cls_ops = collections.Counter()
    acc, cross = collections.Counter(), collections.Counter()
    for r in rows:
        for c, v in r["near"].items():
            cls_ops[c] += 1
            cls_near[c] += int(v)
        acc.update(r["acc"])
        cross.update(r["cross"])
    ext = np.array([r["extra"] for r in rows], dtype=float)
    fix = np.array([r["fixed_extra"] for r in rows], dtype=float)
    cannot = sum(1 for r in rows if r["gather"] or r["bcast"])
    hist = collections.Counter(int(x) for x in ext)
    return dict(
        ops=n, near_ops=sum(r["op_near"] for r in rows),
        near_share=round(sum(r["op_near"] for r in rows) / n, 4) if n else None,
        stream_near_share={c: round(cls_near[c] / cls_ops[c], 4) for c in sorted(cls_ops)},
        stream_ops={c: cls_ops[c] for c in sorted(cls_ops)},
        cross_half_access_share={c: round(cross[c] / acc[c], 4) for c in sorted(acc) if acc[c]},
        ops_never_near=dict(total=cannot, gathered=sum(1 for r in rows if r["gather"]),
                            broadcast_scalar=sum(1 for r in rows if r["bcast"])),
        variable_latency_mean_extra=round(float(ext.mean()), 3), fixed_mean_extra=round(float(fix.mean()), 3),
        vector_weighted=dict(variable=round(float((ext * [r["nv"] for r in rows]).sum() / sum(r["nv"] for r in rows)), 3)),
        extra_histogram={str(k): v for k, v in sorted(hist.items())},
        max_read_um=round(max(r["rd_um"] for r in rows), 1), max_write_um=round(max(r["wr_um"] for r in rows), 1))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    s, geo = geometry()
    p = s["rtl_parameters"]
    reach = s["basis"]["wire_reach_um"]
    sets = {}
    recs, _, _, meta = C.vehicle_records()
    sets["vehicle_as_built"] = [("vehicle", C.resolve(f0, dyn), np.asarray(vm, dtype=np.uint32))
                                for f0, dyn, vm, _ in recs]
    prev = os.environ.get("HDC_V41_VM_ALIGN")
    os.environ["HDC_V41_VM_ALIGN"] = "128"
    try:
        recs_a, _, _, _ = C.vehicle_records()
    finally:
        if prev is None:
            os.environ.pop("HDC_V41_VM_ALIGN")
        else:
            os.environ["HDC_V41_VM_ALIGN"] = prev
    sets["vehicle_a128"] = [("vehicle", C.resolve(f0, dyn), np.asarray(vm, dtype=np.uint32))
                            for f0, dyn, vm, _ in recs_a]
    import w11_vm_dist_spec as SP
    fs, _ = SP.full_shape_ops(65535)
    z = np.zeros(1 << 24, dtype=np.uint32)
    sets["full_shape_l0"] = [(t, f, z) for t, f in fs]
    out = {}
    for k, ops in sets.items():
        out[k] = measure(ops, geo, p, reach)
        print(k, json.dumps(out[k]), flush=True)
    rec = dict(
        schema="opentallas.uarch.w11_vm_crot_nearfar.v1",
        generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        vehicle_meta=meta, stages=p, reach_um=reach,
        near_path=dict(read=1 + math.ceil(max(geo["edge"] + geo["strip_w"] / 2) / reach) + 2,
                       write=math.ceil(max(geo["edge"] + geo["strip_w"] / 2) / reach) + 2,
                       op_extra=p["CR_LEAD"] + 2 * (math.ceil(max(geo["edge"] + geo["strip_w"] / 2) / reach) + 2) + 1),
        far_path=dict(read=p["CR_RD"], write=p["CR_WR"], op_extra=p["CR_LEAD"] + p["CR_RD"] + p["CR_WR"]),
        sets=out,
        source_sha256={r: sha(ROOT / r) for r in ("tools/w11_vm_crot_nearfar.py", "results/floorplan/v41_vm_crot_stages.json",
                                                  "tools/rtl_hdc_v41x_vec_campaign.py", "tools/w11_vm_h.py",
                                                  "tools/w11_vm_dist_spec.py", "tools/hdc_program_v41.py")})
    OUT.write_text(json.dumps(rec, indent=1) + "\n")
    print("near", rec["near_path"], "far", rec["far_path"])


if __name__ == "__main__":
    main()
