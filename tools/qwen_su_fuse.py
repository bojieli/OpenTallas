#!/usr/bin/env python3
"""Qwen ROM stream-unit operator fusion (dataflow level 1, AGENTS.md): the Qwen backend of W11's ISA-generic
chain-forming pass (tools/w11_su_fuse.py on claude/w11-fuse: View, form_chains -- one pass for both designs).

The Qwen unit (rtl/hdc/ot_hdc_vstream.sv, lanes from ot_hdc_stream.sv) lays element (o, i) of a stream op on
vector o * ceil(nin / SW) + i // SW, lane i % SW.  Streams: A always (VM unless a_src), B when the op reads it
(ma == AB, ad == NEGB, md), C when it reads it (mb != OFF, ad == C, mc); ROM-sourced streams are not VM reads.
Element addresses: base + DYN[x_d] + o * so + i * si.  Output: dst VM at d_base + ... ; dst KV is a region write.
A reduction's result (r_base + o * r_so) is a scalar result, never an element stream.

KR fields (same names and widths as W11's FUSE_FIELDS, appended after the fullshape row0 overlay bits 898-899 in
the Qwen 1024-bit word; tools/hdc_isa_qwen_fuse.py): kr_w 1, kr_wb 6, kr_r 4 (A, B, C, -), kr_rb 6, and the
reserved producer-side xkr 1, xkr_wb 6, xkr_lw 1, xkr_map 2, xkr_epi 4 (0).

CYCLES.  In this unit a KR read sits where the VM read sits and the consumer still waits for its producer's
drain (unit-level class register, full-drain SU->SU release): the KR saves VM element reads and writes (ports,
energy), about 0 cycles.  The overlap redesign that would save cycles is results/uarch/qwen_su_overlap_spec.md.

    python3 tools/qwen_su_fuse.py --tp 4 --out results/uarch/qwen_su_fuse_stats.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

KR_DEPTH = 64


def qwen_views(prog, dyn, SW, regions):
    import hdc_isa as I
    import w11_su_fuse as F
    out = []
    names = regions.names
    bases = regions.bases

    def region_of(a):
        return names[max(0, int(np.searchsorted(bases, a, side="right") - 1))]
    for k, f0 in enumerate(prog):
        f = {n: f0.get(n, 0) for n, _ in I.FIELDS}
        u = f["unit"]
        if u == I.UNIT_ME:
            rd = {region_of(f["me_xbase"] + dyn[f["me_d_xbase"]])}
            if f["me_wsrc"]:
                rd.add("KV")
            wr = {region_of(f["me_obase"] + dyn[f["me_d_obase"]])}
            out.append(F.View(su=False, reads=rd, writes=wr, tag=("ME", k)))
            continue
        if u != I.UNIT_SU:
            coll = f0.get("_coll")
            wr = {region_of(coll[1] * 16)} if coll else set()
            out.append(F.View(su=False, reads=set(wr), writes=wr, tag=("SEQ", k)))
            continue
        no = f["su_nout"]
        ni = f["su_nin"] + dyn[f["su_d_nin"]]
        if no == 0 or ni == 0:
            out.append(F.View(su=False, reads=set(), writes=set(), tag=("SU0", k)))
            continue
        nvo = -(-ni // SW)
        o = np.repeat(np.arange(no, dtype=np.int64), ni)
        i = np.tile(np.arange(ni, dtype=np.int64), no)
        vec = o * nvo + i // SW
        lane = i % SW

        def addrs(x):
            return f[f"{x}_base"] + dyn[f[f"{x}_d"]] + o * f[f"{x}_so"] + i * f[f"{x}_si"]
        streams, reads = {}, set()
        use_b = f["ma"] == I.MA_AB or f["ad"] == I.AD_NEGB or f["md"]
        use_c = f["mb"] != I.MB_OFF or f["ad"] == I.AD_C or f["mc"]
        for x, used in (("a", True), ("b", use_b), ("c", use_c)):
            if used and not f[f"{x}_src"]:
                a = addrs(x)
                streams[x] = a
                reads.add(region_of(int(a[0])))
        outa, writes = None, set()
        if f["dst"] == I.DST_VM:
            outa = addrs("d")
            writes.add(region_of(int(outa[0])))
        elif f["dst"] == I.DST_KV:
            writes.add("KV")
        res = (f["r_base"] + np.arange(no, dtype=np.int64) * f["r_so"]) if f["red"] else np.zeros(0, np.int64)
        out.append(F.View(su=True, skip=False, n=no * ni, nv=no * nvo, vw=SW, vec=vec, lane=lane,
                          pred=None, streams=streams, out=outa, res=res, reads=reads, writes=writes,
                          tag=("SU", k), bad=False))
    return out


def layer_program(tp, matrix_rows, post_scale_bases):
    os.environ["QWEN_O4_TP"] = str(tp)
    import hdc_program as P
    import hdc_qwen_fullshape_program as FP
    vm, _ = FP.vm_map()
    lay = FP.LayerZero(None, 0, matrix_rows)
    with FP.program_geometry(vm):
        prog = P.build_program(lay, layers=[0], embed=False, head=False, scale_bases=True)
        prog = FP.insert_post_tp_scales(prog, vm, post_scale_bases)
        prog = FP.split_collectives(prog)
        return prog, vm, lay, P


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", type=Path, required=True, help="a TP-4 layer image's layer0_rom.json")
    ap.add_argument("--tp", type=int, default=4)
    ap.add_argument("--su-width", type=int, default=64)
    ap.add_argument("--depth", type=int, default=KR_DEPTH)
    ap.add_argument("--positions", type=int, nargs="+", default=[0, 100, 8191])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    os.environ["QWEN_O4_TP"] = str(a.tp)
    import hdc_isa as I
    import w11_su_fuse as F
    I.SU_WIDTH = a.su_width
    m = json.loads(a.manifest.read_text())
    prog, vm, lay, P = layer_program(a.tp, m["matrix_layout"], m["post_tp_scale_bases"])
    import hdc_qwen_fullshape_program as FP
    regions = F.Regions(dict(vm, KV=1 << 26))
    vpp = []
    with FP.program_geometry(vm):
        for pos in a.positions:
            dyn = P.dyn_values(lay, token=0, pos=pos)
            vpp.append(qwen_views(prog, dyn, a.su_width, regions))
    edges, alloc, need, rej = F.form_chains(vpp, regions, a.depth)
    v0 = vpp[0]
    su = [k for k, v in enumerate(v0) if v.su]
    fused_reads = sum(n for n in edges.values())
    all_reads = sum(sum(len(s) for s in v0[k].streams.values()) for k in su)
    prods = {p for (p, c, s) in edges}
    vm_writes_saved = sum(v0[p].n for p in prods if p not in need and v0[p].out is not None)
    all_writes = sum(v0[k].n for k in su if v0[k].out is not None)
    chains = {}
    for (p, c, s) in sorted(edges):
        chains.setdefault(p, []).append((c, s))
    rec = dict(schema="opentallas.qwen-su-fuse.v1", tp=a.tp, su_width=a.su_width, kr_depth=a.depth,
               positions=a.positions, su_ops_per_layer=len(su),
               edges=[dict(producer=p, consumer=c, stream=s, elements=int(n)) for (p, c, s), n in sorted(edges.items())],
               kr_peak_entries=alloc["peak"], producers_keeping_vm_write=sorted(int(x) for x in need if x in prods),
               vm_element_reads_per_layer=int(all_reads), vm_element_reads_avoided=int(fused_reads),
               vm_element_writes_per_layer=int(all_writes), vm_element_writes_avoided=int(vm_writes_saved),
               rejects=dict(rej),
               cycles_note=("about 0 cycles in the as-built unit: KR read/write sit where the VM read/write sit and "
                            "dependents still drain (results/uarch/qwen_su_overlap_spec.md)"),
               pass_core="tools/w11_su_fuse.py (claude/w11-fuse)",
               sources={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                        for p in ("tools/qwen_su_fuse.py", "tools/hdc_qwen_fullshape_program.py", "tools/hdc_program.py")},
               manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("su_ops_per_layer", "kr_peak_entries", "vm_element_reads_per_layer",
                                          "vm_element_reads_avoided", "vm_element_writes_per_layer",
                                          "vm_element_writes_avoided", "rejects")}, indent=1))
    print("edges", [(e["producer"], e["consumer"], e["stream"]) for e in rec["edges"]])


if __name__ == "__main__":
    main()
