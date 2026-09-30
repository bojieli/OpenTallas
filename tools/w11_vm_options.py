#!/usr/bin/env python3
"""W11: price three vector-memory organisations of the V4.1 die on one basis (root request 2026-09-30).

  H  HYBRID      lane-group banks (the spec's 128 groups x 2 banks x 6 replicas) plus a compiler / layout rule:
                 every SU operand / output base is 128-aligned and packed rows that cross groups are banned (such
                 an op is re-laid with each row in its own 128-lane-aligned slot).  Per-row scalars (B / D
                 broadcasts) ride the controller's broadcast tree (su_bcast 4) after a fetch from the owning group
                 to the tree root; a rotate network serves only the residual non-local classes and its latency is
                 charged only to the ops that use it.
  C  CENTRAL     the banked VM as one block beside the SU lane array, a full operand crossbar between them: every
                 SU op pays the bank <-> lane distance each way plus the crossbar levels.
  A  FULL        lane-group banks with rotate + broadcast networks on every read class and a lane -> group
     VM_DIST     network on the element write.

Every option serves every client: SU 4 operand reads + gather index + 1 element write (1,024 lanes), the
matvec x gather (64 elements / cycle) and result scatter (128 / cycle), the collective write (4 x 512 b), and
the HE x (8 ports) / QE 32-element / expert-index / XU reads, which share the x-gather path (class X).

Measured here (H): the reduced vehicle's 2,649 stream ops (tools/rtl_hdc_v41x_vec_campaign.vehicle_records,
position 7, with the VM image each op sees) laid out at N = 1,024 / M = 256: per access class the share of
element accesses whose element is not in the lane's group -- as laid out today, after base alignment, and after
the packed-row ban -- the broadcast share, the vector-count cost of the ban, and per op which networks it needs.

Priced (all options): register stages per client and per SU op class (tools/uarch_model.wire_cycles at 0.92 ns /
0.76 ps/um on the geometry below, mux levels at MUX_LEVELS_PER_STAGE a cycle), SRAM macros / mm2 (the spec
record), network logic mm2 from mux2 / flop counts at the hardened SU light lane's measured cell areas, block
footprint, and the token rate at 1M context through tools/uarch_model: AR = evaluate(d)["tokens_s"], MTP =
tau / (v41_verify_T(d, 6, 1) + draft) as speculation_rows() (tau 3.649).  The design dicts derive from
PRESETS["proposal"] with the option's stages; the SU per-op latency is carried by two design keys this tool
that evaluate() prices on the SU vector / reduce nodes (su_op_extra_cycles, su_red_extra_cycles; a graph hook adds
them for a uarch_model without them).

Writes results/uarch/w11_vm_options.json.
    python3 tools/w11_vm_options.py [--out PATH]
"""
from __future__ import annotations

import argparse
import collections
import os
import copy
import datetime
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa_v41 as I                    # noqa: E402
import rtl_hdc_v41x_vec_campaign as C      # noqa: E402
import uarch_model as U                    # noqa: E402
import w11_vm_h as H                       # noqa: E402

OUT = ROOT / "results/uarch/w11_vm_options.json"
SPEC = ROOT / "results/floorplan/v41_vm_dist_spec.json"
LANE_REC = "results/physical_abi3/asap7/hdc/v41x/w11/vec_light1024r/physical.json"
LANE_REC_BRANCH = "claude/w11-dedicated-units"
N, M, NG = 1024, 256, 128
PERIOD_PS, PS_PER_UM = 920.0, 0.76
MUX_LEVELS_PER_STAGE = 8      # ASSUMED unless --mux-levels / --rot-record: 2:1 mux levels in one 0.92 ns stage
ROT_LEVELS = int(math.log2(N))                 # a 1,024-lane rotate (log shifter): 10 levels
BENES_LEVELS = 2 * int(math.log2(N)) - 1       # an arbitrary permutation (gathers): 19 levels
XBAR_LEVELS = int(math.log2(N))                # a 1,024:1 mux tree per output: 10 levels
W = 32


def stages(um: float) -> int:
    return U.wire_cycles(um, 1e12 / PERIOD_PS, PS_PER_UM)


def mux_stages(levels: int) -> int:
    return math.ceil(levels / MUX_LEVELS_PER_STAGE)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---- H: the vehicle's stream ops under the layout rule ---------------------------------------------------------
