"""DIE-KV-64/RF-E 11-03 (DIE-KV-64 directive: astk LEC hang): kit-local wall limit on the OPT-IN raw-prefix base prove.

The kit copy of lec.py only (the shared tools/die_plan/lec.py default is unchanged): every ABC call tagged rawprefix*
gets a wall limit and the raw-prefix work a total budget; on expiry every output of that miter is "undecided", which is
the documented raw_prefix_bases fallback (no base: the register stays a free input, so nothing is assumed away).
The lec_async docker exec passes only a fixed OT_LEC_* list, so the limits are written into the kit copy as constants.
"""
from pathlib import Path

OLD = """    abc = abc_bin()
    r = subprocess.run([abc, "-c", f"&r {miter}; &ps; &fraig -C {conflicts}; &ps; "
                                   f"&sat -a -z -v -C {conflicts * 10}; &ps; &w {swept}"],
                       capture_output=True, text=True)
"""


def new(wall, budget):
    return f"""    abc = abc_bin()
    # RF-E 11-03 kit-local raw-prefix wall (lec_rawprefix_wall.py): {wall:.0f} s per ABC call, {budget:.0f} s total
    wall = {wall:.1f} if tag.startswith("rawprefix") else 0
    if wall:
        import time as _t
        t0 = globals().setdefault("_RP_T0", _t.time())
        if _t.time() - t0 > {budget:.1f}:
            log.append(f"==== {{tag}}\\nRAWPREFIX-BUDGET {budget:.0f}s spent: all outputs undecided (no base)")
            return {{n: "undecided" for n in m.onames}}
    try:
        r = subprocess.run([abc, "-c", f"&r {{miter}}; &ps; &fraig -C {{conflicts}}; &ps; "
                                       f"&sat -a -z -v -C {{conflicts * 10}}; &ps; &w {{swept}}"],
                           capture_output=True, text=True, timeout=wall or None)
    except subprocess.TimeoutExpired:
        log.append(f"==== {{tag}}\\nRAWPREFIX-WALL {wall:.0f}s hit: all {{len(m.onames)}} outputs undecided (no base)")
        return {{n: "undecided" for n in m.onames}}
"""


def apply(lec_py, spec):
    wall, _, budget = str(spec).partition(":")
    wall = float(wall); budget = float(budget or 4 * wall)
    p = Path(lec_py); t = p.read_text()
    if t.count(OLD) != 1:
        raise SystemExit("--lec-rawprefix-wall: lec.py prove() ABC call not in the expected form")
    p.write_text(t.replace(OLD, new(wall, budget), 1))
    return dict(rawprefix_wall_s=wall, rawprefix_budget_s=budget)
