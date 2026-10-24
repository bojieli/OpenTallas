"""BINDER4 10-23 (COORD 20:38 KV rulings: PV entry-pad re-bind; KVN_A0 34 / QK_ISSUE_AGE 34) = kv_regen36.py with the PV
params from KV-P6-V37 @0ec5c902d (kv_pv_entry_r8_v36.json params: TRUNK_D 43, FLAG_D 0). Original BINDER3 note:
(COORD 18:04: the KV v3.6 re-bind carries KV-P5's regenerated schedule constants, rule table @29d54b0e2).
asbuilt.param_regen hook for the KV v3.6 bind: applies the TYPE-kind rule values that KV-P5's kv_param_regen_check.py
computed on the R8-landed v3.6 bind (pass a, same plan + same R8 table -> same landed depths; kept next to this file as
kv_param_rules_bound_v36.json) to the hardened leaves:
  ECTL qkd_ectl3_kiss_st     RESPONSE_LAT, QK_ISSUE_AGE = max(34, RESPONSE_LAT + 11)
  AHUB qkd_ahub_static_dw    AP_OFS[stack WS WN ES EN], FR_OFS
  SEQ  qkd_seq_core_static_s KVN_A0
Guard: the ECTL K round trip is re-measured from this bind's landed legs (8 + krq + krs, one value on every frame) and
must equal the table's RESPONSE_LAT, else the table is stale for this bind -> error (re-run the checker).
NOT applied (recorded open, owners KV-P5 / TOK): rule blockers (PV ctl TRUNK_D/FLAG_D differ N/S, vport DQ, kg row
skew, RH b-stream) and BOOT/compiler values (vport RT, cfg_fia, am lag, down/ret, d2d ages) -> boot image."""
import json
import re
from collections import defaultdict
from pathlib import Path

RULES = Path(__file__).with_name("kv_param_rules_bound_v36.json")
PV = Path(__file__).with_name("kv_pv_entry_r8_v36.json")  # KV-P6-V37 @0ec5c902d entry-pad table (converted)
COORD_PIN = dict(QK_ISSUE_AGE=34, KVN_A0=34)                # COORD 20:38: must equal the rule values
# KV d2d pair image TXDP (COORD 21:5x, CAL-AUTO rtl check): regen_constants.py kv_seam on the kv40 landed seam
# (XDIE_SEAM_K 34,34,32,32,32,31,31 -> [KS_TXS + 2 + SK_TXP, 2+host, 1, 1] + PINREG_EXT = [67,4,3,3]); bind_post.py
# re-derives it from every bind and FAILS on a mismatch, so a seam move cannot go unnoticed.
D2D_TXDP_K = "32'h03030443"
LANDING_SEG = 8


def _ap_lit(vals):
    return "64'h" + "".join(f"{v & 0xffff:04x}" for v in reversed(vals))


def regen(ctx):
    F = ctx.F
    R = {r["param"]: r for r in json.loads(RULES.read_text())["rules"]}
    rl = int(R["RESPONSE_LAT"]["regen_kv35"])
    qk = int(R["QK_ISSUE_AGE"]["regen_kv35"])
    ap = R["AP_OFS[stack]"]["regen_kv35"]
    ap = [int(ap[s]) for s in ("WS", "WN", "ES", "EN")]
    fr = int(R["FR_OFS"]["regen_kv35"])
    kvn = int(R["KVN_A0"]["regen_kv35"])
    pv = json.loads(PV.read_text())["params"] if PV.exists() and ctx.ab.get("land_r8_extra") else None
    for k, v in COORD_PIN.items():
        got = qk if k == "QK_ISSUE_AGE" else kvn
        if got != v:
            raise ValueError(f"KV regen: {k} {got} != COORD-pinned {v}")
    # guard: measured K round trip on this bind
    req, rsp = defaultdict(set), defaultdict(set)
    for (ci, pn, i), d in ctx.sinks.items():
        if d[0] != "x":
            continue
        landed = ctx.bitcyc[(d[1], d[6], d[2], d[3], d[4])] + (d[7] if len(d) > 7 else 0)
        if pn == "kreq" and d[3].startswith("req_"):
            req[F.cells[d[2]].path].add(landed)
        if pn.startswith("rsp_"):
            rsp[ci].add(landed)
    params, rts = {}, set()
    n = defaultdict(int)
    for ci, c in enumerate(F.cells):
        if re.search(r"qkd_ectl3_kiss_st", c.module):
            q, s = req.get(c.path, set()), rsp.get(ci, set())
            if len(q) != 1 or len(s) != 1:
                raise ValueError(f"ECTL {c.path}: krq {sorted(q)} krs {sorted(s)} (one landed depth per leg required)")
            rts.add(LANDING_SEG + next(iter(q)) + next(iter(s)))
            params[c.path] = dict(RESPONSE_LAT=rl, QK_ISSUE_AGE=qk)
            n["ectl"] += 1
        elif re.search(r"qkd_ahub_static_dw", c.module):
            params[c.path] = dict(AP_OFS=_ap_lit(ap), FR_OFS=fr)
            n["ahub"] += 1
        elif pv and re.search(r"ot_qwen_tp8_pv_wide_ctl_tbf", c.module):
            params[c.path] = dict(TRUNK_D=pv["TRUNK_D"], FLAG_D=pv["FLAG_D"])
            n["pv_ctl"] += 1
        elif re.search(r"qkd_d2d_static", c.module):
            params[c.path] = dict(TXDP=D2D_TXDP_K)
            n["d2d"] += 1
        elif re.search(r"qkd_seq_core_static_s", c.module):
            params[c.path] = dict(KVN_A0=kvn)
            n["seq"] += 1
    if rts != {rl}:
        raise ValueError(f"KV rule table {RULES.name} stale: measured K round trips {sorted(rts)} != RESPONSE_LAT {rl}")
    if not (n["ectl"] and n["ahub"] == 1 and n["seq"] == 1 and n["d2d"] == 1):
        raise ValueError(f"KV regen: cells found {dict(n)} (expect ECTL frames, 1 AHUB, 1 seq core)")
    blk = [dict(param=r["param"], module=r["module"], violations=r.get("violations"), pads=r.get("pads"))
           for r in R.values() if r.get("violations") and not (pv and r["param"] in ("TRUNK_D", "FLAG_D"))]
    if pv:
        blk = [b for b in blk if not b["param"].startswith("DQ")]   # entry table: DQ <= 15 + W request pads
    boot = {r["param"]: r["regen_kv35"] for r in R.values() if r["kind"] == "boot"}
    rec = dict(rules=RULES.name, rules_source="KV-P5 kv_param_regen_check.py @29d54b0e2 on the v3.6 R8 pass-a bind",
               applied=dict(RESPONSE_LAT=rl, QK_ISSUE_AGE=qk, AP_OFS_WS_WN_ES_EN=ap, FR_OFS=fr, KVN_A0=kvn, D2D_TXDP_K=D2D_TXDP_K), cells=dict(n),
               measured_RT=sorted(rts), open_blockers=blk, boot_programme=boot)
    if pv:
        rec["applied"].update(TRUNK_D=pv["TRUNK_D"], FLAG_D=pv["FLAG_D"])
        rec["pv_table"] = dict(file=PV.name, source="KV-P6-V37 claude/kv-p6-v37-1023 @0ec5c902d kv_pv_entry_pads_v36.json",
                               boot=dict(pvfin_P0_P1_cal_age_shift=pv["pvfin_P0_P1_cal_age_shift"], cfg_fia=pv["cfg_fia"],
                                         RL=pv["RL"], vport=pv["boot"]))
    return dict(params=params, record=rec)
