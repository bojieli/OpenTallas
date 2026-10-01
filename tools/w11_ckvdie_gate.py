#!/usr/bin/env python3
"""W11 CKV die-service gate: the L20 selected compressed rows through ids -> owned fetch -> all-gather -> collector
-> FP4 merger on four dies (rtl/test/tb_w11_ckvdie_service.sv), exact against the golden.

Inputs (W17 L20 images and golden scratch):
  --images /home/ubuntu/w17work/die/ctx1048576_s20260930_L20   r<k>/expect_vm.hex (SELG ids), r<k>/ckv_s<s>.hex
  --golden /home/ubuntu/w17work/isa/scratch_s20260930/ctx1048576_L20.npz  (ckv20: the position's own row)
The golden's selected rows: tools/rtl_v41_fullshape_layer_campaign.synthetic_state (the same state the ISA executor
uses), rows st["ckv"][20][id] for id < n and ckv20 for id = n.

Checks, per die and per pass (QK, PV):
  * every streamed row is an FP4 group-word row (fmt 1), in rank order, and its dequantised values (the engine's
    attn_deq: E2M1 code x E4M3 scale -> BF16) equal the golden row bit for bit;
  * the own row (id n, selected) is non-zero, re-encoded on every die, and its codes and E4M3 scales equal the
    golden encoder applied to the golden row (fp4 codes of qdq values: identical except a signed zero);
  * the owner die (id[5:4]) writes it to stack id[7:6], sectors 2^22 + 9 * local + k, as the golden encoding;
  * no HBM read outside the image (wrong address), no fault.
Writes --record (never overwrites a failed verdict).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
SRC = ["rtl/chip/ot_chip_v41x_ckv_die_service.sv", "rtl/chip/ot_chip_v41x_ckv_row_encoder.sv",
       "rtl/chip/ot_chip_v41x_ckv_sel_ids.sv", "rtl/chip/ot_chip_v41x_ckv_sel_fetch.sv",
       "rtl/chip/ot_chip_v41x_ckv_selected_dma.sv", "rtl/chip/ot_chip_v41x_ckv_fp4_decode.sv",
       "rtl/chip/ot_chip_v41x_ckv_stream_merge.sv", "rtl/test/tb_w11_ckvdie_service.sv"]
TOOLS = ["tools/w11_ckvdie_gate.py", "tools/hdc_golden_v41.py", "tools/rtl_v41_fullshape_layer_campaign.py",
         "tools/v41_ckv_sel_attn_vectors.py"]
VL = Path(os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
SELG = 447360
CKV_BASE = 1 << 22


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def owner(g):
    return (g >> 4) & 3, (g >> 6) & 3, ((g >> 8) << 4) | (g & 15)


def read_ids(img):
    out = []
    for r in range(4):
        with open(img / f"r{r}" / "expect_vm.hex") as f:
            for i, line in enumerate(f):
                if i >= SELG + 512:
                    break
                if i >= SELG:
                    out.append(int(line, 16))
    ids = [out[r * 512:(r + 1) * 512] for r in range(4)]
    assert all(x == ids[0] for x in ids), "selection differs between ranks"
    return ids[0]


def golden_rows(ids, gold_npz):
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    V.set_arith("chunk8")
    z = np.load(gold_npz)
    new = z["ckv20"].astype(np.float32)
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=False)
    st, desc = LC.synthetic_state(m, 1048576, seed=20260930, layers=[20])   # the headline token's seed (W17)
    src = m.kv_of[20]
    ckv = st["ckv"][src]
    n = len(ckv)
    rows = np.stack([np.asarray(ckv[g], dtype=np.float32) if g < n else new for g in ids])
    return rows, n, new, desc["sha256"].get(f"ckv{src}")


def deq_row(words):
    """16 group words (fmt 1) -> 512 float32 values (E2M1 x E4M3), the engine's attn_deq."""
    import hdc_golden_v41 as V
    e2m1 = np.concatenate([V.E2M1_VALUES, -V.E2M1_VALUES])
    out = np.zeros(512, dtype=np.float32)
    fmts = []
    for g, w in enumerate(words):
        fmts.append(w >> 264)
        for x in range(32):
            code = (w >> (4 * x)) & 15
            sc = (w >> (128 + 8 * (x // 16))) & 255
            out[32 * g + x] = np.float32(e2m1[code] * V.E4M3[sc])
    return V.to_bf16(out), fmts


def prep(a, out):
    ids = read_ids(a.images)
    gold, n, new, ckv_sha = golden_rows(ids, a.golden)
    assert ids == sorted(ids) and len(set(ids)) == 512
    new_sel = ids[-1] == n
    out.mkdir(parents=True, exist_ok=True)
    words = [sum(ids[16 * w + l] << (32 * l) for l in range(16)) for w in range(32)]
    (out / "ids.hex").write_text("".join(f"{w:0128x}\n" for w in words))
    import hdc_golden_v41 as V
    nb = V.bits(np.asarray(new, dtype=np.float32)).astype(np.int64) >> 16
    beats = [sum(int(nb[32 * b + i]) << (32 * i + 16) for i in range(32)) for b in range(16)]
    (out / "nw.hex").write_text("".join(f"{x:0256x}\n" for x in beats))
    (out / "cfg.hex").write_text(f"{n:08x}\n{SELG // 16:08x}\n{n * 512:08x}\n" + "00000000\n" * 5)
    # sparse HBM: the selected rows' sectors and their +-1 neighbours, from each die's ckv_s<k>.hex
    want = {}
    for g in ids:
        for dg in (-1, 0, 1):
            h = g + dg
            if 0 <= h < n:
                d, s, loc = owner(h)
                for k in range(9):
                    want.setdefault((d, s), set()).add(CKV_BASE + 9 * loc + k)
    for d in range(4):
        lines = []
        for s in range(4):
            sec = want.get((d, s), set())
            with open(a.images / f"r{d}" / f"ckv_s{s}.hex") as f:
                for line in f:
                    sa, sw = line.split()
                    if int(sa, 16) in sec:
                        lines.append(f"{s:x} {sa} {sw}\n")
        (out / f"hbm_d{d}.hex").write_text("".join(lines))
    np.save(out / "gold.npy", gold)
    return dict(ids=ids, n=n, new_selected=new_sel, new_nonzero=bool(np.any(new != 0)),
                owned=[sum(1 for g in ids if owner(g)[0] == d) for d in range(4)], ckv_state_sha256=ckv_sha)


def build(b):
    b.mkdir(parents=True, exist_ok=True)
    cmd = [str(VL), "--binary", "--timing", "-j", "8", "-Wno-fatal", "-Wno-WIDTH", "-Wno-TIMESCALEMOD", "-Mdir", str(b),
           "--top-module", "tb_w11_ckvdie_service", "--x-assign", "unique", "--x-initial", "unique",
           *[str(ROOT / s) for s in SRC], "-CFLAGS", "-O1"]
    subprocess.run(cmd, check=True, capture_output=True)
    return b / "Vtb_w11_ckvdie_service"


def check(out_dir, stdout, info):
    import hdc_golden_v41 as V
    sys.path.insert(0, str(ROOT / "tools"))
    from v41_ckv_sel_attn_vectors import fp4_codes
    gold = np.load(out_dir / "gold.npy")
    summ = [x for x in stdout.splitlines() if x.startswith("CKVDIE ")]
    fields = {k: v for k, v in re.findall(r"(\w+)=([\w,]+)", summ[-1])} if summ else {}
    res = dict(fields=fields, rows_checked=0, row_errors=0, fmt_errors=0, passes={})
    rows = {}
    for line in stdout.splitlines():
        if line.startswith("ROW "):
            _, d, p, r, hx = line.split()
            rows.setdefault((int(d), int(p)), {})[int(r)] = hx
    for (d, p), rr in sorted(rows.items()):
        res["passes"][f"d{d}p{p}"] = len(rr)
        for r, hx in rr.items():
            words = [int(hx[67 * e:67 * (e + 1)], 16) for e in range(16)][::-1]
            vals, fmts = deq_row(words)
            res["rows_checked"] += 1
            if any(f != 1 for f in fmts):
                res["fmt_errors"] += 1
            if not np.array_equal(V.bits(vals), V.bits(gold[r].astype(np.float32))):
                res["row_errors"] += 1
    # own row: owner writes = golden encoding of the golden row
    n = info["n"]
    d_own, s_own, loc = owner(n)
    codes, sc = fp4_codes(gold[-1].astype(np.float32))
    ycodes = (codes & 7) | ((V.bits(gold[-1].astype(np.float32)) >> 31) << 3)       # value-canonical zero sign
    packed = sum(int(c) << (4 * i) for i, c in enumerate(ycodes)) | sum(int(s) << (2048 + 8 * b) for b, s in enumerate(sc))
    want = {CKV_BASE + 9 * loc + k: (packed >> (256 * k)) & ((1 << 256) - 1) for k in range(9)}
    got = {}
    for line in stdout.splitlines():
        if line.startswith("HBMW "):
            _, d, s, sec, hx = line.split()
            got[(int(d), int(s), int(sec))] = int(hx, 16)
    res["own_row_writes"] = len(got)
    res["own_row_write_exact"] = len(got) == 9 and all(got.get((d_own, s_own, sec)) == v for sec, v in want.items())
    res["own_row_code_signed_zero_diffs"] = int(np.sum(ycodes != codes))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", type=Path, default=Path("/home/ubuntu/w17work/die/ctx1048576_s20260930_L20"))
    ap.add_argument("--golden", type=Path, default=Path("/home/ubuntu/w17work/isa/scratch_s20260930/ctx1048576_L20.npz"))
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--record", type=Path, default=ROOT / "results/rtl/w11_ckvdie_service_gate.json")
    a = ap.parse_args()
    t0 = time.time()
    vec = a.scratch / "vec"
    info = prep(a, vec)
    exe = build(a.scratch / "obj")
    runs = []
    for lat, ri in ((100, 2), (259, 2)):
        p = subprocess.run([str(exe), f"+dir={vec}", f"+lat={lat}", f"+ri={ri}"], capture_output=True, text=True,
                           timeout=3600)
        res = check(vec, p.stdout, info)
        f = res["fields"]
        ok = (p.returncode == 0 and res["row_errors"] == 0 and res["fmt_errors"] == 0 and
              res["rows_checked"] == 4 * 2 * 512 and f.get("hbm_miss") == "0" and f.get("timeout") == "0" and
              f.get("faults") == "0,0,0,0" and res["own_row_write_exact"])
        runs.append(dict(lat=lat, ri=ri, pass_=ok, **res))
        print(lat, ri, ok, {k: res[k] for k in ("rows_checked", "row_errors", "own_row_write_exact")}, f, flush=True)
    if a.record.is_file() and json.loads(a.record.read_text()).get("status") != "pass":
        raise SystemExit(f"{a.record} holds a failed verdict")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--", *SRC, *TOOLS], cwd=ROOT, text=True).strip()
    rec = dict(schema="w11_ckvdie_service_gate/1",
               scope=("W17 L20 (1M context, position 1048575, seed 20260930): the 512 selected compressed rows through "
                      "four dies' ot_chip_v41x_ckv_die_service (ids from the VM, owned-row fetch from the W17 HBM "
                      "images, behavioural all-gather links, rank-addressed collector, FP4 stream merger), streamed "
                      "twice (QK, PV); every row's engine-dequantised values equal the golden's gathered row "
                      "(synthetic_state ckv store, own row = ckv20). The own row (selected, rank 511) is re-encoded "
                      "per rank from its QDQ4E values by the encoder its owner die uses to write it home (writer path "
                      "in the die: owner write here; persistent store across tokens not exercised). Window rows and the "
                      "attention arithmetic are the existing gates'; the full die is W17's 4-die run."),
               git_head=head, sources_dirty=bool(dirty), source_sha256={s: sha(ROOT / s) for s in SRC + TOOLS},
               images=str(a.images), golden=str(a.golden), golden_sha256=sha(a.golden),
               selection=dict(n_rows_before=info["n"], own_row_selected=info["new_selected"],
                              own_row_nonzero=info["new_nonzero"], owned_per_die=info["owned"],
                              ckv_state_sha256=info["ckv_state_sha256"]),
               runs=runs, wall_s=round(time.time() - t0, 1),
               status="pass" if runs and all(r["pass_"] for r in runs) and not dirty and info["new_selected"] and
               info["new_nonzero"] else "fail")
    a.record.write_text(json.dumps(rec, indent=2) + "\n")
    print(rec["status"])


if __name__ == "__main__":
    main()
