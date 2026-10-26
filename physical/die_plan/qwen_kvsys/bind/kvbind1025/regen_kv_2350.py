"""PATH-KV 2026-10-26 (TOK-QK blocker on b19: bound d2d TXDP [22,4,3,3] vs seam [113,4,3,3]): the ONE KV param_regen
hook of the bind of record.  It composes the three KV parameter rules, each in its own module, so none is silently lost
again (the 2144 recipe pointed param_regen at the age-bounds hook alone and dropped kv_regen.py, leaving the bound top
with the as-built ECTL RESPONSE_LAT / QK_ISSUE_AGE and AHUB AP_OFS / FR_OFS):

  1 kv_regen.py              ECTL RESPONSE_LAT / QK_ISSUE_AGE, AHUB AP_OFS / FR_OFS from the BOUND lane depths (10-23)
  2 regen_agebounds_2144.py  PV FIRST_INPUT_AGE 255 / vport RT 63 capacity bounds (PATH-KV decision 10-25 21:21)
  3 the QC<->KV pair calendar image TXDP on the KV d2d leaf (qkd_d2d_static*, inst d2d_kv / u_d2d), read from the
    committed pair image record pair_image_txdp.json (both dies bind the SAME image).  The value is
    [KS_TXS + KV_CODEC + SK_TXP, 2 + host, 1, 1] + PINREG_EXT of the bound seams (tools/die_plan/regen_constants.py
    D2D_TXDP_K); regen_constants' bound-RTL check re-derives it from the bind and FAILS on any difference, so a stale
    record cannot pass the gate.

  4 KVN_A0 of the seq core (qkd_seq_core_static_s*, inst seq__u_core): KVN_A0 = as-built + dD(d2d_kv.kvn_word_valid ->
    seq__u_core) - dD(d2d_kv.att_rx_v -> kvs_attn.d2d__srx), dD = landed - as-built stages (the regen_constants
    KV-P6 18:09 rule; COORD 10-26 01:13 (2): the committed producer is the source of truth, never hand-set).

A rule that finds nothing to change on this die is an error (fail closed), never a silent skip.
"""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAIR = HERE / "pair_image_txdp.json"
D2D_MODULE_PREFIX = "qkd_d2d_static"


def _load(name, f):
    s = importlib.util.spec_from_file_location(name, f)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _merge(params, more, rule):
    for path, ps in more.items():
        cur = params.setdefault(path, {})
        for k, v in ps.items():
            if k in cur and str(cur[k]) != str(v):
                raise ValueError(f"{rule}: {path}.{k} set twice ({cur[k]} vs {v})")
            cur[k] = v


def txdp(ctx):
    rec = json.loads(PAIR.read_text())
    k = [int(x) for x in rec["D2D_TXDP_K"]]
    word = k[0] | (k[1] << 8) | (k[2] << 16) | (k[3] << 24)
    if rec.get("sv_literal") and int(rec["sv_literal"].split("'h")[1], 16) != word:
        raise ValueError(f"pair image {PAIR.name}: sv_literal {rec['sv_literal']} != packed {k}")
    hits = [c for c in ctx.F.cells if c.module.startswith(D2D_MODULE_PREFIX)
            and (c.path.endswith("d2d_kv") or "u_d2d" in c.path)]
    if len(hits) != 1:
        raise ValueError(f"TXDP: expected one KV d2d leaf ({D2D_MODULE_PREFIX}*), found {[c.path for c in hits]}")
    # the SV literal, so the bound top and regen_constants' bound-RTL check read the same text (decimal 50529393 was a
    # false MISMATCH against 32'h03030471)
    return {hits[0].path: {"TXDP": f"32'h{word:08x}"}}, dict(inst=hits[0].path, TXDP=k, word=f"32'h{word:08x}",
                                                source=rec.get("source"), commit=rec.get("commit"))


def kvn_a0(ctx):
    import re
    kr = _load("kv_regen_legs", HERE.parent / "kv_regen.py")
    F = ctx.F
    legs = kr._legs(ctx)
    seq = [i for i, c in enumerate(F.cells) if c.module.startswith("qkd_seq_core_static_s") and c.path.endswith("seq__u_core")]
    att = [i for i, c in enumerate(F.cells) if re.fullmatch(r"(.*\.)?kvs_attn", c.path)]
    if len(seq) != 1 or len(att) != 1:
        raise ValueError(f"KVN_A0: expected one seq core and one kvs_attn, got {[F.cells[i].path for i in seq + att]}")
    c = F.cells[seq[0]]
    a0 = int(str(c.params["KVN_A0"]).strip('"'))
    d_kvn = kr._one(kr._delta(legs, seq[0], [r"kvn_word_valid"], r"(.*\.)?d2d_kv\.kvn_word_valid"), "KVN_A0 kvn")
    d_rx = kr._one(kr._delta(legs, att[0], [r"d2d__srx"], r"(.*\.)?d2d_kv\.att_rx_v"), "KVN_A0 att_rx")
    v = a0 + d_kvn - d_rx
    return {c.path: {"KVN_A0": v}}, dict(inst=c.path, asbuilt=a0, dD_kvn=d_kvn, dD_att_rx=d_rx, KVN_A0=v)


def regen(ctx):
    params, record = {}, {}
    r1 = _load("kv_regen", HERE.parent / "kv_regen.py").regen(ctx)
    _merge(params, r1["params"], "kv_regen")
    record["kv_regen"] = r1.get("record", {})
    r2 = _load("kv_agebounds", HERE / "regen_agebounds_2144.py").regen(ctx)
    _merge(params, r2["params"], "agebounds")
    record["agebounds"] = r2.get("record", {})
    p3, record["txdp"] = txdp(ctx)
    _merge(params, p3, "txdp")
    p4, record["kvn_a0"] = kvn_a0(ctx)
    _merge(params, p4, "kvn_a0")
    record["hook"] = "physical/die_plan/qwen_kvsys/bind/kvbind1025/regen_kv_2350.py"
    return {"params": params, "record": record}
