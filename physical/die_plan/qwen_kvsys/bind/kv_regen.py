"""BINDER3 10-23 (STEWARD-TOKi 16:39 audit: stale KV hard ages on the bound top): re-derive the KV schedule parameters
that are HARD-CODED in as-built leaves from the BOUND (landed) lane depths (asbuilt.param_regen hook of
tools/die_plan/bind.py; same mechanism as the QC collective coll_regen.py).

Rules (tools/qwen_kv_die/kv_static_die.py KVR-DERIVE / ahub_ages; D = register stages on the die path):
  ECTL  qkd_ectl3_kiss_st (one per hg frame)   RESPONSE_LAT = 8 + D(krq) + D(krs)   (absolute: 8 = landing seg)
        krq = ectl.req_* -> slg.kreq landed depth, krs = slg.krsp -> ectl.rsp_* landed depth; one value per frame
        QK_ISSUE_AGE = max(34, RESPONSE_LAT + 11)   (kv_static_ages: max(QK_ISSUE_AGE_KIT, RL + QK_WRITE_BEFORE_READ);
        34 = attn calendar QK_CONSUME floor; TOK-QK-KVCHK 10-26: the floor was missing here, so the composed hook would
        bind 23 at RL 12 while the 833 boot image of record and regen_constants use 34)
        all frames must agree (the hardened children carry one value): unequal -> error, never a per-frame guess.
  AHUB  qkd_ahub_static_dw                      AP_OFS_s = 2 + L_s + D(ap_s) - D(ks_ahs)
        FR_OFS = D(ks_pvfst) - PV_LEAD - D(ks_ahfr) - D(ks_ahs) - 1
        L_s / PV_LEAD are compiler terms that the bind does not change, so the bound value = as-built value + the
        change of each D term (landed - as-built stages of that leg; an intra-partition leg keeps its as-built
        stages, change 0).  ap_s = ahub.ap<k> (k = 0..3 = stacks WS WN ES EN, AP_OFS[16k +: 16]); ks_ahs = kvs_attn.ahs
        -> ahub.hs_*; ks_pvfst = kvs_attn.pvfst -> pvfin; ks_ahfr = ahub.fr_* -> pvfin; PV_LEAD = kvs_attn.pvst -> pvw_*.
  SEQ   qkd_seq_core_static_s                  KVN_A0 = KVN_A0_asb + dD(d2d_kv.kvn_word_valid -> seq core)
        - dD(d2d_kv.att_rx_v -> kvs_attn)   (KV-P6 18:09: age a starts at the attention programme request, triggered by
        att_rx; kv_regen36 applied it from a table, the composed 2350 hook had dropped it: TOK-QK-KVCHK 10-26)
NOT regenerated here (no lane rule given, or not an RTL parameter) -> recorded in record.open for KV-P5 / TOK:
  PV ctl ot_qwen_tp8_pv_wide_ctl_tbf FIRST_INPUT_AGE / TRUNK_D / FLAG_D (4 + W + DQ + RT_die + 1 needs the boot-image
  vport RT/DQ, which differ per port on the bound top); vport RT/DQ (boot-programmable); ahub am lag / d2d / kvs_ctl
  <-> hroot (compiler schedule terms, from bind_latency.json)."""
import re
from collections import defaultdict

STACKS = ["WS", "WN", "ES", "EN"]
QK_WRITE_BEFORE_READ = 11
QK_ISSUE_AGE_KIT = 34
LANDING_SEG = 8


def _legs(ctx):
    """per crossing sink bit: (source path, source pin, landed, as-built); intra-partition bits: landed = as-built"""
    F = ctx.F
    out = {}
    for (ci, pn, i), d in ctx.sinks.items():
        if d[0] == "x":
            landed = ctx.bitcyc[(d[1], d[6], d[2], d[3], d[4])] + (d[7] if len(d) > 7 else 0)
            out[(ci, pn, i)] = (F.cells[d[2]].path, d[3], landed, d[5])
        elif d[0] == "int":
            out[(ci, pn, i)] = (F.cells[d[1]].path, d[2], None, None)
    return out


