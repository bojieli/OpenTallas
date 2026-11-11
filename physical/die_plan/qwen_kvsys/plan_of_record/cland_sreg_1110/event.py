#!/usr/bin/env python3
"""DIE-KV-97 11-10 cland_sreg_1110: STATUS-REG-1 on the KV ring types whose routed sign-off misses on the landing-ring
status crossing / half-cycle guard (COORD 11-10 kv3_io_cor class fix).

Class (routed, signoff/{tt,ff}/sta.log):
  kv3_io_cor    817517ba2672 a8 TT -480.4  u_cland_ft13_i status copy lap_q -> rv (fclk -> clk, max_delay 416.5, 7 levels)
                               TT -253.6  u_cland_ft1_i oh[4] -> ghi0 (clk rise -> clk fall half cycle)
  kv3_io_cor_v1 a9             TT  -50.7  oh[2] -> ghi0; status copy written -> lap_ok
  kv3_sys_SD_v1                TT -212.1  status copy -> lap_ok
Form: partition_types.<T>.landing_status_reg = true (generator already in main, tools/die_plan/clock_landings.py:
`.STATUS_REG(1)` appended to every count-aligned ring of the type; default absent = byte-same RTL).  The status crossings
end at private per-slot rclk flops (0 logic levels across fclk -> clk); the select/compare and the guard select become
full-period clk -> clk paths; the clk rise -> fall guard path is gone.
Cycles: data q / ready 0 added cycles (lane_added_cycles unchanged); a rv / lap fault is reported 1 clk later
(status_reg_added_fault_cycles 1).  Fault reporting is not on the token schedule, so TOK-VERIFY-1 has no schedule change
to check.  EQ: rtl/test/meso/status_reg/run.sh (lock-step STATUS_REG 0 vs 1 incl. CONTROL_STATUS_COPY 1 / WREG 1 /
WFALL 1 = the kv3_io_cor ring form, 8 phases, 4 mutants caught).
Default TYPES = every KV type with landing_control_status_copy and no landing_status_reg (the same ring form; kv3_io_ft and
kv3_sys_SD have no routed row yet, so they get the form by construction).  Only those keys change (asserted).

usage (repo root): event.py PLAN_IN PLAN_OUT [--types a,b,...]
"""
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "tools" / "die_plan"))

DEFAULT_TYPES = ("kv3_io_cor", "kv3_io_cor_v1", "kv3_sys_SD_v1", "kv3_io_ft", "kv3_sys_SD")


def apply(text, types):
    plan = json.loads(text)
    orig = copy.deepcopy(plan)
    pt = plan["partition_types"]
    changed = []
    for tn in types:
        if tn not in pt:
            raise SystemExit(f"{tn}: not a partition type of this plan")
        t = pt[tn]
        if not t.get("landing_control_status_copy"):
            raise SystemExit(f"{tn}: no landing_control_status_copy (not the ring form this event fixes)")
        if t.get("landing_status_reg") is True:
            continue
        if t.get("landing_status_reg") is not None:
            raise SystemExit(f"{tn}: landing_status_reg already set to {t['landing_status_reg']!r}")
        t["landing_status_reg"] = True
        changed.append(tn)
    for k in plan:
        if k != "partition_types":
            assert plan[k] == orig[k], k
    for tn in pt:
        if tn not in changed:
            assert pt[tn] == orig["partition_types"][tn], tn
        else:
            assert {k: v for k, v in pt[tn].items() if k != "landing_status_reg"} == orig["partition_types"][tn], tn
    out = text
    for tn in changed:
        # splice the changed type object so every other byte stays as it was
        m = re.search(r'^(\s*)"' + re.escape(tn) + r'": ', out, re.M)
        if not m:
            raise SystemExit(f"{tn}: cannot locate the type object in the plan text")
        ind = m.group(1)
        _, j = json.JSONDecoder().raw_decode(out, m.end())
        out = out[:m.end()] + json.dumps(pt[tn], indent=1).replace("\n", "\n" + ind) + out[j:]
    assert json.loads(out) == plan
    return out, changed


def main(argv):
    a, b = argv[0], argv[1]
    types = DEFAULT_TYPES
    if len(argv) > 3 and argv[2] == "--types":
        types = tuple(x for x in argv[3].split(",") if x)
    out, changed = apply(open(a).read(), types)
    try:
        import schema as S
        S.Plan(json.loads(out), Path(a).resolve())
    except ImportError:
        pass
    open(b, "w").write(out)
    print("cland_sreg_1110 applied:", ",".join(changed) or "(none: already set)")


if __name__ == "__main__":
    main(sys.argv[1:])
