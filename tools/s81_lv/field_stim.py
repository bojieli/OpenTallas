#!/usr/bin/env python3
"""S81 layer vehicle, seam S2 (field column): stimulus + CPU golden for one REAL column of the rank-0 ROM field
driven by the 1M token's real L0 activation (owner: s81lv/C-field, 2026-10-12).

COLUMN.  Region 0 of the rank-0 S81 die (return root 0; tb_s81_die_layer port 0, lane NC[0]-1).  Every element pair
the released S81 binding (results/uarch/dsrom_s81_released_binding_20261004/canonical/matrix_map.jsonl.gz, plan rows
[segment, pair, superrow0, count, stride 128, base, words]) gives a region-0 super row (superrow % 128 == 0) of an
FP8 matrix of an L0 field phase whose x is in the pinned 1M-token golden chain:
    attn : x = L0.hc_pre_norm.attn 'x' (the attn-normed BF16 x)  -> wq_a, wkv
    ffn  : x = L0.hc_pre_norm.ffn  'x' (the ffn-normed BF16 x)   -> shared.w1, shared.w3
Each pair is one run of the SAME closed element ot_v41_rom_elem_q_qxpq_w10 (QX 10 / PQ 1 / QM 5 / QS 5, the
dsrom-qelem-qs5f CLOSED parameter set) with that pair's ROM image and configuration.

WEIGHTS.  Real released-checkpoint rows (DeepSeek-V4.1-Flash snapshot dba1be0a..., rank-0 rank_slices of the map):
FP8 E4M3 codes + UE8M0 block scales, laid into the two macros of the pair by the W17/W10 image writer
(tools/v41_die_images_w17w10.add_phase) with the S81 allocator's placement hook (tools/dsrom_1m_field.s81_place),
exactly as the full-region field vehicle tools/dsrom_1m_field.py does.

GOLDEN.  tools/v41_die_images_w17w10.golden_phase (R-ARITH chunk8 golden linear_q: exact 32-block dots, binary32,
2^(xe+we), chunk-of-8 sequential sums, padded pairwise tree) -> per row tag the FP32 accumulator and its BF16 RNE.
The activation quantiser golden (quant_fp8 codes + exponents) is also emitted: the bench quantises x in RTL
(ot_hdc_actquant) and checks it against this before streaming it to the element.

    python3 tools/s81_lv/field_stim.py --out DIR [--pkl su_cases_v2_ildr.pkl] [--snapshot HF_SNAPSHOT]
Writes DIR/<run>/{x,q,e,cfg,stream,gold}.hex, the ROM viamaps (+OT_ROM_DIR=DIR/<run>), DIR/runs.json and a
tb_s81_die_layer stim fragment DIR/<run>/root0.stim ('P'/'C' lines, root 0).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_1m_field as F  # noqa: E402  (sets v41_die_images_w17w10._place = s81_place)
import hdc_golden_v41 as G  # noqa: E402
import rtl_v41_rom_array as A  # noqa: E402
import v41_die_images_w17w10 as I  # noqa: E402

MAP = ROOT / "results/uarch/dsrom_s81_released_binding_20261004/canonical/matrix_map.jsonl.gz"
PKL = Path("/srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl")
SNAP = Path.home() / ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/" \
    "dba1be0a40aa45a94ad051997016db3960a90277"
PHASES = {"attn": ("L0.hc_pre_norm.attn", ("wq_a", "wkv")),
          "ffn": ("L0.hc_pre_norm.ffn", ("shared.w1", "shared.w3"))}
REGION, NREG, LAYER, RANK = 0, 128, 0, 0
OBASE = 0x4000      # VM output base of the bench capture (VM address = OBASE + row tag)


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def golden_x(pkl, case):
    by = {c["name"]: c for c in pkl["cases"]}
    xs = [a for n, _, a, _ in by[case]["checks"] if n == "x"]
    assert len(xs) == 1 and xs[0].shape == (5120,), case
    return np.asarray(xs[0], dtype=np.uint32)


def hexfile(p: Path, vs, w):
    p.write_text("".join(f"{int(v):0{w}x}\n" for v in vs))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pkl", type=Path, default=PKL)
    ap.add_argument("--snapshot", type=Path, default=SNAP)
    ap.add_argument("--max-pairs", type=int, default=0, help="0 = every region-0 pair of the column")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    G.set_arith("chunk8")
    pkl = pickle.load(a.pkl.open("rb"))
    ck = A.Ckpt(a.snapshot)
    ents = {}
    with gzip.open(MAP, "rt") as f:
        for ln in f:
            r = json.loads(ln)
            if r["layer"] == LAYER and r["expert"] is None:
                ents[r["alias"]] = r
    runs = []
    for phase, (case, aliases) in PHASES.items():
        xb = golden_x(pkl, case)
        x = G.from_bits(xb).astype(G.F)
        xq, xe = G.quant_fp8(x)
        codes = A.x_codes(xq)
        for alias in aliases:
            e = ents[alias]
            assert e["format"] == "fp8" and e["K"] == 5120 and len(e["segments"]) == 1, alias
            plans = json.loads(e["plans"]) if isinstance(e["plans"], str) else e["plans"]
            rs = e["rank_slices"][RANK]
            full = A.Mat(ck, e["tensor"].removesuffix(".weight"), "fp8", rs["rows"][1] - rs["rows"][0], e["K"],
                         rs["rows"][0], rs["cols"][0])
            by_pair = {}
            for seg, pair, s0, cnt, stride, base, words in plans:
                for i in range(cnt):
                    s = s0 + i * stride
                    if s % NREG == REGION:
                        by_pair.setdefault(pair, []).append((s, seg))
            for pair in sorted(by_pair):
                if a.max_pairs and len(runs) >= a.max_pairs:
                    break
                pl = sorted(by_pair[pair])
                srows = sorted({s for s, _ in pl})
                loc = {s: j for j, s in enumerate(srows)}
                rows = [r for s in srows for r in (2 * s, 2 * s + 1) if r < e["rows"]]
                sub = F.take(full, rows)
                sub.s81_segments = e["segments"]
                sub.s81_place = [(loc[s], seg, 0) for s, seg in pl]
                fld = I.Field(1, 1, 0, pp=True, fast=True)
                ph = I.add_phase(fld, [sub], (False, False), 0)
                name = f"{phase}_{alias.replace('.', '_')}_p{pair}"
                d = a.out / name
                d.mkdir(exist_ok=True)
                for mb in range(2):
                    inst = "col" + ("b" if mb else "")
                    for parity in (0, 1):
                        t = d / f"{inst}_{parity}.viamap.hex"
                        A.viamap({k // 2: v for k, v in fld.words[mb].items() if k % 2 == parity}, t)
                        t.write_text("".join(t.read_text().splitlines(keepends=True)[:512]))
                gold = I.golden_phase([sub], x)
                tags = sorted(gold)
                hexfile(d / "x.hex", xb, 8)
                hexfile(d / "q.hex", [int.from_bytes(codes[k:k + 32].tobytes(), "little") for k in range(0, 5120, 32)], 64)
                hexfile(d / "e.hex", np.asarray(xe).astype(int) & 1023, 3)
                hexfile(d / "cfg.hex", fld.cfg[0][0], 12)
                hexfile(d / "stream.hex", fld.stream, 12)
                # gold.hex: {tag[15:0], fp32[31:0], bf16[15:0]} per row, tag order
                (d / "gold.hex").write_text("".join(f"{t:04x}{gold[t][0]:08x}{gold[t][1]:04x}\n" for t in tags))
                # tb_s81_die_layer stim fragment for root 0 (gap 1 per partial; the bench measures the real gaps)
                ptxt = (f"P {len(tags):x} 0 {OBASE:x} 0 0 0 0 0 {len(runs) + 1:x} {len(runs):x}\n")
                ptxt += "".join(f"C 1 0 {((t << 13) | 1):x} {gold[t][0]:x} 0\n" for t in tags)
                (d / "root0.stim").write_text(ptxt)
                meta = dict(run=name, phase=phase, x_case=case, alias=alias, tensor=e["tensor"], pair=pair,
                            region=REGION, superrows=srows, rank_rows=[rs["rows"][0] + r for r in rows],
                            local_rows=rows, nrows=len(tags), nbeat=ph["nbeat"], K=e["K"], segments=e["segments"],
                            gold_tags=tags, obase=OBASE)
                (d / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
                runs.append(meta)
    rec = dict(schema="opentallas.s81lv.field_stim.v1", runs=runs, pkl=str(a.pkl), pkl_sha256=sha(a.pkl),
               pkl_snapshots_sha256=pkl.get("snapshots_sha256"), checkpoint_revision=a.snapshot.name,
               checkpoint_header_sha256=ck.pins, matrix_map_sha256=sha(MAP),
               nbeat_max=max(r["nbeat"] for r in runs))
    (a.out / "runs.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"runs={len(runs)} rows={sum(r['nrows'] for r in runs)} nbeat_max={rec['nbeat_max']}")


if __name__ == "__main__":
    main()
