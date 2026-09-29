#!/usr/bin/env python3
"""Bind the layer-0 TP-4 ISA to a token-selected physical ROM layout.

This is a fail-closed admission check.  It produces a descriptor trace even
when the layout is incomplete, but never calls that trace executable unless
each accessed word is backed by an image and all generated constants exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_replay_v41 as R  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402

DEFAULT_LAYOUT = ROOT / "results/rtl/hdc_v41x_fullshape_token_selected_rom_layout.json"
DEFAULT_SHARD = ROOT / "results/rtl/hdc_v41x_fullshape_200k_l0_rank0_image.json"
DEFAULT_QE = ROOT / "results/rtl/hdc_v41x_fullshape_qe_stream_200k_l0_rank0.json"
DEFAULT_ROPE = ROOT / "results/rtl/hdc_v41x_fullshape_rope_sparse_patch.json"
DEFAULT_ROPE_HBM = ROOT / "results/arch/v41_rope_hbm_capacity.json"
DEFAULT_ROPE_CACHE = ROOT / "results/rtl/v41x_rope_hbm_cache.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise ValueError(message)


def bind(layout_path: Path, shard_path: Path, qe_path: Path = DEFAULT_QE,
         rope_path: Path = DEFAULT_ROPE, rope_mode: str = "sparse_fixture") -> dict:
    _require(rope_mode in ("sparse_fixture", "hbm_cache"), f"unknown RoPE mode {rope_mode}")
    layout = json.loads(layout_path.read_text())
    shard = json.loads(shard_path.read_text())
    qe = json.loads(qe_path.read_text())
    _require(layout["layer"] == shard["layer"] == 0 and layout["rank"] == shard["rank"] == 0,
             "binder requires layer 0, rank 0")
    _require(sha(shard_path) == layout["source_image_manifest_sha256"], "source shard hash changed")
    _require(sha(layout_path) == qe["other_engine_layout_sha256"] and
             sha(shard_path) == qe["source_image_manifest_sha256"],
             "QE stream was not packed from these source images")
    selected = tuple(shard["golden_shard"]["experts"])
    _require(selected == tuple(layout["selected_expert_ids"]), "selected expert sequence differs from golden")
    _require(layout["selected_expert_weights_complete"], "selected expert image is incomplete")
    _require(not layout["unplaced_source_tensors"], "checkpoint source tensor has no image")
    _require(tuple(qe["selected_expert_ids"]) == selected,
             "QE stream selected experts differ from golden")
    mats = dict(layout["matrices"])
    mats.update(qe["matrices"])
    consts = layout["constants"]
    expected = {"wq_a", "wkv", "wq_b", "wo_b", "shared.w1", "shared.w3", "shared.w2",
                "gate", "wo_a", "hc_attn_fn", "hc_ffn_fn"}
    expected |= {f"exp{e}.{w}" for e in selected for w in ("w1", "w3", "w2")}
    _require(expected <= mats.keys(), f"missing matrix images: {sorted(expected - mats.keys())}")
    _require(len(expected) == 29, "unexpected token-selected matrix count")
    for name in expected:
        item = mats[name]
        _require(item["word_count"] > 0 and item["base_word"] >= 0,
                 f"invalid matrix range: {name}")
        if item["engine"] == "qe":
            _require(item["geometry"]["word_count"] == item["word_count"] and
                     item.get("logical_stream_sha256") and item.get("image_bytes", 0) > 0,
                     f"QE logical stream/geometry missing: {name}")
        else:
            _require(item["geometry"]["base_word"] == item["base_word"] and
                     item["geometry"]["end_word_exclusive"] == item["base_word"] + item["word_count"],
                     f"matrix geometry/base mismatch: {name}")
            _require(item.get("output_image_sha256") and item.get("output_image_bytes", 0) > 0,
                     f"matrix has no materialized image: {name}")
    for w in ("w1", "w3", "w2"):
        records = [mats[f"exp{e}.{w}"] for e in selected]
        family_base = records[0]["expert_id_base"]
        stride = records[0]["expert_stride_words"]
        _require(stride > 0 and all(x["expert_id_base"] == family_base and
                                   x["expert_stride_words"] == stride and
                                   x["base_word"] == family_base + e * stride
                                   for e, x in zip(selected, records)),
                 f"expert family {w} is not addressable by QE index/stride")
    names = ("attn_norm", "ffn_norm", "q_norm", "kv_norm", "attn_sink", "gate.bias",
             "hc_attn_scale", "hc_attn_base", "hc_ffn_scale", "hc_ffn_base", "pre0")
    _require(set(names) <= consts.keys(), "missing shipped layer constant")
    context = str(shard["context"])
    if rope_mode == "sparse_fixture":
        rope = json.loads(rope_path.read_text())
        _require(context in rope["contexts"] and rope["status"] == "exact_input_only",
                 "no exact sparse RoPE fixture for shard context")
        rp = rope["contexts"][context]
        rp_file = ROOT / rp["file"]
        _require(sha(rp_file) == rp["sha256"] and rp["bytes"] == 256 and
                 rp["position"] == shard["position"] and
                 rp["crom_absolute_first_word"] == rp["crom_word_base"] + rp["position"] * 32,
                 "sparse RoPE patch does not match token position/address")
        rope_source = dict(storage="sparse_crom_fixture", position=rp["position"],
                           base_word=rp["crom_word_base"],
                           absolute_first_word=rp["crom_absolute_first_word"],
                           absolute_last_word=rp["crom_absolute_last_word"],
                           file=rp["file"], sha256=rp["sha256"],
                           claim_boundary="one-position input fixture only")
        bases = {"rope_plain": rp["crom_word_base"]}
    else:
        capacity = json.loads(DEFAULT_ROPE_HBM.read_text())
        cache = json.loads(DEFAULT_ROPE_CACHE.read_text())
        _require(context in capacity["scenarios"] and "plain" in
                 capacity["scenarios"][context]["stages"][0]["table_kinds"],
                 "no HBM plain table capacity at this context/stage")
        fixture = cache["fixtures"]["plain200k" if int(context) == 200000 else "plain1m"]
        _require(cache["status"] == "pass" and fixture["position"] == shard["position"],
                 "HBM RoPE cache fixture does not match token position")
        rope_source = dict(storage="hbm_read_only_table", kind="plain",
                           position=shard["position"], pair_count=32, bytes_per_position=256,
                           capacity_record_sha256=sha(DEFAULT_ROPE_HBM),
                           cache_record_sha256=sha(DEFAULT_ROPE_CACHE),
                           physical_region_base_sector=None, full_table_image_sha256=None,
                           claim_boundary="HBM capacity plus one-position cache proof; full table image "
                                          "and physical HBM region not yet bound")
        bases = {"rope_plain": 0}
    for name in names:
        key = "L0." + ("gate_bias" if name == "gate.bias" else name)
        bases[key] = consts[name]["base_word"]
    lay = R.ShapeLayout(R.SHIPPED, tp_exact=True, constant_bases=bases,
                        rope_storage="hbm_cache" if rope_mode == "hbm_cache" else "crom_fixture")
    qnames = {"wq_a": (0, "wq_a"), "wkv": (0, "wkv"), "wq_b": (0, "wq_b"),
              "wo_b": (0, "wo_b")}
    for name, key in qnames.items():
        lay.qmat[key]["base"] = mats[name]["base_word"]
    for w in ("w1", "w3", "w2"):
        lay.qmat[(0, "shared", w)]["base"] = mats[f"shared.{w}"]["base_word"]
        lay.qmat[(0, "exp", 0, w)]["base"] = mats[f"exp{selected[0]}.{w}"]["expert_id_base"]
    lay.qmat[(0, "exp_stride")] = mats[f"exp{selected[0]}.w1"]["expert_stride_words"]
    for w in ("w1", "w3", "w2"):
        lay.qmat[(0, "exp_stride", w)] = mats[f"exp{selected[0]}.{w}"]["expert_stride_words"]
    lay.mat[(0, "gate")]["base"] = mats["gate"]["base_word"]
    lay.mat[(0, "wo_a")]["base"] = mats["wo_a"]["base_word"]
    lay.mat[(0, "attn", "fn")]["base"] = mats["hc_attn_fn"]["base_word"]
    lay.mat[(0, "ffn", "fn")]["base"] = mats["hc_ffn_fn"]["base_word"]
    lay.cb["rope_plain"] = 0
    program = R.ShapeBuilder(lay).build([0], embed=False, head=False)
    # Packing is an additional gate: the full ISA must preserve every bound
    # address/count and collective field without truncation.
    for pc, fields in enumerate(program):
        try:
            packed = I.encode(full_shape=True, **fields)
            decoded = I.decode(packed, full_shape=True)
        except (ValueError, KeyError, OverflowError) as exc:
            raise ValueError(f"full-shape ISA cannot encode PC {pc}: {exc}") from exc
        for key, value in fields.items():
            if key in I.FULL_LAYOUT and isinstance(value, int):
                _require(decoded[key] == value, f"full-shape ISA truncates {key} at PC {pc}")

    # The adopted QE issues one word per cycle over tiles * nb * IL.  Compare
    # that exact RTL address interval with each matrix's materialized interval.
    qe_regions = {mats[n]["base_word"]: (n, mats[n]) for n in qnames}
    qe_regions.update((mats[f"shared.{w}"]["base_word"],
                       (f"shared.{w}", mats[f"shared.{w}"])) for w in ("w1", "w3", "w2"))
    for w in ("w1", "w3", "w2"):
        n = f"exp{selected[0]}.{w}"
        qe_regions[mats[n]["expert_id_base"]] = (f"exp.{w}", mats[n])
    trace, blockers = [], []
    for pc, f in enumerate(program):
        if f["unit"] != I.UNIT_QE or f.get("qe_mode") != I.QE_LINQ:
            continue
        base = f["qe_wbase"]
        _require(base in qe_regions, f"QE instruction {pc} points outside bound matrix regions: {base}")
        name, image = qe_regions[base]
        _require(f["qe_nout"] == image["geometry"]["nout"] and
                 f["qe_nb"] == image["geometry"]["nb"] and
                 f["qe_tiles"] == image["geometry"]["tiles"],
                 f"QE PC {pc} logical matrix shape differs from {name} image")
        _require(bool(f["qe_fp4"]) == image["format"].startswith("FP4_"),
                 f"QE PC {pc} numeric format differs from {name} image")
        count = f["qe_tiles"] * f["qe_nb"] * I.INTERLEAVE
        if f.get("qe_ind"):
            ids = selected
            _require(f["qe_istride"] == image["expert_stride_words"],
                     f"QE expert stride mismatch at PC {pc}")
        else:
            ids = (0,)
        for eid in ids:
            address = base + eid * f.get("qe_istride", 0)
            end = address + count
            item = mats[f"exp{eid}.{name.split('.')[-1]}"] if f.get("qe_ind") else image
            image_end = item["base_word"] + item["word_count"]
            backed = address >= item["base_word"] and end <= image_end
            trace.append(dict(pc=pc, matrix=name, expert_id=eid if f.get("qe_ind") else None,
                              start_word=address, end_word_exclusive=end,
                              image_end_word_exclusive=image_end, backed=backed))
            if not backed:
                blockers.append(f"QE PC {pc} {name} expert={eid}: streams [{address},{end}) "
                                f"but image ends at {image_end}")
    wo_a = [(pc, f) for pc, f in enumerate(program)
            if f["unit"] == I.UNIT_ME and f.get("_tag") == "L0.out" and f.get("me_wsrc") == 0]
    _require(len(wo_a) == lay.ogr_d, "one wo_a descriptor required per local o-group")
    group_k = R.SHIPPED["heads"] // R.SHIPPED["o_groups"] * R.SHIPPED["hd"]
    group_rows = R.SHIPPED["o_rank"]
    group_words = mats["wo_a"]["word_count"] // lay.ogr_d
    _require(group_words * lay.ogr_d == mats["wo_a"]["word_count"],
             "wo_a image cannot be split by o-group")
    me_trace = []
    for g, (pc, f) in enumerate(wo_a):
        rows = f["me_nout"]
        start = f["me_wbase"]
        x = f["me_xbase"]
        output = f["me_obase"] * I.W_LANES
        expected_start = mats["wo_a"]["base_word"] + g * group_words
        expected_x = lay.vm.map["ACC"] + g * group_k
        expected_output = lay.vm.map["ZA"] + g * group_rows
        me_trace.append(dict(pc=pc, group=g, output_first_row=g * group_rows,
                             output_last_row_exclusive=(g + 1) * group_rows,
                             image_start_word=start, expected_image_start_word=expected_start,
                             image_end_word_exclusive=start + group_words,
                             x_first=x, required_x_first=expected_x,
                             x_last_exclusive=x + group_k,
                             output_first=output, required_output_first=expected_output,
                             rows=rows, xjs=f.get("me_xjs", 0)))
        if (rows != group_rows or f.get("me_xjs", 0) or start != expected_start or
                x != expected_x or output != expected_output):
            blockers.append(f"ME wo_a group {g} descriptor does not match selected image/activation")
    for pc, f in enumerate(program):
        if f["unit"] == I.UNIT_ME and f.get("_tag") == "L0.router" and not f.get("me_wsrc"):
            gate = mats["gate"]
            _require(f["me_wbase"] == gate["base_word"] and
                     f["me_nout"] == gate["nrows"] and
                     f["me_k"] * (1 << f["me_split"]) == gate["ncols"],
                     f"ME gate descriptor/image mismatch at PC {pc}")
        if f["unit"] == I.UNIT_HE and f.get("_tag") in ("L0.hc_attn", "L0.hc_ffn"):
            name = "hc_attn_fn" if f["_tag"] == "L0.hc_attn" else "hc_ffn_fn"
            image = mats[name]
            _require(f["he_wbase"] == image["base_word"] and
                     f["he_nout"] == image["nrows"] and
                     f["he_k"] * R.HC_SPLIT == image["ncols"],
                     f"HE {name} descriptor/image mismatch at PC {pc}")
    if qe["packed_requires_fp4_port_adapter"]:
        blockers.append("packed FP4 QE words require a sector-to-16-lane port adapter; no exact RTL adapter gate")
    if rope_mode == "sparse_fixture":
        blockers.append("sparse token-position RoPE fixture only; production RoPE storage/prefetch unproved")
    else:
        tagged = [pc for pc, f in enumerate(program) if f["unit"] == I.UNIT_SU and
                  f.get("b_src") == I.SRC_CLO and f.get("d_src") == I.SRC_CHI and
                  f.get("b_base", 0) >> 28 in (2, 3)]
        paired_crom = [pc for pc, f in enumerate(program) if f["unit"] == I.UNIT_SU and
                       f.get("b_src") == I.SRC_CLO and f.get("d_src") == I.SRC_CHI]
        controls = [(pc, f) for pc, f in enumerate(program)
                    if f["unit"] == I.UNIT_CTL and f.get("ctl") in (5, 6)]
        _require(len(controls) == 2 and [f["ctl"] for _, f in controls] == [5, 6],
                 "production RoPE requires one CTL5 prefetch and one CTL6 release")
        pre_pc, pre = controls[0]
        rel_pc, rel = controls[1]
        _require(len(tagged) == 3 and paired_crom == tagged and
                 pre_pc < min(tagged) <= max(tagged) < rel_pc,
                 "production RoPE SU reads are not held between CTL5 and CTL6")
        _require(pre.get("ctl_lane") == rel.get("ctl_lane") == 0 and
                 pre.get("ctl_slot") == rel.get("ctl_slot") == 0 and
                 rel.get("wait", 0) & (1 << (I.UNIT_SU - 1)),
                 "production plain RoPE kind/position or SU drain mismatch")
        _require(all(program[pc]["b_base"] == program[pc]["d_base"] == (2 << 28)
                     and program[pc]["b_d"] == program[pc]["d_d"] == I.DYN["ROPE"]
                     and program[pc]["su_nin"] == 64 and program[pc].get("b_half") == 1
                     for pc in tagged), "production RoPE tag or position selector mismatch")
        rope_source["prefetch_pc"] = pre_pc
        rope_source["release_pc"] = rel_pc
        rope_source["su_read_pcs"] = tagged
        blockers.append("production HBM RoPE full-position table image and physical region not bound")
    instruction_trace = []
    for pc, f in enumerate(program):
        instruction_trace.append(dict(
            pc=pc, unit=f["unit"], tag=f.get("_tag"),
            reads=sorted(f.get("_reads", ())), writes=sorted(f.get("_writes", ())),
            fields={k: v for k, v in f.items() if not k.startswith("_")},
        ))
    return dict(schema="opentallas.v41x.fullshape.program_bind.v1",
                status="runnable" if not blockers else "blocked", layer=0, rank=0,
                layout_sha256=sha(layout_path), shard_sha256=sha(shard_path),
                qe_stream_sha256=sha(qe_path), rope_mode=rope_mode,
                rope_patch_sha256=sha(rope_path) if rope_mode == "sparse_fixture" else None,
                rope_token_patch=rope_source if rope_mode == "sparse_fixture" else None,
                rope_hbm_table=rope_source if rope_mode == "hbm_cache" else None,
                resource_trace=dict(qe_logical_qrom_words=qe["logical_qrom_words"],
                                    qe_direct_expanded_bytes=qe["logical_direct_bytes"],
                                    qe_packed_physical_bytes=qe["physical_qe_bytes_reserved"],
                                    other_engine_bytes=qe["other_engine_bytes_reserved"],
                                    packed_die_bytes=qe["packed_die_bytes_reserved"],
                                    rom_capacity_bytes=qe["rom_capacity_bytes"],
                                    direct_expanded_fits_die=qe["direct_expanded_fits_die"],
                                    packed_requires_fp4_port_adapter=qe["packed_requires_fp4_port_adapter"]),
                source_sha256={str(p.relative_to(ROOT)): sha(p) for p in (
                    Path(__file__).resolve(), ROOT / "tools/hdc_replay_v41.py",
                    ROOT / "tools/hdc_isa_v41.py",
                    ROOT / "rtl/hdc/v41/ot_hdc_v41_qe.sv",
                    ROOT / "rtl/hdc/v41x/ot_hdc_v41x_me_adapt.sv")},
                source_experts=list(selected), matrix_count=len(expected),
                constant_count=len(names), instruction_count=len(program),
                instruction_trace=instruction_trace,
                qe_address_trace=trace, me_wo_a_trace=me_trace, blockers=blockers,
                claim_boundary="Descriptor and source image address check; no RTL token or throughput verdict.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT)
    p.add_argument("--shard", type=Path, default=DEFAULT_SHARD)
    p.add_argument("--qe", type=Path, default=DEFAULT_QE)
    p.add_argument("--rope", type=Path, default=DEFAULT_ROPE)
    p.add_argument("--rope-mode", choices=("sparse_fixture", "hbm_cache"), default="sparse_fixture")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    record = bind(args.layout, args.shard, args.qe, args.rope, args.rope_mode)
    out = json.dumps(record, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out)
    else:
        print(out)


if __name__ == "__main__":
    main()
