#!/usr/bin/env python3
"""DS-ROM (DeepSeek-V4.1-Flash, S81) ROM-field matvec nodes MEASURED in RTL at the 1M token: one return region at full
shape at a time, every region of the rank-0 die, one layer per layer type, bit-exact against the golden.

    python3 tools/dsrom_1m_field.py all --work DIR [--jobs 16] [--layers 0,1,2,3,20,21,24]
        [--snapshot <HF snapshot dba1be0a...>] [--gold-vm /home/ubuntu/w17work/die/ctx1048576_s20260930_L20_r0]
        [--record results/rtl/dsrom_1m_allmeasured_20261004/field.json]
    steps: plan (S81 map + golden x) | extract (rank-0 checkpoint slices -> DIR/mats, so a compute host needs no
    checkpoint) | build (Verilator 5.050 vehicle) | run (every phase x region; --run-layers / --only / --regions)
    | record (compose nodes, compare with the S81 model graph tools/dsrom_1m_measure.s58_graph()); `all` = in order.

VEHICLE.  The S81 layer die's field is 2,417 element pairs in 128 return REGIONS (18-19 pairs, 3-5 of them BF16-capable;
results/uarch/dsrom_s81_released_binding_20261004/canonical stage_map region_bounds / BF_site_IDs).  Regions run in
parallel on the same x broadcast and are structurally identical; each ends in its own root and VM write port.  The
vehicle is the PINNED ot_v41_fieldtop_w17w10 (spine + VM model + ot_v41_field_w17w10 with the 1.2 GHz FAST=1/PP=1 W10
element, BP=0) built with NP = 32 pair slots, R = 1 region, NBF = 5: one region at full shape (its 18-19 real pairs
mapped onto slots -- BF16-capable pairs on the RTL's BF16 slots 0,6,12,19,25, FP8/FP4 pairs on the others; unused
slots hold no segment and never start), the full-K x stream from the spine (VRD 64 elements a cycle, golden quant_fp8 /
BF16 RNE in the spine), the region's 6-level return tree (64 leaves; a balanced tree over a region's 36-38 macros has
6 levels too) and root, and the VM row write.
PLACEMENT is the S81 canonical matrix map (matrix_map.jsonl.gz: per plan [segment, pair, superrow0, count, 128,
base, words]): every superrow (rows 2s, 2s+1) of every matrix on the pair the S81 allocator chose, its K segments
as the map gives them; ROM word addresses come from the W17/W10 image writer (tools/v41_die_images_w17w10.add_phase,
used unchanged with the S81 pair assignment in place of its own LPT).
ROWS are real released-checkpoint rows of rank 0; the golden router's six experts of each layer at the 1M token
(/home/ubuntu/w17work/ref/ctx1048576_seed20260930/ctx1048576_LNN.json).  L20's x is the GOLDEN 1M token's x of every
op (the passing TP-4 ISA executor's vector memory before the op's PC, /home/ubuntu/w17work/die/
ctx1048576_s20260930_L20_r0 vm_pcNNN.hex).  Other layers: golden attn_norm / ffn_norm from the layer record for the
phases that read them; operator-internal x (wq_b, cmp.wk, wo_a, wo_b, w2, Engram wkv) seeded.  Every row of every
region is checked bit for bit against tools/hdc_golden_v41 (R-ARITH chunk8: golden linear_q / linear_bf16, FP32 or BF16 by the op's row
format); the golden rows are also cross-checked against the ISA executor's own QE outputs.

PHASES.  The pinned spine runs ONE phase (one x vector, one cfg ROM entry) at a time and issues the next only when
every region has written every row (rows_left over all regions).  Matrices that share one x and x family form one
phase where the S81 placement fits the W10 element in every region (<= 8 segments and classes a pair, <= 16 FP8/FP4
or 8 BF16 words a round a pair); otherwise the S81 entries (the allocator's own units) are grouped greedily into the
fewest legal phases (e.g. compressor wkv and indexer weights_proj share a BF16 pair: two phases; wo_a group rows0 /
rows768 share a BF16 pair in the 3-BF region 93: two phases).  Matrices with different x are separate phases (wo_a
groups, each expert's w2, shared w2); a routed expert is its own phase (a static cfg ROM entry per expert).  Node cycles = sum over its phases of (go -> idle + 1) except the
last, + go -> last VM row write of the last, each phase at the max over the die's 128 regions.

WIRE.  The vehicle holds the spine's BST = 2 broadcast stages and a root writing straight into the VM.  The routed
die geometry adds, per phase: VM x root -> farthest cluster 30 stages (less the 2 in the vehicle) and cluster -> VM
33 (tools/uarch_model.DIE_SHRUNK_INTERIM expert_wire = 30 + 33, the model graph's own wire term); labelled
'routed die geometry wire stages'.  The S81 floorplan's own trunk (results/rtl/dsrom_s81_fulldie_20261004
floorplan.json trunk_stages, field_one_way 41 at 504 um) is reported as a sensitivity.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import copy
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import v41_die_images_w17w10 as I  # noqa: E402
import v41_rom_ksplit_bankmap as S  # noqa: E402
from rtl_v41_rom_array import Ckpt, Mat  # noqa: E402

VERILATOR = os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")
S81 = ROOT / "results/uarch/dsrom_s81_released_binding_20261004/canonical"
REC = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004/field.json"
GOLD_VM = Path("/home/ubuntu/w17work/die/ctx1048576_s20260930_L20_r0")
RANK = 0
NP, NR, NBF, PHW, VAW = 32, 1, 5, 2, 16
BF_SLOTS = [int(p) for p in I.bf16_pairs(NP, NBF)]            # the RTL's is_bf slots: 0, 6, 12, 19, 25
XBASE, OBASE = 0, 32768
CLK = 1.2e9
WIRE_X_TO_FARTHEST, WIRE_CLUSTER_TO_VM, BST_IN_VEHICLE = 30, 33, 2
RTL = [ROOT / f"rtl/v41rom/{n}.sv" for n in ("ot_v41_ret", "ot_v41_rom_elem_w10", "ot_v41_bterm", "ot_v41_chain",
                                             "ot_v41_segtree", "ot_v41_bf16_lanes", "ot_v41_fadd", "ot_v41_bmul2",
                                             "ot_v41_bterm2_w10", "ot_v41_chain2", "ot_v41_segtree2",
                                             "ot_v41_bf16_lanes2")]
RTL += [ROOT / "rtl/common/ot_prefix.sv"]
RTL += [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_fpu", "ot_hdc_fp32_mul_pipe", "ot_hdc_delay", "ot_hdc_cg")]
RTL += [ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv", ROOT / "rtl/hdc/v41/ot_hdc_actquant.sv"]
DIE = [ROOT / f"rtl/v41die/{n}.sv" for n in ("ot_v41_pair_w17w10", "ot_v41_retn_w17w10", "ot_v41_field_w17w10",
                                             "ot_v41_spine_w17w10", "ot_v41_fieldtop_w17w10")]
ROMS = [ROOT / "physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8.v",
        ROOT / "physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v"]
TB = ROOT / "rtl/test/dsrom_sys/tb_dsrom_1m_field.cpp"
TOOLS = [Path(__file__), ROOT / "tools/v41_die_images_w17w10.py", ROOT / "tools/v41_rom_ksplit_bankmap.py",
         ROOT / "tools/rtl_v41_rom_array.py", ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_golden.py",
         ROOT / "tools/v41_die_field.py"]
# --qelem N (default 0 = off): the FP8/FP4 pairs are the DS-V4.1 ROM q-element the S81 die is built from
# (ot_v41_rom_elem_q_qx_w10 at its routed parameters, QX = N; ot_v41_pair_w17w10 QELEM), BF16-capable pairs keep W10's
QRTL = [ROOT / f"rtl/v41rom/{n}.sv" for n in ("ot_v41_rom_elem_q_qx_w10", "ot_v41_rom_elem_qx_w10", "ot_v41_kreg",
                                              "ot_v41_chain3", "ot_v41_chain4", "ot_v41_fadd2",
                                              "ot_v41_bterm3_w10", "ot_v41_bterm4_w10",
                                              "ot_v41_segtree3", "ot_v41_segtree4", "ot_v41_segtree5")]
SOURCES = sorted(set(RTL + DIE + ROMS + [TB] + TOOLS))
S81_FILES = [S81 / "matrix_map.jsonl.gz", S81 / "stage_map.json", S81 / "inventory.json", S81 / "binding.json"]

# phase groups: (node, group, x source).  x source: "attn_norm" / "ffn_norm" (the golden layer's vector), or
# "internal" (an operator-internal vector: the golden VM for L20, a seeded vector elsewhere)
def group_of(alias: str, expert):
    if alias in ("wq_a", "wkv"):
        return "attn.a_proj", "a_proj.fp8", "attn_norm"
    if alias.startswith("compressor.") or alias == "indexer.weights_proj":
        return "attn.a_proj", "a_proj.bf16", "attn_norm"
    if alias.startswith("wq_b") or alias == "indexer.wq_b":
        return "attn.wq_b", "wq_b", "internal"
    if alias == "indexer.wk":
        return "attn.cmp.wk", "cmp.wk", "internal"
    if alias.startswith("wo_a.group"):
        return "attn.wo_a", "wo_a.g" + alias.split(".")[1][5:], "internal"
    if alias.startswith("wo_b"):
        return "attn.wo_b", "wo_b", "internal"
    if alias == "gate":
        return "ffn.router", "router", "ffn_norm"
    if alias in ("shared.w1", "shared.w3"):
        return "ffn.shared_gu", "shared_gu", "ffn_norm"
    if expert is not None and alias.endswith((".w1", ".w3")):
        return "ffn.experts_gu", f"exp{expert}.gu", "ffn_norm"
    if expert is not None and alias.endswith(".w2"):
        return "ffn.down", f"exp{expert}.w2", "internal"
    if alias == "shared.w2":
        return "ffn.down", "shared.w2", "internal"
    if alias.startswith("engram.wkv"):
        return "E1.wkv", "engram.wkv", "internal"
    raise KeyError(alias)


GROUP_ORDER = ["a_proj.fp8", "a_proj.bf16", "wq_b", "cmp.wk", "wo_a.g0", "wo_a.g1", "wo_b", "router", "shared_gu"]
# the W17 L20 rank-0 program (results/rtl/w17_die_l20_images.json): op PCs whose x each L20 group uses
L20_PCS = {"a_proj.fp8": [7, 8], "a_proj.bf16": [24, 42], "wq_b": [14, 39], "cmp.wk": [30], "wo_a.g0": [68],
           "wo_a.g1": [69], "wo_b": [71], "router": [86], "shared_gu": [84, 85], "shared.w2": [89],
           **{f"exp{e}.gu": [a, b] for e, (a, b, _) in {41: (97, 98, 110), 65: (99, 100, 115), 158: (103, 104, 120),
                                                         164: (113, 114, 125), 259: (118, 119, 128),
                                                         266: (123, 124, 131)}.items()},
           **{f"exp{e}.w2": [c] for e, c in {41: 110, 65: 115, 158: 120, 164: 125, 259: 128, 266: 131}.items()}}
LAYERS = (0, 1, 2, 3, 20, 21, 24)       # one per layer type (tools/dsrom_1m_measure.TYPES reps)
REF = Path("/home/ubuntu/w17work/ref/ctx1048576_seed20260930")
SEED = 20260930


def sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ golden VM
def read_sparse(path: Path) -> dict:
    vm, a = {}, 0
    for ln in path.read_text().split():
        if ln.startswith("@"):
            a = int(ln[1:], 16)
        else:
            vm[a] = int(ln, 16)
            a += 1
    return vm


def vm_vec(vm: dict, base: int, n: int) -> np.ndarray:
    return np.array([vm.get(base + i, 0) for i in range(n)], dtype=np.uint32)


# ------------------------------------------------------------------------------------------------ plan
def illegal(mats, reg) -> str | None:
    """The W10 element's per-phase limits (tools/v41_die_images_w17w10.add_phase asserts): <= NSEG segments and
    classes per pair, disjoint unit classes, <= NCH (FP8/FP4) / NCHB (BF16) words per round (q, b) per pair."""
    per = {}
    for mi, m in enumerate(mats):
        for s, si, p in m["regions"].get(str(reg), []):
            e0, el = m["segments"][si]
            per.setdefault(p, []).append(dict(fmt=m["fmt"], e0=e0, elems=el, row=s, tensor=mi))
    for p, segs in per.items():
        if len(segs) > I.NSEG:
            return f"pair {p}: {len(segs)} segments > {I.NSEG}"
        keys = sorted({S.unit_range(g["fmt"], g["e0"], g["elems"]) for g in segs})
        if len(keys) > I.NSEG or any(a1 > b0 for (_, a1), (b0, _) in zip(keys, keys[1:])):
            return f"pair {p}: classes {keys}"
        dem = {}
        for i, u, b, h in S.element_order(segs):
            g = segs[i]
            q = (u - S.unit_range(g["fmt"], g["e0"], g["elems"])[0]) // S.IL
            dem[(q, b)] = dem.get((q, b), 0) + 1
        cap = I.NCHB if segs[0]["fmt"] == "bf16" else I.NCH
        if max(dem.values()) > cap:
            return f"pair {p}: {max(dem.values())} words per round > {cap}"
    return None


def rand_x(name: str, K: int, bf: bool) -> np.ndarray:
    """A seeded operator-internal x (the W17 field gate's distributions): BF16-valued for the FP8-quantised family,
    FP32 for the BF16 family (the spine rounds it RNE)."""
    rng = np.random.default_rng([SEED, zlib.crc32(name.encode())])
    v = (rng.standard_normal(K) * 0.37).astype(np.float32) if bf else G.to_bf16((rng.standard_normal(K) * 0.5)
                                                                                 .astype(G.F))
    return G.bits(np.asarray(v, dtype=G.F)).astype(np.uint32)


def layer_groups(L, ents, rb, bfs):
    """S81 entries of layer L (non-expert + the golden experts) -> {group: (node, xsrc, [mat dicts])}."""
    groups = {}
    for e in ents:
        node, grp, xsrc = group_of(e["alias"], e["expert"])
        sl = e["rank_slices"][RANK]
        regions = {}
        for seg, pair, s0, cnt, stride, base, words in e["plans"]:
            for k in range(cnt):
                sr = s0 + k * stride
                reg = sr % 128
                assert rb[reg] <= pair < rb[reg + 1], (e["alias"], sr, pair)
                if e["format"] == "bf16":
                    assert pair in bfs, (e["alias"], pair)
                regions.setdefault(reg, []).append([sr, seg, pair])
        groups.setdefault(grp, (node, xsrc, []))[2].append(dict(
            alias=e["alias"], tensor=e["tensor"][:-len(".weight")], fmt=e["format"], K=e["K"], rows=sl["rows"],
            cols=sl["cols"], entry_rows=e["rows"], segments=e["segments"], stage=e["stage"],
            t_read_words_max=e["t_read_words_max"], issue_cycles_LAT8_condition=e["issue_cycles_LAT8_condition"],
            conversion=e["conversion"], isa=None, regions={str(k): sorted(v) for k, v in sorted(regions.items())}))
    order = {g: i for i, g in enumerate(GROUP_ORDER)}
    return dict(sorted(groups.items(), key=lambda kv: (order.get(kv[0], 50 + ("w2" in kv[0]) + 2 * (kv[0] == "shared.w2")),
                                                       kv[0])))


def phase_groups(mats):
    """Existing emitter partition, shared with metadata-only source binding."""
    groups = []
    for m in mats:
        if groups and not any(illegal(groups[-1] + [m], r) for r in range(128)):
            groups[-1].append(m)
        else:
            groups.append([m])
    for g in groups:
        bad = [r for r in range(128) if illegal(g, r)]
        if bad:
            raise ValueError((g[0]["alias"], bad[:4], illegal(g, bad[0])))
    return groups


def cmd_bind_schedules(a):
    """Existing phase partition + literal dispatch metadata; no payload or x."""
    from dsrom_s81_execution_binding import CanonicalS81Execution
    from dsrom_stage_program_join import digest
    coverage = ROOT / "results/rtl/dsrom_recovery_20261004/coverage_manifest"
    archive = coverage / "inputs/all40_golden_json.json.gz"
    records = json.loads(gzip.decompress(archive.read_bytes()))
    golden = {r["layer"]: json.loads(r["json_bytes"]) for r in records}
    if set(golden) != set(range(40)):
        raise ValueError("actual all40 source selections required")
    retained = json.loads(gzip.decompress((coverage / "inputs/retained_plan.json.gz").read_bytes()))
    layers = [int(x) for x in a.layers.split(",")]
    if layers != sorted(set(layers)) or not set(layers) <= set(range(40)):
        raise ValueError("ordered distinct actual layers required")
    out = a.work.resolve()
    out.mkdir(parents=True, exist_ok=False)
    execution = CanonicalS81Execution(ROOT)
    sm = execution.stage_join.stage_map
    rb, bfs = sm["region_bounds"], set(sm["BF_site_IDs"])
    entries = {L: [] for L in layers}
    for row in execution.stage_join.by_identity.values():
        m = row["matrix"]; L = m["layer"]
        if L in entries and (m["expert"] is None or m["expert"] in golden[L]["experts"]):
            entries[L].append(m)
    pins = dict(execution.input_sha256)
    for p in (Path(__file__), ROOT/"tools/dsrom_s81_execution_binding.py",
              ROOT/"tools/dsrom_stage_program_join.py", ROOT/"tools/dsrom_s82_payload_interface.py",
              ROOT/"tools/hdc_isa_v41.py", ROOT/"tools/v41_rom_ksplit_bankmap.py",
              ROOT/"tools/v41_die_images_w17w10.py", archive,
              coverage/"inputs/retained_plan.json.gz"):
        pins[str(p.relative_to(ROOT))] = sha(p)
    files, totals = [], dict(source_operations=0, canonical_dispatch_fragments=0,
                            observer_phases=0, selected_matrix_records=0)
    for L in layers:
        g = golden[L]
        if (g["layer"],g["context"],g["position"],g["arith"]) != (L,1048576,1048575,"chunk8"):
            raise ValueError("golden source identity mismatch")
        eids = g["experts"]
        if len(eids)!=6 or eids!=sorted(set(eids)):
            raise ValueError("source dispatcher requires actual ascending six EIDs")
        native, matrix_sources = [], {}
        for node in execution.target_source_nodes([L],position=1048575,include_head=False):
            b = execution.source.bindings[node]
            if not b.get("address_bound"):
                continue
            source = execution.source.nodes[node]
            rank_dispatches=[]
            for rank in range(4):
                resolved=execution.source.resolve(node,rank,expert_ids=eids if b["selector_slot"] is not None else None)
                try:
                    dispatch=execution.dispatch(node,rank,expert_ids=eids if b["selector_slot"] is not None else None)
                except ValueError as error:
                    if str(error)!="original native ME admission fails":
                        raise
                    from dsrom_native_weight_address_join import me_failures
                    # Record source/CFG geometry even when ORIGINAL native ME
                    # cannot issue. This is NOT an admitted/emitted command.
                    dispatch=dict(fragments=[])
                    for rf in resolved["fragments"]:
                        m=rf["matrix"]; row=execution.stage_join.by_identity[(L,m["alias"])]
                        dispatch["fragments"].append(dict(stage=row["stage"],rank=rank,
                            die_id=rf["die_id"],phase=row["phase"],key=row["key"],
                            gather_local_rows=rf["gather_local_rows"],ordered_K=rf["ordered_K"],
                            source_matrix_sha256=row["matrix_sha256"],
                            cfg_logical_range=[25*row["phase"],25*(row["phase"]+1)],
                            native_dispatch_refused=True,native_admission_failures=me_failures(source["instruction"]),
                            source_instruction=source["instruction"]))
                fragments=[]
                for f,rf in zip(dispatch["fragments"],resolved["fragments"]):
                    m=rf["matrix"]
                    record={k:v for k,v in f.items() if k not in ("word","original_word")}
                    record.update(alias=m["alias"],tensor=m["tensor"],
                                  source_rank_slice=rf["source_slice"],
                                  emitted_word_sha256=hashlib.sha256(f["word"].to_bytes(256,"little")).hexdigest() if "word" in f else None)
                    fragments.append(record)
                    if rank==0:
                        matrix_sources.setdefault(m["alias"],[]).append(dict(
                            node=node, instruction_index=source["instruction_index"],
                            template_word_sha256=source["template_word_sha256"],
                            phase=f["phase"],key=f["key"],stage=f["stage"],
                            source_matrix_sha256=f["source_matrix_sha256"]))
                rank_dispatches.append(dict(requested_rank=rank,fragments=fragments))
            native.append(dict(node=node,instruction_index=source["instruction_index"],
                template_word_sha256=source["template_word_sha256"],selector_slot=b["selector_slot"],
                selected_expert=eids[b["selector_slot"]] if b["selector_slot"] is not None else None,
                input_VM_elements=b["consumer_X_FP32_VM_elements"],
                output_VM_base=b["consumer_output_base_elements"],ranks=rank_dispatches))
        phases=[]
        for grp,(node,xsrc,mats) in layer_groups(L,entries[L],rb,bfs).items():
            stages={m["stage"] for m in mats}
            if len(stages)!=1:
                raise ValueError((L,grp,"existing emitter requires single stage",stages))
            if any(m["K"]!=mats[0]["K"] or (m["fmt"]=="bf16")!=(mats[0]["fmt"]=="bf16") for m in mats):
                raise ValueError((L,grp,"existing emitter K/format grouping changed"))
            groups=phase_groups(mats)
            for group in groups:
                name=f"L{L}.{grp}"+("" if len(groups)==1 else "."+"+".join(m["alias"] for m in group))
                for m in group:
                    original=next(e for e in entries[L] if e["alias"]==m["alias"])
                    m["source_bindings"]=matrix_sources.get(m["alias"],[])
                    if not m["source_bindings"]:
                        raise ValueError((L,m["alias"],"missing literal source binding"))
                    m["rank_slices"]=original["rank_slices"]
                    m["ordered_physical_plan_sha256"]=digest(original["plans"])
                phases.append(dict(layer=L,node=node,phase=name,group=grp,stage=next(iter(stages)),
                    K=group[0]["K"],out="fp32" if group[0]["fmt"]=="bf16" or grp=="wo_b" else "bf16",
                    fmts=sorted({m["fmt"] for m in group}),mats=group,
                    regions=sorted({int(r) for m in group for r in m["regions"]}),
                    input_source_kind=xsrc,input_activation_available=False))
        used={m["alias"] for p in phases for m in p["mats"]}
        if used!=set(matrix_sources):
            raise ValueError((L,"observer/source matrix coverage differs",used^set(matrix_sources)))
        record=dict(layer=L,context=1048576,position=1048575,arith="chunk8",experts=eids,
            observer_phase_count=len(phases),observer_phase_order=[p["phase"] for p in phases],
            native_source_order=[n["node"] for n in native],native_dispatch=native,
            phases=phases,rank=0,region_bounds=rb,bf_sites=sorted(bfs),
            allocation="canonical S81 NP2417/BF519/R128; NO R93 remap",
            source_schedule_bound=True,native_execution_qualified=False,
            internal_activation_payloads_provided=False,accepted_runtime_journal=None,
            native_dispatch_refusals=[dict(node=n["node"],failures=r["fragments"][0]["native_admission_failures"])
                for n in native for r in n["ranks"][:1] if r["fragments"][0].get("native_dispatch_refused")])
        path=out/f"L{L:02d}.json.gz"
        path.write_bytes(gzip.compress(json.dumps(record,sort_keys=True,separators=(",",":")).encode(),mtime=0))
        files.append(dict(layer=L,path=path.name,sha256=sha(path),
                          phase_count=len(phases),source_operations=len(native)))
        totals["observer_phases"]+=len(phases);totals["source_operations"]+=len(native)
        totals["canonical_dispatch_fragments"]+=sum(len(r["fragments"]) for n in native for r in n["ranks"])
        totals["selected_matrix_records"]+=len(entries[L])
        print(f"L{L:02d}: {len(phases)} phases, {len(native)} source ops, source binding ready",flush=True)
    manifest=dict(schema="opentallas.dsrom.existing-field-source-schedules.v1",layers=layers,
        inputs=pins,files=files,totals=totals,
        retained_observer_layers=retained["layers"],
        missing_layers_resolved=[L for L in layers if L not in retained["layers"]],
        source_order="Literal demand-r5 instruction order; rank fragment order is existing dispatch order",
        observer_order="Existing dsrom_1m_field.layer_groups and greedy phase partition; NOT native issue order",
        current_candidate_difference="Retained planv is S81+R93 BF520. These canonical BF519 schedules have no remap; candidate phase merge must use actual existing R93 source recipe, not inherit canonical CFG IDs.",
        no_payload_or_activation_generated=True,new_archives=0,new_frontend_builds=0,
        measured_gain=None,accepted_runtime_journal=None)
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return 0


def cmd_plan(a):
    work = a.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    sm = json.loads((S81 / "stage_map.json").read_text())
    rb, bfs = sm["region_bounds"], set(sm["BF_site_IDs"])
    layers = [int(x) for x in a.layers.split(",")]
    experts, ref_sha = {}, {}
    for L in layers:
        j = REF / f"ctx1048576_L{L:02d}.json"
        experts[L] = json.loads(j.read_text())["experts"]
        ref_sha[L] = dict(json=sha(j), npz=sha(REF / f"ctx1048576_L{L:02d}.npz"))
    ents = {L: [] for L in layers}
    with gzip.open(S81 / "matrix_map.jsonl.gz", "rt") as f:
        for ln in f:
            r = json.loads(ln)
            L = r["layer"]
            if L in ents and (r["expert"] is None or r["expert"] in experts[L]):
                ents[L].append(r)
    wops = {o["pc"]: o for o in json.loads((a.gold_vm / "weight_ops.json").read_text())["ops"]}
    assert json.loads((a.gold_vm / "weight_ops.json").read_text())["experts"] == experts[20]
    wjs = {o["pc"]: o for o in json.loads((a.gold_vm.parent / "ctx1048576_s20260930_L20" / "r0" /
                                           "weights.json").read_text())}
    vms = {}

    def vm(pc):
        if pc not in vms:
            vms[pc] = read_sparse(a.gold_vm / f"vm_pc{pc:03d}.hex")
        return vms[pc]

    phases, xs, xsrc_rec, notes = [], {}, {}, []
    for L in layers:
        z = np.load(REF / f"ctx1048576_L{L:02d}.npz")
        for grp, (node, xsrc, mats) in layer_groups(L, ents[L], rb, bfs).items():
            K = mats[0]["K"]
            bf = mats[0]["fmt"] == "bf16"
            assert all(m["K"] == K for m in mats) and all((m["fmt"] == "bf16") == bf for m in mats), (L, grp)
            out = "fp32" if (bf or grp == "wo_b") else "bf16"
            if L == 20:                       # the golden VM before each op: every L20 x is the 1M token's
                xv = None
                for pc in L20_PCS[grp]:
                    op = wops[pc]
                    v = vm_vec(vm(pc - 1), op["x_vm"], op["k"])
                    assert xv is None or np.array_equal(v, xv), (grp, "ops of one phase must share x")
                    xv = v
                    assert wjs[pc]["out"] == out, (grp, pc)
                    for m in mats:
                        if op["unit"] == "QE" and op["tensor"] == m["tensor"] + ".weight":
                            lo = (op["rows"] or [0, op["out_rows"]])[0]
                            m["isa"] = dict(pc=pc, out_vm=op["out_vm"], row0=m["rows"][0] - lo,
                                            fp32=bool(op["unrounded"]))
                src = f"golden VM {a.gold_vm.name} vm_pc{L20_PCS[grp][0] - 1:03d} @ {wops[L20_PCS[grp][0]]['x_vm']}"
                if xsrc != "internal":        # the golden layer record holds the same vector
                    g = G.bits(np.asarray(z[f"L{L}.{xsrc}"], dtype=G.F)).astype(np.uint32)
                    if not np.array_equal(g, xv):
                        notes.append(f"L20 {grp}: VM x differs from ctx1048576_L20.npz {xsrc}")
            elif xsrc != "internal":
                xv = G.bits(np.asarray(z[f"L{L}.{xsrc}"], dtype=G.F)).astype(np.uint32)
                src = f"golden ctx1048576_L{L:02d}.npz L{L}.{xsrc}"
            else:
                xv = rand_x(f"L{L}.{grp}", K, bf)
                src = f"seeded (SEED {SEED}, crc32('L{L}.{grp}')); operator-internal x not in the golden layer record"
            assert len(xv) == K
            stages = {m["stage"] for m in mats}
            assert len(stages) == 1, (L, grp, stages)
            stage = stages.pop()
            # one phase if the S81 placement fits the element in every region (a phase is die-global); else the S81
            # entries (the allocator's own units) are grouped greedily into the fewest legal phases, in order
            bad = [r for r in range(128) if illegal(mats, r)]
            groups = phase_groups(mats)
            for g in groups:
                bad_g = [r for r in range(128) if illegal(g, r)]
                assert not bad_g, (L, grp, g[0]["alias"], bad_g[:4], illegal(g, bad_g[0]))
                name = f"L{L}.{grp}" + ("" if len(groups) == 1 else "." + "+".join(x["alias"] for x in g))
                phases.append(dict(layer=L, node=node, phase=name, group=grp, stage=stage, x_source=src, out=out,
                                   K=K, fmts=sorted({m["fmt"] for m in g}), mats=g,
                                   split_reason=(f"fused phase exceeds the element in regions {bad[:8]}: "
                                                 f"{illegal(mats, bad[0])}") if bad else None,
                                   regions=sorted({int(r) for m in g for r in m["regions"]})))
                xs[name] = xv
    np.savez(work / "x.npz", **xs)
    plan = dict(schema="opentallas.dsrom.1m_field.plan.v2", layers=layers, rank=RANK, experts=experts,
                region_bounds=rb, bf_sites=sorted(bfs), phases=phases, notes=notes, ref=str(REF), ref_sha256=ref_sha,
                gold_vm=str(a.gold_vm), gold_weight_ops_sha256=sha(a.gold_vm / "weight_ops.json"),
                x_sha256={k: hashlib.sha256(v.tobytes()).hexdigest() for k, v in xs.items()})
    (work / "plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    for p in phases:
        print(f"{p['phase']:40s} stage {p['stage']} K {p['K']} {p['fmts']} out {p['out']} regions {len(p['regions'])}")
    print("\n".join(notes))
    return 0


# ------------------------------------------------------------------------------------------------ build
def cmd_build(a):
    out = (a.work / "build").resolve()
    out.mkdir(parents=True, exist_ok=True)
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([VERILATOR, "-V"], text=True)).group(1)
    params = ["-GFAST=1", "-GPP=1", "-GBP=0", f"-GNP={NP}", f"-GR={NR}", f"-GNBF={NBF}", f"-GPHW={PHW}", f"-GVAW={VAW}"]
    rtl = RTL + (QRTL if a.qelem else [])
    if a.qelem:
        params += ["-GQELEM=1", f"-GQXV={a.qelem}"]
    mdir = out / "flat"
    steps = []
    for name, cmd in (
            ("verilate", [VERILATOR, "--cc", "-O3", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD",
                          "--top-module", "ot_v41_fieldtop_w17w10", "--prefix", "Vflat", "--Mdir", str(mdir), *params,
                          *map(str, DIE + ROMS + rtl)]),
            ("make", ["make", "-C", str(mdir), "-f", "Vflat.mk", f"-j{a.jobs}", "Vflat__ALL.a", "OPT_FAST=-O2",
                      "OPT_SLOW=-O1"]),
            ("link", ["g++", "-std=c++20", "-O2", f"-DNR={NR}", f"-DVAW={VAW}", f"-I{vroot}/include",
                      f"-I{vroot}/include/vltstd", f"-I{mdir}", str(TB), str(mdir / "Vflat__ALL.a"),
                      f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp",
                      "-pthread", "-o", str(out / "tb")])):
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, text=True)
        (out / f"{name}.log").write_text(p.stdout + p.stderr)
        steps.append(dict(name=name, seconds=round(time.time() - t0, 1), returncode=p.returncode))
        print(name, steps[-1], flush=True)
        if p.returncode:
            raise SystemExit(f"{name} failed: {(p.stdout + p.stderr)[-3000:]}")
    (out / "build.json").write_text(json.dumps(dict(steps=steps, params=params, qelem=a.qelem, tb_sha256=sha(out / "tb"),
                                                    simulator=subprocess.check_output([VERILATOR, "--version"],
                                                                                      text=True).strip()),
                                               indent=1) + "\n")
    return 0


# ------------------------------------------------------------------------------------------------ region image
def take(m, rows):
    """Row subset of a matrix slice (the region's superrows)."""
    n = copy.copy(m)
    rows = np.asarray(rows, dtype=np.int64)
    n.rows = len(rows)
    if hasattr(m, "u16"):
        n.u16, n.wf = m.u16[rows], m.wf[rows]
    else:
        n.exp = m.exp[rows]
        if m.fmt == "fp8":
            n.codes = m.codes[rows]
        else:
            n.nib = m.nib[rows]
        n.w = G.Q8(m.w.q[rows], m.w.e[rows])
    return n


_PLACE = {}


def s81_place(field, mats):
    """W17/W10 add_phase's placement hook: the S81 allocator's pair for every (superrow, segment)."""
    out, info, off = [], [], 0
    load = np.zeros(field.np, dtype=np.int64)
    for mi, m in enumerate(mats):
        segs = [tuple(s) for s in m.s81_segments]
        info.append(dict(off=off, srows=-(-m.rows // 2), s=len(segs), segs=segs))
        for j, si, slot in m.s81_place:
            e0, el = segs[si]
            load[slot] += S.seg_words(m.fmt, e0, el)
            out.append(dict(mi=mi, tensor=mi, fmt=m.fmt, K=m.K, row=j, e0=e0, elems=el, pair=slot, seg=si,
                            nseg=len(segs)))
        off += m.rows
    return out, info, int(load.max())


I._place = s81_place

_FULL = {}


def cmd_extract(a):
    """The rank-0 checkpoint slices of every phase, as the matrix objects hold them (codes / nibbles / UE8M0 bytes,
    BF16 words), so a compute host without the checkpoint shards can run the vehicle."""
    import v41_die_field as F
    work = a.work.resolve()
    plan = json.loads((work / "plan.json").read_text())
    ck = Ckpt(a.snapshot)
    (work / "mats").mkdir(exist_ok=True)
    for ph in plan["phases"]:
        arr = {}
        for i, m in enumerate(ph["mats"]):
            (r0, r1), (c0, c1) = m["rows"], m["cols"]
            x = F.mat(ck, m["tensor"], m["fmt"], r1 - r0, c1 - c0, r0, c0)
            if m["fmt"] == "bf16":
                arr[f"{i}.u16"] = x.u16
            else:
                arr[f"{i}.exp"] = x.exp
                arr[f"{i}.{'codes' if m['fmt'] == 'fp8' else 'nib'}"] = x.codes if m["fmt"] == "fp8" else \
                    x.nib.astype(np.uint8)
        np.savez(work / "mats" / f"{ph['phase']}.npz", **arr)
    (work / "mats" / "checkpoint.json").write_text(json.dumps(dict(revision=a.snapshot.name,
                                                                   header_sha256=ck.pins)) + "\n")
    print(len(plan["phases"]), "phase slice files")
    return 0


def full_mats(work, ph):
    """Matrix objects (tools/rtl_v41_rom_array.Mat interface) of the phase's rank slices from work/mats."""
    key = ph["phase"]
    if key not in _FULL:
        z = np.load(Path(work) / "mats" / f"{key}.npz")
        ms = []
        for i, m in enumerate(ph["mats"]):
            (r0, r1), (c0, c1) = m["rows"], m["cols"]
            x = Mat.__new__(Mat)
            x.name, x.fmt, x.rows, x.K, x.r0, x.k0, x.phase = m["tensor"], m["fmt"], r1 - r0, c1 - c0, r0, c0, "wq_b"
            if m["fmt"] == "bf16":
                x.u16 = z[f"{i}.u16"]
                x.wf = G.from_bits(x.u16.astype(np.uint32) << 16)
            else:
                x.exp = z[f"{i}.exp"]
                if m["fmt"] == "fp8":
                    x.codes = z[f"{i}.codes"]
                    q = G.E4M3[x.codes]
                else:
                    x.nib = z[f"{i}.nib"]
                    q = G.E2M1[x.nib]
                x.w = G.Q8(q.astype(np.float64), x.exp.astype(np.int64) - 127)
            ms.append(x)
        _FULL.clear()
        _FULL[key] = ms
    return _FULL[key]


def region_image(work, ph, reg, rb, bfs, x, img: Path):
    """Image of region `reg` of phase `ph` on the vehicle; returns (meta, expect {addr: word}, isa_xcheck)."""
    pairs = list(range(rb[reg], rb[reg + 1]))
    bfp = [p for p in pairs if p in bfs]
    qp = [p for p in pairs if p not in bfs]
    assert len(bfp) <= len(BF_SLOTS) and len(qp) <= NP - len(BF_SLOTS)
    qslots = [s for s in range(NP) if s not in BF_SLOTS]
    slot = {p: BF_SLOTS[i] for i, p in enumerate(bfp)} | {p: qslots[i] for i, p in enumerate(qp)}
    fld = I.Field(NP, NR, NBF, pp=True, fast=True)
    assert [int(s) for s in np.flatnonzero(fld.bf)] == BF_SLOTS
    mats, gmap = [], []
    for mm, full in zip(ph["mats"], full_mats(work, ph)):
        pl = mm["regions"].get(str(reg), [])
        if not pl:
            continue
        srows = sorted({s for s, _, _ in pl})
        loc = {s: j for j, s in enumerate(srows)}
        rows = [r for s in srows for r in (2 * s, 2 * s + 1) if r < mm["entry_rows"]]
        sub = take(full, rows)
        sub.s81_segments = mm["segments"]
        sub.s81_place = [(loc[s], seg, slot[p]) for s, seg, p in pl]
        mats.append(sub)
        gmap.append((mm, rows))
    fp32 = ph["out"] == "fp32"
    meta = I.add_phase(fld, mats, (fp32, fp32), 0)
    I.write_field(fld, img, PHW)
    vm = np.zeros(1 << VAW, dtype=np.uint32)
    vm[XBASE:XBASE + ph["K"]] = x
    (img / "vm.hex").write_text("".join(f"{int(v):08x}\n" for v in vm))
    gold = I.golden_phase(mats, G.from_bits(x).astype(G.F))
    expect, xcheck = {}, []
    off = 0
    for (mm, rows), m in zip(gmap, mats):
        for i, r in enumerate(rows):
            f32, b16 = gold[off + i]
            expect[OBASE + off + i] = f32 if fp32 else (b16 << 16)
            xcheck.append((mm["alias"], r, f32, b16))
        off += m.rows
    words = {}
    for p, sl in slot.items():
        segs_on = 0
        for mm in ph["mats"]:
            segs_on += sum(1 for s, _, pp in mm["regions"].get(str(reg), []) if pp == p)
        words[p] = segs_on
    meta = dict(nbeat=meta["nbeat"], t_read=meta["t_read"], t_phase_model=meta["t_phase_model"],
                nrows=meta["nrows"], segments_per_pair_max=meta["segments_per_pair_max"],
                pairs=len(pairs), bf_pairs=len(bfp), busy_pairs=sum(1 for v in words.values() if v))
    return meta, expect, xcheck


def run_one(args):
    work, ph, reg, rb, bfs, keep = args
    G.set_arith("chunk8")
    x = np.load(Path(work) / "x.npz")[ph["phase"]]
    rd = Path(work) / "runs" / ph["phase"] / f"r{reg:03d}"
    if rd.exists():
        shutil.rmtree(rd)
    img = rd / "img"
    img.mkdir(parents=True)
    t0 = time.time()
    meta, expect, xcheck = region_image(work, ph, reg, rb, bfs, x, img)
    (rd / "ops.txt").write_text(f"0 0 {XBASE} {ph['K']} {OBASE} {meta['nrows']}\n")
    t1 = time.time()
    p = subprocess.run([str(Path(work) / "build" / "tb"), str(img), str(rd / "ops.txt")], capture_output=True,
                       text=True)
    t2 = time.time()
    lines = p.stdout.splitlines()
    writes = {}
    for ln in lines:
        t = ln.split()
        if t and t[0] == "W":
            ad = int(t[2])
            writes.setdefault(ad, []).append(int(t[3], 16))
    opl = [ln for ln in lines if ln.startswith("OP ")]
    op = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", opl[0])} if opl else {}
    wrong = [ad for ad, v in expect.items() if writes.get(ad) != [v]]
    extra = [ad for ad in writes if ad not in expect]
    ok = p.returncode == 0 and bool(lines) and lines[-1].startswith("PASS") and not wrong and not extra
    res = dict(phase=ph["phase"], region=reg, pass_=ok, rows=len(expect), mismatched=len(wrong), extra=len(extra),
               first_mismatch=[(ad, writes.get(ad), expect[ad]) for ad in wrong[:3]], **meta,
               go=op.get("go"), first_w=op.get("first_w"), last_w=op.get("last_w"), idle=op.get("idle"),
               phase_cycles=op.get("phase_cycles"), fault=op.get("fault"),
               go_to_last_w=(op["last_w"] - op["go"]) if op.get("last_w", -1) >= 0 else None,
               go_to_idle=(op["idle"] - op["go"]) if op else None,
               image_s=round(t1 - t0, 2), sim_s=round(t2 - t1, 2), tail=lines[-1:] if lines else p.stderr[-300:])
    (rd / "result.json").write_text(json.dumps(dict(res, xcheck=xcheck)) + "\n")
    if not keep:
        shutil.rmtree(img)
        (rd / "sim.log").write_text("\n".join(ln for ln in lines if not ln.startswith("W ")) + "\n")
    else:
        (rd / "sim.log").write_text(p.stdout + p.stderr)
    return res


def cmd_run(a):
    work = a.work.resolve()
    plan = json.loads((work / "plan.json").read_text())
    rb, bfs = plan["region_bounds"], set(plan["bf_sites"])
    only = set(a.only.split(",")) if a.only else None
    tasks = []
    for ph in plan["phases"]:
        if only and ph["phase"] not in only:
            continue
        if a.run_layers and ph["layer"] not in {int(x) for x in a.run_layers.split(",")}:
            continue
        regs = ph["regions"] if not a.regions else [r for r in ph["regions"] if r in set(map(int, a.regions.split(",")))]
        for reg in regs:
            if not a.force and (work / "runs" / ph["phase"] / f"r{reg:03d}" / "result.json").exists():
                continue
            tasks.append((str(work), ph, reg, rb, bfs, a.keep))
    # group by phase so a worker reuses the phase's checkpoint slices
    tasks.sort(key=lambda t: (t[1]["phase"], t[2]))
    print(f"{len(tasks)} region runs", flush=True)
    bad = 0
    with cf.ProcessPoolExecutor(a.jobs) as ex:
        for i, r in enumerate(ex.map(run_one, tasks, chunksize=4)):
            bad += not r["pass_"]
            if not r["pass_"] or i % 50 == 0:
                print(i, r["phase"], r["region"], "PASS" if r["pass_"] else "FAIL", r["rows"], r["go_to_last_w"],
                      r["tail"], r["first_mismatch"], flush=True)
    print("failed", bad)
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ record
def model_nodes(dump: Path | None):
    if dump and dump.exists():
        d = json.loads(dump.read_text())
        src = dict(kind="dump", path=str(dump), sha256=sha(dump))
    else:
        import dsrom_1m_measure as M
        g, T, p = M.s58_graph()
        d = {}
        for n, nd in g.nodes.items():
            if nd.get("_uarch"):
                d[n] = dict(issue_cyc_1p2=nd["issue"] * CLK, depth_cyc_1p2=nd["depth"] * CLK,
                            ctrl_cyc_1p2=nd.get("ctrl", 0.0) * CLK, _uarch=nd.get("_uarch"))
        src = dict(kind="tools/dsrom_1m_measure.s58_graph()", T_s=T)
    return d, src


def cmd_record(a):
    work = a.work.resolve()
    plan = json.loads((work / "plan.json").read_text())
    build = json.loads((work / "build" / "build.json").read_text())
    res = {}
    for ph in plan["phases"]:
        rs = []
        for reg in ph["regions"]:
            f = work / "runs" / ph["phase"] / f"r{reg:03d}" / "result.json"
            rs.append(json.loads(f.read_text()) if f.exists() else None)
        res[ph["phase"]] = rs
    # ISA cross-check of the golden rows (QE ops: the executor's own output words)
    isa_bad, isa_n = 0, 0
    vms = {}
    for ph in plan["phases"]:
        for mm in ph["mats"]:
            if not mm["isa"]:
                continue
            pc = mm["isa"]["pc"]
            if pc not in vms:
                vms[pc] = read_sparse(Path(plan["gold_vm"]) / f"vm_pc{pc:03d}.hex")
    for ph in plan["phases"]:
        isa = {mm["alias"]: mm["isa"] for mm in ph["mats"]}
        for r in res[ph["phase"]]:
            if r is None:
                continue
            for al, row, f32, b16 in r["xcheck"]:
                i = isa[al]
                if not i:
                    continue
                w = vms[i["pc"]].get(i["out_vm"] + i["row0"] + row, 0)
                isa_n += 1
                isa_bad += w != (f32 if i["fp32"] else (b16 << 16))
    model, msrc = model_nodes(a.model_dump)
    W = WIRE_X_TO_FARTHEST - BST_IN_VEHICLE + WIRE_CLUSTER_TO_VM
    fp = json.loads((ROOT / "results/rtl/dsrom_s81_fulldie_20261004/floorplan.json").read_text())["trunk_stages"]
    W_S81 = 2 * fp["stages_at_504"]["field_one_way"] - BST_IN_VEHICLE
    phases_out, nodes = [], {}
    for ph in plan["phases"]:
        rs = [r for r in res[ph["phase"]] if r]
        complete = len(rs) == len(ph["regions"])
        ok = complete and all(r["pass_"] for r in rs)
        worst = max(rs, key=lambda r: (r["go_to_last_w"] or 0, r["go_to_idle"] or 0)) if rs else None
        po = dict(layer=ph["layer"], node=ph["node"], phase=ph["phase"], die_stage=ph["stage"], K=ph["K"],
                  fmts=ph["fmts"], out=ph["out"], x_source=ph["x_source"], split_reason=ph["split_reason"],
                  matrices=[dict(alias=m["alias"], tensor=m["tensor"], rows=m["rows"], cols=m["cols"],
                                                segments=m["segments"], t_read_words_max_s81=m["t_read_words_max"],
                                                issue_cycles_LAT8_condition_s81=m["issue_cycles_LAT8_condition"])
                                           for m in ph["mats"]],
                  regions=len(ph["regions"]), regions_run=len(rs), rows_checked=sum(r["rows"] for r in rs),
                  rows_mismatched=sum(r["mismatched"] + r["extra"] for r in rs), exact=ok,
                  worst_region=worst["region"] if worst else None,
                  go_to_last_row_cycles=worst["go_to_last_w"] if worst else None,
                  go_to_idle_cycles=max(r["go_to_idle"] for r in rs) if rs else None,
                  worst_region_detail={k: worst[k] for k in ("pairs", "bf_pairs", "busy_pairs", "nrows", "t_read",
                                                            "nbeat", "segments_per_pair_max", "t_phase_model")}
                  if worst else None,
                  region_spread_go_to_last_row=[min(r["go_to_last_w"] for r in rs), max(r["go_to_last_w"] for r in rs)]
                  if rs else None)
        phases_out.append(po)
        nodes.setdefault((ph["layer"], ph["node"], ph["stage"]), []).append(po)
    out_nodes = []
    for (L, node, stage), pos in nodes.items():
        meas = sum(p["go_to_idle_cycles"] + 1 for p in pos[:-1]) + pos[-1]["go_to_last_row_cycles"] \
            if all(p["go_to_last_row_cycles"] is not None for p in pos) else None
        wire = W * len(pos)
        tot = meas + wire if meas is not None else None
        mname = node if node.startswith("E1.") else f"L{L}.{node}"
        mn = model.get(mname, {})
        u = mn.get("_uarch") or {}
        mcyc = mn.get("ctrl_cyc_1p2", 0) + mn.get("issue_cyc_1p2", 0) + mn.get("depth_cyc_1p2", 0) if mn else None
        out_nodes.append(dict(
            node=mname, layer=L, die_stage=stage, phases=[p["phase"] for p in pos],
            fmt=u.get("fmt"), K=u.get("K"), rows_model=u.get("rows"),
            rows_rank=sum(m["rows"][1] - m["rows"][0] for ph in plan["phases"] if ph["node"] == node
                          and ph["stage"] == stage and ph["layer"] == L for m in ph["mats"]),
            measured_cycles=meas,
            measured_definition="sum over the node's sequential phases (go -> idle + 1) + go -> last VM row write of "
                                "the last phase, each phase at the max over the die's regions (region vehicle)",
            wire_stage_cycles=wire,
            wire_definition=f"routed die geometry wire stages: {WIRE_X_TO_FARTHEST} (VM x root -> farthest cluster) - "
                            f"{BST_IN_VEHICLE} (spine BST stages already in the vehicle) + {WIRE_CLUSTER_TO_VM} "
                            f"(cluster -> VM) per phase (tools/uarch_model.DIE_SHRUNK_INTERIM)",
            wire_stage_cycles_s81_floorplan=W_S81 * len(pos),
            total_cycles=tot, us=tot / CLK * 1e6 if tot is not None else None,
            total_us_s81_floorplan_wire=(meas + W_S81 * len(pos)) / CLK * 1e6 if meas is not None else None,
            model_cycles=mcyc, model_us=mcyc / CLK * 1e6 if mcyc is not None else None,
            model_breakdown=dict(ctrl=mn.get("ctrl_cyc_1p2"), issue=mn.get("issue_cyc_1p2"),
                                 depth=mn.get("depth_cyc_1p2"),
                                 uarch={k: u.get(k) for k in ("fmt", "K", "rows", "words", "holding", "region",
                                                              "t_read", "t_x", "t_ret", "issue", "depth", "wire",
                                                              "tree", "ksplit", "adder_levels", "bind")}),
            rows_checked=sum(p["rows_checked"] for p in pos), exact=all(p["exact"] for p in pos)))
    qelem = build.get("qelem", 0)
    srcs = {str(p.relative_to(ROOT)): sha(p) for p in SOURCES + S81_FILES + (QRTL if qelem else [])}
    ck = Ckpt(a.snapshot)
    for f in sorted(set(ck.idx[t] for L in plan["layers"] for t in ck.idx if t.startswith(f"layers.{L}."))):
        ck.raw(next(t for t in ck.idx if ck.idx[t] == f))
    allx = all(n["exact"] for n in out_nodes)
    summary = {}
    for n in out_nodes:
        summary.setdefault(n["node"], []).append(n)
    node_summary = []
    for name, ns in summary.items():
        top = max(ns, key=lambda n: n["total_cycles"] or 0)
        node_summary.append(dict(node=name, layer=top["layer"], dies=[n["die_stage"] for n in ns],
                                 total_cycles=top["total_cycles"], us=top["us"],
                                 total_us_s81_floorplan_wire=top["total_us_s81_floorplan_wire"],
                                 model_us=top["model_us"], ratio_measured_over_model=(top["us"] / top["model_us"])
                                 if top["model_us"] else None,
                                 rows_checked=sum(n["rows_checked"] for n in ns), exact=all(n["exact"] for n in ns),
                                 note=("parts on dies " + str([n["die_stage"] for n in ns]) +
                                       " run concurrently if each die receives x; the slowest die is taken")
                                 if len(ns) > 1 else None))
    rec = dict(
        schema="opentallas.dsrom.1m_allmeasured.field.v1",
        status="pass" if allx and isa_bad == 0 else "fail",
        claim_boundary=("RTL measurement (Verilator, 2-state) of the S81 rank-0 dies' ROM-field matvec phases of one "
                        "layer per layer type (L20 at the golden 1M token's x for every op; other layers golden "
                        "attn_norm / ffn_norm x and seeded operator-internal x) on a one-region full-shape vehicle, "
                        "every region, bit-exact vs the golden; node time composed as the pinned spine sequences "
                        "phases; routed-geometry wire stages added analytically. Not a whole-die simulation; no SS/FF "
                        "timing claim for the field here."),
        vehicle=dict(top="ot_v41_fieldtop_w17w10 (pinned, flat)", NP_slots=NP, R=NR, NBF_slots=NBF,
                     qelem=(dict(element="ot_v41_rom_elem_q_qx_w10", QX=qelem, slots="FP8/FP4 (non-BF16) pairs",
                                 params="NB 2 MTP 1 EARLY 1 FAST 1 PP 1 QTIMING_FIX 1 QPIPE 1 QP_XS 1 QP_CAP 0 QP_P1 1 "
                                        "QP_CSAM 10 QZ 1 QZ_NS 8 QZ_NE 4 QY 1") if qelem else None),
                     bf_slots=BF_SLOTS, FAST=1, PP=1, BP=0, PHW=PHW, VAW=VAW, VRD=64, BST=BST_IN_VEHICLE, RST=1,
                     RD=64, ROOTD=128, return_levels_in_region=6,
                     description=__doc__.split("VEHICLE.")[1].split("PHASES.")[0].strip()),
        placement=dict(source=str(S81.relative_to(ROOT)), NP=2417, R=128, BF=519,
                       note="S81 canonical released-binding matrix map (whole rows; BF16 K 5120 rows in 2 segments)"),
        golden=dict(token_position=1048575, context=1048576, seed=20260930, gold_vm=plan["gold_vm"],
                    gold_weight_ops_sha256=plan["gold_weight_ops_sha256"], x_sha256=plan["x_sha256"],
                    experts=plan["experts"], ref=plan["ref"], ref_sha256=plan["ref_sha256"], notes=plan["notes"],
                    arith="chunk8 (tools/hdc_golden_v41)",
                    isa_crosscheck_rows=isa_n, isa_crosscheck_mismatch=isa_bad),
        model_source=msrc,
        node_summary=node_summary, nodes=out_nodes, phases=phases_out,
        not_measured=[
            "*.hc.fn (HE FP32 mixes: the HC engine, not the ROM field)",
            "head.lm_head (head dies, not the layer-die field)",
            "inter-die concurrency of a node split over two dies (e.g. L20 experts on stages 37 and 38): reported "
            "per die; node_summary takes the slowest die",
            "operator-internal x of layers other than L20 (wq_b, cmp.wk, wo_a, wo_b, w2, Engram wkv) is seeded, not "
            "the 1M token's; timing of the field is data-independent, exactness is checked on the x used"],
        simulator=build["simulator"], tb_sha256=build["tb_sha256"], build_steps=build["steps"],
        checkpoint_revision=a.snapshot.name, checkpoint_header_sha256=ck.pins, source_sha256=srcs,
        git_head=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip())
    a.record.parent.mkdir(parents=True, exist_ok=True)
    a.record.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(status=rec["status"], isa=(isa_n, isa_bad)), indent=1))
    for n in out_nodes:
        print(f"{n['node']:24s} st{n['die_stage']} meas {n['measured_cycles']} +wire {n['wire_stage_cycles']} = "
              f"{n['total_cycles']} cyc {n['us']:.4f} us | model {n['model_cycles']} cyc {n['model_us']} us | rows "
              f"{n['rows_checked']} exact {n['exact']}")
    return 0 if rec["status"] == "pass" else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("plan", "bind-schedules", "extract", "build", "run", "record", "all"))
    ap.add_argument("--snapshot", type=Path, default=Path.home() / ".cache/huggingface/hub/models--deepseek-ai--"
                    "DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277")
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--gold-vm", type=Path, default=GOLD_VM)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--layers", default=",".join(map(str, LAYERS)))
    ap.add_argument("--only", default="")
    ap.add_argument("--regions", default="")
    ap.add_argument("--run-layers", default="", help="run: only these layers' phases")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--model-dump", type=Path, default=None)
    ap.add_argument("--record", type=Path, default=REC)
    ap.add_argument("--qelem", type=int, default=0,
                    help="build: 0 = the pinned W10 element (default); N > 0 = the DS q-element with QX = N on the "
                         "FP8/FP4 pairs (ot_v41_pair_w17w10 QELEM)")
    a = ap.parse_args()
    G.set_arith("chunk8")
    steps = {"bind-schedules": [cmd_bind_schedules], "plan": [cmd_plan], "extract": [cmd_extract], "build": [cmd_build], "run": [cmd_run],
             "record": [cmd_record], "all": [cmd_plan, cmd_extract, cmd_build, cmd_run, cmd_record]}[a.cmd]
    for s in steps:
        rc = s(a)
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
