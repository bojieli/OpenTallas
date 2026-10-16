"""SM weight line image (ot_hgi_sm_record / ot_hbm_accel_smh; hgi-1010/d "SM LINE IMAGE", golden packer
tools/dshbm_matched_sm_seq.py gen_op): row r = LPR consecutive 136-B lines, line l = g * 8 + t, lane j of the line covers
chunk ch = g * LA + j.  FP8 (LA 4): 32-element block b = ch * 8 + t, its E4M3 codes at bits 256 j + 8 i, its UE8M0
(e + 127) at bits 1024 + 8 j.  FP4 (LA 8): E2M1 nibbles at bits 128 j + 4 i (element 2m = low nibble), UE8M0 at
1024 + 8 j.  BF16 (LA 64): element k = ch * 8 + t at bits 16 j; bits 1024.. are 0.  Blocks / elements past K are 0."""
import numpy as np

LB = 136
_E4 = None


def e4m3_codes(q):
    global _E4
    import hdc_golden_v41 as V
    if _E4 is None:
        _E4 = np.asarray(V.E4M3[:127], dtype=np.float64)          # magnitudes of codes 0 .. 126 (127 = NaN)
    a = np.abs(q)
    c = np.searchsorted(_E4, a)
    assert np.array_equal(_E4[np.minimum(c, 126)], a), "value not on the E4M3 grid"
    return (c | (np.signbit(q).astype(np.int64) << 7)).astype(np.uint8)


def e2m1_codes(q):
    import hdc_golden_v41 as V
    m = np.asarray(V.E2M1_VALUES, dtype=np.float64)
    a = np.abs(q)
    c = np.searchsorted(m, a)
    assert np.array_equal(m[np.minimum(c, 7)], a), "value not on the E2M1 grid"
    return (c | (np.signbit(q).astype(np.int64) << 3)).astype(np.uint8)


def pack(fmt, w):
    """fmt 0 BF16 (w float32 rows), 1 FP8 / 2 FP4 (w a hdc_golden_v41.Q8: q values, e per 32-block exponents) ->
    uint8 [R, LPR * 136]"""
    if fmt == 0:
        w = np.asarray(w, dtype=np.float32)
        R, K = w.shape
        bits = (w.view(np.uint32) >> 16).astype(np.uint16)
        C = -(-K // 8)
        LA = 64
        Gn = -(-C // LA)
        out = np.zeros((R, Gn, 8, LB), dtype=np.uint8)
        for g in range(Gn):
            for t in range(8):
                for j in range(LA):
                    k = (g * LA + j) * 8 + t
                    if k < K:
                        out[:, g, t, 2 * j] = bits[:, k] & 0xFF
                        out[:, g, t, 2 * j + 1] = bits[:, k] >> 8
        return out.reshape(R, -1)
    q, e = np.asarray(w.q), np.asarray(w.e, dtype=np.int64)
    R, K = q.shape
    nb = K // 32
    fp4 = fmt == 2
    codes = (e2m1_codes(q) if fp4 else e4m3_codes(q)).reshape(R, nb, 32)
    sc = ((e + 127) & 0xFF).astype(np.uint8)
    C = -(-nb // 8)
    LA = 8 if fp4 else 4
    Gn = -(-C // LA)
    out = np.zeros((R, Gn, 8, LB), dtype=np.uint8)
    for g in range(Gn):
        for t in range(8):
            for j in range(LA):
                b = (g * LA + j) * 8 + t
                if b >= nb:
                    continue
                if fp4:
                    out[:, g, t, 16 * j:16 * j + 16] = codes[:, b, 0::2] | (codes[:, b, 1::2] << 4)
                else:
                    out[:, g, t, 32 * j:32 * j + 32] = codes[:, b, :]
                out[:, g, t, 128 + j] = sc[:, b]
    return out.reshape(R, -1)
