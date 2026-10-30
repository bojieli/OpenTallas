"""DIE-S81-36/VES one-block fix (post-freeze, OWNER 12.20): VES ot_s81sl_ve_s internal width 164.16 -> 172.8 um
(aspect 2.105 -> 2.0) in all 74 parent leaf types. Source candidate Codex 921e0939dc1 (results/s81phys_0336/
ves_width_candidate): 387 E-edge M4 pins +8.64, clk entry (82.092,172.8) and every other pin unchanged, PG M5 phase
pairs repeated into the new E strip, OBS widened. The core always grows on its own E side (towards ve_m): R0/MX keep
the origin; MY/R180 shift origin x by -8.64, so clk and every non-E pin keep their exact parent-frame position (parent
clock taps and internal stations unchanged). Parent outline/pins/neighbours unchanged; min gap to any other macro
8.64 um. Only the VES hard_cores lines change (outline_um, lef, pins_file, origin_um for MY/R180, note); exact JSON
equality of everything else is asserted.
usage: delta_ves_w1728_1030.py PLAN_IN PLAN_OUT"""
import copy, json, re, sys
from pathlib import Path

OLD_W, NEW_W, H, DX = 164.16, 172.8, 345.6, 8.64
LEF = "physical/die_plan/s81/cores/leaf/lef/ot_s81sl_ve_s_tpl_w1728.lef"
PINS = "inputs/core_pins/ot_s81sl_ve_s_tpl_w1728.json"
NOTE = " | DIE-S81-36/VES W172.8 one-block fix (E-side growth, delta_ves_w1728_1030.py)"


def fix(c):
    assert c["module"] == "ot_s81sl_ve_s" and c["outline_um"] == [OLD_W, H], c
    c["outline_um"] = [NEW_W, H]
    c["lef"] = LEF
    c["pins_file"] = PINS
    if c.get("orient", "R0") in ("MY", "R180"):
        c["origin_um"] = [round(c["origin_um"][0] - DX, 6), c["origin_um"][1]]
    c["note"] = c.get("note", "") + NOTE
    return c


def apply(plan):
    n = 0
    for t in plan["partition_types"].values():
        for c in t.get("hard_cores", []) or []:
            if c["module"] == "ot_s81sl_ve_s":
                fix(c); n += 1
    assert n == 74, n
    return plan


def rewrite(text):
    expected = apply(json.loads(text))
    lines = text.split("\n"); n = 0
    for i, ln in enumerate(lines):
        if '"module":"ot_s81sl_ve_s"' in ln:
            body = ln.strip(); comma = body.endswith(",")
            c = fix(json.loads(body.rstrip(",")))
            ind = ln[:len(ln) - len(ln.lstrip())]
            lines[i] = ind + json.dumps(c, separators=(",", ":")) + ("," if comma else ""); n += 1
    assert n == 74, n
    out = "\n".join(lines)
    assert json.loads(out) == expected, "unexpected plan edit"
    return out


if __name__ == "__main__":
    Path(sys.argv[2]).write_text(rewrite(Path(sys.argv[1]).read_text()))
