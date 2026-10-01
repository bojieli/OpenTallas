#!/usr/bin/env python3
"""W11: bank specification of the DISTRIBUTED VECTOR MEMORY (VM_DIST) of the DeepSeek-V4.1 die.

Root decision 2026-09-29: the vector memory (VM) becomes lane-group-local banks inside HUB_SU_VECTOR --
128 groups of 8 stream-unit lanes, element i in group i mod 128.  This tool derives, from the sources it
pins, everything a physical owner needs to build and place those banks, and it measures the stream unit's
real access patterns against the bank rule it proposes:

  capacity      the die's VM depth (VM_AW of rtl/chip/ot_chip_v41x_die.sv / _tile.sv at FULL_SHAPE) and the
                highest element the frozen full-shape L0 program's stream ops touch;
  groups        NG = 128 groups, lane l in group l mod 128 (so lane l and element l share a group);
  interleave    element e -> group e mod 128, local word w = e >> 7, bank w[3], macro row w[11:4], column w[2:0];
  macros        every 1R1W macro of physical/asap7_memory_macros/index.json that can hold a group's slice,
                scored on area and on the measured bank-row conflicts; 1RW / 2RW macros are excluded (a read
                replica must take a write in the same cycle as its read);
  replication   one read replica per read class that can be live in the same cycle (A, B, C, D operand
                streams, the gather-index stream G, the tree read X): R = 6;
  read rule     a class is conflict-free in a cycle when, in every group, the words it asks for lie in at most
                one row of each bank; measured on the reduced vehicle's 2,649 stream ops at N = 1,024 (their
                layouts at the full width) and on the full-shape L0 program's 62 stream ops;
  locality      the share of lane reads / writes whose element is NOT in the lane's group (they need a network
                between groups that the model does not price);
  writes        one masked row write per bank per cycle (the macro's one write port, all replicas together);
                fixed-priority arbitration into a per-bank write buffer with read forwarding;
  trees         the three non-SU clients' trees and the SU reducer's result tree: widths, distances from the
                W1 hub geometry (results/floorplan/v41_pack_expanded_woa.json) and register stages by the model's
                rule tools/uarch_model.wire_cycles(um, 1e12/920, 0.76);
  footprint     the SU + VM region (macros + logic at 50% utilisation) and the stages it implies;
  discrepancies every place the microarchitecture model (tools/uarch_model.py VM_DIST, stream_unit) disagrees.

Writes results/floorplan/v41_vm_dist_spec.json.
    python3 tools/w11_vm_dist_spec.py [--out PATH] [--positions 1048575 65535]
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import w11_vm_variant  # noqa: E402,F401  (VM-H / C_rotate sources and rules: rtl/w11crot)
import hdc_isa_v41 as I                    # noqa: E402
import rtl_hdc_v41x_vec_campaign as C      # noqa: E402
import uarch_model as U                    # noqa: E402

OUT = ROOT / "results/floorplan/v41_vm_dist_spec.json"
FLOORPLAN = ROOT / "results/floorplan/v41_pack_expanded_woa.json"
MACROS = ROOT / "physical/asap7_memory_macros/index.json"
BINDER = ROOT / "results/rtl/hdc_v41x_fullshape_program_bind_rope_hbm.json"
BUDGET = ROOT / "results/arch/arch_budget_v41.json"
RTL_DIE = ROOT / "rtl/chip/ot_chip_v41x_die.sv"
RTL_TILE = ROOT / "rtl/chip/ot_chip_v41x_tile.sv"
# The die / tile RTL is read only for its VM_AW default; the record keeps the matched lines (capacity.vm_aw_lines)
# rather than the files' digests, so the VM_DIST RTL edits that follow do not orphan the spec.
SOURCES = [Path(__file__).resolve(), ROOT / "tools/uarch_model.py", ROOT / "tools/rtl_hdc_v41x_vec_campaign.py",
           ROOT / "tools/hdc_isa_v41.py", ROOT / "tools/hdc_program_v41.py", ROOT / "tools/hdc_golden_v41.py",
           ROOT / "tools/hdc_golden.py", FLOORPLAN, MACROS, BINDER, BUDGET]

# ---- the design point ----------------------------------------------------------------------------------------
N_LANES, M_SFU = 1024, 256           # the SU at spec width (ot_hdc_v41x_vec N / M)
LPG = 8                              # lanes per group (root decision)
NG = N_LANES // LPG                  # 128 groups
PERIOD_PS = 920.0                    # 0.92 ns ASAP7 clock (briefing hard rule; the model's VM_DIST basis)
PS_PER_UM = 0.76                     # the model's loaded-channel wire delay (WIRE_PS_PER_UM_LOADED)
UTIL = 0.5                           # logic placement utilisation (task)
READ_CLASSES = ("A", "B", "C", "D", "G", "X")      # operand streams, gather index, the non-SU tree read
# the model's VM_DIST presets and the clients' rates (tools/uarch_model.py PRESETS["proposal"], VM_DIST)
X_READ_ELEMS, RET_WRITE_ELEMS = 64, 128
COLL_WORDS, COLL_WORD_BITS = 4, 512


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(ROOT))


def stages(um: float) -> int:
    return U.wire_cycles(um, 1e12 / PERIOD_PS, PS_PER_UM)


# ---- capacity --------------------------------------------------------------------------------------------------
def vm_aw() -> dict:
    pat = re.compile(r"parameter integer VM_AW\s*=\s*FULL_SHAPE \? (\d+) : (\d+)")
    die, tile = pat.search(RTL_DIE.read_text()), pat.search(RTL_TILE.read_text())
    if not die or not tile or die.groups() != tile.groups():
        raise SystemExit("VM_AW of the die and the tile disagree or are missing")
    full, red = map(int, die.groups())
    return dict(full_shape_vm_aw=full, reduced_vm_aw=red, words=1 << full, bytes=4 << full,
                vm_aw_lines={rel(RTL_DIE): die.group(0), rel(RTL_TILE): tile.group(0)},
                mib=(4 << full) / 2**20, source="VM_AW default of ot_chip_v41x_die and ot_chip_v41x_tile "
                "(FULL_SHAPE ? 19 : 16); the tile's vm array is 2^VM_AW 32-bit words")


# ---- the stream ops -------------------------------------------------------------------------------------------
def full_dyn(pos: int, token: int = 0) -> list[int]:
    """The core's DYN bank at FULL_SHAPE (rtl/hdc/v41x/ot_hdc_core_v41x.sv S_DYN, FULL_SHAPE branch)."""
    DIM, TOPK, HDIM, RP, LG, W = 5120, 512, 512, 32, 6, 16
    FW, SCAN, TP = 128, 16384, 4
    p1 = pos + 1
    n2 = p1 >> 1
    ns1, ns2 = min(p1, TOPK), min(n2, TOPK)
    rnds = lambda x: 0 if x == 0 else ((x - 1) >> LG) + 1
    rnd16 = lambda x: 0 if x == 0 else ((x - 1) >> 4) + 1
    d = [0] * 64
    num = [0, token * DIM, pos * RP, (pos - 1) * RP if pos else 0, pos, p1, n2, n2 - 1 if n2 else 0, ns1, ns2,
           p1 + ns1, p1 + ns2, rnds(p1), rnds(n2), rnds(p1 + ns1), rnds(p1 + ns2), pos * HDIM, p1 * HDIM,
           4 if pos & 1 else 0, 64 if pos & 1 else 0, (n2 - 1) * HDIM if n2 else 0, rnd16(p1), rnd16(n2),
           rnd16(p1 + ns1), rnd16(p1 + ns2)]
    d[:len(num)] = num
    win = min(p1, FW)
    sc1, sc2 = (p1 + TP - 1) // TP, (n2 + TP - 1) // TP
    scr = (min(p1, SCAN) + TP - 1) // TP
    vals = {"WIN": win, "NC1": p1, "NC2": n2, "NS1": ns1, "NS2": ns2, "T0": win, "T1": win + ns1, "T2": win + ns2,
            "SC1": sc1, "SC2": sc2, "SCR": scr, "NSL1": min(sc1, TOPK), "NSL2": min(sc2, TOPK),
            "NSLR": min(scr, TOPK), ("ceil", "SC1", 16): (sc1 + 15) >> 4, ("ceil", "SC1", 8): (sc1 + 7) >> 3,
            ("ceil", "SC2", 16): (sc2 + 15) >> 4, ("ceil", "SCR", 16): (scr + 15) >> 4,
            ("ceil", "T0", 32): (win + 31) >> 5, ("ceil", "T1", 32): (win + ns1 + 31) >> 5,
            ("ceil", "T2", 32): (win + ns2 + 31) >> 5, "WINM1": win - 1, "WIN_ROW": win * HDIM,
            "WINM1_ROW": (win - 1) * HDIM}
    for k, slot in I.FULL_DYN.items():
        d[slot] = vals[k]
    return d


