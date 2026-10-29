DIE-HEAD-29 OCV model fix (COORD RULING 10-29 10:01), collected Thu Oct 29 10:29:10 AM PDT 2026. Tool change + tests + replays; no merge to main.

CHANGE  tools/die_plan/die_sta_related.py clock_ocv_fn.branch: per tap, a virtual START tap (new is_start_virtual_tap:
        part None AND port '__st__<path>', i.e. virtual_tap / start_stage_emit die-level start flop clock pins outside every
        hard core) carries no hard-core class-B latency (no B.cell_share*core_lat, B stages 0).  Every other tap (core /
        partition taps, and any part-None tap without the '__st__' name) is unchanged, bit for bit.  A virtual -> core pair
        keeps core_lat on the core side only.  Same callable for the planner (count_align_plan.clock_contexts -> ca_ocv)
        and the gate (die_sta_related main / count_align_start_ports): one shared model, no per-die fork, no new flag.
        Verdict logic untouched: missing data delay / missing tap / missing view stays fail closed (UNMEASURED).
TESTS   test_die_sta_start_virtual_ocv.py (5): predicate; virtual-virtual = core_lat-0 pessimism (table + flat) and >10 ps
        below the old charge; core/core and core/part-None-glue pairs bit-identical to the old model; mixed pair strictly
        between; unmeasured / no-tap START ports stay fail closed.  Focused suite (20 files, docker python:3.12):
        new 216 pass / 4 skip; origin/main tools 213 pass / 4 skip / 3 fail (the 3 new delta tests, as expected).  CHECKED.
REPLAYS (base = origin/main c0c65228405 tools, new = this branch; replay_summary.txt, cmp2.py)
        QC  DIE-QC-25 g25 sta_gate (4 signed views): rest of die_sta_related.json identical (only count_aligned/*/start_skew
            rows differ), logs identical; START 538 rows, ok 538 -> 538, 0 flips; min sync TT 79.5 -> 99.5, FF 63.8 -> 84.3.
            base == HEAD-START-4 qc_old byte-identical.
        S81 DIE-S81-17 cabind sta (go15 proof, plan_s11, declared insertion): same form; START 1139 rows, 0 flips;
            min sync TT 80.3 -> 101.0, FF 82.3 -> 97.8.
        KV  DIE-KV-28 sta_E_edge inputs (intel1, 4 signed views, HB4): same form; START 1687 rows, 0 flips;
            min sync TT 115.2 -> 124.4, FF 150.9 -> 166.3.  base == DIE-KV-28 original byte-identical.
        HBM NOT REPLAYED: no die_sta_related run found on intel1/intel2/epyc2 (last 48 h).
        HEAD planner (plan5 spice_edge on proof_r1): 1706/1706 clean both; START interval width median 113.4 -> 28.5 ps,
            skew limit min 97.4 -> 123.7, min sync dist clean 123.9 -> 150.2.
HEAD    gate start-port row on routed proof_r1, v1p plan, V1 measured data delay (probe_dh29.py, probe_*.json):
            1643 ports, 1190 measured 0 FAIL both; 453 unmeasured fail closed both (0 turn PASS).
            spice_cell TT min sync 83.2 -> 130.2 (below 100: 125 -> 0), FF 100.0 -> 135.6
            spice_edge TT 104.3 -> 151.0 (0 -> 0),             FF 111.6 -> 147.2
            OCV setup+hold median TT 112.1 -> 18.8 (cell) / 110.9 -> 17.5 (edge); FF 86.2 -> 14.7 / 85.5 -> 14.0.
        Differs slightly from the HEAD-START-4 probe (129.8): that probe used core_lat=0 but kept nB=max(1,..)=1 B stage.