def _delta(legs, ci, ports, src_rx=None):
    """{landed - as-built} over the bits of `ports` of cell ci (fed from a source matching src_rx); 0 for intra bits"""
    v = set()
    for (c, pn, i), (sp, spn, landed, asb) in legs.items():
        if c != ci or not any(re.fullmatch(p, pn) for p in ports):
            continue
        if src_rx and not re.fullmatch(src_rx, f"{sp}.{spn}"):
            continue
        v.add(0 if landed is None else landed - asb)
    return v


def _one(v, what):
    if len(v) != 1:
        raise ValueError(f"{what}: leg lands at {sorted(v)} (one value per leg required)")
    return v.pop()


def _ap_list(lit):
    s = str(lit).strip('"')
    m = re.fullmatch(r"64'b([01]{64})", s)
    if m:
        b = m.group(1)
        vals = [int(b[64 - 16 * (k + 1):64 - 16 * k], 2) for k in range(4)]
    else:
        m = re.fullmatch(r"64'h([0-9a-fA-F_]+)", s)
        h = int(m.group(1).replace("_", ""), 16)
        vals = [(h >> (16 * k)) & 0xffff for k in range(4)]
    return [x - 65536 if x >= 32768 else x for x in vals]


def _ap_lit(vals):
    return "64'h" + "".join(f"{v & 0xffff:04x}" for v in reversed(vals))