def full_shape_ops(pos: int):
    b = json.loads(BINDER.read_text())
    ops = []
    for row in b["instruction_trace"]:
        f = dict(row["fields"])
        if f.get("unit") != I.UNIT_SU:
            continue
        for k, v in list(f.items()):
            if isinstance(v, list):
                v = tuple(v)
            if isinstance(v, (str, tuple)):
                f[k] = I.FULL_DYN[v]
        g = dict((k, 0) for k, _ in I.FIELDS)
        g.update(f)
        ops.append((row["tag"], C.resolve(g, full_dyn(pos))))
    return ops, b["instruction_count"]


def vehicle_ops():
    recs, _, _, meta = C.vehicle_records()
    ops = []
    for f0, dyn, vm, _ in recs:
        f = C.resolve(f0, dyn)
        ops.append(("vehicle", f, np.asarray(vm, dtype=np.uint32)))
    return ops, meta


def streams(f, vm=None):
    """Per stream class: the element addresses in (o, i) order, or None when the stream is not read from VM."""
    no, ni = f["nout"], f["nin"]
    idx = None
    if f["aind"]:
        cnt = ni if f["aind"] == I.IND_I else no
        if vm is not None:
            idx = np.asarray(vm[f["aibase"]:f["aibase"] + cnt], dtype=np.int64)
            if len(idx) < cnt:
                idx = None
    st = {}
    for s, name in zip("abcd", "ABCD"):
        if f[f"{s}src"] == I.SRC_VM:
            if s == "a" and f["aind"] and idx is None:
                st[name] = None          # gathered operand, index values unknown (no VM image)
            else:
                st[name] = C.addrs(f, s, no, ni, idx if s == "a" else None)
    if f["cpair"] and f["csrc"] == I.SRC_VM and st.get("A") is not None:
        st["C"] = st["A"] ^ 1
    return st