CLS = ("A", "B", "C", "D", "G", "E")


def align(f):
    g = dict(f)
    for k in ("abase", "bbase", "cbase", "dbase", "obase", "aibase"):
        g[k] = f[k] - (f[k] % NG)
    return g


def class_addrs(f, g, vm):
    """Per class the element addresses (o, i order) with g's bases; index values read at f's aibase."""
    no, ni = f["nout"], f["nin"]
    idx = None
    if f["aind"]:
        cnt = ni if f["aind"] == I.IND_I else no
        idx = np.asarray(vm[f["aibase"]:f["aibase"] + cnt], dtype=np.int64)
    out = {}
    for s, name in zip("abcd", "ABCD"):
        if f[f"{s}src"] == I.SRC_VM:
            out[name] = C.addrs(g, s, no, ni, idx if s == "a" else None)
    if f["cpair"] and f["csrc"] == I.SRC_VM and "A" in out:
        out["C"] = out["A"] ^ 1
    if f["aind"]:
        cnt = ni if f["aind"] == I.IND_I else no
        o, i = np.meshgrid(np.arange(no), np.arange(ni), indexing="ij")
        out["G"] = (g["aibase"] + (i if f["aind"] == I.IND_I else o)).reshape(-1).astype(np.int64)
    if f["dst"] == I.DST_VM:
        out["E"] = C.out_addrs(g).astype(np.int64)
    return out


def tally(vecs, f, st):
    """Per class: elements, non-local elements, broadcast elements (all lanes of a row... one address a vector)."""
    el, rem, bc = collections.Counter(), collections.Counter(), collections.Counter()
    for lanes, e in vecs:
        for cls, a in st.items():
            x = a[e] & ((1 << 24) - 1)
            el[cls] += len(x)
            if len(x) > 1 and len(np.unique(x)) == 1:
                bc[cls] += len(x)          # one element to every lane: the broadcast path, not a network
                continue
            rem[cls] += int(np.count_nonzero((x % NG) != (lanes % NG)))
    return el, rem, bc


