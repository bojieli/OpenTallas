"""GENBUG (FABLE-PD-QCC-0740): a plan hard-core row with param_wrap {base, params} names ONE paramod of the bound module.
The QC S4PQ bind passed with 0 errors while the plan rows said SKEW_N 6 / SKEW_S 7/8 and the bound RTL instances held 8/9 and
8/10; only the kit-rtl step (param_wrap.wrap_bound) looked, one type at a time.  This check reads the BOUND RTL text of the type
(the emitted <module>.sv, after every parameter regeneration of the bind) and compares each planned hard-core row that carries
param_wrap with the instance `<base> #(.P(v), ...) <inst> (` the row's physical_inst names: base module and every planned
parameter value must be equal.  Binder.cmd_bind adds HARD_CORE_PARAM_WRAP errors (the bind fails); the CLI is the report mode:
  python3 tools/die_plan/hard_core_param.py PLAN.json BINDDIR [MANIFEST.json]   (every mismatch, exit 1 if any)"""
import json
import re
import sys
from pathlib import Path

_PARAM = re.compile(r"\.(\w+)\s*\(\s*([^()]*?)\s*\)")


def _int(v):
    try:
        return int(str(v).replace("_", ""), 0)
    except ValueError:
        return None


def check_bound_text(tn, text, hard_cores):
    """-> [str]: one line per planned param_wrap row whose bound instance differs (missing instance, base module, a parameter)."""
    out = []
    for hc in hard_cores or []:
        pw = hc.get("param_wrap")
        if not pw:
            continue
        inst = (hc.get("physical_inst") or "").removeprefix("u_bound.")
        where = f"type {tn} row {hc.get('inst')}"
        if not inst or "." in inst:
            out.append(f"{where}: physical_inst must be u_bound.<local> (got {hc.get('physical_inst')})")
            continue
        pat = re.compile(r"^([ \t]+)(\w+)[ \t]+(#\([^\n]*?\))[ \t]+" + re.escape(inst) + r"[ \t]*\(", re.M)
        hits = list(pat.finditer(text))
        if len(hits) != 1:
            out.append(f"{where}: expected one bound instance {inst}, found {len(hits)}")
            continue
        h = hits[0]
        if h.group(2) != pw["base"]:
            out.append(f"{where} ({inst}): bound module {h.group(2)}, plan param_wrap base {pw['base']}")
            continue
        have = {k: v for k, v in _PARAM.findall(h.group(3))}
        for k, v in pw["params"].items():
            got = have.get(k)
            if got is None or _int(got) != int(v):
                out.append(f"{where} ({inst}): parameter {k} bound {got}, plan param_wrap {v}")
    return out


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) not in (2, 3):
        sys.exit(__doc__)
    plan = json.load(open(argv[0]))
    rtl = Path(argv[1])
    rtl = rtl / "rtl" if (rtl / "rtl").is_dir() else rtl
    rows, types, missing = [], 0, []
    for tn, t in plan["partition_types"].items():
        if not any(h.get("param_wrap") for h in t.get("hard_cores", []) or []):
            continue
        f = rtl / f"{t['module']}.sv"
        types += 1
        if not f.is_file():
            missing.append(tn)
            continue
        rows += check_bound_text(tn, f.read_text(errors="replace"), t.get("hard_cores"))
    for r in rows:
        print("HARD_CORE_PARAM_WRAP", r)
    for tn in missing:
        print("HARD_CORE_PARAM_NORTL", tn)
    print("HARD_CORE_PARAM_SUM", argv[0], "types_with_param_wrap", types, "no_bound_rtl", len(missing), "mismatches", len(rows))
    return 1 if rows else 0


if __name__ == "__main__":
    sys.exit(main())
