#!/usr/bin/env python3
"""hold_margin_family.py -- the reg-to-reg FF hold repair TARGET per die family (HOLD-MARGIN-FAMILY 11-17, FABLE-CLOSURE-STRATEGY lever 1).

Every routed kit used to land at -3..-41 ps internal FF hold: the pre-route (pregrt_ff_hold) and GRT repairs close reg-to-reg hold to
margin 0..10 on estimated parasitics and detailed-route RC then moves the zero-logic station / relay pairs by tens of ps.  The target is
now a die-family value read by the common flow:

    QC / KV / HEAD type kits (plan die qwen_compute, qwen_kvsys, s81_head)   40 ps
    core kits (svc and hard cores, every core_flow.apply kit)                15 ps
    S81 / HBM type kits                                                      unchanged (S81 runs its own 10; HBM parked)

Where it lands (all repair TARGETS; every hold GATE stays FF hold >= 0, ports unchanged):
  * GRT FF repair   config.mk  export OT_HOLD_FF_MARGIN = max(caller value, family)        (gen_phys.write_type_kit, core_flow.apply)
  * pre-route repair config.mk export OT_PREGRT_HOLD_R2R_MARGIN = family                   (pregrt_ff_hold.py extra reg-to-reg pass;
                                                                                             ports and cross-tap guard unchanged)
  * setup guard      config.mk export OT_HOLD_SETUP_GUARD_PS = 0                           (hold_guard_grt.tcl: the chunked GRT hold repair
                                                                                             stops when worst setup falls below min(setup before the
                                                                                             repair, 0); pregrt keeps its own fail-safe, TT setup
                                                                                             rejected below the -42 ps R-MINIMAL gate)
  * evidence line    config.mk export OT_HOLD_FAMILY_MARGIN_PS = <ps>   (check_kit() reads it back)
Precedence: per-item env OT_HOLD_FF_MARGIN_PS (kit_wave item_env) > die plan key die.hold_ff_margin_ps / type key hold_ff_margin_ps >
family table.  Gen environment OT_HOLD_FAMILY_MARGIN=0 switches the family value off (A/B, old-flow reproduction).

A knob only works if the tools tree that generates the kit carries it: run `hold_margin_family.py check KITDIR [DIE|core]` on the first kit
of every wave; it exits 1 when the expected lines are missing from the kit's config.mk (stale tools tree).
"""
import os
import re
import sys
from pathlib import Path

FAMILY_PS = {"qwen_compute": 40.0, "qwen_kvsys": 40.0, "s81_head": 40.0}
CORE_PS = 15.0
SETUP_GUARD_PS = 0.0
OFF_ENV = "OT_HOLD_FAMILY_MARGIN"


def enabled(env=None):
    return str((os.environ if env is None else env).get(OFF_ENV, "")).strip() != "0"


def _num(v, what):
    x = float(v)
    if not 0.0 <= x <= 100.0:
        raise ValueError(f"{what} {x:g} outside [0, 100] ps")
    return x


def family_margin(die, plan_die=None, type_cfg=None, env=None):
    """the die-family reg-to-reg hold repair target (ps) or None (no family value).  die: plan die name; plan_die: the plan's die dict
    (key hold_ff_margin_ps); type_cfg: the type dict (key hold_ff_margin_ps wins over the die)."""
    if not enabled(env):
        return None
    vals = [FAMILY_PS.get(die)]
    if plan_die and plan_die.get("hold_ff_margin_ps") is not None:
        vals.append(_num(plan_die["hold_ff_margin_ps"], "die.hold_ff_margin_ps"))
    if type_cfg and type_cfg.get("hold_ff_margin_ps") is not None:
        vals.append(_num(type_cfg["hold_ff_margin_ps"], "type.hold_ff_margin_ps"))
    vals = [v for v in vals if v is not None]
    return max(vals) if vals else None       # table, die key and type key are FLOORS: the largest wins


def explicit(plan_die=None, type_cfg=None, env=None):
    """True when the family value comes from a plan key (die.hold_ff_margin_ps / type hold_ff_margin_ps): then it is the value, not a floor"""
    if not enabled(env):
        return False
    return bool((type_cfg and type_cfg.get("hold_ff_margin_ps") is not None) or (plan_die and plan_die.get("hold_ff_margin_ps") is not None))


def core_margin(env=None):
    return CORE_PS if enabled(env) else None


def grt_margin(caller, die=None, plan_die=None, type_cfg=None, env=None, core=False):
    """effective GRT FF repair margin = max(caller, per-item OT_HOLD_FF_MARGIN_PS, family table, die.hold_ff_margin_ps, type key); None stays None
    (two-mode kits).  The caller's value (gen.py --hold-ff-margin, even 0) and a per-item value may RAISE the margin, never lower it below the floor."""
    if caller is None:
        return None
    fam = core_margin(env) if core else family_margin(die, plan_die, type_cfg, env)
    if fam is None:
        return caller
    return max(float(caller), fam)


def config_lines(fam, setup_guard=SETUP_GUARD_PS, pregrt=True):
    """config.mk lines of a family value (empty when fam is None).  pregrt: also the pre-route reg-to-reg pass"""
    if fam is None:
        return []
    out = [f"export OT_HOLD_FAMILY_MARGIN_PS = {fam:g}"]
    if pregrt:
        out.append(f"export OT_PREGRT_HOLD_R2R_MARGIN = {fam:g}")
    out.append(f"export OT_HOLD_SETUP_GUARD_PS = {setup_guard:g}")
    return out


def mk_value(text, key):
    val = None
    for line in text.splitlines():
        m = re.match(r"^\s*(?:override\s+)?(?:export\s+)?" + re.escape(key) + r"\s*[:?]?=\s*(.*?)\s*$", line)
        if m:
            val = m.group(1)
    return val


def check_kit(kit, die=None, core=False, env=None, plan_die=None, type_cfg=None):
    """problems (list of strings; empty = the knob reached the kit) of a generated kit's config.mk against the expected family value"""
    fam = core_margin(env) if core else family_margin(die, plan_die, type_cfg, env)
    if fam is None:
        return []
    text = (Path(kit) / "config.mk").read_text()
    bad = []
    got = mk_value(text, "OT_HOLD_FF_MARGIN")
    if got is None:
        bad.append("config.mk has no OT_HOLD_FF_MARGIN (two-mode kit or a tools tree without the knob)")
    elif float(got) < fam:
        bad.append(f"OT_HOLD_FF_MARGIN {got} < family {fam:g}")
    if mk_value(text, "OT_HOLD_FAMILY_MARGIN_PS") is None:
        bad.append("config.mk has no OT_HOLD_FAMILY_MARGIN_PS: the generator's tools tree predates HOLD-MARGIN-FAMILY")
    return bad


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "check":
        kit = sys.argv[2]
        tag = sys.argv[3] if len(sys.argv) > 3 else "core"
        probs = check_kit(kit, None if tag == "core" else tag, core=tag == "core")
        for p in probs:
            print("HOLD_FAMILY_CHECK FAIL", p)
        print("HOLD_FAMILY_CHECK", "FAIL" if probs else "OK", kit)
        sys.exit(1 if probs else 0)
    print(__doc__)
    sys.exit(2)
