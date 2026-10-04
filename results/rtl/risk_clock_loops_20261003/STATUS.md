# STATUS: control-loop clock ceiling (2026-10-03). The session hit its usage limit; detached jobs are still running.

## Collect the following (Codex or the next session)
1. **Qwen screens on ot-pve1** (`~/rcl-20261003/runs/qwen/`):
   - `spine_fi0_833`, `spine_fi1_833`, `spine_fi0_1111`, `vstream_sw64_1111`: Yosys was still running after 30+ min (vstream about 34 GB).
   - `core_bb_833`, `core_bb_1111`: OpenROAD phase.
   - Copy each `<label>.json` to `screens/qwen/`.
   - For the ME spine, read `phases.rep.focus.issue` and `.addr`. They hold the `ready = !active && !pend` / `j`,`k`,`t`,`cur` loops.
2. **Qwen one-shot collective route** at `ot-pve1:~/rcl-20261003/routes/qwen_oneshot_die_d32_0833/`.
   - Wait for `exit` to contain `corner_rc`.
   - Copy `physical.json` and `corner_sta.json` to `routes/`.
   - In `corner_sta`, use `worst_reg_to_reg_slack_ps`. Its `worst_register_d_slack` also matches combinational pins named D.
3. **DS ROM screens** (finished ones are committed in `screens/ds`; summary script `jobs/ds_sum.py`; still running on agidock: ds01_core_1g2/0g9, ds10_topk_merge, ds09_sel, ds05_vec_n16_full, ds08_idx_ring_port; on pve1: ds02_spine_k6144/k512, ds04_su_adapt, ds11_coll_dma, ds05_vec_bbdp_n64).
   - Locations: `ot-agidock128:~/rcl-20261003/runs/ds/*.json` and `ot-pve1:~/rcl-20261003/runs/ds/*.json`.
   - Launcher: `~/rcl-20261003/jobs/ds_jobs.sh` on both hosts.
   - Copy them to `screens/ds/`.
   - Blocks: core_v41x sequencer (black-boxed units), spine_w17w10, rom_adapt, su_adapt, v41x_vec, sinkhorn_seq, accept (NSLOT=8), idx FIFO/ring port, sel_ctl, coll_topk_merge, coll_dma, oneshot_px, pkg_ctrl_x, hbm_karb, window_refill, q-element ICG enable.
4. **HBM screens.**
   - Location: `ot-agidock128:~/rcl-20261003/runs/hbm*/` and `ot-pve1:~/rcl-20261003/runs/hbm*/`.
   - Launcher: `~/rcl-20261003/jobs/hbm_jobs*.sh`.
   - Copy them to `screens/hbm/`.
   - Blocks: gpu_issue, bulk_copy, stack, rf_service, full_sm_service, scratch_service, rf_visibility_fence(+w6), w2_nc6 quarantine, KV lifecycle, hbm_r14_pc, barrier, router_topk, expert_fetch, nvls_switch, mtp_accept_guarded.
   - Done in the screens (see REPLAY.md): issue, bulk_copy, stack, fence, fence_w6, mtp, kvlife, topk, scratch, barrier.
   - Still running: rfsvc_ack_833, fullsm_ack_833, r14pc_1024/833, w2nc6_833/1024, kvjoined_833 and efetch_nr_833 on agidock; nvls_833/967 on pve1, all under `runs/hbm2/`.
   - Summary script: `jobs/hbm_sum.py hbm2`.
   - The streaming HBM controller already has a routed record on branch `claude/qwen-hbm-sustained-bw-20261003` @ 52ce3e9c1:

     | Period | Result | WNS | fmax |
     |---|---|---|---|
     | 1.024 ns | PASS | +19 ps | — |
     | 0.833 ns | — | -4.7 ps | 1.194 GHz |

     It runs in the HBM service clock, so this is acceptable.
5. **Next routes.** Route the worst one or two genuinely loop-carried paths that the screen fails by more than 150 ps, using the TP-sequencer recipe in `jobs/route_tpseq.sh` (`--orfs-corner WC --hold-corners WC,BC`, 60/25 ps, `ADDER_MAP_FILE=`, `OT_ORFS_NUM_CORES=16`), then run `corner_sta.py`.
   - Route `ot_gpu_issue` (Qwen params) and `ot_gpu_bulk_copy` FIRST: they are the HBM per-token loops at 590-810 MHz.
   - Candidates already known: DS q-element ICG enable (`ot_v41_rom_elem_w10.sv:172-180`, earlier estimate -530 ps) and `ot_coll_topk_merge`.
6. **Memory policy.** Launch every synth through `~/bin/admit.sh <GB> --`. Synths over 5 GB go to ot-pve1 or ot-epyc1tb. agidock ran out of memory once in this session, and the first ME-spine and vstream screens died there.

## Screen-tool caveats
- The ABC mapping depends on the target period: TP sequencer at 1.111 ns screened -18 ps but routed +72 ps.
- Blocks with more than 4,000 ports are placed with `-skip_io`, so only their register-to-register paths count.
- `ot_hdc_vreduce` standalone triggers a Yosys derive assert. It is covered inside vstream.
