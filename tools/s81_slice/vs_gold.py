#!/usr/bin/env python3
"""S81-SLICE vs (SU lane engine) bench golden: one layer's SU element ops on the 1M token's real operands.

Operands come from the su_cases pickle (tools/s81_suhc/fixtures/su_cases_v2_ildr.pkl, the hub executor's die-share cases);
expected answers from the CPU golden (dsrom_su_swiglu.golden_swiglu, hdc_golden_v41 softplus / sqrt / add / rope_tail,
the moe_sum id-order chain, hc_gate.g_quant = the act-quant), each ASSERTED against the case's executor check first.
Each case's rows are mapped into one beat leaf's store (vp, 1,024 rows of 4 FP32) at compiler-style layouts (vs header).

Writes into OUT:
  img.mem   1,024 rows x 128 b (the leaf-store image the bench writes through vp's row-pair port), imgv.mem row valid
  prog.mem  entries {kind 4, op 4, arg 24, cmd 160} (192 b):  kind 1 = vs command (cmd = vp c_d);  kind 2 = RDOUT check
            (arg = {exp index 14, pairs 8 ... see below}); kind 0 = end
  exp.mem   expected row pairs (256 b), expm.mem their word masks (8 b)
  xq.mem    expected vq XQ beats {e1 10, q1 256, e0 10, q0 256} in arrival order (532 b), xqi.mem their idx (8 b)
    python3 tools/s81_slice/vs_gold.py CASES.pkl OUT L0|L2
"""
import pickle
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "tools/s81_suhc"))
import os
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import hc_gate as HG          # noqa: E402
import hdc_golden_v41 as V    # noqa: E402
import dsrom_su_swiglu as SG  # noqa: E402

F = np.float32
OP = dict(SW=8, QB=9, RA=10, RB=11, QR=12, MOE=13)


def u32(x):
    return np.asarray(x, F).view(np.uint32)


def f32(b):
    return np.asarray(b, np.uint32).view(F)


