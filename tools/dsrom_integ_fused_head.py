#!/usr/bin/env python3
"""DS-ROM integration checkpoint, vehicle (b): the L1 FUSED DSpark draft head on the S81 full-shape head argmax
path (rtl/dsrom_sys/integration/ot_dsrom_s81_head_amax_fh.sv, FH = 1), TP4 x 32,320 rows, R = 128 lanes, at
position 1,048,575, bit-exact against tools/hdc_golden_v41 (HDC_V41_ARITH = chunk8, the 1M reference's contract).

Operands (honest labels):
  LG   the released lm_head rows at position 1,048,575: the 1M reference token's golden head logits
       (ctx1048576_head.npz 'logits'), standing in for draft slot 0's lm_head output (the draft shares the lm_head
       rows; slot 0's hidden state at 1M needs a DSpark forward pass, which is model inference and not run here);
  MK   markov(y) = mv(mtp.2.markov_head.head, mtp.2.markov_head.embed[y]) on the released weights, y the verified
       1M token (argmax LG): a 129,280 x 256 golden matvec, the draft chain's Markov bias for row 0;
  d1   = argmax(add(LG, MK)) (Model.draft's step: one FP32 RNE add, LG first, first maximum).
Runs: FH = 1 (op 1 capture/verify -> y, op 2 fused -> d1, every fused lane value checked) and the control FH = 0
(op 2 argmaxes MK alone: the silent wrong draft the as-built S81 path would give for the reduced core's fused
encoding).

    python3 tools/dsrom_integ_fused_head.py --scratch DIR [--out results/rtl/dsrom_integration_20261004/fused_head.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
GOLD = Path("/home/ubuntu/w17work/ref/ctx1048576_seed20260930")
SNAP = Path("/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/"
            "dba1be0a40aa45a94ad051997016db3960a90277")
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
SRC = ["rtl/rom/collectives/ot_rom_coll_pkg.sv", "rtl/rom/collectives/ot_rom_coll_skid.sv",
       "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/dsrom_sys/s81_native_head/ot_rom_argmax_rows.sv",
       "rtl/dsrom_sys/integration/ot_dsrom_s81_head_amax_fh.sv"]
TB = "rtl/dsrom_sys/integration/tb_dsrom_s81_fused_head_tp4.sv"
ROWS, TP = 32320, 4
VERIFY = dict(id=21946, logits_sha256="241c577cb0e19ef9ffa7efb0e08c6d6004ef21827101ebfe21276582acf49ec2",
              record="results/rtl/w17_v41_1m_reference_token.json (next_token at position 1,048,575)")


def sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def bf16_tensor(name):
    idx = json.loads((SNAP / "model.safetensors.index.json").read_text())["weight_map"]
    f = SNAP / idx[name]
    with open(f, "rb") as fh:
        n = struct.unpack("<Q", fh.read(8))[0]
        hdr = json.loads(fh.read(n))[name]
        assert hdr["dtype"] == "BF16", hdr
        lo, hi = hdr["data_offsets"]
        fh.seek(8 + n + lo)
        raw = np.frombuffer(fh.read(hi - lo), dtype=np.uint16).reshape(hdr["shape"])
    return (raw.astype(np.uint32) << 16).view(np.float32), dict(file=idx[name], shape=hdr["shape"])


def golden():
    import hdc_golden_v41 as V
    V.set_arith("chunk8")
    lg = np.load(GOLD / "ctx1048576_head.npz")["logits"].astype(np.float32)
    assert lg.shape == (TP * ROWS,)
    y = int(np.argmax(lg))
    ybits = int(V.bits(lg[y:y + 1])[0])
    emb, ei = bf16_tensor("mtp.2.markov_head.embed.weight")
    mh, mi = bf16_tensor("mtp.2.markov_head.head.weight")
    mk = np.asarray(V.mv(mh, emb[y]), dtype=np.float32)
    fused = np.asarray(V.add(lg, mk), dtype=np.float32)
    d1 = int(np.argmax(fused))
    s = np.sort(fused)[::-1]
    return dict(lg=lg, mk=mk, fused=fused, y=y, y_bits=ybits, d1=d1, d1_bits=int(V.bits(fused[d1:d1 + 1])[0]),
                mk_argmax=int(np.argmax(mk)), mk_argmax_bits=int(V.bits(mk[int(np.argmax(mk)):int(np.argmax(mk)) + 1])[0]),
                fused_margin=float(s[0] - s[1]), weights=dict(embed=ei, head=mi), bitsf=V.bits)


def build(obj: Path, fh: int):
    exe = obj / "Vtb_dsrom_s81_fused_head_tp4"
    if exe.exists():
        return exe
    obj.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(VERILATOR), "--cc", "--exe", "--build", "-j", "8", "-O2", "-Wno-fatal", "-Wno-lint",
                    "-Wno-style", "--top-module", "tb_dsrom_s81_fused_head_tp4", f"-GFH={fh}", "--Mdir", str(obj),
                    *[str(ROOT / s) for s in SRC + [TB]], str(ROOT / "rtl/dsrom_sys/integration/tb_dsrom_s81_fused_head_tp4_harness.cpp"),
                    "-CFLAGS", "-O1"], check=True, capture_output=True, cwd=ROOT)
    return exe


OPL = re.compile(r"OP (\d) fh=(\d) id=(\d+) val=([0-9a-f]+) beats=(\d+) first_beat=(\d+) last_beat=(\d+) "
                 r"dn0=(-?\d+) dn1=(-?\d+) dn2=(-?\d+) dn3=(-?\d+) final=(\d+) done=(\d+)")


def run(exe, scratch: Path, fh: int):
    dump = scratch / f"fused_fh{fh}.dump"
    t0 = time.time()
    r = subprocess.run([str(exe), f"+LG={scratch / 'lg.hex'}", f"+MK={scratch / 'mk.hex'}", f"+DUMP={dump}"],
                       capture_output=True, text=True)
    ops = {}
    for m in OPL.finditer(r.stdout):
        op, _, i, v, nb, fb, lb, d0, d1, d2, d3, fin, done = m.groups()
        ops[int(op)] = dict(id=int(i), bits=int(v, 16), beats=int(nb), first_beat=int(fb), last_beat=int(lb),
                            rank_dn=[int(d0), int(d1), int(d2), int(d3)], final=int(fin), done=int(done),
                            last_beat_to_rank0_result=int(d0) - int(lb), last_beat_to_final=int(fin) - int(lb),
                            first_beat_to_final=int(fin) - int(fb))
    ok = r.returncode == 0 and "DONE" in r.stdout and set(ops) == {1, 2}
    return dict(returncode=r.returncode, completed=ok, ops=ops, wall_s=round(time.time() - t0, 1),
                tail=(r.stdout + r.stderr).splitlines()[-6:]), dump


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "results/rtl/dsrom_integration_20261004/fused_head.json")
    a = ap.parse_args()
    sc = a.scratch.resolve()
    sc.mkdir(parents=True, exist_ok=True)
    g = golden()
    assert g["y"] == VERIFY["id"], g["y"]
    assert hashlib.sha256(g["lg"].tobytes()).hexdigest() == VERIFY["logits_sha256"]
    bits = g["bitsf"]
    (sc / "lg.hex").write_text("".join(f"{int(b):08x}\n" for b in bits(g["lg"])))
    (sc / "mk.hex").write_text("".join(f"{int(b):08x}\n" for b in bits(g["mk"])))
    print("golden y", g["y"], "d1", g["d1"], hex(g["d1_bits"]), "markov-only", g["mk_argmax"], flush=True)
    res = {}
    for fh in (1, 0):
        exe = build(sc / f"obj_fh{fh}", fh)
        res[fh], dump = run(exe, sc, fh)
        if fh == 1 and dump.exists():
            got = {}
            for ln in dump.read_text().split("\n"):
                if ln:
                    i, v = ln.split()
                    got[int(i, 16)] = int(v, 16)
            exp = bits(g["fused"])
            ids = np.fromiter(got.keys(), dtype=np.int64)
            vals = np.fromiter(got.values(), dtype=np.uint32)
            mism = int((exp[ids] != vals).sum())
            res[fh]["fused_lanes"] = dict(rows_seen=len(got), rows_expected=TP * ROWS, bit_mismatches=mism,
                                          missing=TP * ROWS - len(got))
        print(fh, json.dumps({k: v for k, v in res[fh].items() if k != "tail"}), flush=True)
    r1, r0 = res[1], res[0]
    ok1 = (r1["completed"] and r1["ops"][1]["id"] == g["y"] and r1["ops"][1]["bits"] == g["y_bits"]
           and r1["ops"][2]["id"] == g["d1"] and r1["ops"][2]["bits"] == g["d1_bits"]
           and r1["fused_lanes"]["bit_mismatches"] == 0 and r1["fused_lanes"]["missing"] == 0)
    ok0 = (r0["completed"] and r0["ops"][1]["id"] == g["y"] and r0["ops"][2]["id"] == g["mk_argmax"]
           and r0["ops"][2]["bits"] == g["mk_argmax_bits"])
    lat = {k: r1["ops"][2][k] - r1["ops"][1][k] for k in ("last_beat_to_rank0_result", "last_beat_to_final")}
    rec = dict(
        schema="opentallas.dsrom-integration.fused-head.v1",
        vehicle="S81 head argmax TP4 (4 ranks x 32,320 rows, R = 128 lanes, NW 21, AW 30) with the L1 fused draft "
                "head ported into ot_dsrom_s81_head_amax_fh (FH = 1); minimum component of the head die",
        position=1048575,
        finding=("L1 (main ec7b1ff18) was built only on the reduced core's engine-0 ot_hdc_v41_matvec (i_oacc); "
                 "ot_hdc_core_v41x routes weight ops to ot_hdc_v41x_me_adapt when X_ME = 1 (S81: X_ME = 1, "
                 "X_ROM = 1) and decodes `ad` only for the stream unit, so the fused encoding would argmax the "
                 "Markov output alone (control FH = 0 below)"),
        operands=dict(LG="ctx1048576_head.npz logits (released lm_head at position 1,048,575), standing in for draft "
                         "slot 0's lm_head output (same rows; slot 0's DSpark hidden state at 1M is model inference, "
                         "not run)",
                      MK="mv(mtp.2.markov_head.head, mtp.2.markov_head.embed[y]), released weights, chunk8",
                      y=g["y"], verify_reference=VERIFY, weights=g["weights"],
                      sha256=dict(head_npz=sha(GOLD / "ctx1048576_head.npz"), lg_hex=sha(sc / "lg.hex"),
                                  mk_hex=sha(sc / "mk.hex"))),
        golden=dict(verify_id=g["y"], verify_bits=g["y_bits"], draft_d1=g["d1"], draft_d1_bits=g["d1_bits"],
                    fused_top2_margin=g["fused_margin"], markov_only_argmax=g["mk_argmax"],
                    markov_only_bits=g["mk_argmax_bits"]),
        fh1=r1, fh0_control=r0,
        added_latency_cycles=dict(design=6, basis="1 synchronous addend read + 5 ot_fp32_add_rne_pipe stages",
                                  measured_op2_minus_op1=lat),
        pass_=bool(ok1 and ok0), fh1_exact=bool(ok1), fh0_control_reproduces_wrong_draft=bool(ok0),
        notes=["addend memory behavioural (32,320 words a rank, R ports); silicon banks it by return lane, which "
               "requires the Markov rows to return on the same lanes as the head rows (row-congruent placement of the "
               "markov_head table on the head die) or a VM read path of R words a cycle",
               "FH = 0 is the as-built ot_dsrom_s81_head_amax (capture / fuse ignored); the original file is unchanged"],
        source_sha256={p: sha(ROOT / p) for p in SRC + [TB, "rtl/dsrom_sys/integration/tb_dsrom_s81_fused_head_tp4_harness.cpp",
                                                        "tools/dsrom_integ_fused_head.py",
                                                        "rtl/dsrom_sys/s81_native_head/ot_dsrom_s81_head_amax.sv"]},
        simulator=subprocess.run([str(VERILATOR), "--version"], capture_output=True, text=True).stdout.strip())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print("PASS" if rec["pass_"] else "FAIL", json.dumps(dict(golden=rec["golden"], latency=lat)))
    return 0 if rec["pass_"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
