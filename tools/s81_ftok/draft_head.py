#!/usr/bin/env python3
"""S81 DSpark DRAFT HEAD on RTL (s81-functional-token r3, 2026-10-14): for every draft block row i (5 rows), the last
DSpark stage's final-norm x -> lm_head roots of all 129,280 rows (field partials, golden) -> the native head terminal of
all four ranks (ot_s81_native_head_tp4: per row the RTL join root4096 + ((root1024 + 0) + 0)) -> per row the
production Markov row engine ot_dsrom_markov_row (the dot+join of ot_dsrom_markov_head_driver: markov_head[v] .
embed[d_i], K 256 BF16, joined to the head logit by the separate add) on the RELEASED mtp.2.markov_head weights ->
ot_rom_argmax_reduce per rank, ranks chained 0 -> 3 -> d_{i+1}.

Golden (tools/s81_ftok/mtp_golden.py draft_head.npz, = Model.draft): xf_i, head logits, Markov bias, final logits,
d_i (in), d_{i+1} (out).  Asserted here before writing: merge(roots) == head logit for every row, csum(w * x) of the
Markov row == the Markov bias, add(head, markov) == the final logit.

    python3 tools/s81_ftok/draft_head.py golden --mtp DIR --work WDIR      # checkpoint host
    python3 tools/s81_ftok/draft_head.py run    --work WDIR [--rows 0,1,2,3,4] [--mut 1]
Verdict: S81_DRAFT_HEAD PASS|FAIL row=i token=<id>.  --mut 1: ot_dsrom_markov_row MUTANT_FOLD 1 (its designed negative
control), must FAIL.
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
VOCAB, K, RANKS, MK = 129280, 5120, 4, 256
ROWS = VOCAB // RANKS
TB = "rtl/dsrom_sys/s81_native_head_connect/test/tb_s81_draft_head.sv"
RTL = ["rtl/rom/collectives/ot_rom_coll_pkg.sv", "rtl/rom/collectives/ot_rom_argmax_reduce.sv",
       "rtl/rom/collectives/ot_rom_coll_skid.sv", "rtl/test/s81_native_head_terminal/native_head_carried.sv",
       "rtl/dsrom_sys/s81_native_head_connect/ot_s81_native_head_tp4.sv", "rtl/hdc/ot_hdc_fastfp.sv",
       "rtl/common/ot_prefix.sv", "rtl/v41rom/ot_v41_bmul2.sv", "rtl/v41rom/ot_dsrom_bmul3.sv", "rtl/v41rom/ot_v41_fadd.sv",
       "rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_row.sv"]
VL = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"


def bf16_rows(name, ids, ck_root):
    """rows of a [129280, 256] BF16 tensor of the checkpoint as uint16"""
    idx = json.loads((ck_root / "model.safetensors.index.json").read_text())["weight_map"] \
        if (ck_root / "model.safetensors.index.json").exists() else None
    files = [idx[name]] if idx else sorted(p.name for p in ck_root.glob("*.safetensors"))
    for fn in files:
        with open(ck_root / fn, "rb") as f:
            n = int.from_bytes(f.read(8), "little")
            h = json.loads(f.read(n))
            if name not in h:
                continue
            e = h[name]
            assert e["dtype"] == "BF16" and e["shape"][1] == MK, e
            off = 8 + n + e["data_offsets"][0]
            if ids is None:
                f.seek(off)
                return np.frombuffer(f.read(e["shape"][0] * MK * 2), dtype="<u2").reshape(-1, MK).copy()
            out = []
            for i in ids:
                f.seek(off + int(i) * MK * 2)
                out.append(np.frombuffer(f.read(MK * 2), dtype="<u2").copy())
            return np.array(out)
    raise KeyError(name)


def beats_hex(rows16):
    """[n, 256] uint16 -> 16 lines of 64 hex a row (element l of beat b at bits 16l)"""
    r = np.asarray(rows16, np.uint64).reshape(-1, 16, 16)
    lines = []
    for row in r:
        for b in row:
            v = 0
            for l_ in range(15, -1, -1):
                v = (v << 16) | int(b[l_])
            lines.append(f"{v:064x}\n")
    return lines


def cmd_golden(a):
    import dsrom_1m_head as DH
    DH.setup_gate()
    G, gate = DH.G, DH.gate
    snap = Path(os.environ.get("OT_V41_FLASH_SNAPSHOT", DH.SNAP))
    ck = DH.Ckpt(snap)
    z = np.load(Path(a.mtp) / "draft_head.npz")
    w = Path(a.work)
    w.mkdir(parents=True, exist_ok=True)
    mw = bf16_rows("mtp.2.markov_head.head.weight", None, snap)
    assert mw.shape == (VOCAB, MK), mw.shape
    with open(w / "mk_w.hex", "w") as f:
        for s in range(0, VOCAB, 4096):
            f.writelines(beats_hex(mw[s:s + 4096]))
    mwf = (mw.astype(np.uint32) << 16).view(np.float32)
    rec = dict(rows=[], snapshot=str(snap))
    for i in range(len(z["tokens_in"])):
        xf, hl, mb, fl = z["xf"][i], z["head_logits"][i], z["markov"][i], z["logits"][i]
        tin, tout = int(z["tokens_in"][i]), int(z["tokens_out"][i])
        xe = bf16_rows("mtp.2.markov_head.embed.weight", [tin], snap)
        xef = (xe.astype(np.uint32) << 16).view(np.float32)[0]
        mk = G.csum(G.mul(mwf, xef[None, :]))
        assert np.array_equal(G.bits(mk), G.bits(mb)), "markov csum == golden markov bias"
        assert np.array_equal(G.bits(G.add(hl, mk)), G.bits(fl)), "head + markov == golden logits"
        (w / f"mk_x_d{i}.hex").write_text("".join(beats_hex(xe)))
        for r in range(RANKS):
            ra, rb = [], []
            for s in range(0, ROWS, 2048):
                n = min(2048, ROWS - s)
                m = gate.Mat(ck, "head", "bf16", n, K, r0=r * ROWS + s)
                p = G.mul(np.asarray(m.wf, dtype=G.F), np.asarray(xf, G.F)[None, :])
                ra.append(G.csum(p[:, :4096]))
                rb.append(G.csum(p[:, 4096:]))
                assert np.array_equal(G.bits(DH.merge(ra[-1], rb[-1])), G.bits(hl[r * ROWS + s:r * ROWS + s + n])), \
                    "roots merge == golden draft head logits"
            ra, rb = np.concatenate(ra), np.concatenate(rb)
            with open(w / f"roots_d{i}_r{r}.mem", "w") as f:
                for x, y in zip(G.bits(ra), G.bits(rb)):
                    f.write(f"{int(x):08x}{int(y):08x}\n")
            with open(w / f"logits_d{i}_r{r}.mem", "w") as f:
                for x in G.bits(fl[r * ROWS:(r + 1) * ROWS]):
                    f.write(f"{int(x):08x}\n")
        am = int(np.argmax(fl))
        assert am == tout, (am, tout)
        (w / f"expect_d{i}.mem").write_text(f"{am:08x}\n{int(G.bits(fl[am:am + 1])[0]):08x}\n")
        rec["rows"].append(dict(row=i, token_in=tin, token_out=tout, bits=int(G.bits(fl[am:am + 1])[0])))
        print(f"draft row {i}: d_in {tin} -> d_out {tout}, roots/markov/join asserted", flush=True)
    (w / "golden.json").write_text(json.dumps(rec, indent=1) + "\n")


def cmd_run(a):
    w = Path(a.work)
    obj = w / f"obj_m{a.mut}"
    exe = obj / "Vtb_s81_draft_head"
    if not exe.exists():
        obj.mkdir(parents=True, exist_ok=True)
        cmd = [str(VL), "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-lint", "--top-module", "tb_s81_draft_head",
               "-Mdir", str(obj), "-j", "16", f"-GMUT={a.mut}", *[str(ROOT / s) for s in RTL], str(ROOT / TB), "-CFLAGS", "-O1"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        (w / f"build_m{a.mut}.log").write_text(" ".join(cmd) + "\n" + r.stdout + r.stderr)
        if r.returncode:
            sys.exit(f"build failed: {w}/build_m{a.mut}.log")
    ok_all = True
    for i in [int(x) for x in a.rows.split(",")]:
        r = subprocess.run([str(exe), f"+DIR={w}", f"+D={i}"], capture_output=True, text=True)
        (w / f"run_m{a.mut}_d{i}.log").write_text(r.stdout + r.stderr)
        v = [x for x in r.stdout.splitlines() if x.startswith("S81_DRAFT_HEAD")]
        print("\n".join(v) if v else f"row {i} NO RESULT\n" + (r.stdout + r.stderr)[-1500:], flush=True)
        ok_all &= bool(v) and " PASS " in v[-1] + " "
    return 0 if ok_all == (a.mut == 0) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("step", choices=("golden", "run"))
    ap.add_argument("--work", required=True)
    ap.add_argument("--mtp", default=None)
    ap.add_argument("--rows", default="0,1,2,3,4")
    ap.add_argument("--mut", type=int, default=0)
    a = ap.parse_args()
    return dict(golden=cmd_golden, run=cmd_run)[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
