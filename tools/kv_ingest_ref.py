#!/usr/bin/env python3
"""Reference model of the KV ingest engine (rtl/hdc/ingest/ot_hdc_kv_ingest.sv).

The golden side of the ingest contract (docs/ARCH_SPEC_PREFILL.md section 6):

* descriptor and payload encoders -- what the host / GPU-side sender produces;
* the HBM image the engine must leave, derived from the DECODE core's own
  layout functions, not from the RTL's address arithmetic:
    - Qwen3 (QKV): tools/hdc_program.py Layout.k_elem / v_elem with one FP8
      E4M3 byte per element (HBM byte address = element index), values rounded
      by the golden's to_fp8 (tools/hdc_golden.py);
    - V4.1 index keys (IKEY): the lossless 68-B super-block layout that the
      index-key stream reads (rtl/hdc/v41x/ot_hdc_v41x_idx_kstream.sv header);
    - V4.1 compressed / window rows (ROWS): row slots of `pitch` sectors,
      16-row groups split over the tensor group's dies and the die's stacks;
  and the V4.1 wire records themselves: a 68-B index key (E2M1 codes + UE8M0
  scales) whose decode equals hdc_golden_v41.qdq_fp4_e8m0 bit for bit.
"""
from __future__ import annotations

import numpy as np

SECTOR = 32
BEAT = 64
M_RAW, M_QKV, M_ROWS, M_IKEY = 0, 1, 2, 3
FMT_FP32, FMT_BF16, FMT_FP8 = 0, 1, 2


# -- FP8 E4M3 --------------------------------------------------------------------
def fp8_code(v):
    """E4M3 code of values already on the E4M3 grid (the golden's to_fp8 output)."""
    v = np.asarray(v, dtype=np.float64)
    s = (np.signbit(v) & (v != 0)).astype(np.int64)
    a = np.abs(v)
    code = np.zeros(a.shape, dtype=np.int64)
    nz = a > 0
    e = np.floor(np.log2(np.where(nz, a, 1.0))).astype(np.int64)
    sub = nz & (e < -6)
    nrm = nz & ~sub
    code[sub] = np.round(a[sub] / 2.0 ** -9).astype(np.int64)
    m = np.round((a[nrm] / np.exp2(e[nrm]) - 1.0) * 8).astype(np.int64)
    code[nrm] = ((e[nrm] + 7) << 3) | m
    assert np.all(code <= 0x7E)
    return ((s << 7) | code).astype(np.uint8)


def fp8_value(c):
    c = np.asarray(c, dtype=np.int64)
    s = np.where(c & 0x80, -1.0, 1.0)
    e = (c >> 3) & 0xF
    m = c & 7
    v = np.where(e == 0, m * 2.0 ** -9, (1 + m / 8.0) * np.exp2(e - 7))
    return (s * v).astype(np.float32)


# -- descriptors -------------------------------------------------------------------
def desc(mode, *, fmt=0, rmw=0, fence=0, tag=0, a0=0, a1=0, a2=0, a3=0, n0=0, n1=0, n2=0, n4=0, n5=0, n6=0, nb=0):
    d = mode | (fmt << 4) | (rmw << 6) | (fence << 7) | (tag << 8)
    d |= (a0 << 16) | (a1 << 48) | (a2 << 80) | (a3 << 112)
    d |= (n0 << 144) | (n1 << 168) | (n2 << 184) | (n4 << 216) | (n5 << 224) | (n6 << 232) | (nb << 240)
    return d


def beats_of(payload: bytes):
    """512-bit beats (little-endian) of one segment, the last one zero padded."""
    pad = (-len(payload)) % BEAT
    b = payload + bytes(pad)
    return [int.from_bytes(b[i:i + BEAT], "little") for i in range(0, len(b), BEAT)]


