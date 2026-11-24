"""adv_latdefine.py -- PRECHECK ADV-LAT-DEFINE (COORD 11-24 02:xx, FABLE-RC-ALL e78094d6; report only).

A latency-changing Verilog define on a type (partition_types.<t>.verilog_defines) changes the cycles the kit RTL really has; the latency
compiler / LATCHECK and the bind elab price from a PROFILE (the die-wide asbuilt `defines`, plus an explicit profile list when given).
A type listing such a define that the profile does not list is realised by the kit but not priced / elaborated (S81 J7 t14 SPR/XRB; the
mixed RIP / SRAMREG / CFX types of ARCH-R2).

SEED = defines whose latency effect ARCH-R2 measured or read (lanes/handoff/S81-KVLEAF-T2-ARCH-R2-mixed_define_table.tsv): OT_S81SL_VP_SRAMREG
(+1 on every vp output), OT_S81SL_VP_CFX (+1 hc_post write-back), OT_S81SL_LEP_RIP1 / RIP3 (+RIP on the ring-out lane), OT_S81SL_LEP_ROS3
(not read), OT_S81SL_VP_SELREP / OT_S81SL_LEP_CRP2 / WREP5 (expected 0, not confirmed: listed as UNCONFIRMED), kv_seam: any define matching
`kv_seam|KV_SEAM|SEAM` and OT_S81SL_KV_TRANSPORT.  An extra seed regex can be given (kw seed_re / env OT_ADV_LATDEFINE_RE).

Per seed define: types listing it, how many of them the profile lists (profile = as-built `defines` names, + kw profile list), and the types
NOT covered; a define listed by only some types of one family (the type name minus its __t<N>/cl suffix) is MIXED.  Without an as-built the
profile is empty: NOT-RUN is said in the summary.  findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

CHECK = "ADV-LAT-DEFINE"
MAX_LINES = 25
SEED = {
    "OT_S81SL_VP_SRAMREG": "+1 on every vp output (kv store loop 5)",
    "OT_S81SL_VP_CFX": "+1 hc_post write-back",
    "OT_S81SL_LEP_RIP1": "+RIP cycles on the ring-out lane ri",
    "OT_S81SL_LEP_RIP3": "ri +3 cycles vs RIP 0",
    "OT_S81SL_LEP_ROS3": "ROS3 not read (latency unknown)",
    "OT_S81SL_KV_TRANSPORT": "kv transport (kv_seam)",
}
UNCONFIRMED = {"OT_S81SL_VP_SELREP", "OT_S81SL_LEP_CRP2", "OT_S81SL_LEP_WREP5"}
SEAM_RE = re.compile(r"kv_seam|KV_SEAM|_SEAM", re.I)


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def family(tn):
    return re.sub(r"(__(cl|pv|sid|r8)\w*)+$", "", re.sub(r"__t\d+", "", tn))


def judge(types, profile, seed_re=None):
    """types {name: [defines]} -> {define: dict(listing=[types], missing=[types not in profile], mixed=[families])}"""
    by = defaultdict(list)
    for tn, ds in types.items():
        for d in ds or []:
            if d in SEED or d in UNCONFIRMED or SEAM_RE.search(d) or (seed_re and seed_re.search(d)):
                by[d].append(tn)
    fam_all = defaultdict(set)
    for tn in types:
        fam_all[family(tn)].add(tn)
    out = {}
    for d, lst in by.items():
        miss = [t for t in lst if d not in profile]
        mixed = sorted({family(t) for t in lst if fam_all[family(t)] - set(lst)})
        out[d] = dict(listing=sorted(lst), missing=sorted(miss), mixed=mixed)
    return out


def _findings(raw, plan_path, tree=None, **kw):
    ab = kw.get("asbuilt")
    if isinstance(ab, str):
        ab = json.loads(Path(ab).read_text())
    prof = set((ab or {}).get("defines") or []) if isinstance(ab, dict) else set()
    prof |= set(kw.get("profile") or [])
    seed_re = re.compile(kw.get("seed_re") or os.environ.get("OT_ADV_LATDEFINE_RE") or "(?!)")
    types = {tn: t.get("verilog_defines") or [] for tn, t in (raw.get("partition_types") or {}).items() if isinstance(t, dict)}
    r = judge(types, prof, seed_re)
    out, nmiss = [], 0
    for d, v in sorted(r.items(), key=lambda kv: -len(kv[1]["missing"])):
        if not v["missing"] and not v["mixed"]:
            continue
        nmiss += len(v["missing"])
        eff = SEED.get(d, "listed as UNCONFIRMED / seam define" if d in UNCONFIRMED or SEAM_RE.search(d) else "extra seed")
        out.append(_w(f"{d} ({eff}): {len(v['listing'])} type(s) list it, {len(v['missing'])} not in the compiler profile "
                      f"({', '.join(v['missing'][:4])}{' ...' if len(v['missing']) > 4 else ''}); "
                      f"MIXED in {len(v['mixed'])} famil(ies) ({', '.join(v['mixed'][:4])}{' ...' if len(v['mixed']) > 4 else ''}); "
                      f"fix: list it in the profile / die-wide defines, or give every type of the family the same define"))
    out = out[:MAX_LINES]
    out.append(_w("summary", f"{len(r)} latency-define(s) in use over {sum(1 for t in types.values() if t)} types; {nmiss} (type, define) pairs not in the profile; "
                             f"{sum(1 for v in r.values() if v['mixed'])} define(s) MIXED within a family"
                             + ("" if isinstance(ab, dict) or kw.get("profile") else "; NOT-RUN profile check: no as-built given (every listing counts as missing)")))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], None, asbuilt=sys.argv[2] if len(sys.argv) > 2 else None):
        print(ln)
