#!/usr/bin/env python3
"""S81 layer vehicle, seam S7 (sub-agent s81lv/C-engram): Engram lookup -> VM on layer L1 at P = 1,048,575.

Three steps:

  golden  (EPYC1: needs the released checkpoint rows; OT_V41_FLASH_SNAPSHOT = the ds_ckpt subset)
          The 1M reference token's history (results/rtl/w17_v41_1m_reference_token.json token_history), the
          released compressed token map (the sha-pinned payload tools/engram_token_map_image.py packs into the
          token-map ROM), tools/hdc_golden_v41.EngramTables (the golden hash: primes / offsets / multipliers of
          inference/engram.py) on the RELEASED config -> the 24 row ids of layer 1; the rows themselves are read from
          the released checkpoint (layers.1.engram.embed.weight F8_E4M3 [N, 256], .scale F8_E8M0 [N, 8]) by
          tools/rtl_v41_fullshape_layer_campaign.Checkpoint.rows.  Writes the golden JSON (ids, residues, 256 code
          bytes + 8 scale bytes per row, checkpoint provenance).
  stim    (any host) golden JSON -> bench files in a scratch dir:
            tok.hex     the 8 history tokens (raw ids) the bench feeds the real lead producer (token-map ROM + idwin)
            hbm_r<k>.hex  the HBM replay for home rank k (4 ranks x 6 columns): one line per recorded request,
                        "<atom> <9 atoms of 256 b>", the row in the lookup engine's table layout (264-B rows: 256
                        codes, byte 256 = scale, 257..260 CRC-32/MPEG-2 over bytes 0..256, ROWSTRIPE=1: 288-B rows)
            exp_r<k>.hex  the expected VM writes: "<row> <512 b>" (5 VM rows per Engram row, README layout)
          and cross-checks the RTL package's own hash model (hdc_v41_engram_shipped.hashes) against the golden ids.
  run     (fleet host) Verilator build of tb_s81lv_engram (+ the bucket mutant) and runs for the 4 home ranks;
          writes results/rtl/s81_layer_vehicle_1012/engram/bench_record.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
REF = ROOT / "results/rtl/w17_v41_1m_reference_token.json"
CONFIG = ROOT / "compiler/models/deepseek-v4.1-flash/inference_config.json"
TMAP = ROOT / "results/uarch/h4_c0_ds_external_source_provenance_20261003/r1/payloads/fbc8c3ec76fc1143_L01_token_map.npy"
TMAP_SHA = "fbc8c3ec76fc11430b854fb2ff267fdf923b5ff2d4f869e3c0433d8edc6479b1"
RES = ROOT / "results/rtl/s81_layer_vehicle_1012/engram"
GOLDEN = RES / "golden_L1_P1048575.json"
RECORD = RES / "bench_record.json"
D = ROOT / "rtl/dsrom_sys/s81_lv/engram"
LAYER, LI = 1, 0                     # Engram layer 1 = engram index 0 (cfg_layer 0)
NR, CPR, ATOMS = 4, 6, 9
VPR = 5                              # VM rows per Engram row


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ----------------------------------------------------------------------------------------------------------- golden
def tables():
    import hdc_golden_v41 as V
    if sha(TMAP) != TMAP_SHA:
        raise SystemExit("released token map identity")
    tm = np.load(TMAP, allow_pickle=False)
    V.compressed_token_map = lambda path, size: (tm, int(tm.max()) + 1)
    c = json.loads(CONFIG.read_text())
    return V.EngramTables(c, c["vocab_size"]), c, tm


def cmd_golden(a):
    import rtl_v41_fullshape_layer_campaign as LC
    t, c, tm = tables()
    ref = json.loads(REF.read_text())
    assert ref["position"] == 1048575 and ref["context"] == 1048576
    hist = [int(x) for x in ref["token_history"]]
    ids = t.hashes(hist, LI).reshape(-1)                         # [24] global row ids, column order (n-1, head)
    res = ids - t.offsets[LI]
    assert np.all(res >= 0) and np.all(res < t.primes[LI].reshape(-1))
    ck = LC.Checkpoint()
    wn, sn = f"layers.{LAYER}.engram.embed.weight", f"layers.{LAYER}.engram.embed.scale"
    wm, sm = ck.meta(wn), ck.meta(sn)
    assert wm[0]["dtype"] == "F8_E4M3" and sm[0]["dtype"] == "F8_E8M0", (wm[0], sm[0])
    codes = np.asarray(ck.rows(wn, ids), np.uint8)               # [24, 256] E4M3 codes
    scales = (np.asarray(ck.rows(sn, ids)) + 127).astype(np.uint8)   # [24, 8] raw UE8M0 bytes
    assert codes.shape == (24, 256) and scales.shape == (24, 8)
    win = [int(tm[hist[-1 - s]]) for s in range(4)]              # w0 = newest
    rec = dict(schema="opentallas.s81lv.engram_golden.v1", layer=LAYER, position=1048575, context=1048576,
               token_history=hist, window_compressed_newest_first=win,
               row_ids=[int(x) for x in ids], residues=[int(x) for x in res],
               rows=[dict(col=j, id=int(ids[j]), codes=codes[j].tobytes().hex(), scales=scales[j].tobytes().hex())
                     for j in range(24)],
               scales_uniform_per_row=[bool(len(set(scales[j].tolist())) == 1) for j in range(24)],
               source=dict(golden="tools/hdc_golden_v41.EngramTables.hashes (released config, released token map) + "
                                  "released checkpoint rows (Checkpoint.rows)",
                           checkpoint=str(ck.snap), weight_shard=wm[2], scale_shard=sm[2],
                           weight_shape=wm[0]["shape"], scale_shape=sm[0]["shape"],
                           rows_sha256=hashlib.sha256(codes.tobytes() + scales.tobytes()).hexdigest(),
                           sha256={str(p.relative_to(ROOT)): sha(p) for p in
                                   (REF, CONFIG, TMAP, TOOLS / "hdc_golden_v41.py",
                                    TOOLS / "rtl_v41_fullshape_layer_campaign.py", Path(__file__))}))
    out = Path(a.out) if a.out else GOLDEN
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print("golden", out, "ids", rec["row_ids"][:3], "uniform scales", sum(rec["scales_uniform_per_row"]), "/ 24")


# ------------------------------------------------------------------------------------------------------------- stim
def crc_mpeg2(data: bytes) -> int:
    c = 0xFFFFFFFF
    for b in data:
        c ^= b << 24
        for _ in range(8):
            c = ((c << 1) ^ 0x04C11DB7) if c & 0x80000000 else (c << 1)
            c &= 0xFFFFFFFF
    return c


def col_base(primes_flat, rk, j, rowb):
    acc = 0
    for i in range(j):
        sz = int(primes_flat[rk * CPR + i]) * rowb
        acc += (sz + 31) & ~31
    return acc


def stim_files(g: dict, out: Path, rowstripe: int):
    t, _, _ = tables()
    primes = t.primes[LI].reshape(-1)
    rowb = 288 if rowstripe else 264
    out.mkdir(parents=True, exist_ok=True)
    (out / "tok.hex").write_text("".join(f"{x:x}\n" for x in g["token_history"]))
    for rk in range(NR):
        hl, el = [], []
        for j in range(CPR):
            col = rk * CPR + j
            r = g["rows"][col]
            codes, sc = bytes.fromhex(r["codes"]), bytes.fromhex(r["scales"])
            body = codes + sc[:1]                                  # the engine's row: 256 codes + ONE scale byte
            row = body + crc_mpeg2(body).to_bytes(4, "little") + bytes(rowb - 261)
            b = col_base(primes, rk, j, rowb) + g["residues"][col] * rowb
            a0, off = b >> 5, b & 31
            span = bytes(off) + row
            span += bytes(ATOMS * 32 - len(span))
            assert len(span) == ATOMS * 32, (len(span), off)
            atoms = [int.from_bytes(span[32 * k:32 * k + 32], "little") for k in range(ATOMS)]
            hl.append(f"{a0:x} " + " ".join(f"{x:064x}" for x in atoms) + "\n")
            # expected VM rows (README layout): 4 code rows (64 codes each, byte i at bits 8i) + 1 scale row
            for q in range(4):
                el.append(f"{VPR * col + q:x} {int.from_bytes(codes[64 * q:64 * q + 64], 'little'):0128x}\n")
            el.append(f"{VPR * col + 4:x} {int.from_bytes(sc, 'little'):0128x}\n")
        (out / f"hbm_r{rk}.hex").write_text("".join(hl))
        (out / f"exp_r{rk}.hex").write_text("".join(el))
    # the RTL package's own hash model agrees with the golden ids (informational: the RTL computes them itself)
    import hdc_v41_engram_shipped as ES
    w = g["window_compressed_newest_first"]
    pk = [int(x) for x in np.asarray(ES.hashes(ES.shipped_tables(), [w[3], w[2], w[1], w[0]])[LI]).reshape(-1)]
    return pk == g["row_ids"]


def cmd_stim(a):
    g = json.loads(Path(a.golden).read_text())
    ok = stim_files(g, Path(a.out), a.rowstripe)
    print("stim", a.out, "package hash == golden ids:", ok)


# -------------------------------------------------------------------------------------------------------------- run
RTL = [ROOT / "rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv", ROOT / "rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv",
       ROOT / "rtl/dsrom_sys/engram/ot_dsrom_engram_lookup.sv", ROOT / "rtl/dsrom_sys/engram/dsfd_engram_lkp.sv",
       ROOT / "rtl/dsrom_sys/engram/ot_dsrom_engram_token_map.sv",
       ROOT / "rtl/dsrom_sys/engram/ot_dsrom_engram_idwin.sv",
       ROOT / "rtl/dsrom_sys/engram/ot_dsrom_engram_lead_producer.sv",
       ROOT / "physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v",
       ROOT / "rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv", ROOT / "rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv",
       D / "ot_s81lv_engram.sv", D / "ot_s81lv_engram_hbm_tlm.sv", D / "tb_s81lv_engram.sv"]
RE = re.compile(r"S81LV_ENGRAM (PASS|FAIL) rank=(\d) vm_rows=(\d+) checked=(\d+) mismatches=(\d+) hbm_req=(\d+) "
                r"hbm_unrecorded=(\d+) crc_bad=(\d+) fault=(\d) done=(\d) cycles=(\d+)")


def build(obj: Path, defines):
    vl = os.environ.get("VERILATOR", "verilator")
    subprocess.run([vl, "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
                    "-Wno-PINCONNECTEMPTY", "-Wno-IMPORTSTAR", "-Wno-DECLFILENAME", *defines,
                    "--top-module", "tb_s81lv_engram", "-Mdir", str(obj), *map(str, RTL)],
                   check=True, capture_output=True)
    return obj / "Vtb_s81lv_engram"


def cmd_run(a):
    import engram_token_map_image as TI
    s = Path(a.scratch)
    s.mkdir(parents=True, exist_ok=True)
    g = json.loads(GOLDEN.read_text())
    if not (s / "rom").exists():
        TI.prepare(s / "rom")
    rec = dict(schema="opentallas.s81lv.engram_bench.v1", seam="S7 engram lookup -> VM (L1)", layer=LAYER,
               position=1048575, configs={}, mutants={})
    for rs in a.rowstripe:
        st = s / f"stim_rs{rs}"
        rec["package_hash_matches_golden"] = stim_files(g, st, rs)
        for tag, defs in (("base", []), ("mut_bucket", ["+define+OT_S81LV_ENGRAM_MUT_BUCKET"])):
            exe = build(s / f"obj_rs{rs}_{tag}", [f"-GROWSTRIPE={rs}", *defs])
            runs = []
            for rk in range(NR):
                p = subprocess.run([str(exe), f"+RANK={rk}", f"+OT_ROM_DIR={s / 'rom'}", f"+TOK={st / 'tok.hex'}",
                                    f"+HBM={st / f'hbm_r{rk}.hex'}", f"+EXP={st / f'exp_r{rk}.hex'}", "+SEED=7"],
                                   capture_output=True, text=True, timeout=3600)
                m = RE.search(p.stdout)
                if not m:
                    runs.append(dict(rank=rk, pass_=False, log=p.stdout[-1200:] + p.stderr[-600:]))
                    continue
                v = m.groups()
                errs = [ln for ln in p.stdout.splitlines() if ln.startswith("ERR")][:4]
                runs.append(dict(rank=rk, pass_=v[0] == "PASS", vm_rows_written=int(v[2]), vm_rows_checked=int(v[3]),
                                 mismatches=int(v[4]), hbm_requests=int(v[5]), hbm_unrecorded=int(v[6]),
                                 crc_bad=int(v[7]), fault=int(v[8]), done=int(v[9]), cycles=int(v[10]),
                                 first_errors=errs))
                print(tag, "rs", rs, "rank", rk, v[0], flush=True)
            for r in runs:
                r["pass"] = r.pop("pass_")
            key = f"rowstripe{rs}"
            if tag == "base":
                rec["configs"][key] = dict(pass_=all(r["pass"] for r in runs), runs=runs,
                                           rows_checked=sum(r.get("vm_rows_checked", 0) for r in runs))
            else:
                rec["mutants"][key] = dict(mutant="bucket index +1 on the lookup's HBM request (column 0 of the rank)",
                                           define="OT_S81LV_ENGRAM_MUT_BUCKET", fails=all(not r["pass"] for r in runs),
                                           runs=runs)
    for v in rec["configs"].values():
        v["pass"] = v.pop("pass_")
    rec["status"] = "PASS" if (all(v["pass"] for v in rec["configs"].values())
                               and all(m["fails"] for m in rec["mutants"].values())) else "FAIL"
    rec["golden"] = dict(file=str(GOLDEN.relative_to(ROOT)), sha256=sha(GOLDEN), source=g["source"]["golden"],
                         rows_sha256=g["source"]["rows_sha256"], checkpoint=g["source"]["checkpoint"],
                         scales_uniform_rows=sum(g["scales_uniform_per_row"]))
    rec["source_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in RTL + [Path(__file__)]}
    rec["commit"] = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                                   text=True).stdout.strip()
    out = Path(a.record) if a.record else RECORD
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print("RECORD", out, rec["status"])


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("golden")
    p.add_argument("--out")
    p = sp.add_parser("stim")
    p.add_argument("--golden", default=str(GOLDEN))
    p.add_argument("--out", required=True)
    p.add_argument("--rowstripe", type=int, default=0)
    p = sp.add_parser("run")
    p.add_argument("--scratch", required=True)
    p.add_argument("--rowstripe", type=int, nargs="+", default=[0, 1])
    p.add_argument("--record")
    a = ap.parse_args()
    dict(golden=cmd_golden, stim=cmd_stim, run=cmd_run)[a.cmd](a)


if __name__ == "__main__":
    main()