def measure_h(ops):
    tot = {k: collections.Counter() for k in ("elements", "remote_asis", "remote_aligned", "remote_h", "bcast")}
    nv_asis = nv_h = 0
    per_op = []
    banned = aligned_fixed = 0
    for tag, f, vm in ops:
        if f["nout"] == 0 or f["nin"] == 0:
            continue
        lay = C.layout(f, N, M)
        if lay["bad"]:
            continue
        vw = lay["vw"]
        # the physical lane of each live element (dead lanes of a slot are skipped, not compacted)
        vec0 = [(H.phys_lanes(f, lay, oo, ii), C.elem_index(f, oo, ii)) for oo, ii in lay["vecs"]]
        st_raw = class_addrs(f, f, vm)
        g = align(f)
        st_al = class_addrs(f, g, vm)
        el, r_asis, bc = tally(vec0, f, st_raw)
        _, r_al, bc_al = tally(vec0, f, st_al)
        vecs_h, r_h, nv = vec0, r_al, len(vec0)
        multi = lay["packed"] and lay["nsh"] > 0
        if multi and sum(r_al.values()) > 0:
            # the ban: a row per 128-lane-aligned slot (a slot of max(S, 128) lanes; rows per vector = vw / slot)
            slot = max(lay["S"], NG)
            per_vec = max(1, vw // slot)
            no_f = f["nout"]
            vh = []
            for o0 in range(0, no_f, per_vec):
                oo, ii, ln = [], [], []
                for k in range(per_vec):
                    o = o0 + k
                    if o >= no_f:
                        break
                    oo.append(np.full(f["nin"], o)), ii.append(np.arange(f["nin"])), ln.append(k * slot + np.arange(f["nin"]))
                oo, ii, ln = np.concatenate(oo), np.concatenate(ii), np.concatenate(ln)
                vh.append((ln, C.elem_index(f, oo, ii)))
            _, r_b, _ = tally(vh, f, st_al)
            if sum(r_b.values()) < sum(r_al.values()):
                vecs_h, r_h, nv = vh, r_b, len(vh)
                banned += 1
        if sum(r_asis.values()) and not sum(r_al.values()):
            aligned_fixed += 1
        for c in el:
            tot["elements"][c] += el[c]
            tot["remote_asis"][c] += r_asis[c]
            tot["remote_aligned"][c] += r_al[c]
            tot["remote_h"][c] += r_h[c]
            tot["bcast"][c] += bc_al[c]
        nv_asis += len(vec0)
        nv_h += nv
        per_op.append(dict(red=bool(f["red"]), bcast=sorted(c for c in bc_al if bc_al[c]),
                           residual=sorted(c for c in r_h if r_h[c]),
                           residual_aligned=sorted(c for c in r_al if r_al[c]),
                           gather=bool(f["aind"]), vectors=len(vec0), vectors_h=nv))
    cls = [c for c in CLS if tot["elements"][c]]
    share = lambda k: {c: round(tot[k][c] / tot["elements"][c], 4) for c in cls}  # noqa: E731
    n_ops = len(per_op)
    return dict(
        ops=n_ops, vectors_as_laid=nv_asis, vectors_h=nv_h, vector_ratio=round(nv_h / nv_asis, 4),
        ops_fixed_by_alignment_alone=aligned_fixed, ops_relaid_by_ban=banned,
        elements={c: tot["elements"][c] for c in cls},
        remote_share_as_laid=share("remote_asis"), remote_share_aligned=share("remote_aligned"),
        remote_share_h=share("remote_h"), broadcast_share=share("bcast"),
        residual_elements_h={c: tot["remote_h"][c] for c in cls},
        residual_elements_aligned={c: tot["remote_aligned"][c] for c in cls},
        ops_needing_rotate=sum(1 for p in per_op if p["residual"]),
        ops_needing_rotate_by_class=dict(collections.Counter(c for p in per_op for c in p["residual"])),
        ops_needing_rotate_aligned_only=sum(1 for p in per_op if p["residual_aligned"]),
        ops_needing_rotate_by_class_aligned_only=dict(collections.Counter(c for p in per_op
                                                                          for c in p["residual_aligned"])),
        ops_with_broadcast=sum(1 for p in per_op if p["bcast"]),
        reduce_ops=sum(1 for p in per_op if p["red"]),
        gather_ops=sum(1 for p in per_op if p["gather"]),
    ), per_op


# ---- geometry, networks and stages --------------------------------------------------------------------------
def lane_cells():
    """Cell areas of the hardened SU light lane (the density basis)."""
    txt = subprocess.run(["git", "-C", str(ROOT), "show", f"{LANE_REC_BRANCH}:{LANE_REC}"], capture_output=True,
                         text=True)
    p = ROOT / LANE_REC
    r = json.loads(p.read_text() if p.exists() else txt.stdout)
    m = r["place_and_route"]["metrics"]
    comb_um2 = (m["standard_cell_area_um2"] - m["sequential_area_um2"]) / (m["standard_cell_count"] -
                                                                            m["sequential_cell_count"])
    flop_um2 = m["sequential_area_um2"] / m["sequential_cell_count"]
    return dict(record=LANE_REC, record_ref=LANE_REC_BRANCH if not p.exists() else "worktree",
                comb_cell_um2=round(comb_um2, 4), flop_um2=round(flop_um2, 4),
                utilization=m["utilization_fraction"], lane_cell_um2=m["standard_cell_area_um2"],
                lane_core_um2=m["core_area_um2"])


def net_area(kind, n_stage_regs, cells):
    """mm2 of cells and of footprint for one 1,024-lane x 32-bit network of `kind`."""
    comb = {"rotate": N * W * ROT_LEVELS, "benes": N * W * BENES_LEVELS, "crossbar": N * (N - 1) * W,
            "bcast": 2 * N * W // W}[kind]      # a scalar broadcast: ~2 buffers a leaf lane
    flops = N * W * n_stage_regs if kind != "bcast" else W * 2 * n_stage_regs
    um2 = comb * cells["comb_cell_um2"] + flops * cells["flop_um2"]
    return dict(kind=kind, comb_cells=comb, flops=flops, cell_mm2=um2 / 1e6, footprint_mm2=um2 / 1e6 / 0.5)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--limit", type=int, default=0, help="first N vehicle ops only (a smoke test; not a record)")
    ap.add_argument("--mux-levels", type=int, default=0,
                    help="measured 2:1 mux levels a 0.92 ns stage (from the rotate network's hardening)")
    ap.add_argument("--mux-basis", default="", help="the record(s) the measured mux levels come from")
    a = ap.parse_args()
    global MUX_LEVELS_PER_STAGE
    if a.mux_levels:
        MUX_LEVELS_PER_STAGE = a.mux_levels
    spec = json.loads(SPEC.read_text())
    cells = lane_cells()

    # ---- H measurement
    recs, _, _, meta = C.vehicle_records()
    ops = [("vehicle", C.resolve(f0, dyn), np.asarray(vm, dtype=np.uint32)) for f0, dyn, vm, _ in recs]
    if a.limit:
        ops = ops[:a.limit]
    hm, per_op = measure_h(ops)
    print("H", json.dumps(hm), flush=True)
    # the builder's alignment rule (HDC_V41_VM_ALIGN=128) and the vector unit's per-op decision (option H RTL)
    prev = os.environ.get("HDC_V41_VM_ALIGN")
    os.environ["HDC_V41_VM_ALIGN"] = "128"
    try:
        recs_a, _, _, meta_a = C.vehicle_records()
    finally:
        if prev is None:
            os.environ.pop("HDC_V41_VM_ALIGN")
        else:
            os.environ["HDC_V41_VM_ALIGN"] = prev
    ops_a = [("vehicle", C.resolve(f0, dyn), np.asarray(vm, dtype=np.uint32)) for f0, dyn, vm, _ in recs_a]
    if a.limit:
        ops_a = ops_a[:a.limit]
    def rule_ops_of(ops_):
        out = []
        for tag, f, vm in ops_:
            if f["nout"] == 0 or f["nin"] == 0 or H.layout_h(f, N, M)["bad"]:
                continue
            out.append(dict(flags=H.rule(f, N, M), red=bool(f["red"]), ew=f["dst"] == I.DST_VM))
        return out
    hchk = H.check(ops_a, N, M)
    hchk.pop("unsafe")
    print("H rule (vehicle, aligned)", hchk, flush=True)
    # the full-shape L0 program (results/rtl/hdc_v41x_fullshape_program_bind_rope_hbm.json, bound at the
    # builder's 32-alignment: an upper bound on H's networks), the basis of the full-shape model's keys
    import w11_vm_dist_spec as SP
    fs_ops, _ = SP.full_shape_ops(65535)
    zvm = np.zeros(1 << 24, dtype=np.uint32)
    fs_ops = [(t, f, zvm) for t, f in fs_ops]
    hchk_fs = H.check(fs_ops, N, M)
    hchk_fs.pop("unsafe")
    print("H rule (full-shape L0)", hchk_fs, flush=True)
    rule_ops = rule_ops_of(fs_ops)
    rule_ops_vehicle = rule_ops_of(ops_a)

    # ---- geometry basis: the spec record's SU + VM block (macros at area, lane / VM logic at 50 %)
    fp, geo, tr = spec["footprint"], spec["geometry"], spec["trees"]
    sram_mm2 = spec["macros"]["total_mm2"]
    macros = spec["macros"]["total"]
    UT = 0.5                                                           # the spec's logic utilisation
    lanes_mm2 = fp["per_group"]["lanes_logic_um2"] * NG / 1e6 / UT   # lane cells (the spec's) at 50 %
    vmlog_mm2 = fp["per_group"]["vm_logic_um2"] * NG / 1e6 / UT
    macro_mm2_placed = fp["per_group"]["macro_um2"] * NG / 1e6
    blk0 = fp["block_mm2"]
    assert abs(blk0 - (lanes_mm2 + vmlog_mm2 + fp["per_group"]["macro_um2"] * NG / 1e6)) < 0.05, "spec block basis"
    W0, H0 = fp["block_w_um"], fp["block_h_um"]
    bcast = 4                           # the controller's broadcast tree (root-accepted su_bcast_stages)

    def dist_geometry(extra_mm2):
        s = math.sqrt((blk0 + extra_mm2) / blk0)
        Wd, Hd = W0 * s, H0 * s
        return dict(block_mm2=blk0 + extra_mm2, w_um=Wd, h_um=Hd, scale=s,
                    x_gather_um=tr["x_gather"]["distance_um"] * s, ret_scatter_um=tr["ret_scatter"]["distance_um"] * s,
                    coll_um_at_port=tr["ret_scatter"]["distance_um"] * s,
                    coll_um_w1=tr["coll_write"]["distance_um"] * s,
                    su_results_um=tr["su_results"]["distance_um"] * s,
                    rotate_um=Wd + Hd,                     # worst group <-> lane pair: corner to corner
                    scalar_fetch_um=(Wd + Hd) / 2)         # owning group -> the broadcast tree's root (centre)

    options = {}

    # ---- A: full VM_DIST
    def price_A():
        g = dist_geometry(0.0)
        for _ in range(3):                       # the network's own area grows the block: iterate
            rot = stages(g["rotate_um"]) + mux_stages(ROT_LEVELS)
            ben = stages(g["rotate_um"]) + mux_stages(BENES_LEVELS)
            nets = [net_area("rotate", rot, cells) for _ in "ABCDGE"] + [net_area("benes", ben, cells)] + \
                   [net_area("bcast", stages(g["scalar_fetch_um"]) + bcast, cells) for _ in "BD"]
            net_fp = sum(x["footprint_mm2"] for x in nets)
            g = dist_geometry(net_fp)
        scal = stages(g["scalar_fetch_um"]) + bcast
        cl = dict(x_gather=stages(g["x_gather_um"]), ret_scatter=stages(g["ret_scatter_um"]),
                  coll_write=stages(g["coll_um_at_port"]), coll_write_from_w1_hub=stages(g["coll_um_w1"]),
                  su_results=stages(g["su_results_um"]), he_qe_xu_expert_reads="= x_gather (class X)")
        su = dict(control_broadcast=bcast, unit_stride_read=rot, scalar_read=max(rot, scal), gather_read=ben,
                  element_write=rot, reduce_result=cl["su_results"])
        vec_extra = bcast + rot + rot                  # a dependent op: its operands in, its elements out
        red_extra = bcast + rot + cl["su_results"]
        return dict(geometry=g, networks=nets, network_cell_mm2=sum(x["cell_mm2"] for x in nets),
                    network_footprint_mm2=net_fp, clients=cl, su_op_class_stages=su,
                    su_op_extra_cycles=vec_extra, su_red_extra_cycles=red_extra, su_issue_ratio=1.0)

    # ---- H: hybrid
    def price_H(ban):
        rkey = "residual" if ban else "residual_aligned"
        n_res_cls = sorted(c for c, v in hm["residual_elements_h" if ban else "residual_elements_aligned"].items() if v)
        g = dist_geometry(0.0)
        for _ in range(3):
            rot = stages(g["rotate_um"]) + mux_stages(ROT_LEVELS)
            ben = stages(g["rotate_um"]) + mux_stages(BENES_LEVELS)
            nets = [net_area("rotate", rot, cells) for c in n_res_cls if c != "G"]
            if hm["gather_ops"]:
                nets.append(net_area("benes", ben, cells))
            nets += [net_area("bcast", stages(g["scalar_fetch_um"]) + bcast, cells) for _ in "BD"]
            net_fp = sum(x["footprint_mm2"] for x in nets)
            g = dist_geometry(net_fp)
        scal = stages(g["scalar_fetch_um"])            # to the controller tree's root; the tree itself is shared
        cl = dict(x_gather=stages(g["x_gather_um"]), ret_scatter=stages(g["ret_scatter_um"]),
                  coll_write=stages(g["coll_um_at_port"]), coll_write_from_w1_hub=stages(g["coll_um_w1"]),
                  su_results=stages(g["su_results_um"]), he_qe_xu_expert_reads="= x_gather (class X)")
        # per op: the networks it needs (measured), averaged separately over reductions and element ops
        ext = {True: [], False: []}
        for p in per_op:
            x = bcast
            if p["bcast"]:
                x += scal
            reads = [c for c in p[rkey] if c != "E"]
            if p["gather"] and "A" in reads:
                x += ben
            elif reads:
                x += rot
            if p["red"]:
                x += cl["su_results"]
            elif "E" in p[rkey]:
                x += rot
            ext[p["red"]].append(x)
        su = dict(control_broadcast=bcast, local_read=0, scalar_read=scal, residual_rotate_read=rot,
                  gather_read=ben, local_element_write=0, residual_rotate_write=rot, reduce_result=cl["su_results"],
                  residual_classes=n_res_cls)
        return dict(geometry=g, networks=nets, network_cell_mm2=sum(x["cell_mm2"] for x in nets),
                    network_footprint_mm2=net_fp, clients=cl, su_op_class_stages=su,
                    su_op_extra_cycles=round(float(np.mean(ext[False])), 3),
                    su_red_extra_cycles=round(float(np.mean(ext[True])), 3),
                    su_op_extra_basis="mean over the vehicle's element ops / reductions of the stages each needs",
                    su_issue_ratio=hm["vector_ratio"] if ban else 1.0,
                    layout_rule="bases 128-aligned; packed cross-group rows banned (re-laid one row a 128-lane slot)"
                    if ban else "bases 128-aligned only; packed rows kept (their residual rides the rotate network)")

    # ---- C: central banked VM with a full crossbar
    def price_C(kind):
        sL = math.sqrt(lanes_mm2 * 1e6)                                   # lane array square (50 % utilisation)
        nets = [net_area(kind, 0, cells) for _ in "ABCDGE"]
        for _ in range(3):
            vm_mm2 = macro_mm2_placed + vmlog_mm2 + sum(x["footprint_mm2"] for x in nets)
            dV = vm_mm2 * 1e6 / sL                                        # the VM strip's depth beside the array
            lane_um = sL + sL / 2 + dV                                    # farthest bank -> farthest lane
            lv = XBAR_LEVELS if kind == "crossbar" else ROT_LEVELS
            one_way = stages(lane_um) + mux_stages(lv)
            nets = [net_area(kind, one_way, cells) for _ in "ABCDGE"]
            if kind == "rotate":
                nets[4] = net_area("benes", stages(lane_um) + mux_stages(BENES_LEVELS), cells)
        port_um = dV + sL / 2                                              # farthest bank -> VM port (die side)
        cl = dict(x_gather=stages(port_um), ret_scatter=stages(port_um), coll_write=stages(port_um),
                  su_results=stages(sL / 2 + dV), he_qe_xu_expert_reads="= x_gather (class X)")
        gth = one_way if kind == "crossbar" else stages(lane_um) + mux_stages(BENES_LEVELS)
        su = dict(control_broadcast=bcast, operand_read=one_way, gather_read=gth, element_write=one_way,
                  reduce_result=cl["su_results"])
        geo_c = dict(lane_array_mm2=lanes_mm2, lane_side_um=sL, vm_block_mm2=vm_mm2, vm_depth_um=dV,
                     bank_to_lane_um=lane_um, bank_to_port_um=port_um, block_mm2=lanes_mm2 + vm_mm2)
        # sensitivity: root's framing (~3.85 mm each way: SU_RETURN_UM, the lane array only)
        rt = stages(U.SU_RETURN_UM if hasattr(U, "SU_RETURN_UM") else 3850.0) + mux_stages(XBAR_LEVELS)
        return dict(geometry=geo_c, networks=nets, network_cell_mm2=sum(x["cell_mm2"] for x in nets),
                    network_footprint_mm2=sum(x["footprint_mm2"] for x in nets), clients=cl,
                    su_op_class_stages=su, su_op_extra_cycles=bcast + 2 * one_way,
                    su_red_extra_cycles=bcast + one_way + cl["su_results"], su_issue_ratio=1.0,
                    sensitivity_3850um_each_way=dict(one_way=rt, su_op_extra_cycles=bcast + 2 * rt))

    options["H"] = price_H(True)
    options["H_align_only"] = price_H(False)

    def price_H_rtl():
        o = copy.deepcopy(options["H_align_only"])
        su, cl = o["su_op_class_stages"], o["clients"]
        # X streams (gathered A, half streams, other strides) cross the class-X trees: group -> VM port (x gather)
        # and port -> lanes / groups (the scatter run), XI_ELEMS elements a cycle
        su["gather_read"] = cl["x_gather"] + cl["ret_scatter"]
        su["x_path"] = f"class-X trees, {H.XI_ELEMS} elements a cycle (x_gather + ret_scatter stages)"
        rot, ben, scal = su["residual_rotate_read"], su["gather_read"], su["scalar_read"]

        def extras(ops_):
            ext = {True: [], False: []}
            for p in ops_:
                x = bcast + H.hold(p["flags"], rot=rot, gath=ben, scal=scal)
                x += cl["su_results"] if p["red"] else (1 if p["ew"] else 0)
                ext[p["red"]].append(x)
            return (round(float(np.mean(ext[False])), 3) if ext[False] else 0.0,
                    round(float(np.mean(ext[True])), 3) if ext[True] else 0.0)
        e_fs, r_fs = extras(rule_ops)
        e_v, r_v = extras(rule_ops_vehicle)
        su["local_element_write_stages"] = 1
        o.update(su_op_extra_cycles=e_fs, su_red_extra_cycles=r_fs,
                 su_issue_ratio=round(hchk_fs["issue_cycles"] / hchk_fs["vectors_packed"], 4),
                 vehicle_aligned=dict(su_op_extra_cycles=e_v, su_red_extra_cycles=r_v,
                                      su_issue_ratio=round(hchk["issue_cycles"] / hchk["vectors_packed"], 4)),
                 su_op_extra_basis=("the vector unit's own per-op decision (rtl/hdc/v41x/ot_hdc_v41x_vec.sv VMD_NG, "
                                    "tools/w11_vm_h.rule) on the full-shape L0 program (bound at 32-alignment; the "
                                    "vehicle built with HDC_V41_VM_ALIGN=128 in vehicle_aligned): broadcast 4 + "
                                    "its hold + the result tree (reductions) or the local write (1); issue x the "
                                    "unpacked layout's vector ratio"),
                 layout_rule="VM regions 128-aligned by the builder (HDC_V41_VM_ALIGN=128); op offsets as built",
                 rule_check=dict(full_shape_l0=hchk_fs, vehicle_aligned=hchk))
        return o
    options["H_rtl"] = price_H_rtl()
    options["C"] = price_C("crossbar")
    options["C_rotate"] = price_C("rotate")
    options["A"] = price_A()

    # ---- token rates
    def hook(extra_vec, extra_red):
        orig = U.arch_graph

        def g(ctx):
            arch, b = orig(ctx)
            cyc = 1.0 / U.A._env()["clock"]
            for nd in b.g.nodes.values():
                r = nd.get("resource")
                if nd["kind"] in ("vector", "reduce") and r and r[0] in ("su", "sfu"):
                    nd["depth"] += (extra_red if nd["kind"] == "reduce" else extra_vec) * cyc
            return arch, b
        return orig, g

    def rate(d):
        orig, g = hook(d.get("su_op_extra_cycles", 0), d.get("su_red_extra_cycles", 0))
        if not getattr(U, "SU_OP_EXTRA_NATIVE", False):
            U.arch_graph = g                    # evaluate() without the keys: the graph hook adds them
        try:
            r = U.evaluate(copy.deepcopy(d))
            r.pop("_g")
            Tp, T1 = U.v41_verify_T(copy.deepcopy(d), U.V41_POSITIONS, 1)
        finally:
            U.arch_graph = orig
        mtp = U.V41_TAU / (Tp + U.V41_DRAFT_FRACTION * T1)
        return dict(ar_tokens_s=round(r["tokens_s"], 1), mtp_tokens_s=round(mtp, 1), T_us=round(r["T_us"], 2),
                    verify_over_ar=round(Tp / T1, 4))

    base = copy.deepcopy(U.PRESETS["proposal"])
    for k in ("vm_x_gather_stages", "vm_ret_scatter_stages", "vm_coll_write_stages", "su_ret_stages",
              "su_bcast_stages", "su_op_extra_cycles", "su_red_extra_cycles", "su_issue_ratio"):
        base.pop(k, None)
    rows = {}
    rows["flat_vm_reference"] = dict(design=dict(name="flat_vm_reference"), **rate(dict(base, name="flat")))
    rows["model_vm_dist_6_6_6_4"] = dict(design=dict(vm_x_gather_stages=6, vm_ret_scatter_stages=6,
                                                     vm_coll_write_stages=6, su_ret_stages=4, su_bcast_stages=4),
                                         **rate(dict(base, name="m", vm_x_gather_stages=6, vm_ret_scatter_stages=6,
                                                     vm_coll_write_stages=6, su_ret_stages=4, su_bcast_stages=4)))
    for k, o in options.items():
        cl = o["clients"]
        dd = dict(vm_x_gather_stages=cl["x_gather"], vm_ret_scatter_stages=cl["ret_scatter"],
                  vm_coll_write_stages=cl["coll_write"], su_ret_stages=cl["su_results"], su_bcast_stages=bcast,
                  su_op_extra_cycles=o["su_op_extra_cycles"], su_red_extra_cycles=o["su_red_extra_cycles"],
                  su_lanes=base["su_lanes"] / o["su_issue_ratio"], sfu_lanes=base["sfu_lanes"] / o["su_issue_ratio"])
        o["design_keys"] = dd
        o["rates"] = rate(dict(base, name=f"opt_{k}", **dd))
        if k.startswith("C"):
            s = o["sensitivity_3850um_each_way"]
            o["sensitivity_3850um_each_way"]["rates"] = rate(dict(base, name=f"opt_{k}_3850", **dict(
                dd, su_op_extra_cycles=s["su_op_extra_cycles"],
                su_red_extra_cycles=bcast + s["one_way"] + cl["su_results"])))
        # the SU extra alone (clients at the option's stages, no per-op extra) and the per-op extra alone
        o["rates_clients_only"] = rate(dict(base, name=f"opt_{k}_cl", **dict(dd, su_op_extra_cycles=0,
                                                                             su_red_extra_cycles=0)))
        o["sram"] = dict(macro=spec["macros"]["chosen"], macros=macros, mm2=sram_mm2,
                         note="the same replica / bank count serves every option: the port demand is the SU's")
        o["footprint_mm2"] = round(o["geometry"]["block_mm2"], 3)
        print(k, o["rates"], o["footprint_mm2"], round(o["network_footprint_mm2"], 3), flush=True)

    rec = dict(
        schema="opentallas.uarch.w11_vm_options.v1",
        generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source_commit=subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                                     text=True).stdout.strip(),
        basis=dict(clock_ps=PERIOD_PS, wire_ps_per_um=PS_PER_UM, stage_rule="tools/uarch_model.wire_cycles",
                   mux_levels_per_stage=MUX_LEVELS_PER_STAGE, mux_levels_basis=a.mux_basis or "ASSUMED", rotate_levels=ROT_LEVELS, benes_levels=BENES_LEVELS,
                   crossbar_levels=XBAR_LEVELS, density=cells,
                   network_cells=("rotate: N x 32 x log2 N mux2; Benes: N x 32 x (2 log2 N - 1); full crossbar: "
                                  "N x (N - 1) x 32 mux2 (a 1,024:1 mux tree per output bit); a stage register "
                                  "of N x 32 flops per pipeline stage; mux2 = the lane's mean combinational cell, "
                                  "footprint at 50 % utilisation (the spec's logic basis)"),
                   geometry=("distributed (H, A): the spec record's SU + VM block (macros at area, lane / VM logic "
                             "at 50 %), grown by the network footprint; rotate span = block W + H, scalar fetch "
                             "= (W + H) / 2; collective write with the endpoint at the VM port (W10 placement, as "
                             "the model's 6); central (C): the lane array (the spec's lane logic at 50 %) as a "
                             "square with the VM strip (macros + VM logic + crossbar) along one side"),
                   su_per_op=("a dependent SU op pays the controller broadcast (4, every option) + its operand "
                              "path + its element-write path (reductions: + the result tree instead of the write); "
                              "the model's SU node depths exclude all of these (su_bcast / su_ret are not in "
                              "evaluate())"),
                   model="tools/uarch_model.py PRESETS['proposal'] (identical evaluate() to claude/w11-dedicated-"
                         "units 73ba9c9b on these keys: AR 3,747.6 / MTP 5,811.4 tok/s at 6/6/6/4 on both)",
                   positions=U.V41_POSITIONS, tau=U.V41_TAU, ctx=1048576),
        h_measurement=dict(source="reduced vehicle, position 7 (tools/rtl_hdc_v41x_vec_campaign.vehicle_records); "
                           "idealised alignment (every op base rounded down to 128); physical lanes",
                           meta=meta, **hm),
        h_rtl_rule=dict(source="the vehicle built with HDC_V41_VM_ALIGN=128, the vector unit's per-op rule",
                        meta=meta_a, **hchk),
        rates=rows, options=options,
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in
                       [Path(__file__).resolve(), ROOT / "tools/uarch_model.py", ROOT / "tools/rtl_hdc_v41x_vec_campaign.py",
                        ROOT / "tools/w11_vm_h.py", ROOT / "tools/w11_vm_dist_spec.py",
                        ROOT / "results/rtl/hdc_v41x_fullshape_program_bind_rope_hbm.json",
                        *sorted((ROOT / "results/physical_abi3/asap7/chip/w11_vm_rot").glob("lps*/physical.json")),
                        SPEC, ROOT / "tools/hdc_isa_v41.py", ROOT / "tools/hdc_program_v41.py"]})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
