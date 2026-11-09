"""KV-TRANSPORT-FIX 11-08: the ASTK per-EP EXP offset and the Z calendar base from the BOUND lanes (TRANSPORT-2 path 4c).

Offset.  qkd_astk_ep_s_e / _head_e trigger at age cal_exp + eo after the EP's own start, eo = EO_E e + EO_RL (e + e / 2).  The default
(9 / 3) is the law of the as-built relays; on the bound chain the token check tokd[5] == static_trigger faults on every EP but the first.
    eo(e + 1) - eo(e) = JOIN + zhop(e + 1) + qhop(e)        JOIN = 9 (local join, proved on the as-built RL 3 strip: 12 = 9 + 0 + 3)
qhop(e) = S(e) - S(e + 1), S = the landed depth of ep e's qi: the command chain is a pure delay line from ctl qo, so S is cumulative.
zhop(e) = the landed depth of ep e's zi (one hop, from ep e - 1's zo).

Z base.  qkd_attn_cal_gen_r17 emits Z - EXP = 250 + walk; the strip needs more, for two reasons, both measured in tb_qkd_astk_calendar
at the triple the generator really emits (every context tested, at D_QK 0 and 16, minimum passes and minus 1 fails):
    RTL_GAP = 24   the as-built RL 3 strip already needs Z + 24: the ASTK expansion (compiler law dZ 40 - dEXP 16) never reached the generator
    chain   = max over stacks [eo(7) + S(7) + D(ep 7 zo -> zn)] - REF     REF = 93 + 6 + 0 (RL 3 strip: default eo(7), ctl -> ep 7, zn 0)
    ZB_ADD  = RTL_GAP + chain                                              (bound KV: 24 + 58, WS 24 + 59 = 83)
The chain term was checked on depths it was not derived from (+3 zn, +2 ctl -> ep 7, +6 mid chain: predicted = measured).
The compiler already models Z at generator + dZ, so it adds ZB_ADD - dZ (kv_static_programme attention_calendar, astk_zb_add).

Each EP position is its own partition type on all four stacks, so EO_E / EO_RL are per-type constants and one ZB_ADD serves the die.
Fail closed: a port with more than one non-zero depth, stacks that disagree on the offsets (would fork the kv3_hg types), an offset the
EO_E / EO_RL form cannot encode (e 4 even, e 6 a multiple of 3), an offset past the 8-bit eo port, or a negative ZB_ADD."""
import re

EP = ("qkd_astk_ep_s_e", "qkd_astk_ep_s_head_e")
ATTN = "qkd_kvs_attn_fl"
JOIN = 9
REF = 93 + 6 + 0
RTL_GAP = 24
PATH = re.compile(r"astk_(WS|WN|ES|EN)__u_strip_u_strip_g_ep_(\d)__u_ep")
ZN_PORT = "u_strip_u_strip_g_zn_0_u_zn__zi"


def _one(ctx, path, port, what):
    v = sorted(set(x for x in ctx.depth(path, port).values() if x))     # 0 = a tied / local bit, as kv_ex_join_regen
    if len(v) != 1:
        raise ValueError(f"{what}: {path}.{port} lands at depths {v} (one non-zero depth per chain hop)")
    return v[0]


def pair(e, t):
    """EO_E e + EO_RL (e + e / 2) == t, smallest EO_RL"""
    if e == 0:
        if t != 0:
            raise ValueError(f"eo(0) = {t}: the chain head has no offset term")
        return 9, 3
    for r in range(0, 256):
        v = t - r * (e + e // 2)
        if v >= 0 and v % e == 0 and v // e < 256:
            return v // e, r
    raise ValueError(f"no EO_E / EO_RL pair for e {e} eo {t}")


def laws(q, z, zn):
    """q[e] cumulative qi depth e = 0..7, z[e] zi depth e = 1..7, zn = ep 7 zo -> zn: (eo list, last-EP arrival term)"""
    eo = [0]
    for e in range(7):
        eo.append(eo[e] + JOIN + z[e + 1] + q[e] - q[e + 1])
    return eo, eo[7] + q[7] + zn


def ep_offset(ctx):
    idx, attn, zn_cell = {}, [], {}
    for c in ctx.F.cells:
        m = PATH.fullmatch(c.path)
        if c.kind == "leaf" and c.module in EP:
            if not m:
                raise ValueError(f"ep path {c.path}: no stack / row")
            idx.setdefault(m.group(1), {})[int(m.group(2))] = c.path
        elif c.module == ATTN:
            attn.append(c.path)
        z = re.fullmatch(r"native_composite_\w+_astk_(WS|WN|ES|EN)", c.path)
        if z:
            zn_cell[z.group(1)] = c.path
    if not idx:
        return {}, dict(eps=0, note="no ASTK EP in this design: no parameter set")
    if len(attn) != 1:
        raise ValueError(f"{ATTN}: {len(attn)} instances")
    params, per = {}, {}
    for st, row in sorted(idx.items()):
        if sorted(row) != list(range(8)):
            raise ValueError(f"stack {st}: EP rows {sorted(row)}")
        if st not in zn_cell:
            raise ValueError(f"stack {st}: no composite holding the zn input")
        q = {e: _one(ctx, row[e], "qi", "command chain") for e in range(8)}
        z = {e: _one(ctx, row[e], "zi", "token hop") for e in range(1, 8)}
        zn = _one(ctx, zn_cell[st], ZN_PORT, "ep 7 -> zn")
        eo, last = laws(q, z, zn)
        per[st] = dict(qi=[q[e] for e in range(8)], zi=[z[e] for e in range(1, 8)], zn=zn, eo=eo, last=last)
    tables = {tuple(v["eo"]) for v in per.values()}
    if len(tables) != 1:
        raise ValueError(f"EP offsets differ between stacks (would fork the kv3_hg types): { {k: v['eo'] for k, v in per.items()} }")
    eo = list(next(iter(tables)))
    if max(eo) > 255:
        raise ValueError(f"eo past the 8-bit range: {eo}")
    pairs = {e: pair(e, eo[e]) for e in range(8)}
    for row in idx.values():
        for e, p in row.items():
            params[p] = dict(EO_E=pairs[e][0], EO_RL=pairs[e][1])
    chain = max(v["last"] for v in per.values()) - REF
    if chain < 0:
        raise ValueError(f"chain term {chain} < 0: the chain is shorter than the RL 3 reference, re-measure the calendar")
    zb = RTL_GAP + chain
    params[attn[0]] = dict(ZB_ADD=zb)
    return params, dict(rule="eo(e+1) - eo(e) = 9 + zhop(e+1) + qhop(e); ZB_ADD = 24 + max(eo7 + S7 + zn) - 99", eo=eo,
                        pairs={str(e): pairs[e] for e in range(8)}, per_stack=per, zb_add=zb, chain=chain, rtl_gap=RTL_GAP, ref=REF, attn=attn[0],
                        compiler="attention_calendar adds zb_add - dZ to Z, HUB_Z, HUB_RECIP, HUB_PUB")
