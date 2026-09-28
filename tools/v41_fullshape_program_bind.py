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


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise ValueError(message)


def bind(layout_path: Path, shard_path: Path) -> dict:
    layout = json.loads(layout_path.read_text())
    shard = json.loads(shard_path.read_text())
    _require(layout["layer"] == shard["layer"] == 0 and layout["rank"] == shard["rank"] == 0,
             "binder requires layer 0, rank 0")
    _require(sha(shard_path) == layout["source_image_manifest_sha256"], "source shard hash changed")
    selected = tuple(shard["golden_shard"]["experts"])
    _require(selected == tuple(layout["selected_expert_ids"]), "selected expert sequence differs from golden")
    _require(layout["selected_expert_weights_complete"], "selected expert image is incomplete")
    _require(not layout["unplaced_source_tensors"], "checkpoint source tensor has no image")
    mats, consts = layout["matrices"], layout["constants"]
    expected = {"wq_a", "wkv", "wq_b", "wo_b", "shared.w1", "shared.w3", "shared.w2",
                "gate", "wo_a", "hc_attn_fn", "hc_ffn_fn"}
    expected |= {f"exp{e}.{w}" for e in selected for w in ("w1", "w3", "w2")}
    _require(expected <= mats.keys(), f"missing matrix images: {sorted(expected - mats.keys())}")
    _require(len(expected) == 29, "unexpected token-selected matrix count")
    for name in expected:
        item = mats[name]
        _require(item["word_count"] > 0 and item["base_word"] >= 0,
                 f"invalid matrix range: {name}")
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
    bases = {"rope_plain": 0}
    for name in names:
        key = "L0." + ("gate_bias" if name == "gate.bias" else name)
        bases[key] = consts[name]["base_word"]
    lay = R.ShapeLayout(R.SHIPPED, tp_exact=True, constant_bases=bases)
    qnames = {"wq_a": (0, "wq_a"), "wkv": (0, "wkv"), "wq_b": (0, "wq_b"),
              "wo_b": (0, "wo_b")}
    for name, key in qnames.items():
        lay.qmat[key]["base"] = mats[name]["base_word"]
    for w in ("w1", "w3", "w2"):
        lay.qmat[(0, "shared", w)]["base"] = mats[f"shared.{w}"]["base_word"]
        lay.qmat[(0, "exp", 0, w)]["base"] = mats[f"exp{selected[0]}.{w}"]["expert_id_base"]
    lay.qmat[(0, "exp_stride")] = mats[f"exp{selected[0]}.w1"]["expert_stride_words"]
    lay.mat[(0, "gate")]["base"] = mats["gate"]["base_word"]
    lay.mat[(0, "wo_a")]["base"] = mats["wo_a"]["base_word"]
    lay.mat[(0, "attn", "fn")]["base"] = mats["hc_attn_fn"]["base_word"]
    lay.mat[(0, "ffn", "fn")]["base"] = mats["hc_ffn_fn"]["base_word"]
    lay.cb["rope_plain"] = 0
    program = R.ShapeBuilder(lay).build([0], embed=False, head=False)

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
    _require(len(wo_a) == 1, "expected one grouped wo_a descriptor")
    pc, f = wo_a[0]
    group_k = R.SHIPPED["heads"] // R.SHIPPED["o_groups"] * R.SHIPPED["hd"]
    group_rows = R.SHIPPED["o_rank"]
    rows_per_subop = f["me_tiles"] * (lay.G >> f["me_split"]) * I.W_LANES
    _require(rows_per_subop * I.INTERLEAVE == mats["wo_a"]["nrows"],
             "wo_a sub-op output-row coverage differs from image")
    me_trace = []
    for j in range(I.INTERLEAVE):
        output_first = j * rows_per_subop
        expected_group = output_first // group_rows
        actual_x = f["me_xbase"] + j * f["me_xjs"]
        required_x = f["me_xbase"] + expected_group * group_k
        me_trace.append(dict(subop=j, output_first_row=output_first,
                             output_last_row_exclusive=output_first + rows_per_subop,
                             x_first=actual_x, required_x_first=required_x,
                             x_last_exclusive=actual_x + group_k))
    if any(x["x_first"] != x["required_x_first"] for x in me_trace):
        blockers.append("ME wo_a uses j*xjs; TP4 requires the same 4096-element activation "
                        "for j=0..3 and the next for j=4..7")
    # This entry point begins with an already-loaded layer-0 state, so the
    # embedding token map and other layers' YaRN table are outside its scope.
    if "rope_plain" in layout["unplaced_generated"]:
        blockers.append("generated layer-0 RoPE plain region missing")
    return dict(schema="opentallas.v41x.fullshape.program_bind.v1",
                status="runnable" if not blockers else "blocked", layer=0, rank=0,
                layout_sha256=sha(layout_path), shard_sha256=sha(shard_path),
                source_experts=list(selected), matrix_count=len(expected),
                constant_count=len(names), instruction_count=len(program),
                qe_address_trace=trace, me_wo_a_trace=me_trace, blockers=blockers,
                claim_boundary="Descriptor and source image address check; no RTL token or throughput verdict.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT)
    p.add_argument("--shard", type=Path, default=DEFAULT_SHARD)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    record = bind(args.layout, args.shard)
    out = json.dumps(record, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out)
    else:
        print(out)


if __name__ == "__main__":
    main()
