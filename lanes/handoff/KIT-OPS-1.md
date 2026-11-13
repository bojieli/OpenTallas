# KIT-OPS-1 handoff (kit-wave operations lane; COORD is the coordinator) -- 2026-11-12 21:39 PST

## Done (RESULT posted for each)
- (a), (b), (d) done earlier; see the queue. Live kit_wave.py = main 21bad708b185.
- (c) HEAD rp18 armed 19:57 + 4 types added 20:27 (hd_serdes, hd_ctl_n, hd_mesh, hd_st_str).
- (f) HEAD rp18r1 21:3x: wave plan epyc8 (+4 gen hosts) kit-ops-1/head_rp18r1/prep/source_plan_wave.json 0f32a32a3ea8 = r1 prepared plan with sink_bins paths -> head_rp18c/prep/assets (byte-identical), so only 6 blocks change. 21:37 launches: hd_tile, hd_turn_a, hd_spn_end, hd_spn_eshim_rx, hd_spn_wshim_tx. Revert = s81_head.prev_kitops1_rp18r1.
  hd_spn HELD: r1 export picks u_rrl_147, which is already the FLOW-6 reader raw export pair; waiting on HEAD-96 r2. To release on r2: re-run run_head_rp18r1.sh as a new dir, make source_plan_wave.json the same way, probe (head_cmp/probe.py) to confirm only intended blocks change, stage + manifest, switch plan, drop the hd_spn hold.
  4 rp18 HEAD route jobs CRASHed with DRT-0255 maze route (turn_a, turn_b, wshim_rx, wshim_tx): reported to COORD as a HEAD routing class.

## In progress: (e) S81 ready12b-A
- src epyc8 kw45/src_s81_main_7073a6b4a5 = archive of main 7073a6b4a599 + KITOPS1_OVERLAY.txt (plan_r12bA6/plan_h2_2249 = event plan 18c864518844; dead-input proof from origin/claude/s81-dead-reprove2-1112@8fa82e457d, not in main).
- strict bind rc 0 -> kit-ops-1/s81_r12bA/out_main_7073a6b4a5_b (bound .sv identical to out_r12bA_dst after normalization). asbuilt kit-ops-1/s81_r12bA/asbuilt_kitops1_7073a6b4a5.json (base -> archive).
- out + asbuilt staged to epyc7/9/intel1/epyc2. src copies running: epyc7 (orphan rsync pid 3799005 on epyc8) and stage_s81src_{e9,i1,e2}.out.
- Next: manifest the src on 5 hosts (manifest2.sh), then on intel2: python3 -I /tmp/kitops1_s81_switch.py STAMP 7073a6b4a599c1de9e041896421b3b779045df1d <src> <out_b> <asbuilt>. The script is scratchpad s81_r12bA_switch.py; it needs /tmp/kitops1_s81_{tb_new,sets}.json and plan_sha. Then coord-commit, verify on origin, count S81 LAUNCH lines, post the RESULT.
- Open asks to COORD: train 8fa82e457d; the 4 in-flight old-RTL rows of the 71 (c3x_C__t1, leaf__t34, leaf__t61, kv512_C__t1).
