#!/usr/bin/env python3
"""Integer ROM macro map for every DeepSeek-V4.1 ROM-array die.

Rung 2 of the acceptance ladder (docs/INTEGRATED_PHYSICAL_PLAN.md).  Every
checkpoint tensor owned by a layer die is bound to whole macros of a real
catalog view (physical/asap7_memory_macros); nothing is fractional.

Capacity is judged in *macros that fit the die floorplan*, not against the
2,714,287,356-byte "rom_bytes_per_die" of results/arch/v41_die_placement.json.
That figure is (total checkpoint bytes) / 188 dies: a mean by construction,
so any replicated or padded tensor makes some die exceed it.  The binding
physical limit is the ROM slot count of the packed floorplan
(tools/v41_floorplan_pack.py), which this record feeds.

Ownership, dense splits and Engram spill rows are the same as
tools/v41_floorplan_spill_relocation.py (program-declared partitions;
unknown partitions stay fully replicated).  Bank formats:

* routed expert matrix: one eight-bank ``ot_rom_8192x274_m8`` set per matrix,
  mapping of rtl/chip/ot_chip_v41x_qtile_pair_bank.sv (tools/v41_floorplan_stage_bankmap.reserve)
* dense FP8 matrix: 264-bit {UE8M0 scale, 32 E4M3 codes} words, eight parallel banks
* wo_a expanded: BF16, eight banks of 256 useful bits/word
* wo_a compact: rtl/chip/ot_chip_v41x_woa_compact_bank.sv, eight banks of 80-bit
  words (8 codes + 2 scales) in ``ot_rom_8192x104_m8``
* small raw constants (norms, biases, sinks, HC base/scale): word-aligned pool
  of 264-bit words, read through the constant/HE port
* larger raw tensors (HC fn, gate): own 264-bit-word macros
* Engram spill rows: one 264-byte row = eight 264-bit words, 1024 rows/macro

ECC is not included (the tested witness has no ECC image); this is recorded
as an open item, not assumed free.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_floorplan_stage_bankmap as B  # noqa: E402

CATALOG = ROOT / "physical/asap7_memory_macros/index.json"
OWNERS = ROOT / "results/arch/v41_stage_owner_preflight.json"
PLACEMENT = ROOT / "results/arch/v41_die_placement.json"
COMPLETE = ROOT / "results/floorplan/v41_stage17_complete_reservation.json"
WOA_BANK = ROOT / "rtl/chip/ot_chip_v41x_woa_compact_bank.sv"
QTILE_BANK = ROOT / "rtl/chip/ot_chip_v41x_qtile_pair_bank.sv"
WOA_ME = ROOT / "results/rtl/v41_woa_compact_me.json"
DEPTH = 8192
WIDE = "ot_rom_8192x274_m8"
NARROW = "ot_rom_8192x104_m8"
SMALL_POOL_LIMIT_WORDS = DEPTH  # tensors below one macro of words share the pool
ROW_QUARTER = {"attn.wq_a.weight", "attn.wkv.weight", "attn.wq_b.weight",
               "ffn.shared_experts.w1.weight", "ffn.shared_experts.w3.weight",
               "ffn.shared_experts.w2.weight", "engram.wkv.weight"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class Headers:
    def __init__(self, snapshot: Path):
        self.snapshot = snapshot
        self.index_path = snapshot / "model.safetensors.index.json"
        self.idx = json.loads(self.index_path.read_text())["weight_map"]
        self.cache: dict[str, dict] = {}
        self.pins: dict[str, str] = {}

    def __call__(self, name: str) -> dict:
        f = self.idx[name]
        if f not in self.cache:
            with (self.snapshot / f).open("rb") as h:
                n = struct.unpack("<Q", h.read(8))[0]
                raw = h.read(n)
            self.cache[f] = json.loads(raw)
            self.pins[f] = hashlib.sha256(raw).hexdigest()
        return self.cache[f][name]


def words264(nbytes: int) -> int:
    return math.ceil(nbytes * 8 / 264)


def dense_entries(meta: Headers, layer: int, compact_woa: bool) -> list[dict]:
    """Rank-local dense tensor reservations for one layer (identical on all ranks)."""
    idx = meta.idx
    out, used = [], set()
    names = sorted(k for k in idx if k.startswith(f"layers.{layer}.")
                   and ".ffn.experts." not in k and ".engram.embed." not in k)
    for name in names:
        if name in used or (name.endswith(".scale") and name[:-6] + ".weight" in idx):
            continue
        m = meta(name)
        shape = m["shape"]
        nbytes = m["data_offsets"][1] - m["data_offsets"][0]
        local = name.split(f"layers.{layer}.")[1]
        e = dict(tensor=name, dtype=m["dtype"], source_shape=shape, source_tensors=[name])
        if m["dtype"] == "F8_E4M3" and name.endswith(".weight") and len(shape) == 2:
            rows, cols = shape
            sc = name[:-7] + ".scale"
            e["source_tensors"].append(sc)
            used.add(sc)
            if local in ROW_QUARTER:
                assert rows % 4 == 0
                rows //= 4
                e["split"] = "program_declared_output_row_quarter"
            elif local == "attn.wo_b.weight":
                assert cols % 4 == 0
                cols //= 4
                e["split"] = "program_declared_K_quarter"
            elif local == "attn.wo_a.weight":
                rows //= 4
                e["split"] = "output_groups_quarter"
            else:
                e["split"] = "conservative_full_replication"
            e["rank_shape"] = [rows, cols]
            if local == "attn.wo_a.weight" and compact_woa:
                # 8 banks x 80-bit words (8 E4M3 codes + 2 UE8M0 scales); see WOA_BANK.
                words_per_bank = rows * cols // 64
                per_bank = math.ceil(words_per_bank / DEPTH)
                e.update(representation="compact_fp8_80bit_8bank", macro=NARROW,
                         macro_count=8 * per_bank, banks=8, words_per_bank=words_per_bank,
                         payload_bytes=8 * words_per_bank * 10, local_group="ROM_MAC.ME")
            elif local == "attn.wo_a.weight":
                payload = rows * cols * 2
                per_bank = math.ceil(payload / (8 * DEPTH * 32))
                e.update(representation="bf16_expanded_256bit_8bank", macro=WIDE,
                         macro_count=8 * per_bank, banks=8, words_per_bank=payload // (8 * 32),
                         payload_bytes=payload, local_group="ROM_MAC.ME")
            else:
                assert cols % 32 == 0
                words_per_bank = math.ceil(rows / 8) * (cols // 32)
                e.update(representation="fp8_264bit_rowscale_8bank", macro=WIDE,
                         macro_count=8 * math.ceil(words_per_bank / DEPTH), banks=8,
                         words_per_bank=words_per_bank, payload_bytes=rows * (cols + cols // 32),
                         local_group="ROM_MAC.dense_QE")
        else:
            split = "conservative_full_replication"
            if name.endswith("ffn.gate.weight") or name.endswith("attn.attn_sink") \
                    or name.endswith("attn.indexer.weights_proj.weight"):
                assert nbytes % 4 == 0
                nbytes //= 4
                split = "program_declared_output_row_quarter"
            words = words264(nbytes)
            e.update(split=split, representation="raw_264bit_words", payload_bytes=nbytes,
                     words=words, local_group="VM.CONSTANT_HE")
            if words >= SMALL_POOL_LIMIT_WORDS:
                e.update(macro=WIDE, macro_count=math.ceil(words / DEPTH), banks=1)
            else:
                e.update(macro=WIDE, macro_count=0, banks=0, pooled=True)
        used.update(e["source_tensors"])
        out.append(e)
    return out


def derive(snapshot: Path, compact_woa: bool, detail: tuple[int, int] | None = None) -> dict:
    meta = Headers(snapshot)
    cat = json.loads(CATALOG.read_text())["macros"]
    owners = json.loads(OWNERS.read_text())
    place = json.loads(PLACEMENT.read_text())
    complete = json.loads(COMPLETE.read_text())
    mean_cap = math.floor(place["rom_bytes_per_die"])
    spill_rows_total = complete["spill_proposal"]["layer_spill_rows"]
    q, rem = divmod(spill_rows_total, 112)
    # Check every routed expert header matches the fixed matrix reservation.
    expert_mat = {}
    for fam, shape in (("w1", [2304, 2560]), ("w3", [2304, 2560]), ("w2", [5120, 1152])):
        rows, cols = shape[0] // 4, shape[1] * 2
        expert_mat[fam] = B.reserve(rows, cols)
    checked = 0
    for name in meta.idx:
        if name.startswith("layers.") and ".ffn.experts." in name and name.endswith(".weight") \
                and int(name.split(".")[1]) < 40:
            fam = name.split(".")[-2]
            w = meta(name)
            s = meta(name[:-7] + ".scale")
            exp = [5120, 1152] if fam == "w2" else [2304, 2560]
            if not (w["dtype"] == "I8" and w["shape"] == exp and s["dtype"] == "F8_E8M0"):
                raise ValueError(f"{name}: unexpected expert format {w} {s}")
            checked += 1
    expert_macros_each = sum(r["macros"] for r in expert_mat.values())
    expert_payload_each = sum(r["useful_payload_bytes"] for r in expert_mat.values())

    dies = []
    detail_map = None
    for stage in range(owners["stage_count"]):
        dense_layers = [o["layer"] for o in owners["layer_owners"] if o["dense_owner_stage"] == stage]
        ranges = [dict(layer=o["layer"], first=r["expert_ids"][0], last=r["expert_ids"][1])
                  for o in owners["layer_owners"] for r in o["routed_expert_candidate_owners"]
                  if r["stage"] == stage]
        n_exp = sum(r["last"] - r["first"] + 1 for r in ranges)
        dense = [e for layer in dense_layers for e in dense_entries(meta, layer, compact_woa)]
        pool_words = sum(e["words"] for e in dense if e.get("pooled"))
        pool_macros = math.ceil(pool_words / DEPTH)
        for rank in range(4):
            ordinal = stage * 4 + rank
            spill_rows = q + (ordinal < rem)
            spill_macros = math.ceil(spill_rows / 1024)
            counts = {WIDE: 0, NARROW: 0}
            counts[WIDE] += n_exp * expert_macros_each
            for e in dense:
                counts[e["macro"]] += e["macro_count"]
            counts[WIDE] += pool_macros + spill_macros
            payload = (n_exp * expert_payload_each + sum(e["payload_bytes"] for e in dense)
                       + spill_rows * 264)
            area = sum(counts[m] * cat[m]["area_um2"] for m in counts) / 1e6
            phys = sum(counts[m] * cat[m]["capacity_bits"] for m in counts) // 8
            by_group = {}
            by_group["ROM_MAC.expert"] = {WIDE: n_exp * expert_macros_each}
            for e in dense:
                if e["macro_count"]:
                    g = by_group.setdefault(e["local_group"], {})
                    g[e["macro"]] = g.get(e["macro"], 0) + e["macro_count"]
            g = by_group.setdefault("VM.CONSTANT_HE", {})
            g[WIDE] = g.get(WIDE, 0) + pool_macros
            by_group["ENGRAM.spill"] = {WIDE: spill_macros}
            dies.append(dict(die=f"layer_s{stage:02d}_r{rank}", role="layer", stage=stage, rank=rank,
                             dense_layers=dense_layers, routed_experts=n_exp, spill_rows=spill_rows,
                             macros={k: v for k, v in counts.items() if v},
                             macros_by_group=by_group,
                             payload_bytes=payload, physical_macro_bytes=phys,
                             macro_area_mm2=round(area, 6),
                             mean_model_budget_bytes=mean_cap,
                             bytes_over_mean_model=payload - mean_cap))
            if detail and detail == (stage, rank):
                detail_map = bank_map(stage, rank, ranges, dense, pool_words, spill_rows,
                                      expert_mat, complete, q, rem, cat)
    # Dedicated Engram table dies: whole rows to the mean budget, as proposed.
    sp = complete["spill_proposal"]
    eg_rows = mean_cap // 264
    eg_m = math.ceil(eg_rows / 1024)
    dies_eg = dict(role="engram_table", count=place["counts"]["engram"], rows_per_die=eg_rows,
                   macros={WIDE: eg_m}, macro_area_mm2=round(eg_m * cat[WIDE]["area_um2"] / 1e6, 6),
                   status="whole rows; 264-bit words, 8 reads/row; gather port count unbound")
    # Head dies: embed + head (+ MTP) bytes remain the analytical mean model.
    head_bytes = math.ceil(place["rom_bytes_per_die"] - place["head_die_spare_bytes"])
    head_rows = sp["head_die_rows"] // 4
    hm = math.ceil(words264(head_bytes) / DEPTH) + math.ceil(head_rows / 1024)
    dies_head = dict(role="head", count=place["counts"]["head"], payload_bytes=head_bytes + head_rows * 264,
                     macros={WIDE: hm}, macro_area_mm2=round(hm * cat[WIDE]["area_um2"] / 1e6, 6),
                     status="mean-model head bytes packed at 264 useful bits/word; exact head tensor image not derived")
    layer = [d for d in dies]
    busiest = max(layer, key=lambda d: (d["macro_area_mm2"], d["die"]))
    return dict(
        schema="opentallas.v41.die_macromap.v1",
        status="integer_macro_binding_capacity_judged_against_floorplan_slots",
        representation="compact_woa" if compact_woa else "expanded_woa",
        checkpoint_revision=snapshot.name,
        index_sha256=sha(meta.index_path),
        checkpoint_header_sha256=dict(sorted(meta.pins.items())),
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p in
                       [CATALOG, OWNERS, PLACEMENT, COMPLETE, WOA_BANK, QTILE_BANK, WOA_ME,
                        Path(__file__).resolve(), ROOT / "tools/v41_floorplan_stage_bankmap.py"]},
        expert_matrix_headers_checked=checked,
        expert_matrix_reservation={k: {kk: v[kk] for kk in ("rows", "cols", "beats", "macros",
                                                             "required_rows_per_bank", "allocated_rows_per_bank",
                                                             "useful_payload_bytes")}
                                   for k, v in expert_mat.items()},
        macro_views={m: {k: cat[m][k] for k in ("width_um", "height_um", "area_um2", "capacity_bits", "min_period_ps")}
                     for m in (WIDE, NARROW)},
        mean_model_budget_bytes=mean_cap,
        mean_model_note=("rom_bytes_per_die = checkpoint bytes / 188: every die over it by a replicated "
                         "or padded byte; it is an accounting mean, not a physical capacity"),
        layer_dies=layer,
        engram_table_dies=dies_eg,
        head_dies=dies_head,
        summary=dict(
            layer_die_count=len(layer),
            max_macros=max(sum(d["macros"].values()) for d in layer),
            max_wide_macros=max(d["macros"].get(WIDE, 0) for d in layer),
            max_narrow_macros=max(d["macros"].get(NARROW, 0) for d in layer),
            max_macro_area_mm2=busiest["macro_area_mm2"],
            min_macro_area_mm2=min(d["macro_area_mm2"] for d in layer),
            busiest_die=busiest["die"],
            dies_over_mean_model=sum(d["bytes_over_mean_model"] > 0 for d in layer),
            max_bytes_over_mean_model=max(d["bytes_over_mean_model"] for d in layer),
            total_payload_bytes=sum(d["payload_bytes"] for d in layer),
            total_macro_area_mm2=round(sum(d["macro_area_mm2"] for d in layer), 3)),
        open_items=["ECC image and bits not included (witness has none)",
                    "dense tensors with unknown partitions remain fully replicated",
                    "expert matrices use a separate 8192-deep set each: 5,760 of 8,192 rows used (70.3%)",
                    "head-die image is the analytical mean model, not an exact tensor image",
                    "gather/read-port schedule for pooled constants and Engram spill unbound"],
        busiest_die_bank_map=detail_map)


def bank_map(stage, rank, ranges, dense, pool_words, spill_rows, expert_mat, complete, q, rem, cat):
    """Named, sequential macro IDs for every tensor slice on one die."""
    mid = {WIDE: 0, NARROW: 0}
    items = []

    def take(macro, n):
        first = mid[macro]
        mid[macro] += n
        return f"{macro}#{first}", f"{macro}#{first + n - 1}"

    for r in ranges:
        for e in range(r["first"], r["last"] + 1):
            for fam in ("w1", "w3", "w2"):
                res = expert_mat[fam]
                lo, hi = take(WIDE, res["macros"])
                items.append(dict(tensor=f"layers.{r['layer']}.ffn.experts.{e}.{fam}", rank=rank,
                                  output_rows=[rank * res["rows"], (rank + 1) * res["rows"]],
                                  macro=WIDE, first=lo, last=hi, group="ROM_MAC.expert",
                                  rows_per_bank=res["required_rows_per_bank"]))
    for e in dense:
        if e["macro_count"]:
            lo, hi = take(e["macro"], e["macro_count"])
            items.append(dict(tensor=e["tensor"], rank=rank, split=e["split"], rank_shape=e.get("rank_shape"),
                              representation=e["representation"], macro=e["macro"], first=lo, last=hi,
                              group=e["local_group"]))
    pool = math.ceil(pool_words / DEPTH)
    word = 0
    lo, hi = take(WIDE, pool) if pool else (None, None)
    pooled = []
    for e in dense:
        if e.get("pooled"):
            pooled.append(dict(tensor=e["tensor"], word_first=word, words=e["words"]))
            word += e["words"]
    items.append(dict(tensor="constant_pool", macro=WIDE, first=lo, last=hi, group="VM.CONSTANT_HE",
                      members=pooled))
    sp = complete["spill_proposal"]
    ordinal = stage * 4 + rank
    start = sp["dedicated_table_die_rows"] + sp["head_die_rows"] + ordinal * q + min(ordinal, rem)
    intervals, base = [], 0
    for t in sp["tables"]:
        a, b = max(start, base), min(start + spill_rows, base + t["rows"])
        if a < b:
            intervals.append(dict(tensor=t["tensor"], row_begin=a - base, row_end=b - base))
        base += t["rows"]
    lo, hi = take(WIDE, math.ceil(spill_rows / 1024))
    items.append(dict(tensor="engram_spill", rows=spill_rows, intervals=intervals, macro=WIDE,
                      first=lo, last=hi, group="ENGRAM.spill", rows_per_macro=1024))
    return dict(stage=stage, rank=rank, macro_totals=dict(mid), entries=items)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--compact-woa", action="store_true")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--bankmap-output", type=Path, help="write the busiest die's full bank map here")
    a = p.parse_args()
    rec = derive(a.snapshot, a.compact_woa)
    if a.bankmap_output:
        b = next(d for d in rec["layer_dies"] if d["die"] == rec["summary"]["busiest_die"])
        full = derive(a.snapshot, a.compact_woa, detail=(b["stage"], b["rank"]))
        bm = full["busiest_die_bank_map"]
        bm.update(schema="opentallas.v41.die_bankmap.v1", representation=rec["representation"],
                  source_sha256=rec["source_sha256"], checkpoint_revision=rec["checkpoint_revision"],
                  status="named integer macro binding for the busiest layer die; ports/ECC open")
        a.bankmap_output.write_text(json.dumps(bm, indent=1) + "\n")
    rec.pop("busiest_die_bank_map")
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec["summary"], indent=1))


if __name__ == "__main__":
    main()
