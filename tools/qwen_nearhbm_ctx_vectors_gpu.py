#!/usr/bin/env python3
"""Near-HBM attention bench vectors from the REAL Qwen3-8B prompt at long context (P4095 / P8191), from the GPU ISA golden.

The REAL_MEM long-context campaign (/srv/opentallas-scratch/claude/realmem-ctx8k) recorded, per position P and layer
n in 0..2, the GPU ISA golden's KV history before the layer (kv_pre/L<n>_die<d>.npy), the token's K/V (kv_at_P) and
every die's X after the layer (L<nn>_die<d>_x.hex).  This tool re-runs ONE layer program at P on the local GPU
(tools/qwen_rom_position_oracle_gpu.GpuTP, the bit-checked torch port of the golden) from those records and captures
the near-HBM attention operands at their program points:

    q    = VM[QR : QR + 1024] before PC 11 (QK; post q-norm/RoPE, h-major; the bench rounds it to BF16 as the golden)
    K, V = the KV window after the layer, positions 0..P (FP8 E4M3, so position P is the token's own write)
    gold = VM[ATTN : ATTN + 1024] after PC 15 (P.V x reciprocal(Z), the O-projection input)

and refuses unless the layer's X equals the recorded X of every die and the token K/V equals kv_at_P.  Output per
(P, layer, die): q.hex / kv.hex / gold.hex / meta.json in tools/qwen_nearhbm_attn_ref.py's bench format.
`--check` (separate process, NumPy CPU reference -- no model arithmetic: one attention op) recomputes
qwen_nearhbm_attn_ref.golden_die(q, K, V) from the written files and requires it bit-equal to gold.hex.

    python3 tools/qwen_nearhbm_ctx_vectors_gpu.py --gold G --prep PREP --positions 4095,8191 --layers 0,1,2 --out V
    python3 tools/qwen_nearhbm_ctx_vectors_gpu.py --check V
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
QK_PC, ATTN_PC = 11, 15
TP, NH, KVH, HD = 4, 8, 2, 128


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_hex32(p):
    return np.array([int(x, 16) for x in Path(p).read_text().split() if not x.startswith("@")], dtype=np.uint32)


FP8_BITS = None


def fp8_bytes(vals_u32):
    """FP8-valued binary32 bit patterns -> E4M3 bytes (exact lookup; -0 and non-FP8 values refuse)."""
    global FP8_BITS
    if FP8_BITS is None:
        tab = {}
        for b in range(256):
            if b in (0x7F, 0xFF, 0x80):
                continue
            s, e, m = b >> 7, (b >> 3) & 15, b & 7
            mag = (m / 8.0) * 2.0 ** -6 if e == 0 else (1 + m / 8.0) * 2.0 ** (e - 7)
            tab[int(np.float32(-mag if s else mag).view(np.uint32))] = b
        FP8_BITS = (np.array(sorted(tab), dtype=np.uint32), np.array([tab[k] for k in sorted(tab)], dtype=np.uint8))
    keys, codes = FP8_BITS
    i = np.searchsorted(keys, vals_u32)
    i = np.minimum(i, len(keys) - 1)
    if not np.array_equal(keys[i], vals_u32):
        raise SystemExit("KV value that is not an E4M3 code (or -0)")
    return codes[i]


def run(a):
    os.environ.update(QWEN_O4_GROUPS="6144", QWEN_O4_TP="4", HDC_SU_WIDTH="1024", HDC_KV_FMT="fp8")
    sys.path.insert(0, str(ROOT / "tools"))
    import torch
    import qwen_rom_position_oracle_gpu as O
    import hdc_isa as I
    if not torch.cuda.is_available():
        raise SystemExit("local GPU only")
    T = O.torch_golden(torch.device("cuda"))
    st = O.selftest(T)
    if not all(st.values()):
        raise SystemExit(f"primitive self-test failed: {st}")
    layers = [int(x) for x in a.layers.split(",")]
    m = O.GpuTP(T, a.prep, range(max(layers) + 1), head=False)
    VM, X = m.VM, m.VM["X"]
    QR, ATT = VM["QR"], VM["ATTN"]
    # the program points: PC 11 is the KV-sourced QK, PC 15 writes ATTN, PC 16 is the dense O projection
    f11, f15, f16 = m.prog[0][QK_PC], m.prog[0][ATTN_PC], m.prog[0][ATTN_PC + 1]
    if not (f11["unit"] == I.UNIT_ME and f11["me_wsrc"] and f11["me_xbase"] == QR and f15["d_base"] == ATT
            and f16["unit"] == I.UNIT_ME and not f16["me_wsrc"] and f16["me_xbase"] == ATT):
        raise SystemExit("layer program does not have the expected QK / ATTN / O points")
    oracle = json.loads((a.gold / "oracle.json").read_text())
    summary = []
    for P in [int(x) for x in a.positions.split(",")]:
        g = a.gold / f"P{P}"
        prec = oracle["per_position"][str(P)]
        tok = prec["token"]
        for n in layers:
            src = g / "x_preload.hex" if n == 0 else g / f"L{n - 1:02d}_die0_x.hex"
            if n:
                xs = {sha(g / f"L{n - 1:02d}_die{d}_x.hex") for d in range(TP)}
                if len(xs) != 1:
                    raise SystemExit("dies disagree on the layer input X")
            x = read_hex32(src).view(np.float32)
            vm = torch.zeros((TP, m.VM_ELEMS), dtype=torch.float32, device=T.dev)
            vm[:, X:X + 4096] = torch.from_numpy(x.copy()).to(T.dev)[None]
            pre = np.stack([np.load(g / "kv_pre" / f"L{n}_die{d}.npy") for d in range(TP)]).astype(np.uint32)
            for d in range(TP):
                if sha(g / "kv_pre" / f"L{n}_die{d}.npy") != prec["kv_pre_sha256"][f"L{n}_die{d}"]:
                    raise SystemExit("kv_pre file differs from the oracle record")
            m.kv[n] = torch.from_numpy(pre.view(np.float32).copy()).to(T.dev)
            # one layer, the oracle's own loop with two capture points
            kv, crom = m.kv[n], m.crom[n]
            q = att = None
            with m.FP.program_geometry(m.VM):
                dyn = m.P.dyn_values(m.lays[0], token=tok, pos=P)
                for idx, seg in enumerate(m.desc):
                    first = seg["program_base"]
                    end = m.desc[idx + 1]["program_base"] if idx + 1 < len(m.desc) else len(m.prog[0])
                    for pc in range(first, end):
                        f = m.prog[0][pc]
                        if any(m.prog[d][pc] != f for d in range(TP)):
                            raise SystemExit(f"die programs differ at pc {pc}")
                        if pc == QK_PC:
                            q = vm[:, QR:QR + NH * HD].cpu().numpy().copy()
                        if f["unit"] == I.UNIT_ME:
                            (m.me_kv(vm, kv, f, dyn, P) if f["me_wsrc"] else m.me_dense(n, vm, f, dyn))
                        elif f["unit"] == I.UNIT_SU:
                            m.su(vm, kv, crom, f, dyn)
                        if pc == ATTN_PC:
                            att = vm[:, ATT:ATT + NH * HD].cpu().numpy().copy()
                    if seg["kind"] == m.P.COLL_ALLREDUCE:
                        lo, hi = seg["vm_word"] * m.W, (seg["vm_word"] + seg["words"]) * m.W
                        summed = T.fold([vm[d, lo:hi].clone() for d in range(TP)])
                        vm[:, lo:hi] = summed[None]
                    elif seg["kind"] != m.P.COLL_END:
                        raise SystemExit("unexpected layer collective")
            vmh = vm.cpu().numpy()
            kvh = m.kv[n].cpu().numpy().view(np.uint32)
            lay = m.lays[0]
            t = np.arange(P + 1)
            for d in range(TP):
                want = read_hex32(g / f"L{n:02d}_die{d}_x.hex")
                if not np.array_equal(vmh[d, X:X + 4096].view(np.uint32), want):
                    raise SystemExit(f"P{P} L{n} die{d}: layer X differs from the recorded golden")
                kp = json.loads((g / "kv_at_P" / f"L{n}_die{d}.json").read_text())
                if [f"{int(b):08x}" for b in kvh[d][kp["k_elem"]]] != kp["k_bits"] or \
                        [f"{int(b):08x}" for b in kvh[d][kp["v_elem"]]] != kp["v_bits"]:
                    raise SystemExit(f"P{P} L{n} die{d}: token K/V differs from kv_at_P")
                W = m.W
                kb = np.zeros((P + 1, KVH, HD), dtype=np.uint8)
                vb = np.zeros((P + 1, KVH, HD), dtype=np.uint8)
                for h in range(KVH):
                    dd = np.arange(HD)
                    kel = ((h * (8192 // W) + t[:, None] // W) * HD + dd[None]) * W + t[:, None] % W
                    vel = lay.kv_v0 + (h * 8192 + t[:, None]) * HD + dd[None]
                    assert lay.k_elem(0, h, P, 5) == kel[P, 5] and lay.v_elem(0, h, P, 5) == vel[P, 5]
                    kb[:, h] = fp8_bytes(kvh[d][kel].reshape(-1)).reshape(P + 1, HD)
                    vb[:, h] = fp8_bytes(kvh[d][vel].reshape(-1)).reshape(P + 1, HD)
                o = a.out / f"P{P}" / f"L{n}" / f"die{d}"
                o.mkdir(parents=True, exist_ok=True)
                qb = (q[d].view(np.uint32) >> 16)          # informational: the bench takes BF16 (round below)
                # BF16 RNE as the golden's to_bf16 (QK uses me_round=1): via the torch port on the captured values
                qbf = T.u32(T.to_bf16(torch.from_numpy(q[d].copy()).to(T.dev))).cpu().numpy().astype(np.uint64)
                if np.any(qbf & 0xFFFF):
                    raise SystemExit("BF16 rounding left low bits")
                (o / "q.hex").write_text("".join(f"{int(v >> 16):04x}\n" for v in qbf))
                with open(o / "kv.hex", "w") as fh:
                    for arr in (kb, vb):
                        for tt in range(P + 1):
                            for h in range(KVH):
                                fh.write(bytes(arr[tt, h, ::-1]).hex() + "\n")
                (o / "gold.hex").write_text("".join(f"{int(v):08x}\n" for v in att[d].view(np.uint32)))
                meta = dict(ctx=P + 1, position=P, layer=n, die=d, token=tok, hd=HD, source="GPU ISA golden",
                            gold_dir=str(g), x_in_sha256=sha(src), out_sha256=hashlib.sha256(att[d].view(np.uint32).tobytes()).hexdigest(),
                            q_raw_low16_nonzero=int(np.count_nonzero(qb != (q[d].view(np.uint32) >> 16))))
                (o / "meta.json").write_text(json.dumps(meta))
                summary.append({"P": P, "layer": n, "die": d, "dir": str(o.relative_to(a.out)),
                                "files": {f: sha(o / f) for f in ("q.hex", "kv.hex", "gold.hex", "meta.json")}})
                print(f"P{P} L{n} die{d}: X and token K/V match the golden; vectors written", flush=True)
    rec = {"schema": "opentallas.qwen-nearhbm-ctx-vectors.v1", "tool_sha256": sha(Path(__file__)),
           "oracle_tool_sha256": sha(ROOT / "tools/qwen_rom_position_oracle_gpu.py"), "gold": str(a.gold),
           "oracle_json_sha256": sha(a.gold / "oracle.json"), "prep_json_sha256": sha(a.prep / "prep.json"),
           "device": torch.cuda.get_device_name(0), "capture": {"q": f"VM[QR={QR}:+1024] before PC {QK_PC}",
                                                               "gold": f"VM[ATTN={ATT}:+1024] after PC {ATTN_PC}"},
           "vectors": summary}
    (a.out / "vectors.json").write_text(json.dumps(rec, indent=1) + "\n")


def check(a):
    sys.path.insert(0, str(ROOT / "tools"))
    import qwen_nearhbm_attn_ref as R
    G = R.G
    rec = json.loads((a.check / "vectors.json").read_text())
    res = []
    for v in rec["vectors"]:
        o = a.check / v["dir"]
        T = json.loads((o / "meta.json").read_text())["ctx"]
        q = (np.array([int(x, 16) for x in (o / "q.hex").read_text().split()], dtype=np.uint32) << 16).view(np.float32).reshape(NH, HD)
        rows = (o / "kv.hex").read_text().split()
        arr = np.array([list(bytes.fromhex(r))[::-1] for r in rows], dtype=np.uint8).reshape(2, T, KVH, HD)
        K, V = (R.FP8_VAL[arr[0]].astype(np.float32), R.FP8_VAL[arr[1]].astype(np.float32))
        g = R.golden_die(q, K, V)
        want = np.array([int(x, 16) for x in (o / "gold.hex").read_text().split()], dtype=np.uint32)
        ok = bool(np.array_equal(G.bits(g).reshape(-1), want))
        res.append({"dir": v["dir"], "golden_die_equals_isa_attn": ok})
        print(v["dir"], ok, flush=True)
    out = {"schema": "opentallas.qwen-nearhbm-ctx-vectors-check.v1", "reference": "tools/qwen_nearhbm_attn_ref.py golden_die",
           "reference_sha256": sha(ROOT / "tools/qwen_nearhbm_attn_ref.py"), "rows": res,
           "verdict": "PASS" if all(r["golden_die_equals_isa_attn"] for r in res) else "FAIL"}
    (a.check / "check.json").write_text(json.dumps(out, indent=1) + "\n")
    print(out["verdict"])
    return 0 if out["verdict"] == "PASS" else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gold", type=Path)
    ap.add_argument("--prep", type=Path)
    ap.add_argument("--positions", default="4095,8191")
    ap.add_argument("--layers", default="0,1,2")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--check", type=Path)
    a = ap.parse_args()
    if a.check:
        return check(a)
    run(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
