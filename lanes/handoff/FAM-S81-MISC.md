# FAM-S81-MISC handoff (2026-11-21 ~12:05 PST) - STOOD DOWN at ~310k context; successor needed: FAM-S81-MISC-R2

Family (10 unsigned S81 types): s81sl_kv_leaf t1..t5, gunit__t1, iqf__t1, seqhost__t1, eng__t1, phy__t1. No sub-family >= 10.
Hub rows posted via bin/post.sh FAM-S81-MISC (see lanes/posts). Private work dir: epyc10 /srv/opentallas-scratch2/claude/fam-s81-misc/ (clone/ = lane clone, branch fam-s81-misc-ea-relay, already pushed to main).

## kv_leaf t5 (representative)
- Baseline kit: autopilot 58679f87d907 (epyc9, goal route, J5 plan 224567138ab); placed 23:46 (572,843 um2, 335k cells, worst setup -273 at place). Route result NOT read yet (waiter ot-wait 1768776 on intel2 was armed; read ~/.local/state/ot-status / autopilot jobs/58679f87d907).
- Slit rows (FABLE-VISUAL-0030 cause 6): lanes/handoff/FAM-S81-MISC-t5-slit-rows.json (16 hard_cores origin_um rows, dxA -43.2, dxB -25.92, y pitch 155.52 from 17.28) + FAM-S81-MISC-t5-tap-rows.json (4 added taps re-sited: clk_t29,t31,t32,t35).
- Private gate on J5+rows (candMISC1, unit oth-ubuntu-102429-1795254918): BIND 0, LATCHECK 873/873, LAT diff 0, PRE PASS, G0 89 = 87 inherited + 2 NEW on t5: (a) ft0 slot 277 station sites over g_ln[9] (ft0 regs_um run in the strip x 51-95 just west of column A; do not move column A west), (b) KITFIT-OUTLINE g_ln[10] at x 0.108 < kit CORE_AREA x 4.32. => rows NOT foldable as posted. S81-J6-ASSEMBLY-R2 told not to take them.
- Re-solve in flight: var.py variants v1 (A -34.56/B -25.92), v2 (A -17.28/B -25.92), v3 (A 0/B -25.92), each writes var_<n>.json + g0_<n>/g0_report.json in the work dir (G0 on the 85 MB plan takes >15 min, not seconds). Unit chain: bash bnm0s5zjz output (harness task) / pgrep var.py on epyc10. Pick the variant with 0 new t5 G0 findings; if none, move ft0 regs_um instead. Then: tree s81-j6/candMISC1 (mk_tree.sh) + gate.sh candMISC1 via ot-run --priority plan --plan-job bind; then private t5 kit at normal priority (ot-run refuses plan priority for kits; copy the 58679f87d907 gen dir + row patches, diff -rq, never hand-build env); hand rows to S81-J6-ASSEMBLY-R2 for J7 only after the gate is clean.

## kv_leaf t2 split (COORD ACCEPTED the cut)
- Cut x=1693: part A = west 0-1693 (u_lf band + glue, same band as t5, 335k cells measured), part B = east 1693-4328 (183 SRAM macros, store). 0 macros straddle. S81-J6-ASSEMBLY-R2 owns the die-level re-partition for J7.
- Part-B synth census job: epyc10 unit started by `ot-run ... bash censusB.sh` (harness task bx31etbpf), script fam-s81-misc/censusB.sh, result fam-s81-misc/censusB/out.txt + yosys.log. Synthesizes module ot_s81sl_kv_leaf (instance u_g_kv_u_kv, params CNIK 1 CNIK_MUT 0 CP 1 CP_MUT 0 HARD_RQ 0) with SRAMs as black boxes, `synth -run begin:fine` + stat (generic gate count, an estimate, not the ORFS ASAP7 count). If it exceeds ~400k generic cells, part B needs a second cut.
- t2 rows were cancelled by FLEET-WATCH-R4 as REDESIGN (yosys hung 12-16 h, attempts 2/4 too).

## gunit__t1
- lanes/handoff/FAM-S81-MISC-gunit-j7-delta.json (1 op): clock.landing_reader_start, share_trunk, depth 14, from reach_rules.py fix --rules 1 on C3d plan 2ea6cd2f. R-REACH-1 start_reach 2,815 um -> 0 errors after. Needs bind + G0 + LATCHECK (+14 START control cycles, data 0). Monitor pin 297.6 um (2.4 margin).

## phy__t1
- Cause: bank epoch input .ea(rst_n) = raw arst_n over 4.3 mm to u_bout_hbmrd_o*/eq D (place setup -2,585 ps). Plan already had the TAIL-1118 port_relays (cbr0-7). Fix = tool, on main 4ad784e4086 (reset_port_relays: relayed bank ea follows its relay; 0 cycles, 0 flops). Needs a fresh J6-bound gen on the refreshed rt (J7 apply owner); not measured yet.

## iqf / seqhost / eng
- iqf, seqhost: place WNS ~ -1040/-1015, worst = reset flop -> monitor arm 2.3/1.7 mm; J6 monitor-home brings them to 30.8/58.9 um (0 over 300 in C3c/C3d); plus 2-stage reset relay per bank. No own row. eng: nothing failing, routing since 16:06.

## Rules reminders
No rm; ot-delete only; kill exact PIDs; coord changes only via bin/coord-commit.sh / bin/post.sh; heavy only via ot-run; ot-wait waiters with run_in_background.

## Update 12:1x: census run 1 (censusB.sh) failed at hierarchy (ot_s81sl_cmp_pool missing: only 4 rtl files read). Rerun = censusB2.sh (reads every rtl/*.sv + *_bb.v of the t2 kit), result fam-s81-misc/censusB/out.txt and yosys.log (harness task b587gvo10, OT_LANE FAM-S81-MISC). Read it first; if hierarchy still fails, add the missing module file and rerun.

## Update 12:2x: censusB2.sh also failed (shell mangled the file list). Current run = censusB3.sh (loop-built yosys script), result fam-s81-misc/censusB/out3.txt + yosys3.log (harness task b43p84q7q). Read it first.

## Update 12:3x CORRECTION (t5 variants): var.py v1 did NOT produce a G0 report: check.py wrote no g0_v1/g0_report.json (var.py crashed with FileNotFoundError after check.py; it never printed check.py stderr). The v1 plan var_v1.json (85 MB) exists. The shell loop (pid 2826475 on epyc10) is still on v2/v3 with the same bug: kill exact PIDs after a cmdline check, then fix var.py to print r.stderr / r.returncode of check.py (likely needs the gate.sh flags and the tools-tree env: gate.sh runs check.py from the candMISC1 tree with OT_RT_CURRENT exported and rt_pin --export), and rerun v1 first.
