# Actual H10 BF source pilot

Selected u_f_0L01, col_h10_l4_lp_asb_x/E2, actual full-field phase106 attn.wo_a, six rows, three BF pairs1/5/10. Native BF family hold and idle-Q source scope remain explicit. Walker returns all six fixture values with zero faults at833ps; expected and observed returns412,415,424,427,428,436. Static programme replay/control gate is separate and still pending; this walker receipt admits no production measurement or full token.

The source guard now checks exact per-module CFG identities: H10 r0/r1/r2/r0_nx=42/35/35/42 (154), H9=35/35/35/35 (140). Three focused tests reject duplicate/missing banks and equal-count wrong partitions. The original H10 fixed140 guard failure is preserved remotely. Fresh retry2 passed source preparation but hit its4GiB memory cgroup; retry3 at8GiB completed exit0. No RTL change, no added cycles, defaults unchanged.

Fleet root epyc2:/srv/opentallas-scratch2/claude/codex-ds-bf-1131. Original h10x and h10x_retry2 failures preserved. Passing h10x_retry3_mem8, unit oth-ubuntu-3505388-1793568204; run_h10_retry3_mem8.sh reuses immutable h10vec. Static/control continuation run_h10_static.sh, intel2 client2218433, /tmp/codex-ds-bf-h10-static.log, unit oth-ubuntu-3733399-1793568795.
