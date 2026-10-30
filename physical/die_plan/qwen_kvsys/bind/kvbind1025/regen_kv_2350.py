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


SEAM_NAMES = ("KS_RXV", "KS_RXP", "KS_TXS", "KS_TXK", "KS_TXB", "SK_TXV", "SK_TXP")


def bind_txdp(ctx):
    """TOK-KV-4 10-29 (KV-024 + the HOST record abort): the pair-image KV half this bind needs, from ITS landed legs, by
    the regen_constants laws (kv_seam / kv_host_rec_rt, same constants): XDIE_SEAM_K = as-built seam + Delta per
    d2d_kv <-> kvs_attn bundle, HOST_REC_RT = landed record_send_kind/witness_slot out + record_tx(_observed_v) back,
    D2D_TXDP_K = [KS_TXS + codec + SK_TXP, 2 + HOST_REC_RT, 1, 1] + PINREG_EXT.  One age per bundle, else ERROR."""
    import re
    rc = _load("regen_constants_laws", HERE.parents[4] / "tools" / "die_plan" / "regen_constants.py")
    kr = _load("kv_regen_legs_t", HERE.parent / "kv_regen.py")
    F = ctx.F
    legs = kr._legs(ctx)

    def cell(rx):
        ix = [i for i, c in enumerate(F.cells) if re.fullmatch(rf"(.*\.)?{rx}", c.path)]
        if len(ix) != 1:
            raise ValueError(f"TXDP: expected one {rx} cell, found {[F.cells[i].path for i in ix]}")
        return ix[0]
    ci = {"d2d_kv": cell("d2d_kv"), "kvs_attn": cell("kvs_attn")}
    st = {}
    for s, (sl, sp, dl, dp) in rc.KV_SEAM.items():
        v = kr._delta(legs, ci[dl], [dp], rf"(.*\.)?{sl}\.{sp}")
        st[s] = rc.KV_ANCHOR["seam"][s] + kr._one(v, f"TXDP seam {s}")
    out, back = set(), set()
    for (c, pn, i), (sp, spn, ld, asb) in legs.items():
        if re.fullmatch(r"(.*\.)?d2d_kv", sp) and spn in ("record_send_kind", "record_witness_slot") and pn == spn:
            out.add(ld or 0)
        elif c == ci["d2d_kv"] and pn in ("record_tx", "record_tx_observed_v"):
            back.add(ld or 0)
    for nm, v in (("out", out), ("back", back)):
        if len(v) > 1:
            raise ValueError(f"TXDP: HOST record {nm} bundle lands unequal {sorted(v)}")
    hrt = (out.pop() if out else 0) + (back.pop() if back else 0)
    k = [st["KS_TXS"] + rc.KV_CODEC_LANDED + st["SK_TXP"], 2 + hrt, 1, 1]
    k = [x + p for x, p in zip(k, rc.PINREG_EXT["K"])]
    return k, ",".join(str(st[n]) for n in SEAM_NAMES), hrt


def txdp(ctx):
    rec = json.loads(PAIR.read_text())
    k = [int(x) for x in rec["D2D_TXDP_K"]]
    word = k[0] | (k[1] << 8) | (k[2] << 16) | (k[3] << 24)
    if rec.get("sv_literal") and int(rec["sv_literal"].split("'h")[1], 16) != word:
        raise ValueError(f"pair image {PAIR.name}: sv_literal {rec['sv_literal']} != packed {k}")
    # KV-024 (DIE-KV-37-RC 10-29): the record was applied verbatim, so a bind whose seams moved (SK_TXP 78 -> 77) bound
    # the stale K0 170.  The record must be the image compiled on THIS bind (run_mu833.sh derives KST/HRT from it):
    # fail closed on any difference in K or in the seam stages the image was compiled with.
    kb, seam, hrt = bind_txdp(ctx)
    have = (k, str(rec.get("XDIE_SEAM_K")), int(rec.get("HOST_REC_RT", -1)))
    if have != (kb, seam, hrt):
        raise ValueError(f"pair image {PAIR.name} is stale for this bind: record K {k} XDIE_SEAM_K {have[1]} HOST_REC_RT "
                         f"{have[2]} vs bind K {kb} XDIE_SEAM_K {seam} HOST_REC_RT {hrt}; recompile the pair image on this "
                         "bind (physical/die_plan/qwen_kvsys/boot_v36/run_mu833.sh) and commit its D2D_TXDP_K + seams")
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
