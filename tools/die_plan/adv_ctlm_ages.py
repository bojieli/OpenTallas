"""adv_ctlm_ages.py -- PRECHECK ADV-CTLM-AGES (COORD 11-24 03:4x; report only).

QC tt_ctlm: a core compiled for a 21-edge transport while the plan / program prices 20 faults at boot.  Compares, per compiled ctlm program,
  * the program's lane ages R_CMD / R_HR / R_SS / R_AG (/ R_ST) -- ctlm_image.py --lane-ages input, recorded as relay.R_* in
    ctlm_metadata_source.json (tree results/**/*ctlm_metadata_source.json) -- with the BOUND LATCHECK delivered cycles of the matching lanes
    (bind_out/bind_lane_asbuilt.json): tt_ctlm__cmd_cmd_wi (CMD), tt_ctlm__hr_hr_wi (HR), tt_ctlm__tl_st_wi (ST), and a tt_ctlm lane whose name
    carries _ss / _ag (SS / AG) when one exists (not judged otherwise);
  * the core's compiled XPF_TRANSPORT_EDGES (results/arch/*/HR_SOURCE_CONTRACT.json compiled_XPF_TRANSPORT_EDGES, any master) with the rule
    xpf = 1 + R_HR (die_params), and with the program's own xpf_transport_edges.
C1g positive: program 19/19/17/17 against delivered 14/10/(10)/(13); contract XPF 21 vs 1 + 19 = 20.
findings(raw, plan_path, tree=None, bind_out=...) -> WARN lines, never raises.
"""
import glob
import json
import os
import re
import sys
from pathlib import Path

CHECK = "ADV-CTLM-AGES"
MAX_META = 12


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


LANE_KEYS = (("R_CMD", r"tt_ctlm__cmd_cmd_wi$"), ("R_HR", r"tt_ctlm__hr_hr_wi$"), ("R_ST", r"tt_ctlm__tl_st_wi$"),
             ("R_SS", r"tt_ctlm__\w*_ss(_|$)"), ("R_AG", r"tt_ctlm__\w*_ag(_|$)"))


def judge(relay, xpf_prog, contract_xpfs, delivered):
    """-> list of (kind, text).  relay {R_*: int}, xpf_prog int|None, contract_xpfs {master: int}, delivered {R_key: cycles}"""
    out = []
    for k, _rx in LANE_KEYS:
        if k in relay and k in delivered and int(relay[k]) != int(delivered[k]):
            out.append(("AGE", f"{k} program {relay[k]} vs delivered {delivered[k]}"))
    if "R_HR" in relay:
        want = 1 + int(relay["R_HR"])
        if xpf_prog is not None and int(xpf_prog) != want:
            out.append(("XPF-PROG", f"program xpf_transport_edges {xpf_prog} != 1 + R_HR {relay['R_HR']} = {want}"))
        for m, v in sorted(contract_xpfs.items()):
            if int(v) != want:
                out.append(("XPF-CORE", f"core {m.split('_')[-3:][0] if False else m} compiled XPF_TRANSPORT_EDGES {v} != 1 + program R_HR {relay['R_HR']} = {want}"))
    return out


def _delivered(bind_out):
    p = Path(bind_out) / "bind_lane_asbuilt.json"
    lanes = json.loads(p.read_text())["lanes"]
    got = {}
    for x in lanes:
        n = x.get("lane", "")
        for k, rx in LANE_KEYS:
            if re.search(rx, n) and k not in got:
                got[k] = x.get("table") if x.get("table") is not None else x.get("bind_plan_cycles")
    return got


def _findings(raw, plan_path, tree=None, **kw):
    bind_out = kw.get("bind_out") or os.environ.get("OT_ADV_BIND_OUT")
    if not tree:
        return [_w("not checked: no tree (needs <tree>/results ctlm_metadata_source.json + HR_SOURCE_CONTRACT.json)")]
    metas = sorted(glob.glob(str(Path(tree) / "results" / "**" / "*ctlm_metadata_source.json"), recursive=True))[:MAX_META]
    cons = sorted(glob.glob(str(Path(tree) / "results" / "arch" / "*" / "HR_SOURCE_CONTRACT.json")))
    xpfs = {}
    for c in cons:
        try:
            for r in json.loads(Path(c).read_text()):
                if isinstance(r, dict) and r.get("compiled_XPF_TRANSPORT_EDGES") is not None:
                    xpfs[r["master"]] = r["compiled_XPF_TRANSPORT_EDGES"]
        except (OSError, ValueError, TypeError):
            continue
    if not metas:
        return [_w("summary: no ctlm_metadata_source.json under the tree results (nothing compiled with lane ages to compare)")]
    if not bind_out or not (Path(bind_out) / "bind_lane_asbuilt.json").is_file():
        deliv = {}
        note = "NOT-RUN delivered-cycle comparison: no bind_out with bind_lane_asbuilt.json (XPF rule still checked)"
    else:
        deliv, note = _delivered(bind_out), ""
    out, nprog, nbad = [], 0, 0
    for m in metas:
        try:
            d = json.loads(Path(m).read_text())
        except (OSError, ValueError):
            continue
        relay = {k: v for k, v in (d.get("relay") or {}).items() if k.startswith("R_") and isinstance(v, int)}
        if not relay:
            continue
        nprog += 1
        res = judge(relay, d.get("xpf_transport_edges"), xpfs, deliv)
        if res:
            nbad += 1
            out.append(_w(f"{Path(m).name[:60]}: program ages " + "/".join(str(relay.get(k, '-')) for k in ("R_CMD", "R_HR", "R_SS", "R_AG")) +
                          " vs delivered " + "/".join(str(deliv.get(k, '-')) for k in ("R_CMD", "R_HR", "R_SS", "R_AG")) +
                          ": " + "; ".join(t for _, t in res)[:420] + "; the compiled program does not match the bound lanes: recompile with the bound ages "
                          "(ctlm_image.py --lane-ages) or fix the lane cycles"))
    out.append(_w("summary", f"{nbad} of {nprog} compiled ctlm program(s) disagree with the bound lane cycles / XPF rule; {len(xpfs)} core master(s) with compiled XPF"
                             + (f"; {note}" if note else "")))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    for ln in findings({}, sys.argv[1], sys.argv[1], bind_out=sys.argv[2] if len(sys.argv) > 2 else None):
        print(ln)
