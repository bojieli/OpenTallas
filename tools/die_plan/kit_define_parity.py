#!/usr/bin/env python3
"""kit_define_parity: report-only (r703) check that a kit's VERILOG_DEFINES equal the bind's effective define set for that type.

LEC (lec.py) reads the KIT's own RTL under the kit's own config.mk defines, so a kit built with other defines than the bind
elaborated passes LEC while differing from the bound design (S81 svc: OT_SVC_SRX=7 in the bind, kit SRX 0 by RTL default).
Bind set for a type = the as-built defines (kit_rtl.json "defines": the die-wide ones, with values) that the kit's sources
reference, plus the type's own verilog_defines (kit_rtl.json "type_defines").  Kit set = config.mk -D tokens except SYNTHESIS.
Rows: (type, define, kit, bind) with '<unset>' for an absent one.  Latency/function-changing names carry LAT=1.
Needs <kit>/kit_rtl_paths.json -> filelist -> kit_rtl.json beside it; without it the kit is SKIPPED (not a pass).
  python3 -I kit_define_parity.py KIT [KIT ...]   prints  WARN KITDEF-PARITY <type> <define> kit=<v> bind=<v>
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rtl_lint

UNSET = "<unset>"
_USE = re.compile(r"`(?:ifdef|ifndef|elsif|undef)\s+(\w+)|`(\w+)")
# names whose value or presence changes cycles or logic function (judged from the RTL readers; report marks them LAT)
LAT_NAMES = {"OT_S81SL_VP_CFX", "OT_S81SL_VP_SRAMREG", "OT_S81SL_VP_SELREP", "OT_S81SL_CRR_PRE2", "OT_SVC_SRX", "OT_SVC_GP",
             "OT_SVC_BCAST", "OT_SVC_NATIVE_RT2_CALENDAR", "OT_SVC_ENG_XS", "OT_SVC_H8", "OT_SVC_MERGE_H4", "OT_SVC_ATTCUT",
             "OT_SVC_ATT_LAND_SRAM", "OT_SVC_ALLQ", "OT_S81_SERDES_TXPIPE", "OT_S81_SERDES_RXPIPE", "OT_S81_SERDES_RXNEG",
             "OT_S81_SERDES_RST_TREE", "OT_S81_SH_APIPE9", "OT_S81_SH_APIPE10", "OT_COLL_NATIVE32", "OT_GUNIT_BF_M1REG",
             "OT_GUNIT_BF_C1REG", "OT_GUNIT_BF_SVREG", "OT_GUNIT_BF_FWPIPE", "OT_BKQ_ECO3", "OT_S81C_HCORE_RST_TIMED",
             "OT_S81C_HCORE_CTLA", "OT_S81SL_LEP_RIP1", "OT_S81SL_LEP_RIP3", "OT_ATTN_HCORE", "OT_SVC_H8_REUSE_RT2"}


def _split(d):
    n, _, v = _norm(d).partition("=")
    return n, (v if _ else "")


def _norm(d):
    return d[2:] if d.startswith("-D") else d


def parity(kit):
    """-> (status, type, rows).  status OK | SKIP:<why>."""
    kit = Path(kit).resolve()
    rp = kit / "kit_rtl_paths.json"
    if not rp.is_file() or not (kit / "config.mk").is_file():
        return "SKIP:no kit_rtl_paths.json/config.mk", kit.name, []
    kj = Path(json.loads(rp.read_text()).get("filelist", "")).with_name("kit_rtl.json")
    if not kj.is_file():
        return "SKIP:no kit_rtl.json", kit.name, []
    doc = json.loads(kj.read_text())
    cfg = rtl_lint.config(kit)
    kitd = {}
    for tok in cfg.get("VERILOG_DEFINES", []):
        if tok.startswith("-D"):
            n, v = _split(tok)
            if n != "SYNTHESIS":
                kitd[n] = v
    used = set()
    for p in rtl_lint._kit_sources(kit):
        if p.suffix in (".sv", ".v", ".svh", ".vh") and p.is_file():
            for a, b in _USE.findall(p.read_text(errors="ignore")):
                used.add(a or b)
    bind = {}
    for d in doc.get("defines", []) or []:
        n, v = _split(d)
        if n != "SYNTHESIS" and n in used:
            bind[n] = v
    for d in doc.get("type_defines", []) or []:
        n, v = _split(d)
        if n != "SYNTHESIS":
            bind[n] = v
    rows = []
    for n in sorted(set(kitd) | set(bind)):
        kv, bv = kitd.get(n), bind.get(n)
        if kv == bv:
            continue
        show = lambda x: UNSET if x is None else (x if x != "" else "1")
        rows.append((n, show(kv), show(bv)))
    return "OK", doc.get("plan_type") or kit.name, rows


def lines(kit):
    st, ty, rows = parity(kit)
    if st != "OK":
        return [f"KITDEF-PARITY SKIP {ty} {st[5:]}"]
    return [f"WARN KITDEF-PARITY {ty} {n} kit={k} bind={b}" + (" LAT=1" if n in LAT_NAMES else "") for n, k, b in rows]


def main(argv=None):
    n = 0
    for k in (argv if argv is not None else sys.argv[1:]):
        for l in lines(k):
            print(l)
            n += l.startswith("WARN")
    print("KITDEF-PARITY mismatches", n)
    return 0          # report-only (r703)


if __name__ == "__main__":
    raise SystemExit(main())