def regen(ctx):
    F = ctx.F
    legs = _legs(ctx)
    params, rec, open_ = {}, dict(ectl={}, ahub={}), []
    # ---- ECTL K round trip
    req_by_src = defaultdict(set)
    for (c, pn, i), (sp, spn, landed, asb) in legs.items():
        if landed is not None and spn.startswith("req_") and pn == "kreq":
            req_by_src[sp].add(landed)
    rts = {}
    for ci, c in enumerate(F.cells):
        if not re.search(r"qkd_ectl3_kiss_st", c.module):
            continue
        krq = _one(set(req_by_src.get(c.path, set())), f"ECTL {c.path} krq")
        krs = _one({x for (cc, pn, i), (sp, spn, landed, asb) in legs.items()
                    if cc == ci and pn.startswith("rsp_") and landed is not None for x in [landed]}, f"ECTL {c.path} krs")
        rts[c.path] = dict(krq=krq, krs=krs, RT=LANDING_SEG + krq + krs)
    if rts:
        vals = {v["RT"] for v in rts.values()}
        if len(vals) != 1:
            raise ValueError(f"ECTL: K round trips differ per frame {sorted(vals)} (the hardened children take one "
                             f"RESPONSE_LAT): equalise krq/krs in the plan or the r8 table")
        rt = vals.pop()
        qk = max(QK_ISSUE_AGE_KIT, rt + QK_WRITE_BEFORE_READ)
        for p in rts:
            params[p] = dict(RESPONSE_LAT=rt, QK_ISSUE_AGE=qk)
        rec["ectl"] = dict(rule="RESPONSE_LAT = 8 + krq + krs; QK_ISSUE_AGE = max(34, RESPONSE_LAT + 11)", frames=len(rts),
                           RESPONSE_LAT=rt, QK_ISSUE_AGE=qk,
                           krq=sorted({v["krq"] for v in rts.values()}), krs=sorted({v["krs"] for v in rts.values()}))
    # ---- AHUB offsets (delta form)
    for ci, c in enumerate(F.cells):
        if not re.search(r"qkd_ahub_static_dw", c.module):
            continue
        ap0 = _ap_list(c.params["AP_OFS"])
        fr0 = int(str(c.params["FR_OFS"]).strip('"'))
        d_ap = [_one(_delta(legs, ci, [f"ap{k}"]), f"AHUB ap{k}") for k in range(4)]
        d_hs = _one(_delta(legs, ci, [r"hs_\w+"]), "AHUB ks_ahs")
        cidx = ctx.cell_index()
        pvfin = next((i for i, x in enumerate(F.cells) if re.fullmatch(r"(.*\.)?pvfin", x.path)), None)
        d_pvfst = _one(_delta(legs, pvfin, [r"\w+"], r".*kvs_attn\.pvfst"), "AHUB ks_pvfst") if pvfin is not None else 0
        d_ahfr = _one(_delta(legs, pvfin, [r"\w+"], re.escape(c.path) + r"\.fr_\w+"), "AHUB ks_ahfr") \
            if pvfin is not None else 0
        pvw = [i for i, x in enumerate(F.cells) if re.search(r"pvw_[01]__u_RH_r0$|pvw_[01]$", x.path)]
        d_lead = set()
        for i in pvw:
            d_lead |= _delta(legs, i, [r"\w+"], r".*kvs_attn\.pvst")
        d_lead = _one(d_lead, "AHUB PV_LEAD") if d_lead else 0
        ap = [a + dap - d_hs for a, dap in zip(ap0, d_ap)]
        fr = fr0 + d_pvfst - d_lead - d_ahfr - d_hs
        params[c.path] = dict(AP_OFS=_ap_lit(ap), FR_OFS=fr)
        rec["ahub"] = dict(rule="AP_OFS_s += dD(ap_s) - dD(ks_ahs); FR_OFS += dD(ks_pvfst) - dPV_LEAD - dD(ks_ahfr) - "
                                "dD(ks_ahs)", stacks=STACKS, AP_OFS_asbuilt=ap0, AP_OFS=ap, FR_OFS_asbuilt=fr0, FR_OFS=fr,
                           dD=dict(ap=d_ap, ks_ahs=d_hs, ks_pvfst=d_pvfst, ks_ahfr=d_ahfr, PV_LEAD=d_lead))
        del cidx
    # ---- SEQ KVN_A0 (delta form, KV-P6 18:09)
    seq = [ci for ci, c in enumerate(F.cells) if re.search(r"qkd_seq_core_static_s", c.module)]
    if len(seq) != 1:
        raise ValueError(f"SEQ: {len(seq)} qkd_seq_core_static_s leaves (one seq core per die)")
    ci = seq[0]
    c = F.cells[ci]
    a0 = c.params.get("KVN_A0", (getattr(ctx, "param_defaults", {}) or {}).get((getattr(c, "ytype", None), c.module), {}).get("KVN_A0"))
    if a0 is None:
        raise ValueError(f"SEQ {c.path}: as-built KVN_A0 unknown")
    a0 = int(str(a0).strip('"'))
    attn = [i for i, x in enumerate(F.cells) if re.fullmatch(r"(.*\.)?kvs_attn", x.path)]
    if len(attn) != 1:
        raise ValueError(f"SEQ KVN_A0: {len(attn)} kvs_attn leaves")
    d_kvn = _one(_delta(legs, ci, [r"\w+"], r"(.*\.)?d2d_kv\.kvn_word_valid"), "SEQ kvn_word_valid -> seq core")
    d_rx = _one(_delta(legs, attn[0], [r"\w+"], r"(.*\.)?d2d_kv\.att_rx_v"), "SEQ att_rx_v -> kvs_attn")
    kvn = a0 + d_kvn - d_rx
    if not (0 <= kvn and kvn + 4 < 256):
        raise ValueError(f"SEQ KVN_A0 {kvn} outside the 8-b age window (asb {a0} + {d_kvn} - {d_rx})")
    params[c.path] = dict(KVN_A0=kvn)
    rec["seq"] = dict(rule="KVN_A0 += dD(kvn_word_valid -> seq core) - dD(att_rx_v -> kvs_attn)", KVN_A0_asbuilt=a0,
                      KVN_A0=kvn, dD=dict(kvn=d_kvn, att_rx=d_rx))
    open_ += [
        "PV ctl ot_qwen_tp8_pv_wide_ctl_tbf FIRST_INPUT_AGE/TRUNK_D/FLAG_D: 4 + W + DQ + RT_die + 1 needs the boot vport "
        "RT/DQ (per-port bound round trips differ) -> KV-P5 rule + boot image",
        "vport RT/DQ: boot-programmable, boot image must carry the bound round trip",
        "ahub am lag (EXP_START), d2d sys_c<->hub_C, kvs_ctl<->hroot: compiler schedule terms (bind_latency.json)"]
    rec["open"] = open_
    return dict(params=params, record=rec)