class Tally:
    """Per class: vectors, elements, remote elements; per bank geometry: vectors over budget."""

    def __init__(self, geoms):
        self.geoms = geoms
        self.vec = collections.Counter()
        self.elem = collections.Counter()
        self.remote = collections.Counter()
        self.remote_nb = collections.Counter()
        self.bcast = collections.Counter()
        self.over = {g: collections.Counter() for g in geoms}
        self.over_ops = {g: collections.Counter() for g in geoms}
        self.worst = {g: collections.Counter() for g in geoms}
        self.unknown = 0
        self.max_elem = -1
        self.examples = {g: [] for g in geoms}

    def add(self, cls, lanes, a, tag, k_op):
        a = np.asarray(a, dtype=np.int64) & ((1 << 24) - 1)
        self.vec[cls] += 1
        self.elem[cls] += len(a)
        self.max_elem = max(self.max_elem, int(a.max()))
        rem = int(np.count_nonzero((a % NG) != (lanes % NG)))
        self.remote[cls] += rem
        u = np.unique(a)
        if len(u) == 1 and len(a) > 1:
            self.bcast[cls] += 1
        else:
            self.remote_nb[cls] += rem
        grp, w = u % NG, u // NG
        for gname, (rw, nb) in self.geoms.items():
            bank, row = (w // rw) % nb, w // (rw * nb)
            keys = set(zip(grp.tolist(), bank.tolist(), row.tolist()))
            cnt = collections.Counter((g_, b_) for g_, b_, _ in keys)
            mx = max(cnt.values())
            self.worst[gname][cls] = max(self.worst[gname][cls], mx)
            if mx > 1:
                self.over[gname][cls] += 1
                self.over_ops[gname][(cls, k_op)] += 1
                if len(self.examples[gname]) < 6:
                    self.examples[gname].append(dict(tag=tag, op=k_op, cls=cls, rows_in_one_bank=int(mx)))

    def summary(self):
        cls = sorted(self.vec)
        out = dict(vectors=dict((c, self.vec[c]) for c in cls), elements=dict((c, self.elem[c]) for c in cls),
                   remote_elements=dict((c, self.remote[c]) for c in cls),
                   remote_share=dict((c, round(self.remote[c] / max(1, self.elem[c]), 4)) for c in cls),
                   remote_share_excluding_broadcasts=dict(
                       (c, round(self.remote_nb[c] / max(1, self.elem[c]), 4)) for c in cls),
                   broadcast_vectors=dict((c, self.bcast[c]) for c in cls),
                   gathered_streams_without_index_values=self.unknown, max_element=self.max_elem,
                   by_geometry={})
        for g in self.geoms:
            ops = collections.Counter(c for c, _ in self.over_ops[g])
            out["by_geometry"][g] = dict(
                vectors_over_budget=dict((c, self.over[g][c]) for c in cls),
                ops_over_budget=dict((c, ops[c]) for c in cls),
                worst_rows_in_one_bank=dict((c, self.worst[g][c]) for c in cls),
                conflict_free=all(self.over[g][c] == 0 for c in cls), examples=self.examples[g])
        return out


def measure(ops, geoms, with_vm):
    t = Tally(geoms)
    for k, item in enumerate(ops):
        tag, f = item[0], item[1]
        vm = item[2] if with_vm else None
        if f["nout"] == 0 or f["nin"] == 0:
            continue
        lay = C.layout(f, N_LANES, M_SFU)
        if lay["bad"]:
            continue
        st = streams(f, vm)
        wr = C.out_addrs(f) if f["dst"] == I.DST_VM else None
        for oo, ii in lay["vecs"]:
            e = C.elem_index(f, oo, ii)
            # the physical lane of each live element: lane l takes (o_v + l / S, i_v + l mod S); a slot's dead
            # lanes (i >= ni) are skipped, not compacted
            if lay["flat"]:
                g_ = oo * f["nin"] + ii
                lanes = g_ - g_.min()
            else:
                lanes = (oo - oo.min()) * lay["S"] + (ii - ii.min())
            for cls, a in st.items():
                if a is None:
                    t.unknown += 1
                    continue
                t.add(cls, lanes, a[e], tag, k)
            if f["aind"]:
                t.add("G", lanes, f["aibase"] + (ii if f["aind"] == I.IND_I else oo), tag, k)
            if wr is not None:
                t.add("E", lanes, wr[e], tag, k)
    return t.summary()


# ---- macros -------------------------------------------------------------------------------------------------
def macro_candidates(words_per_group):
    m = json.loads(MACROS.read_text())["macros"]
    rows = []
    for name, v in sorted(m.items()):
        if v["kind"] != "sram":
            continue
        sp = v["spec"]
        entry = dict(name=name, ports=sp["ports"], words=sp["words"], bits=sp["bits"], area_um2=v["area_um2"],
                     w_um=v["width_um"], h_um=v["height_um"], fmax_ss_mhz=v["fmax_mhz"]["ss"],
                     clk_to_q_ss_ps=v["clk_to_q_ps"]["ss"], read_energy_fj_tt=v["read_energy_fj_tt"])
        if sp["ports"] != "1r1w":
            entry["excluded"] = ("a read replica takes a write every cycle its bank is written and a read every "
                                 "cycle its class reads: one read and one write port are needed; " + sp["ports"] +
                                 " cannot do both in one cycle")
            rows.append(entry)
            continue
        if sp["bits"] % 32:
            entry["excluded"] = "row is not a whole number of 32-bit elements"
            rows.append(entry)
            continue
        rw = sp["bits"] // 32
        cap = sp["words"] * rw
        nb = max(1, math.ceil(words_per_group / cap))
        entry.update(row_words=rw, words_per_macro=cap, banks_per_replica=nb,
                     used_fraction=round(words_per_group / (nb * cap), 3),
                     area_per_replica_um2=round(nb * v["area_um2"], 1),
                     meets_clock_ss=v["fmax_mhz"]["ss"] >= 1e6 / PERIOD_PS)
        rows.append(entry)
    return rows


# ---- geometry -------------------------------------------------------------------------------------------------
def regions():
    fp = json.loads(FLOORPLAN.read_text())
    reg = {r[0]: dict(x=r[2], y=r[3], w=r[4], h=r[5]) for r in fp["soft_regions"] if str(r[0]).startswith("HUB")}
    return reg


def grid_distances(x0, yc, w, h, cols, rows_, port):
    """Group tiles on a cols x rows grid over [x0, x0+w] x [yc-h/2, yc+h/2]; Manhattan distances from `port`
    to the farthest group centre, and from the block centre to the farthest group centre."""
    tw, th = w / cols, h / rows_
    far_port = far_ctr = 0.0
    cx, cy = x0 + w / 2, yc
    for i in range(cols):
        for j in range(rows_):
            gx, gy = x0 + (i + 0.5) * tw, yc - h / 2 + (j + 0.5) * th
            far_port = max(far_port, abs(gx - port[0]) + abs(gy - port[1]))
            far_ctr = max(far_ctr, abs(gx - cx) + abs(gy - cy))
    return far_port, far_ctr, tw, th


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--positions", type=int, nargs="*", default=[1048575, 65535, 200])
    a = ap.parse_args()

    cap = vm_aw()
    words_per_group = cap["words"] // NG
    cands = macro_candidates(words_per_group)
    geoms = {c["name"]: (c["row_words"], c["banks_per_replica"]) for c in cands if "excluded" not in c}
    geoms["word_interleaved_16_banks (no such macro)"] = (1, 16)

    # -- measured access patterns at N = 1,024 / M = 256 -------------------------------------------------------
    veh, meta = vehicle_ops()
    pattern = dict(vehicle=dict(source="the reduced V4.1 vehicle's one-token program (hdc_program_v41.Builder), "
                                "every stream op laid out at N = 1,024 / M = 256 by rtl_hdc_v41x_vec_campaign.layout; "
                                "gathered operands use the index values the ISA simulator holds before the op",
                                meta=meta, **measure(veh, geoms, True)))
    full = {}
    for pos in a.positions:
        ops, n_instr = full_shape_ops(pos)
        full[str(pos)] = dict(stream_ops=len(ops), **measure(ops, geoms, False))
    pattern["full_shape_l0"] = dict(source=f"{rel(BINDER)} instruction trace ({n_instr} instructions), stream ops "
                                    "resolved with the core's FULL_SHAPE DYN bank at each position; gathered "
                                    "operand streams (a_ind) are counted but their index values are unknown here",
                                    positions=full)

    # -- chosen macro -----------------------------------------------------------------------------------------
    CHOICE = "ot_sram_1r1w_256x256_m2_r2c2"
    comparison = []
    for c in cands:
        if "excluded" in c:
            continue
        fl = next(iter(full.values()))["by_geometry"][c["name"]]
        comparison.append(dict(name=c["name"], total_macros=NG * len(READ_CLASSES) * c["banks_per_replica"],
                               total_mm2=round(NG * len(READ_CLASSES) * c["area_per_replica_um2"] / 1e6, 3),
                               vehicle_vectors_over_budget=sum(pattern["vehicle"]["by_geometry"][c["name"]]
                                                               ["vectors_over_budget"].values()),
                               full_l0_vectors_over_budget=sum(fl["vectors_over_budget"].values()),
                               meets_clock_ss=c["meets_clock_ss"]))
    ch = next(c for c in cands if c["name"] == CHOICE)
    R = len(READ_CLASSES)
    per_group_macros = R * ch["banks_per_replica"]
    total_macros = NG * per_group_macros
    macro_mm2 = total_macros * ch["area_um2"] / 1e6

    # -- per-group logic ----------------------------------------------------------------------------------------
    ub = json.loads(BUDGET.read_text())["unit_areas_um2"]
    dff = U.DFF_UM2
    mux2 = 0.5 * dff                      # a 2:1 mux bit at half a DFFHQNx1 (no mux entry in the budget)
    rw = ch["row_words"]
    nb = ch["banks_per_replica"]
    # read alignment: each lane of each read class picks its word out of the replica's nb rows (nb * rw words)
    rd_select = (4 + 1) * LPG * 32 * (nb * rw - 1) * mux2
    x_select = 1 * 32 * (nb * rw - 1) * mux2                    # the tree read: one word a cycle a group
    wbuf_depth = 4
    wbuf = nb * wbuf_depth * (rw * 32 * 2 + 8 + 2) * dff        # data + mask + row + class, per bank
    fwd = (R * nb) * wbuf_depth * rw * 32 * mux2                # forwarding muxes on every replica read
    tree_leaf = (32 + 32 + 32 + 16) * dff * 2                   # x / ret / coll / result leaf registers, in + out
    vm_logic_um2 = rd_select + x_select + wbuf + fwd + tree_leaf
    lanes_um2 = (N_LANES - M_SFU) * ub["su_light_lane_um2"] + M_SFU * ub["su_lane_um2"]
    group_lanes_um2 = lanes_um2 / NG
    group_macro_um2 = per_group_macros * ch["area_um2"]
    group_tile_um2 = group_macro_um2 + (group_lanes_um2 + vm_logic_um2) / UTIL
    block_mm2 = NG * group_tile_um2 / 1e6

    # -- geometry and trees -------------------------------------------------------------------------------------
    reg = regions()
    su, hvm, hco = reg["HUB_SU_VECTOR"], reg["HUB_VM"], reg["HUB_COLLECTIVE"]
    port = (su["x"], hvm["y"] + hvm["h"] / 2)                   # the VM port: west edge of the SU region, VM strip centre
    coll_ctr = (hco["x"] + hco["w"] / 2, hco["y"] + hco["h"] / 2)
    coll_to_port = abs(coll_ctr[0] - port[0]) + abs(coll_ctr[1] - port[1])
    # the block spans the region's width, centred on the port's y (the region's own centre line)
    bw = su["w"]
    bh = block_mm2 * 1e6 / bw
    fits = bh <= su["h"]
    cols, rows_ = 16, 8                                          # 128 group tiles
    far_port, far_ctr, tw, th = grid_distances(su["x"], port[1], bw, bh, cols, rows_, port)
    # the same block with the lanes at their cell area (the model's basis) and only the VM logic at 50%
    block_raw_mm2 = NG * (group_macro_um2 + group_lanes_um2 + vm_logic_um2 / UTIL) / 1e6
    bh_raw = block_raw_mm2 * 1e6 / bw
    far_port_raw, far_ctr_raw, _, _ = grid_distances(su["x"], port[1], bw, bh_raw, cols, rows_, port)
    # the model's square (3,458 um, lanes only at 100%)
    model_side = math.sqrt(lanes_um2)
    model_far_port, model_far_ctr = model_side + model_side / 2, model_side
    tree = dict(
        x_gather=dict(client="matvec x-broadcast read (ME / QE / HE / XU x operands; model vm_read_elems)",
                      elements_per_cycle=X_READ_ELEMS, root_data_bits=X_READ_ELEMS * 32,
                      root_request_bits=cap["full_shape_vm_aw"] + 7 + 1,
                      per_group_bits_per_cycle=32, groups_live_per_cycle=X_READ_ELEMS,
                      path="farthest group -> VM port (gather), request broadcast outward on the same run",
                      distance_um=round(far_port), stages=stages(far_port),
                      model_distance_um=round(model_far_port), model_rule_stages=stages(model_far_port),
                      model_stages=U.VM_DIST["vm_x_gather_stages"]),
        ret_scatter=dict(client="matvec result write (model vm_write_elems)", elements_per_cycle=RET_WRITE_ELEMS,
                         root_data_bits=RET_WRITE_ELEMS * 32, root_ctl_bits=cap["full_shape_vm_aw"] + RET_WRITE_ELEMS,
                         per_group_bits_per_cycle=32, path="VM port -> farthest group",
                         distance_um=round(far_port), stages=stages(far_port),
                         model_distance_um=round(model_far_port), model_rule_stages=stages(model_far_port),
                         model_stages=U.VM_DIST["vm_ret_scatter_stages"]),
        coll_write=dict(client="collective DMA write from HUB_COLLECTIVE (4 x 512-bit words)",
                        elements_per_cycle=COLL_WORDS * COLL_WORD_BITS // 32,
                        root_data_bits=COLL_WORDS * COLL_WORD_BITS,
                        root_ctl_bits=COLL_WORDS * (cap["full_shape_vm_aw"] - 4 + 1),
                        per_group_bits_per_cycle=32,
                        path="HUB_COLLECTIVE centre -> VM port -> farthest group",
                        distance_um=round(coll_to_port + far_port), stages=stages(coll_to_port + far_port),
                        model_distance_um=round(coll_to_port + model_far_port),
                        model_rule_stages=stages(coll_to_port + model_far_port),
                        model_stages=U.VM_DIST["vm_coll_write_stages"]),
        su_results=dict(client="SU chunk8 reducer results (N/8 = 128 slots)", elements_per_cycle=N_LANES // 8,
                        root_data_bits=N_LANES // 8 * 32, root_ctl_bits=2 * 24 + N_LANES // 8,
                        per_group_bits_per_cycle=32,
                        path="reducer root at the block centre -> farthest group (a broadcast bus; each group "
                             "takes the slots whose address it owns)",
                        distance_um=round(far_ctr), stages=stages(far_ctr),
                        model_distance_um=round(model_far_ctr), model_rule_stages=stages(model_far_ctr),
                        model_stages=U.VM_DIST["su_ret_stages"]))

    # -- write ports ---------------------------------------------------------------------------------------------
    writes = dict(
        macro_write_port="one masked 256-bit row write per bank per cycle (ot_sram_1r1w: w_ce/w_addr/wd/w_mask); "
                         "every write goes to all R replicas of its bank",
        clients=[dict(cls="E", client="SU element writes", per_group_per_cycle="<= 8 words, <= 1 row per bank "
                      "under the read rule applied to the write stream", back_pressure=False),
                 dict(cls="R", client="SU reducer results", per_group_per_cycle="1 word (consecutive r_so = 1 "
                      "results); <= 128 in the worst case", back_pressure=False),
                 dict(cls="S", client="matvec result scatter", per_group_per_cycle="1 word", back_pressure=False),
                 dict(cls="C", client="collective DMA write", per_group_per_cycle="0.5 word",
                      back_pressure=True, note="exclusive with every engine: the core drains all units before a "
                      "collective (ot_hdc_core_v41x S_ISSUE, d_unit 6)")],
        chosen="fixed-priority arbitration E > R > S > C per bank into a per-bank write buffer "
               f"({wbuf_depth} rows, merged by row) with read forwarding on every replica read port",
        never_loses_a_write="a write enters the buffer the cycle it arrives; the buffer drains one row a cycle "
                            "through the macro port when E does not use it; every read port compares its row "
                            "with the buffer and takes the newest buffered words, so a buffered write is "
                            "'written' (protocol of ot_hdc_v41x_vec) the cycle after it arrives; a full buffer "
                            "holds the collective tree (valid/ready) and raises a sticky fault for the fixed-"
                            "timing classes (never a silent drop)",
        cost_cycles="0 on every read (forwarding) while the buffer does not fill; the depth is sized from the "
                    "RTL monitor's measured per-bank occupancy (results/rtl/w11_vm_dist_gate.json)",
        alternative_rejected="dedicated write banks (a live-value table with one replica set per write class) "
                             f"multiply the {total_macros} macros by the 3 fixed-timing classes "
                             f"({3 * macro_mm2:.1f} mm2)")

    # -- discrepancies -------------------------------------------------------------------------------------------
    veh_s = pattern["vehicle"]
    remote_su = sum(veh_s["remote_elements"].get(c, 0) for c in "ABCDEG")
    elems_su = sum(veh_s["elements"].get(c, 0) for c in "ABCDEG")
    disc = [
        dict(item="SU operand reads and element writes are not lane-group-local",
             model="VM_DIST prices 0 stages for SU reads / element writes ('element writes are local'); the "
                   "stream_unit ledger has no network between lanes and banks",
             measured=f"{remote_su:,} of {elems_su:,} SU element accesses of the vehicle at N = 1,024 "
                      f"({remote_su / max(1, elems_su):.1%}) name an element in another group (base not a "
                      "multiple of 128, packed rows, pair / half streams, broadcasts)",
             consequence="a group-to-lane network per read class (rotation + broadcast at least) and a lane-to-"
                         "group network for element writes; its stages add to the SU fetch / write depth"),
        dict(item="tree distances assume a 3,458 um lane square at 100% utilisation without the VM macros",
             model=f"x gather / scatter {model_far_port:,.0f} um, collective {coll_to_port + model_far_port:,.0f} "
                   f"um, results {model_far_ctr:,.0f} um",
             measured=f"the SU + VM block is {block_mm2:.2f} mm2 ({bw:,.0f} x {bh:,.0f} um): "
                      f"{far_port:,.0f} / {coll_to_port + far_port:,.0f} / {far_ctr:,.0f} um",
             consequence=f"stages x {tree['x_gather']['stages']} (model 6), scatter "
                         f"{tree['ret_scatter']['stages']} (6), collective {tree['coll_write']['stages']} (11), "
                         f"SU results {tree['su_results']['stages']} (4); with the lanes at their cell area "
                         f"(the model's basis) {stages(far_port_raw)} / {stages(far_port_raw)} / "
                         f"{stages(coll_to_port + far_port_raw)} / {stages(far_ctr_raw)}"),
        dict(item="VM SRAM area",
             model=f"vm_ports {math.ceil(X_READ_ELEMS * 32 / 256) + math.ceil(RET_WRITE_ELEMS * 32 / 256)} x "
                   f"1024x256 macros + su_vm_ports_mm2 6.0 = "
                   f"{((math.ceil(X_READ_ELEMS * 32 / 256) + math.ceil(RET_WRITE_ELEMS * 32 / 256)) * U.SRAM_256B_MACRO['um2'] / 1e6 + 6.0):.2f} mm2",
             measured=f"{total_macros} x {CHOICE} = {macro_mm2:.2f} mm2 (R = {R} read replicas x "
                      f"{ch['banks_per_replica']} banks x {NG} groups)"),
        dict(item="non-SU readers outside the model's x-gather client list",
             model="x gather = the matvec x operand (64 elements/cycle)",
             measured="the core also reads the VM through HE x (8 ports), QE 32-element reads and expert index, "
                      "XU element / 32-element reads, the select's 4 x 16 score reads, the QE streamer's expert "
                      "id, and the die's word ports A / B (package controller, collective source); all of them "
                      "share the x-gather tree and its replica (class X)"),
    ]
    for pos, fr in full.items():
        for g, v in fr["by_geometry"].items():
            if g == CHOICE and not v["conflict_free"]:
                disc.append(dict(item=f"read rule violations, full-shape L0 at position {pos}",
                                 measured=v["vectors_over_budget"], examples=v["examples"]))
    vg = veh_s["by_geometry"][CHOICE]
    if not vg["conflict_free"]:
        disc.append(dict(item="read rule violations, reduced vehicle laid out at N = 1,024",
                         measured=vg["vectors_over_budget"], ops=vg["ops_over_budget"], examples=vg["examples"],
                         consequence="such a vector needs one extra array cycle per extra row in a bank: the SU "
                                     "must split it (issue cost) or stall; neither exists in ot_hdc_v41x_vec"))

    rec = dict(
        schema="opentallas.floorplan.v41_vm_dist_spec.v1",
        status="spec",
        claim_boundary=("Analytical bank specification of the distributed VM, sized from pinned sources; access "
                        "patterns measured by laying out real stream ops (reduced vehicle, full-shape L0) at "
                        "N = 1,024.  No RTL, synthesis or placement evidence in this record; the RTL gate is "
                        "results/rtl/w11_vm_dist_gate.json."),
        capacity=dict(cap, per_group_words=words_per_group, per_group_bits=words_per_group * 32,
                      full_shape_l0_highest_element={p: fr["max_element"] for p, fr in full.items()}),
        groups=dict(count=NG, lanes_per_group=LPG, lane_to_group="lane l in group l mod 128",
                    element_to_group="element e in group e mod 128",
                    sfu_lanes_per_group=M_SFU // NG, light_lanes_per_group=LPG - M_SFU // NG),
        interleave=dict(group="e[6:0]", local_word="w = e[18:7] (12 bits, 4,096 words)",
                        column="w[2:0] (32-bit element of the 256-bit row)", bank="w[3]", macro_row="w[11:4]",
                        example={str(e): dict(group=e % NG, word=e // NG, bank=(e // NG >> 3) & 1,
                                              row=e // NG >> 4, column=e // NG & 7)
                                 for e in (0, 127, 128, 1023, 1024, 365024, (1 << cap["full_shape_vm_aw"]) - 1)}),
        macros=dict(candidates=cands, chosen=CHOICE,
                    reason="its row is the group's 8-lane vector (256 bits) and its capacity splits the "
                           "group's 4,096 words into exactly two banks (row parity), so any 8 consecutive local "
                           "words -- an unaligned stride-1 vector of the group's 8 lanes -- fall in one row of "
                           "each bank.  No geometry built from the index's macros is conflict-free on the "
                           "measured ops (word interleaving would need 32-bit banks, which the index lacks); on "
                           "the full-shape L0 program 256x256 and 128x256 violate on the same vectors, and "
                           "256x256 is 9% smaller and has half the macros (see comparison)",
                    comparison=comparison,
                    banks_per_replica=ch["banks_per_replica"], read_replicas=R, read_classes=list(READ_CLASSES),
                    per_group=per_group_macros, total=total_macros, total_mm2=round(macro_mm2, 3),
                    bits_stored_per_replica=cap["words"] * 32, replication_overhead=R),
        read_rule=dict(
            statement="per cycle, per group, per read class: the local words asked for lie in at most one row "
                      "of each bank (at most two 8-word rows of opposite parity); a broadcast counts once",
            holds_for="any stride-1 run of <= 9 consecutive local words; any broadcast; row-aligned packed rows",
            classes=dict(A="operand A (and the gathered A)", B="operand B", C="operand C (pair mode: A ^ 1)",
                         D="operand D", G="gather-index read", X="tree read (all non-SU readers)"),
            measured=pattern),
        writes=writes,
        per_group_ports_bits_per_cycle=dict(
            su_operand_reads=4 * LPG * 32, su_gather_index_read=LPG * 32, su_element_write=LPG * 32,
            su_reducer_result_write=32, x_gather_read=32, ret_scatter_write=32, coll_write=32,
            replica_read_ports=R * ch["banks_per_replica"] * ch["bits"], bank_write_ports=nb * ch["bits"]),
        trees=tree,
        geometry=dict(hub_su_vector=su, hub_vm=hvm, hub_collective=hco, vm_port_xy_um=[round(port[0], 2),
                      round(port[1], 2)], collective_centre_to_port_um=round(coll_to_port, 1),
                      block_w_um=round(bw, 1), block_h_um=round(bh, 1), fits_hub_su_vector=fits,
                      group_grid=[cols, rows_], group_tile_w_um=round(tw, 1), group_tile_h_um=round(th, 1),
                      rule=f"wire_cycles(um, 1e12/{PERIOD_PS:g}, {PS_PER_UM}) (tools/uarch_model.py)"),
        footprint=dict(
            per_group=dict(macros=per_group_macros, macro_um2=round(group_macro_um2, 1),
                           lanes_logic_um2=round(group_lanes_um2, 1), vm_logic_um2=round(vm_logic_um2, 1),
                           vm_logic_parts_um2=dict(read_select=round(rd_select, 1), x_select=round(x_select, 1),
                                                   write_buffer=round(wbuf, 1), forwarding=round(fwd, 1),
                                                   tree_leaves=round(tree_leaf, 1)),
                           tile_um2=round(group_tile_um2, 1)),
            block_mm2=round(block_mm2, 3), block_w_um=round(bw, 1), block_h_um=round(bh, 1),
            basis="macros at their area; lane and VM logic at 50% utilisation; 16 x 8 group tiles spanning "
                  "HUB_SU_VECTOR's width, centred on the VM port's y",
            vm_only_increment_mm2=round(NG * (group_macro_um2 + vm_logic_um2 / UTIL) / 1e6, 3),
            variant_lanes_at_cell_area=dict(
                block_mm2=round(block_raw_mm2, 3), block_w_um=round(bw, 1), block_h_um=round(bh_raw, 1),
                x_gather_um=round(far_port_raw), x_gather_stages=stages(far_port_raw),
                ret_scatter_stages=stages(far_port_raw), coll_write_stages=stages(coll_to_port + far_port_raw),
                su_results_um=round(far_ctr_raw), su_results_stages=stages(far_ctr_raw),
                note="the model's lane-area basis (11.96 mm2 of cells, no utilisation) plus the VM macros"),
            excludes="the lane <-> group network for non-local SU accesses (see discrepancies)"),
        discrepancies=disc,
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_commit=subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                     cwd=ROOT).stdout.strip(),
        source_sha256={rel(p): sha(p) for p in SOURCES},
    )
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(capacity=rec["capacity"]["mib"], macros=rec["macros"]["total"],
                          mm2=rec["macros"]["total_mm2"], block=[rec["footprint"]["block_w_um"],
                                                                 rec["footprint"]["block_h_um"]],
                          stages={k: (v["stages"], v["model_stages"]) for k, v in tree.items()})))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