class Leaf:
    def __init__(self):
        self.img = {}
        self.top = 0
        self.prog, self.exp, self.expm, self.xq, self.xqi = [], [], [], [], []

    def alloc(self, nrows):
        nrows += nrows & 1                               # keep row-pair alignment
        a = self.top
        self.top += nrows
        assert self.top <= 1024, "leaf store overflow"
        return a

    def put(self, rows):
        a = self.alloc(len(rows))
        for i, r in enumerate(rows):
            self.img[a + i] = [int(w) for w in r]
        return a

    def cmd(self, op, a0, n, ob=0, wb=0, uq=0, umq=0, umb=0, umi=0, j0=0, lim=0, w0=0, w1=0, a1=0):
        imm = ob | wb << 10 | uq << 11 | umq << 12 | umb << 13 | umi << 14 | j0 << 22 | lim << 32 | w0 << 64 | w1 << 96
        c = OP[op] | a0 << 4 | a1 << 14 | n << 24 | imm << 32
        self.prog.append((1, OP[op], 0, c))

    def check(self, op, base, rows, masks):
        """expected rows (4 words each, None = don't care) from row base: RDOUT of the covering row pairs"""
        assert base % 2 == 0
        if len(rows) % 2:
            rows = rows + [None]; masks = masks + [0]
        idx = len(self.exp)
        for i in range(0, len(rows), 2):
            lo, hi = rows[i] or [0] * 4, rows[i + 1] or [0] * 4
            self.exp.append(sum(int(w) << (32 * k) for k, w in enumerate(list(lo) + list(hi))))
            self.expm.append(masks[i] | masks[i + 1] << 4)
        self.prog.append((2, OP[op], idx << 10 | (len(rows) // 2) << 0, base))

    def expect_xq(self, y64, idx):
        q = HG.g_quant(np.asarray(y64, F))
        assert len(q) == 2
        (e0, c0), (e1, c1) = q
        w = lambda c: int.from_bytes(bytes(np.asarray(c, np.uint8)), "little")
        self.xq.append(w(c0) | (int(e0) & 0x3FF) << 256 | w(c1) << 266 | (int(e1) & 0x3FF) << 522)
        self.xqi.append(idx)

    def write(self, out):
        out.mkdir(parents=True, exist_ok=True)
        with open(out / "img.mem", "w") as f, open(out / "imgv.mem", "w") as g:
            for r in range(1024):
                ws = self.img.get(r, [0, 0, 0, 0])
                f.write("%032x\n" % sum(w << (32 * k) for k, w in enumerate(ws)))
                g.write("%d\n" % (r in self.img))
        with open(out / "prog.mem", "w") as f:
            for kind, op, arg, c in self.prog + [(0, 0, 0, 0)]:
                f.write("%048x\n" % (kind << 188 | op << 184 | arg << 160 | c))
        open(out / "exp.mem", "w").write("".join("%064x\n" % e for e in self.exp) or "0\n")
        open(out / "expm.mem", "w").write("".join("%02x\n" % m for m in self.expm) or "0\n")
        open(out / "xq.mem", "w").write("".join("%0133x\n" % e for e in self.xq) or "0\n")
        open(out / "xqi.mem", "w").write("".join("%02x\n" % e for e in self.xqi) or "0\n")
        open(out / "counts.txt", "w").write("%d %d %d\n" % (len(self.prog), len(self.exp), len(self.xq)))


def rows4(words):
    w = list(words)
    w += [0] * (-len(w) % 4)
    return [w[i:i + 4] for i in range(0, len(w), 4)]


def il(a, b):
    """interleave two row lists: a0, b0, a1, b1, ..."""
    out = []
    for x, y in zip(a, b):
        out += [x, y]
    return out


def main():
    cases = pickle.load(open(sys.argv[1], "rb")); out = Path(sys.argv[2]); L = sys.argv[3] if len(sys.argv) > 3 else "L0"
    V.set_arith("chunk8")
    by = {c["name"]: c for c in cases["cases"]}
    lf = Leaf()
    lim_bits = None
    # ------------------------------------------------ SW: every expert slot (6 routed + shared), 24 elements = 6 groups
    sw_all = []
    for s in range(7):
        c = by[f"{L}.swiglu.s{s}"]
        init = dict(c["init"]); op = c["ops"][0]
        g, uu = np.asarray(init[64], F), np.asarray(init[88], F)
        w = np.asarray(init[136], F)[0] if 136 in init else None
        lim = f32([op["imm3"]])[0]; lim_bits = int(op["imm3"])
        a = SG.golden_swiglu(g, uu, None if w is None else np.repeat(w, len(g)).astype(F), lim)
        assert np.array_equal(u32(a), np.asarray(c["checks"][0][2], np.uint32)), f"{L} swiglu s{s} golden vs case check"
        sw_all.append((g, uu, w, a))
        a0 = lf.put(il(rows4(u32(g)), rows4(u32(uu))))
        ob = lf.alloc(6)
        wb_ = int(u32([w])[0]) if w is not None else 0x3F800000          # the shared expert: w = 1.0 (exact)
        lf.cmd("SW", a0, 6, ob=ob, wb=1, lim=lim_bits, w0=wb_, w1=wb_)
        lf.check("SW", ob, rows4(u32(a)), [0xF] * 6)
    # SW -> vq (quant2): one 64-element vector = 2 act-quant blocks: block 0 = slot 0's 24 + slot 1's first 8, block 1 =
    # slot 1's last 16 + slot 2's first 16; w0 / w1 = the weights of slots 0 / 1 for groups 0..7 / 8..15 (real operands,
    # a bench composition: the golden uses the same per-group weights)
    g64 = np.concatenate([sw_all[0][0], sw_all[1][0], sw_all[2][0][:16]]).astype(F)
    u64 = np.concatenate([sw_all[0][1], sw_all[1][1], sw_all[2][1][:16]]).astype(F)
    wv = np.concatenate([np.repeat(sw_all[0][2], 32), np.repeat(sw_all[1][2], 32)]).astype(F)
    a64 = SG.golden_swiglu(g64, u64, wv, f32([lim_bits])[0])
    a0 = lf.put(il(rows4(u32(g64)), rows4(u32(u64))))
    ob = lf.alloc(16)
    lf.cmd("SW", a0, 16, ob=ob, wb=1, uq=1, umq=1, umi=0x21, lim=lim_bits, w0=int(u32([sw_all[0][2]])[0]),
           w1=int(u32([sw_all[1][2]])[0]))
    lf.check("SW", ob, rows4(u32(a64)), [0xF] * 16)
    lf.expect_xq(a64, 0x21)
    # ------------------------------------------------ QB (z_quant): 64 values of this layer's attention output (o_own)
    z = f32(by[f"{L}.attend_tail"]["checks"][0][2])[:64]
    a0 = lf.put(rows4(u32(z)))
    lf.cmd("QB", a0, 8, umq=1, umi=0x2A)
    lf.expect_xq(z, 0x2A)
    # ------------------------------------------------ RA: sqrt(softplus) of the die's router rows
    c = by[f"{L}.router_act"]
    x = np.asarray(dict(c["init"])[64], F)
    r = V.sqrt(V.softplus(x))
    assert np.array_equal(u32(r), np.asarray(c["checks"][0][2], np.uint32)), f"{L} router_act golden vs case"
    a0 = lf.put(rows4(u32(x)))
    ob = lf.alloc(2)
    lf.cmd("RA", a0, len(x), ob=ob)
    lf.check("RA", ob, rows4(u32(r)), [(1 << len(x)) - 1 if len(x) < 4 else 0xF] * len(rows4(u32(r))))
    # ------------------------------------------------ RB: router scores + bias (top-6 is the G-unit's)
    c = by[f"{L}.route"]
    sc = np.asarray(dict(c["init"])[64], F); bias = f32(c["cr_lo"][:len(sc)])
    rb = V.add(sc, bias)
    assert np.array_equal(u32(rb), np.asarray(c["checks"][0][2], np.uint32)), f"{L} route RB golden vs case"
    a0 = lf.put(il(rows4(u32(sc)), rows4(u32(bias))))
    ob = lf.alloc(len(sc) // 4)
    lf.cmd("RB", a0, len(sc) // 4, ob=ob)
    lf.check("RB", ob, rows4(u32(rb)), [0xF] * (len(sc) // 4))
    # ------------------------------------------------ QR: the head's RoPE tail (last 64 of 512), cos / sin of the token
    c = by[f"{L}.q_rope"]
    q = np.asarray(dict(c["init"])[64], F)
    cos, sin = f32(c["cr_lo"][:32]), f32(c["cr_hi"][:32])
    qo = V.rope_tail(q.reshape(1, -1), (cos, sin)).reshape(-1)
    assert np.array_equal(u32(qo), np.asarray(c["checks"][0][2], np.uint32)), f"{L} q_rope golden vs case"
    tail = q[-64:]
    cs = [[u32([cos[2 * i]])[0], u32([sin[2 * i]])[0], u32([cos[2 * i + 1]])[0], u32([sin[2 * i + 1]])[0]] for i in range(16)]
    a0 = lf.put(il(rows4(u32(tail)), cs))
    ob = lf.alloc(16)
    lf.cmd("QR", a0, 16, ob=ob)
    lf.check("QR", ob, rows4(u32(qo[-64:])), [0xF] * 16)
    # ------------------------------------------------ MOE: expert sum in id order then shared, BF16 at the end
    c = by[f"{L}.moe_sum"]
    nr = c["ops"][0]["nout"]
    e = np.asarray(dict(c["init"])[64], F).reshape(nr, 7)
    acc = V.add(e[:, 0], e[:, 1])
    for k in range(2, 7):
        acc = V.add(acc, e[:, k])
    y = V.to_bf16(acc)
    assert np.array_equal(u32(y), np.asarray(c["checks"][0][2], np.uint32)), f"{L} moe_sum golden vs case"
    # the beat's 64 elements: the case's nr rows + (64 - nr) rows of the other layer's case (real operands)
    Lo = "L2" if L == "L0" else "L0"
    e2 = np.asarray(dict(by[f"{Lo}.moe_sum"]["init"])[64], F).reshape(-1, 7)
    E = np.concatenate([e, e2[:64 - nr]]).astype(F)
    acc = V.add(E[:, 0], E[:, 1])
    for k in range(2, 7):
        acc = V.add(acc, E[:, k])
    y64 = V.to_bf16(acc)
    a0 = lf.put([r for k in range(7) for r in rows4(u32(E[:, k]))])
    ob = lf.alloc(16)
    lf.cmd("MOE", a0, 8, ob=ob)
    lf.check("MOE", ob, rows4(u32(y64)), [0xF] * 16)
    lf.write(out)
    print("VS_GOLD %s rows=%d prog=%d exp_pairs=%d xq=%d lim=%08x" % (L, lf.top, len(lf.prog), len(lf.exp), len(lf.xq), lim_bits))


if __name__ == "__main__":
    main()
