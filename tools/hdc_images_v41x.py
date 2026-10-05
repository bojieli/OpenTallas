#!/usr/bin/env python3
"""Weight and constant images of the re-specified V4.1 decode core (rtl/hdc/v41x/ot_hdc_core_v41x.sv).

    python3 tools/hdc_images_v41x.py --out DIR [--mtp GAMMA] [--hhw 8]

The program, the instruction fields and the ISA-level simulator (tools/hdc_program_v41.py) keep the as-built
layout (Layout).  Each re-specified engine reads its weights from memories in ITS OWN layout; this tool builds
those images from the same Layout, and fixes, per engine, the translation from an as-built base (the value the
instruction field carries) to the engine's base -- the adapter applies it (rtl/hdc/v41x/ot_hdc_v41x_*_adapt.sv).

* cfg.hex: straps of the bench -- [0] the KV word where the index keys start (the ME slot routes a KV-sourced
  op at or above it to the indexer engine, below it to the attention engine); [1] me_xs (the ME weight-tile base
  shift, below).
* HE -> ot_hdc_v41x_hcp: 8 weight banks of HHW binary32 lanes.  Matrix fn [nout, K] (K = 8 * he_k) at as-built
  HE ROM word b is placed at bank word b + o*R + r (R = ceil(he_k / HHW)), bank k, lane l = fn[o][8*(r*HHW+l)+k]:
  the IDENTITY translation, legal because the engine's footprint nout*R words fits the as-built he_k*IL
  (asserted).  File hbank.hex: line a*8 + k = bank k word a, lanes 0..HHW-1 (lane 0 in the low bits).

* ME weight ops -> ot_hdc_v41x_wgt_tile KIND 1 (the BF16/FP32 weight engine, MG chunk units = 8*MG lanes,
  lane = one bank of binary32 weights).  The image is built from the PROGRAM's ME weight ops (me_wsrc = 0), so it
  is exactly what the ISA model multiplies: row n = (t*IL + j)*W + l of an op takes, at term i = c*kc + k, the
  as-built ROM lane (q*S + c)*W + l of word wbase + r*ts + k*ks + (j >> jsh)*js (t = r*per_round + q), against x
  element xbase + j*xjs + i (asserted: xks = 1, xcs = kc).  An op whose x moves with the slot j (xjs != 0, grouped
  wo_a) runs as IL sub-ops, sub-op j over rows t*W + l; any other op is one sub-op over rows n = 0 .. nout-1.
  A sub-op of nrows rows x K terms runs at segment plg = clamp(ceil(log2(ceil(K/8))), ME_PMIN_LG, log2 MG):
  nbeat = ceil(K / 8P) beats, rpg = MG/P rows per row group, nrg = ceil(nrows / rpg) groups; bank b (= slot*8P +
  (i mod 8P)) word base + rg*nbeat + q holds row rg*rpg + slot, term q*8P + (i mod 8P).  Base of sub-op j:
  (wbase << me_xs) + j*nrg*nbeat, me_xs the smallest shift that keeps every op's image disjoint (cfg.hex [1]).
  File mbank.hex: line a*8*MG + b = bank b word a.  The adapter (ot_hdc_v41x_me_adapt) derives the same plg,
  nbeat, nrg, bases (me_geometry below is the reference).

* IDX -> the index-key HBM (ot_hdc_v41x_idx_kstream's 68-B format: per key 128 E2M1 codes + 4 UE8M0 scales,
  1,024-key super-blocks of 17 4-KB blocks, block 0 the scales, blocks 1..16 the codes of 64 keys each).  The
  key array of the index-key region at KV word wb starts at HBM block (wb - ik_base) / 128 * 17; key t's codes
  (dims 0..31 of the reduced 32-dim key, the rest zero) are sector (B0 + 1 + t/64)*128 + 2*(t%64), its scale
  byte the low byte of 32-bit field t%8 of sector B0*128 + t/8.  File ikhbm.hex (sectors of 256 bits): the keys
  of the golden-prefilled KV image (kv.hex, when present -- the single-step state); keys written at run time
  reach the HBM through the core's key writer (ot_hdc_v41x_idx_kwr).

MTP builds (--mtp GAMMA) use tools/hdc_program_v41.mtp_layout, so the MTP-only weights (mtp.0-2 layers, their
hyper-connection projections) are covered by the same placement rule.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402
import hdc_program_v41 as P  # noqa: E402

IL = I.INTERLEAVE


def he_matrices(lay):
    """(as-built base, fn [nout, K] binary32) of every HE matrix, recovered from the as-built HE ROM words:
    word b + k'*IL + j holds, in lane c*NL + l, row j*NL + l at column c*kc + k'."""
    S, NL = V.HC_SPLIT, I.HE_LANES
    hw = np.stack(lay.hwords)                       # [words, S*NL]
    out = []
    for key, mat in lay.mat.items():
        if not (isinstance(key, tuple) and key[-1] == "fn"):
            continue
        b, n, kc = mat["base"], mat["n"], mat["k"]
        blk = hw[b:b + kc * IL].reshape(kc, IL, S, NL)          # [k', j, c, l]
        w = blk.transpose(1, 3, 2, 0).reshape(IL * NL, S * kc)   # [j*NL + l, c*kc + k']
        out.append((b, w[:n].astype(np.float32), kc))
    return out


def hbank_image(lay, hhw):
    """{word*8 + bank: [hhw] uint32} of the HCP weight banks, identity-translated."""
    img = {}
    for b, w, kc in he_matrices(lay):
        n, K = w.shape
        R = -(-kc // hhw)
        assert n * R <= kc * IL, (b, n, R, kc)       # the engine's footprint fits the as-built one
        bits = G.bits(w).astype(np.uint32)
        for o in range(n):
            for r in range(R):
                for k in range(8):
                    lanes = np.zeros(hhw, dtype=np.uint32)
                    for l in range(hhw):
                        col = 8 * (r * hhw + l) + k
                        if col < K:
                            lanes[l] = bits[o, col]
                    img[(b + o * R + r) * 8 + k] = lanes
    return img


def write_banked(path, img, lane_bits, lanes):
    """A $readmemh image with explicit @addresses (sparse)."""
    digits = lane_bits * lanes // 4
    with open(path, "w") as fh:
        prev = None
        for a in sorted(img):
            if prev is None or a != prev + 1:
                fh.write(f"@{a:x}\n")
            fh.write(f"{P.pack_lanes(img[a], lane_bits):0{digits}x}\n")
            prev = a


ME_PMIN_LG = 1


def me_geometry(f, mg):
    """Sub-op geometry of an ME weight op on the weight tile of mg chunk units (the adapter's own rule)."""
    S = 1 << f["me_split"]
    K = S * f["me_k"]
    per_round = I.GROUPS // S
    lg = mg.bit_length() - 1
    nch = -(-K // 8)
    plg = min(lg, max(ME_PMIN_LG, (nch - 1).bit_length()))
    nbeat = -(-K // (8 << plg))
    rpg = mg >> plg
    splitj = f["me_xjs"] != 0
    T = f["me_tiles"] * per_round
    nrows = T * I.W_LANES if splitj else f["me_nout"]
    nrg = -(-nrows // rpg)
    return dict(S=S, K=K, per_round=per_round, plg=plg, nbeat=nbeat, rpg=rpg, splitj=splitj, nsub=IL if splitj else 1,
                nrows=nrows, nrg=nrg, subfp=nrg * nbeat)


def me_ops(lay, prog):
    """{as-built wbase: an ME weight op of the program that reads it} (every op of a base has one shape)."""
    ops = {}
    keys = ("me_nout", "me_tiles", "me_k", "me_ts", "me_ks", "me_js", "me_jsh", "me_split", "me_xks", "me_xcs",
            "me_xjs")
    for f in prog:
        if f["unit"] != I.UNIT_ME or f.get("me_wsrc", 0):
            continue
        f = {k: f.get(k, 0) for k, _ in I.FIELDS}
        assert f["me_d_wbase"] == 0 and f["me_d_k"] == 0 and f["me_d_tiles"] == 0 and f["me_d_nout"] == 0, f
        assert f["me_xks"] == 1 and f["me_xcs"] == f["me_k"] and f["me_hg"] == 0 and f["me_mmode"] == 0, f
        old = ops.get(f["me_wbase"])
        assert old is None or all(old[k] == f[k] for k in keys), (old, f)
        ops[f["me_wbase"]] = f
    return ops


def mbank_image(lay, prog, mg):
    """({line: uint32}, me_xs) of the weight-tile banks for every ME weight op of prog."""
    W = I.W_LANES
    L = 8 * mg
    words = np.stack(lay.words).astype(np.uint32)            # [nwords, W*GROUPS] BF16
    ops = me_ops(lay, prog)
    subs = []
    for wb, f in sorted(ops.items()):
        g = me_geometry(f, mg)
        S, K, kc = g["S"], g["K"], f["me_k"]
        for sj in range(g["nsub"]):
            rows = np.arange(g["nrows"])
            if g["splitj"]:
                t, l, j = rows // W, rows % W, np.full(len(rows), sj)
            else:
                t, j, l = rows // (W * IL), (rows // W) % IL, rows % W
            nidx = (t * IL + j) * W + l
            r, q = t // g["per_round"], t % g["per_round"]
            i = np.arange(K)
            c, kk = i // kc, i % kc
            word = wb + r[:, None] * f["me_ts"] + kk[None, :] * f["me_ks"] + (j[:, None] >> f["me_jsh"]) * f["me_js"]
            lane = (q[:, None] * S + c[None, :]) * W + l[:, None]
            w = words[word, lane] << 16                          # [rows, K] binary32 bits
            w[nidx >= f["me_nout"]] = 0
            subs.append((wb, sj, g, w))
    xs = 0
    while True:
        spans = sorted(((wb << xs) + sj * g["subfp"], (wb << xs) + (sj + 1) * g["subfp"]) for wb, sj, g, _ in subs)
        if all(a[1] <= b[0] for a, b in zip(spans, spans[1:])):
            break
        xs += 1
    img = {}
    for wb, sj, g, w in subs:
        base = (wb << xs) + sj * g["subfp"]
        P8 = 8 << g["plg"]
        rows, K = w.shape
        for rho in range(rows):
            rg, slot = divmod(rho, g["rpg"])
            for i in range(K):
                q, b = divmod(i, P8)
                img[(base + rg * g["nbeat"] + q) * L + slot * P8 + b] = int(w[rho, i])
    return img, xs


def write_words(path, img, bits):
    """A sparse $readmemh image of single words."""
    digits = bits // 4
    with open(path, "w") as fh:
        prev = None
        for a in sorted(img):
            if prev is None or a != prev + 1:
                fh.write(f"@{a:x}\n")
            fh.write(f"{img[a]:0{digits}x}\n")
            prev = a


def program_of(lay):
    """The program(s) whose weight ops the images serve: the one-position program, or the MTP image's."""
    if lay.mtp:
        gamma = lay.nslots - 1
        return P.build_mtp(lay, min(gamma, lay.m.dspark_block))[0]
    return P.Builder(lay).build()


MAG2 = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 6: 5, 8: 6, 12: 7}      # doubled E2M1 magnitude -> code


def enc_fp4(vals):
    """Exact FP4 (E2M1 x UE8M0) encoding of a QDQ4 block of 32 BF16-valued floats: (codes nibble list, u),
    or None when the block does not encode exactly (the RTL's rule, ot_hdc_v41x_idx_enc32)."""
    v = np.asarray(vals, dtype=np.float32)
    nz = v != 0
    if not nz.any():
        return [0] * 32, 0
    b = (G.bits(v).astype(np.int64) >> 16)
    emax = int(((b >> 7) & 255)[nz].max())
    u = emax - 2
    if not (0 <= u <= 252):
        return None
    codes = []
    for x in v:
        if x == 0:
            codes.append(0)
            continue
        m2 = abs(float(x)) / 2.0 ** (u - 127) * 2
        if m2 not in MAG2:
            return None
        codes.append(MAG2[int(m2)] | (8 if x < 0 else 0))
    return codes, u


def ikhbm_image(lay, kv):
    """{sector: 256-bit int} of the index keys held in the KV image kv (elements)."""
    W = I.W_LANES
    ik = min(a for n, a in lay.kv.map.items() if n.startswith("IK")) // W
    img = {}
    for name, base in lay.kv.map.items():
        if not name.startswith("IK"):
            continue
        off = base // W - ik
        assert base % W == 0 and off % 128 == 0, name       # the adapter's map: 128-word units
        b0 = off // 128 * 17
        s = int(name[2:])
        for t in range(lay.nrows[s]):
            row = np.array([kv[lay.kt_elem(base, t, d)] for d in range(P.HD)], dtype=np.float32)
            if not row.any():
                continue
            enc = enc_fp4(row)
            assert enc is not None, (name, t)
            codes, u = enc
            cs = (b0 + 1 + t // 64) * 128 + 2 * (t % 64)
            img[cs] = img.get(cs, 0) | P.pack_lanes(codes, 4)
            ss = b0 * 128 + t // 8
            img[ss] = img.get(ss, 0) | (u << (32 * (t % 8)))
    return img


def write(out, lay, hhw=8, mg=8):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    hb = hbank_image(lay, hhw)
    write_banked(out / "hbank.hex", hb, 32, hhw)
    mb, me_xs = mbank_image(lay, program_of(lay), mg)
    write_words(out / "mbank.hex", mb, 32)
    # cfg.hex (the bench's straps): [0] the KV word where the index keys start (ME-slot class of a KV op)
    ik = min(a for n, a in lay.kv.map.items() if n.startswith("IK")) // I.W_LANES
    assert all(a < ik * I.W_LANES for n, a in lay.kv.map.items() if not n.startswith("IK"))
    (out / "cfg.hex").write_text(f"{ik:06x}\n{me_xs:06x}\n")
    ikh = {}
    if (out / "kv.hex").exists():
        kv = G.from_bits(np.array([int(x, 16) for x in (out / "kv.hex").read_text().split()], dtype=np.uint32))
        ikh = ikhbm_image(lay, kv)
    write_words(out / "ikhbm.hex", ikh, 256)
    meta = {"hhw": hhw, "hbank_lines": len(hb), "hbank_top": max(hb) + 1 if hb else 0, "ik_base_word": ik,
            "mg": mg, "me_xs": me_xs, "mbank_words": len(mb), "mbank_top_line": max(mb) + 1 if mb else 0,
            "ikhbm_sectors": len(ikh)}
    (out / "v41x_images.json").write_text(json.dumps(meta))
    return meta


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mtp", type=int, help="MTP layout with this gamma (tools/hdc_program_v41.mtp_layout)")
    ap.add_argument("--hhw", type=int, default=8)
    ap.add_argument("--mg", type=int, default=8, help="ME weight tile chunk units (8*mg lanes)")
    a = ap.parse_args()
    model = V.Model()
    lay = P.mtp_layout(model, a.mtp) if a.mtp else P.Layout(model)
    print(json.dumps(write(a.out, lay, a.hhw, a.mg)))


if __name__ == "__main__":
    main()
