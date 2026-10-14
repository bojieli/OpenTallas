#!/usr/bin/env python3
"""S81 head stage on RTL for the 1M token (s81-functional-token r3, 2026-10-14): lm_head roots of ALL 129,280 rows ->
the S81 native head terminal of all four ranks (ot_s81_native_head_tp4 = 4 x s81_native_head_carried: per row the
golden padded-tree join root4096 + ((root1024 + 0) + 0) on three ot_hdc_fp32_add_fast, the ROM carried argmax
ot_rom_argmax_reduce, the rank chain 0 -> 1 -> 2 -> 3 in ascending vocabulary order) -> the next token.

The lm_head roots are the field's partial sums (K 0..4095 and 4096..5119, chunk8 csum) of the released head.weight
against the golden final-norm x (shard ctx1048576_head.npz xf), computed here and asserted: merge == csum of the full
row == the shard's golden logit, for every row.  (One return group of this matvec is RTL-measured on the native ROM
element by tools/dsrom_1m_head.py lmhead; here, as in the layer vehicle, the field's roots enter as golden.)

    python3 tools/s81_ftok/head_stage.py golden --work DIR          # checkpoint host: roots_r{0..3}.mem, golden.json
    python3 tools/s81_ftok/head_stage.py run    --work DIR [--mut 1] # tb_s81_head_tp4 (Verilator)
Verdict line: S81_HEAD PASS|FAIL token=<id> (expect 21946).  --mut 1: the rank-0 join drops phase B (root1024), must FAIL.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
VOCAB, K, RANKS = 129280, 5120, 4
ROWS = VOCAB // RANKS
TOKEN = 21946
TB = "rtl/dsrom_sys/s81_native_head_connect/test/tb_s81_head_tp4.sv"
RTL = ["rtl/rom/collectives/ot_rom_coll_pkg.sv", "rtl/rom/collectives/ot_rom_argmax_reduce.sv", "rtl/rom/collectives/ot_rom_coll_skid.sv",
       "rtl/test/s81_native_head_terminal/native_head_carried.sv",
       "rtl/dsrom_sys/s81_native_head_connect/ot_s81_native_head_tp4.sv", "rtl/hdc/ot_hdc_fastfp.sv"]
VL = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"


def cmd_golden(a):
    import dsrom_1m_head as DH
    DH.setup_gate()
    G, gate = DH.G, DH.gate
    xf, logits = DH.golden_x()
    snap = Path(os.environ.get("OT_V41_FLASH_SNAPSHOT", DH.SNAP))
    ck = DH.Ckpt(snap)
    w = Path(a.work)
    w.mkdir(parents=True, exist_ok=True)
    rec = dict(rows=VOCAB, ranks=RANKS, snapshot=str(snap), xf_sha256=__import__("hashlib").sha256(xf.tobytes()).hexdigest())
    for r in range(RANKS):
        ra, rb = [], []
        for s in range(0, ROWS, 2048):
            n = min(2048, ROWS - s)
            m = gate.Mat(ck, "head", "bf16", n, K, r0=r * ROWS + s)
            p = G.mul(np.asarray(m.wf, dtype=G.F), xf[None, :])
            ra.append(G.csum(p[:, :4096]))
            rb.append(G.csum(p[:, 4096:]))
            assert np.array_equal(G.bits(DH.merge(ra[-1], rb[-1])), G.bits(G.csum(p))), "padded-tree split"
            assert np.array_equal(G.bits(DH.merge(ra[-1], rb[-1])), G.bits(logits[r * ROWS + s:r * ROWS + s + n])), "golden logits"
        ra, rb = np.concatenate(ra), np.concatenate(rb)
        with open(w / f"roots_r{r}.mem", "w") as f:
            for x, y in zip(G.bits(ra), G.bits(rb)):
                f.write(f"{int(x):08x}{int(y):08x}\n")
        with open(w / f"logits_r{r}.mem", "w") as f:
            for x in G.bits(logits[r * ROWS:(r + 1) * ROWS]):
                f.write(f"{int(x):08x}\n")
        print(f"rank {r}: {ROWS} rows, merge == csum == golden logits", flush=True)
    am = int(np.argmax(logits))
    rec.update(argmax=am, argmax_bits=int(G.bits(logits[am:am + 1])[0]), argmax_is_token=am == TOKEN,
               max_ties=int(np.sum(logits == logits[am])))
    assert am == TOKEN, am
    (w / "golden.json").write_text(json.dumps(rec, indent=1) + "\n")
    (w / "expect.mem").write_text(f"{am:08x}\n{rec['argmax_bits']:08x}\n")
    print(json.dumps(rec))


def cmd_run(a):
    w = Path(a.work)
    obj = w / f"obj_m{a.mut}"
    exe = obj / "Vtb_s81_head_tp4"
    if not exe.exists():
        obj.mkdir(parents=True, exist_ok=True)
        cmd = [str(VL), "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-lint", "--top-module", "tb_s81_head_tp4",
               "-Mdir", str(obj), "-j", "16", f"-GMUT={a.mut}", *[str(ROOT / s) for s in RTL], str(ROOT / TB), "-CFLAGS", "-O1"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        (w / f"build_m{a.mut}.log").write_text(" ".join(cmd) + "\n" + r.stdout + r.stderr)
        if r.returncode:
            sys.exit(f"build failed: {w}/build_m{a.mut}.log")
    r = subprocess.run([str(exe), f"+DIR={w}"], capture_output=True, text=True)
    (w / f"run_m{a.mut}.log").write_text(r.stdout + r.stderr)
    v = [x for x in r.stdout.splitlines() if x.startswith("S81_HEAD")]
    print("\n".join(v) if v else "NO RESULT\n" + (r.stdout + r.stderr)[-2000:])
    ok = bool(v) and " PASS " in v[-1] + " "
    return 0 if ok == (a.mut == 0) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("step", choices=("golden", "run"))
    ap.add_argument("--work", required=True)
    ap.add_argument("--mut", type=int, default=0)
    a = ap.parse_args()
    return dict(golden=cmd_golden, run=cmd_run)[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
