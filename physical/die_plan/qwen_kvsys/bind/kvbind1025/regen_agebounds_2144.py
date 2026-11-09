"""Apply the approved KV boot-programmable storage bounds to explicit as-built parameters.

This changes hardware capacity, never the loaded age or arithmetic/schedule latency.
Old compressed GEN netlists still explicitly select the former 127/31 capacities;
updating RTL defaults alone cannot update those instance parameters.

KV-PLAN-1 11-09: the bounds are read from tools/qwen_kv_die/kv_bootage.py BOUNDS (the compiler's own table:
VPORT_RT, PV_FIRST_INPUT_AGE), never hard-coded here.  The old literal RT 63 predates DIE-KV-12 (COORD 10-28, bound
63 -> 95), so every plan_p4 vport (bound round trip 64..71) bound with RT 63 and faulted at boot (age_bad sticky).
"""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BOOTAGE = ROOT / "tools" / "qwen_kv_die" / "kv_bootage.py"


def bounds(path=BOOTAGE):
    """BOUNDS = dict(...) of kv_bootage.py, parsed (not imported: the module reads env and the source tree)"""
    for node in ast.parse(Path(path).read_text()).body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1 and getattr(node.targets[0], "id", None) == "BOUNDS"
                and isinstance(node.value, ast.Call) and getattr(node.value.func, "id", None) == "dict"):
            return {k.arg: ast.literal_eval(k.value) for k in node.value.keywords}
    raise ValueError(f"no BOUNDS = dict(...) in {path}")


def regen(ctx):
    b = bounds()
    rt, fia = int(b["VPORT_RT"]), int(b["PV_FIRST_INPUT_AGE"])
    params = {}
    counts = {"FIRST_INPUT_AGE": 0, "RT": 0}
    for c in ctx.F.cells:
        defaults = ctx.param_defaults.get((c.ytype, c.module), {})
        available = set(c.params) | set(defaults)
        change = {}
        if c.module == "qkd_pv16_vport_b" and "RT" in available:
            change["RT"] = rt
        if (re.fullmatch(r"ot_qwen_tp8_pv_wide_ctl_tbf(?:_p)?", c.module)
                or re.fullmatch(r"qkd_pvw_die_t(?:_f)?_b[af]", c.module)) and "FIRST_INPUT_AGE" in available:
            change["FIRST_INPUT_AGE"] = fia
        if change:
            params[c.path] = change
            for key in change:
                counts[key] += 1
    if not counts["RT"] or not counts["FIRST_INPUT_AGE"]:
        raise ValueError(f"expected boot-programmable PV leaves, found {counts}")
    return {"params": params, "record": {"counts": counts, "added_schedule_cycles": 0, "RT": rt, "FIRST_INPUT_AGE": fia,
            "bounds_file": str(BOOTAGE.relative_to(ROOT)),
            "source": "PATH-KV decision 2026-10-25 21:21; RTL source 453dda0da433; DIE-KV-12 RT 95; KV-PLAN-1 11-09"}}
