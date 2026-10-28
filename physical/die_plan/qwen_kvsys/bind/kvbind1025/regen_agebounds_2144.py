"""Apply the approved KV boot-programmable storage bounds to explicit as-built parameters.

This changes hardware capacity, never the loaded age or arithmetic/schedule latency.
Old compressed GEN netlists still explicitly select the former 127/31 capacities;
updating RTL defaults alone cannot update those instance parameters.
"""
import re


def regen(ctx):
    params = {}
    counts = {"FIRST_INPUT_AGE": 0, "RT": 0}
    for c in ctx.F.cells:
        defaults = ctx.param_defaults.get((c.ytype, c.module), {})
        available = set(c.params) | set(defaults)
        change = {}
        if c.module == "qkd_pv16_vport_b" and "RT" in available:
            change["RT"] = 63
        if (re.fullmatch(r"ot_qwen_tp8_pv_wide_ctl_tbf(?:_p)?", c.module)
                or re.fullmatch(r"qkd_pvw_die_t(?:_f)?_b[af]", c.module)) and "FIRST_INPUT_AGE" in available:
            change["FIRST_INPUT_AGE"] = 255
        if change:
            params[c.path] = change
            for key in change:
                counts[key] += 1
    if not counts["RT"] or not counts["FIRST_INPUT_AGE"]:
        raise ValueError(f"expected boot-programmable PV leaves, found {counts}")
    return {"params": params, "record": {"counts": counts, "added_schedule_cycles": 0,
            "source": "PATH-KV decision 2026-10-25 21:21; RTL source 453dda0da433"}}