# -- Qwen3 (QKV) ----------------------------------------------------------------------
class QwenKV:
    """The Qwen core's KV layout (hdc_program.Layout) at FP8: element index = byte."""

    def __init__(self, L, KV, HD, TMAX, W=16):
        self.L, self.KV, self.HD, self.TMAX, self.W = L, KV, HD, TMAX, W
        self.TW = TMAX // W
        self.kv_v0 = L * KV * self.TW * HD * W
        self.nbytes = 2 * self.kv_v0

    def k_elem(self, L, g, t, d):
        return ((L * self.KV + g) * self.TW + t // self.W) * self.HD * self.W + d * self.W + t % self.W

    def v_elem(self, L, g, t, d):
        return self.kv_v0 + ((L * self.KV + g) * self.TMAX + t) * self.HD + d

    def image(self, codes_k, codes_v, base=None):
        """codes_k/v [L][T, KV, HD] uint8 -> byte image (resident zeros elsewhere)."""
        img = np.zeros(self.nbytes, dtype=np.uint8) if base is None else base.copy()
        for L in range(self.L):
            T = codes_k[L].shape[0]
            t = np.arange(T)[:, None, None]
            g = np.arange(self.KV)[None, :, None]
            d = np.arange(self.HD)[None, None, :]
            img[self.k_elem(L, g, t, d)] = codes_k[L]
            img[self.v_elem(L, g, t, d)] = codes_v[L]
        return img

    def block_desc(self, L, j, t_lo, t_hi, fmt, rmw=0, fence=0, tag=0):
        W, HD = self.W, self.HD
        kb = self.k_elem(L, 0, j * W, 0)
        vb = self.v_elem(L, 0, j * W, 0)
        assert kb % SECTOR == 0 and vb % SECTOR == 0
        return desc(M_QKV, fmt=fmt, rmw=rmw, fence=fence, tag=tag, a0=kb // SECTOR, a1=vb // SECTOR,
                    a2=self.TW * HD * W // SECTOR, a3=self.TMAX * HD // SECTOR,
                    n1=int(np.log2(HD)), n4=self.KV, n5=t_lo, n6=t_hi)


def qkv_payload(k, v, fmt):
    """One block's payload: K rows then V rows, [t][head][d] (vLLM FlashAttention NHD),
    k/v float32 [T, KV, HD] (fmt FP32 / BF16: the values; FP8: E4M3-grid values)."""
    parts = []
    for x in (k, v):
        x = np.ascontiguousarray(x, dtype=np.float32)
        if fmt == FMT_FP32:
            parts.append(x.tobytes())
        elif fmt == FMT_BF16:
            import hdc_golden as G           # the serving engine's BF16: round to nearest even
            parts.append((G.bits(G.to_bf16(x)) >> 16).astype(np.uint16).tobytes())
        else:
            parts.append(fp8_code(x).tobytes())
    return b"".join(parts)


# -- V4.1 rows and index keys ---------------------------------------------------------
def row_slot(r, ndie, die, ns, ring=0):
    """(stack, local row) of global row / key r on this die, or None if it is another die's."""
    if ring:
        return 0, r % ring
    g = r // 16
    if g % ndie != die:
        return None
    gd = g // ndie
    return gd % ns, (gd // ns) * 16 + r % 16


def rows_image(nsec, rows, first, rb, pitch, base, stride, ndie, die, ns, ring=0, init=None):
    img = np.zeros(nsec * SECTOR, dtype=np.uint8) if init is None else init.copy()
    for i, rec in enumerate(rows):
        sl = row_slot(first + i, ndie, die, ns, ring)
        if sl is None:
            continue
        stk, loc = sl
        a = (base + (0 if ring else stk * stride) + loc * pitch) * SECTOR
        img[a:a + pitch * SECTOR] = 0
        img[a:a + rb] = np.frombuffer(rec, dtype=np.uint8)
    return img


def ikey_image(nsec, keys, first, base, stride, ndie, die, ns, init=None):
    """keys: 68-B records (64 B codes, 4 B scales).  Per stack 1,024-key super-blocks of 17 x 4 KB."""
    img = np.zeros(nsec * SECTOR, dtype=np.uint8) if init is None else init.copy()
    for i, rec in enumerate(keys):
        sl = row_slot(first + i, ndie, die, ns)
        if sl is None:
            continue
        stk, loc = sl
        sb, j = divmod(loc, 1024)
        blk = (base + stk * stride + sb * 17 * 128) * SECTOR
        code = blk + (1 + j // 64) * 4096 + (j % 64) * 64
        img[code:code + 64] = np.frombuffer(rec[:64], dtype=np.uint8)
        img[blk + 4 * j:blk + 4 * j + 4] = np.frombuffer(rec[64:68], dtype=np.uint8)
    return img


def encode_ikey(x):
    """The 68-B wire record of one index key (128 values): E2M1 codes two per byte
    (element 2i in the low nibble, as torch.float4_e2m1fn_x2) and one UE8M0 scale
    byte per 32 (exponent + 127), exactly fp4_act_quant with a UE8M0 scale."""
    import hdc_golden_v41 as G4
    x = np.asarray(x, dtype=np.float32).reshape(-1, 32)
    amax = np.maximum(np.max(np.abs(x), axis=1), G4.FP4_AMAX_FLOOR_E8M0).astype(np.float32)
    e = G4._ceil_log2(G4.mul(amax, G4.FP4_MAX_INV))
    v = np.clip(x.astype(np.float64) * np.exp2(-e)[:, None], -G4.FP4_MAX, G4.FP4_MAX)
    q = G4._round_grid(v, 0, 1)
    idx = np.searchsorted(G4.E2M1_VALUES, np.abs(q))
    assert np.array_equal(G4.E2M1_VALUES[idx], np.abs(q))
    nib = (idx | np.signbit(q) * 8).astype(np.uint8).reshape(-1)        # -0 keeps its sign (code 8)
    codes = (nib[0::2] | (nib[1::2] << 4)).astype(np.uint8)
    scales = (np.asarray(e) + 127).astype(np.uint8)
    return codes.tobytes() + scales.tobytes()


def decode_ikey(rec):
    import hdc_golden_v41 as G4
    b = np.frombuffer(rec, dtype=np.uint8)
    nib = np.empty(128, dtype=np.int64)
    nib[0::2] = b[:64] & 15
    nib[1::2] = b[:64] >> 4
    val = G4.E2M1_VALUES[nib & 7] * np.where(nib & 8, -1.0, 1.0)
    e = b[64:68].astype(np.int64) - 127
    return G4.to_bf16((val.reshape(4, 32) * np.exp2(e)[:, None]).astype(np.float32).reshape(-1))


def encode_window(x):
    """528-B window row (512 E4M3 codes, then 16 UE8M0 scales, one per 32): act_quant with a UE8M0
    scale, exactly hdc_golden_v41.quant_fp8; its decode equals qdq_fp8 (the products are exact in BF16)."""
    import hdc_golden_v41 as G4
    q, e = G4.quant_fp8(np.asarray(x, dtype=np.float32), 32)
    codes = fp8_code(q.astype(np.float32))
    return codes.tobytes() + (np.asarray(e) + 127).astype(np.uint8).tobytes()


def decode_window(rec):
    import hdc_golden_v41 as G4
    b = np.frombuffer(rec, dtype=np.uint8)
    v = fp8_value(b[:512]).astype(np.float64).reshape(16, 32) * np.exp2(b[512:528].astype(np.int64) - 127)[:, None]
    return G4.to_bf16(v.astype(np.float32).reshape(-1))


def encode_ckv(x):
    """288-B compressed row (512 E2M1 codes low nibble first, then 32 E4M3 scales, one per 16):
    fp4_act_quant with an E4M3 scale, exactly the forward half of hdc_golden_v41.qdq_fp4_e4m3."""
    import hdc_golden_v41 as G4
    x = np.asarray(x, dtype=np.float32).reshape(-1, 16)
    amax = np.maximum(np.max(np.abs(x), axis=1), G4.FP4_AMAX_FLOOR_E4M3).astype(np.float32)
    # the release's T.Cast(FP8, amax / 6) is __NV_SATFINITE: the scale saturates at 448 (codes clamp at +-6)
    s = np.minimum(G4._e4m3_round(amax.astype(np.float64) / G4.FP4_MAX), 448.0)
    a = np.abs(x.astype(np.float64))
    code = np.zeros(a.shape, dtype=np.int64)
    for i, m in enumerate(G4.E2M1_MIDPOINTS):
        t = m * s[:, None]
        code = np.where((a > t) | ((a == t) & ((i + 1) % 2 == 0)), i + 1, code)
    nib = (code | (x < 0) * 8).astype(np.uint8).reshape(-1)     # the golden's np.sign: -0 gives +0
    return (nib[0::2] | (nib[1::2] << 4)).astype(np.uint8).tobytes() + fp8_code(s.astype(np.float32)).tobytes()


def decode_ckv(rec):
    """The golden's reading: E2M1 x E4M3 scale, exact, stored as BF16."""
    import hdc_golden_v41 as G4
    b = np.frombuffer(rec, dtype=np.uint8)
    nib = np.empty(512, dtype=np.int64)
    nib[0::2] = b[:256] & 15
    nib[1::2] = b[:256] >> 4
    val = G4.E2M1_VALUES[nib & 7] * np.where(nib & 8, -1.0, 1.0)
    s = fp8_value(b[256:288]).astype(np.float64)
    return G4.to_bf16((val.reshape(32, 16) * s[:, None]).astype(np.float32).reshape(-1))


def sectors(img):
    return [int.from_bytes(img[i:i + SECTOR].tobytes(), "little") for i in range(0, len(img), SECTOR)]
