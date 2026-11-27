"""G0 START tap ports (C-START-TAP-PORT-MISSING, P-FALSE-GREEN; FABLE-RC-HEAD 1247, COORD safety fix, BLOCKING).

Every die-level START stage (start_stage_emit.py: ot_dp_landing_origin / ot_dp_landing_root / relay, clk = its own die clock
tap port t_st_<id>__clk) needs one output port on the die clock tree (ctree.v, first module).  The live HEAD W12f die clock
was regenerated without those 1,389 ports (nodes and repeaters existed, assigns did not); G0 passed with 0 errors and
die_sta then refused the tree.  This check names every required port that the die clock module does not export.

Required ports (first source that exists wins):
  1. explicit start_stages.json[.gz] (check.py --start-stages / env OT_START_STAGES): stages[].clock_port
  2. the plan itself: clock.landing_network.start_tree.provider.nodes[].clock_port (QC form)
  3. PLANDIR/start_stages.json[.gz], or the one PLANDIR/../provider_*/start_stages.json[.gz]
Present ports: the header port list of the first module of the die clock Verilog (check.py --die-ctree / env OT_DIE_CTREE,
else PLANDIR/ctree.v, PLANDIR/die_ctree.v, PLANDIR/../die_clock/ctree.v).
Required known but no die clock Verilog resolvable: WARN (cannot verify), never silent.  Missing port: ERROR.
"""
import glob
import gzip
import json
import os
import re
from pathlib import Path

CHECK = "start_tap_ports"
_HDR = re.compile(r"\bmodule\s+(\w+)\s*\((.*?)\)\s*;", re.S)


def _load_json(p):
    p = str(p)
    op = gzip.open if p.endswith(".gz") else open
    with op(p, "rt") as f:
        return json.load(f)


def _stage_ports(doc):
    """[(stage id, port, region)] from an ot_start_stages/1 document (stages and relay entries that carry a clock_port)."""
    out = []
    for key in ("stages", "relays", "relay_stages"):
        rows = doc.get(key) if isinstance(doc, dict) else None
        if isinstance(rows, list):
            for s in rows:
                if isinstance(s, dict) and s.get("clock_port"):
                    out.append((str(s.get("id", s["clock_port"])), s["clock_port"], s.get("region")))
    return out


def required_ports(raw, plan_dir=None, start_stages=None):
    """-> (source label, [(id, port, region)]) or (None, [])."""
    start_stages = start_stages or os.environ.get("OT_START_STAGES")
    if start_stages:
        return str(start_stages), _stage_ports(_load_json(start_stages))
    try:
        nodes = raw["clock"]["landing_network"]["start_tree"]["provider"]["nodes"]
    except (KeyError, TypeError):
        nodes = None
    if nodes:
        return "plan clock.landing_network.start_tree.provider.nodes", \
            [(str(n.get("id", n["clock_port"])), n["clock_port"], n.get("region")) for n in nodes if n.get("clock_port")]
    if plan_dir:
        d = Path(plan_dir)
        for pat in ("start_stages.json", "start_stages.json.gz"):
            if (d / pat).is_file():
                return str(d / pat), _stage_ports(_load_json(d / pat))
        hits = sorted(glob.glob(str(d.parent / "provider_*" / "start_stages.json*")))
        if len(hits) == 1:
            return hits[0], _stage_ports(_load_json(hits[0]))
    return None, []


def find_ctree(plan_dir=None, die_ctree=None):
    die_ctree = die_ctree or os.environ.get("OT_DIE_CTREE")
    if die_ctree:
        return str(die_ctree)
    if plan_dir:
        d = Path(plan_dir)
        for c in (d / "ctree.v", d / "die_ctree.v", d.parent / "die_clock" / "ctree.v"):
            if c.is_file():
                return str(c)
    return None


def ctree_ports(path):
    """set of port names in the header of the first module of the clock Verilog (comments stripped)."""
    txt = Path(path).read_text()
    txt = re.sub(r"//[^\n]*", "", txt)
    m = _HDR.search(txt)
    if not m:
        raise ValueError(f"{path}: no module header")
    return {p.strip() for p in m.group(2).split(",") if p.strip()}


def census(raw, plan_dir=None, start_stages=None, die_ctree=None):
    src, req = required_ports(raw, plan_dir, start_stages)
    ct = find_ctree(plan_dir, die_ctree)
    rec = dict(required=len(req), required_source=src, die_ctree=ct, missing=[])
    if req and ct:
        try:
            have = ctree_ports(ct)
        except (OSError, ValueError) as ex:
            rec["unreadable"] = f"{type(ex).__name__}: {ex}"
            return rec
        rec["missing"] = [r for r in req if r[1] not in have]
    return rec


def check(raw, R, plan_dir=None, start_stages=None, die_ctree=None, max_msgs=20):
    """G0 hook: ERROR per missing START tap port (first max_msgs named, the rest counted), WARN when unverifiable."""
    rec = census(raw, plan_dir, start_stages, die_ctree)
    miss = rec.pop("missing")
    rec["missing_count"] = len(miss)
    if rec.get("unreadable"):
        # a recorded die clock that cannot be read is a FAIL (no START tap port can be proven); WARN is only for a die with no clock record
        R.err(CHECK, f"{rec['required']} START stage tap ports required ({rec['required_source']}) but the recorded die clock "
                     f"{rec['die_ctree']} cannot be read: {rec['unreadable']}")
    if rec["required"] and not rec["die_ctree"]:
        R.warn(CHECK, f"{rec['required']} START stage tap ports required ({rec['required_source']}) but no die clock Verilog to "
                      "verify them against (pass check.py --die-ctree or OT_DIE_CTREE); START tap ports UNVERIFIED")
    for sid, port, region in miss[:max_msgs]:
        R.err(CHECK, f"START stage {sid} (type die_start_stage, region {region}): port {port} missing from die clock "
                     f"{rec['die_ctree']} ({len(miss)} missing of {rec['required']}; die_sta refuses the tree)")
    if len(miss) > max_msgs:
        R.err(CHECK, f"... {len(miss) - max_msgs} more START stage tap ports missing from {rec['die_ctree']} "
                     f"(first {max_msgs} named above; first port {miss[0][1]}, last {miss[-1][1]})")
    rec["missing_ports_head"] = [m[1] for m in miss[:max_msgs]]
    return rec
