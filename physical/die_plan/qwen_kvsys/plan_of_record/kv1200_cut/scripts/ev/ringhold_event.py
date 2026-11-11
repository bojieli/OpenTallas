#!/usr/bin/env python3
"""DIE-KV-97 11-10 cland_sreg_1110 step 2 (hold half, on top of event.py): per-receiver ring_hold sender min for the
three relaunch types, so each relaunches ONCE with both fixes (COORD 11-10).

Class (routed FF sign-off, kv3_io_cor a8 / kv3_io_cor_v1 a9): the hold misses on the ring input ports
(ft*_i, i_host_fdi, cland_fstart_in_* -> ring s_d / sd_c / g_wreg.fs_q, falling-edge writer) are the KV-PLAN-2 RINGHOLD
class: plan clock.ring_hold.sender_ps -385 puts the input min at 31.5 ps after the capture fall at the port, and the
receiver's own fclk_in tree adds 87-120 ps before the capture flop (e.g. io_cor ft17_i[485] -68.9, io_cor_v1 ft23_i
-119.1).  PLAN-GEN-RULES rule A does not reach these ports by design (ring ports are timed against the forwarded fclk,
not vclk); rule A / AT on these three types is a no-op (checked: 0 types, 0 cores, plan bytes unchanged).
Form: KV-PLAN-2 form A, clock.ring_hold.sender_ps_types {receiver: ps} (tool on main 17002ccba5e, landing_contract.
ring_sender_ps): the sender's fclk_out leaves from the launching clk leaf, so the sender insertion cancels and the real
sender data-vs-fclk min is >= 0; KV-PLAN-2 measured worst +10.55 ps FF, minus 60 ps die-level tap-skew allowance = -50.
No RTL / pin / outline / cycle change; the real seam stays a parent obligation (io_hold NEEDS_PARENT).

usage (repo root, a tree with 17002ccba5e): ringhold_event.py PLAN_IN PLAN_OUT [--ps -50] [--types a,b]
"""
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "tools" / "die_plan"))

TYPES = ("kv3_io_cor", "kv3_io_cor_v1", "kv3_sys_SD_v1")
PS = -50.0


def apply(text, types=TYPES, ps=PS):
    plan = json.loads(text)
    orig = copy.deepcopy(plan)
    rh = plan.get("clock", {}).get("ring_hold")
    if rh is None:
        raise SystemExit("plan has no clock.ring_hold (nothing to override)")
    per = rh.setdefault("sender_ps_types", {})
    for tn in types:
        if tn not in plan["partition_types"]:
            raise SystemExit(f"{tn}: not a partition type")
        if tn in per and float(per[tn]) != ps:
            raise SystemExit(f"{tn}: sender_ps_types already {per[tn]}")
        per[tn] = ps
    for k in plan:
        if k != "clock":
            assert plan[k] == orig[k], k
    assert {k: v for k, v in plan["clock"].items() if k != "ring_hold"} == {k: v for k, v in orig["clock"].items()
                                                                              if k != "ring_hold"}
    assert {k: v for k, v in rh.items() if k != "sender_ps_types"} == {k: v for k, v in orig["clock"]["ring_hold"].items()
                                                                       if k != "sender_ps_types"}
    m = re.search(r'^(\s*)"ring_hold": ', text, re.M)
    if not m:
        raise SystemExit("cannot locate clock.ring_hold in the plan text")
    _, j = json.JSONDecoder().raw_decode(text, m.end())
    out = text[:m.end()] + json.dumps(rh, indent=1).replace("\n", "\n" + m.group(1)) + text[j:]
    assert json.loads(out) == plan
    return out


def main(argv):
    a, b = argv[0], argv[1]
    types, ps = TYPES, PS
    i = 2
    while i < len(argv):
        if argv[i] == "--ps":
            ps = float(argv[i + 1]); i += 2
        elif argv[i] == "--types":
            types = tuple(x for x in argv[i + 1].split(",") if x); i += 2
        else:
            raise SystemExit(f"unknown arg {argv[i]}")
    out = apply(open(a).read(), types, ps)
    import schema as S
    S.Plan(json.loads(out), Path(a).resolve())
    open(b, "w").write(out)
    print("cland_sreg_1110 step 2 ring_hold.sender_ps_types:", {t: ps for t in types})


if __name__ == "__main__":
    main(sys.argv[1:])
