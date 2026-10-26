#!/usr/bin/env python3
"""PATH-KV 2026-10-26 (ROOT-MERGE-13 rebase of the KV bind-of-record plan onto main): the plan edits the bind branch
carried BEYOND regen_b3 (live_width_cleanup -> explicit_split -> live_width_cleanup), re-applied to a regen_b3 output of
main's plan.  Derived by diffing regen_b3(merge-base plan) against the branch plan (24056abd8 -> 1768d1f6f):
  * partition_types[T].reset.start_role = "bootstrap" (codex/kv-plan-1309 folded bootstrap roles) on exactly the 41
    types T the branch set it on (BOOTSTRAP_TYPES, derived from that diff) -- never by copying branch type bodies;
  * reset.start_port = "mission_start_global", reset.relay_avoid_cores removed (branch reset START source);
  * NOT applied (main wins, SYS3 shoreline packet e055c9ee57 is the approved sys_c): kv3_sys_c (clock/contents/ft_slots/
    internal_stations/reset), die.pg domains, latency L664, lane L747 (branch: sysc 1309 north-channel 8 internal stations).
usage: rebase_extras_0010.py PLAN_IN PLAN_OUT REPORT"""
import json
import sys

START_ROLE = "bootstrap"
BOOTSTRAP_TYPES = ["kv3_hg", "kv3_hg_v1", "kv3_hg_v1p2", "kv3_hg_v1p3", "kv3_hg_v1p4", "kv3_hg_v1p5", "kv3_hg_v1p6", "kv3_hg_v3",
                   "kv3_hgi_v3", "kv3_hgi_v4", "kv3_hgi_v5", "kv3_hgi_v6", "kv3_hgi_v7", "kv3_hgi_v8", "kv3_hroot",
                   "kv3_hub_Ei", "kv3_hub_Eo", "kv3_hub_Wo", "kv3_io_cor", "kv3_io_cor_v1", "kv3_io_ft", "kv3_io_ft_v1",
                   "kv3_pc", "kv3_pc_v1", "kv3_pc_v3", "kv3_pv_v1", "kv3_pv_v12", "kv3_pv_v1n", "kv3_pv_v2", "kv3_pv_v2n",
                   "kv3_pv_v3", "kv3_pv_v3n", "kv3_pv_v4", "kv3_pv_v4n", "kv3_pv_v5", "kv3_pv_v5n", "kv3_pv_v6",
                   "kv3_pv_v6n", "kv3_pv_v7", "kv3_sys_SD", "kv3_sys_SD_v1"]


def main(pin, pout, rep):
    P = json.load(open(pin))
    added = []
    for tn in BOOTSTRAP_TYPES:
        r = P["partition_types"][tn].setdefault("reset", {})
        if "start_role" not in r:
            r["start_role"] = START_ROLE
            added.append(tn)
        elif r["start_role"] != START_ROLE:
            raise SystemExit(f"{tn}: start_role {r['start_role']} != {START_ROLE}; decide explicitly")
    R = P["reset"]
    R["start_port"] = "mission_start_global"
    had_avoid = R.pop("relay_avoid_cores", None)
    json.dump(P, open(pout, "w"), indent=1)
    open(pout, "a").write("\n")
    json.dump(dict(schema="opentallas.kv.rebase_extras.v1", start_role_added=added,
                   reset=dict(start_port="mission_start_global", relay_avoid_cores_removed=had_avoid),
                   main_wins=["kv3_sys_c", "die.pg", "latency.L664", "lanes.L747"]), open(rep, "w"), indent=1)
    print(f"start_role added to {len(added)} types; reset.start_port set")


if __name__ == "__main__":
    main(*sys.argv[1:])
