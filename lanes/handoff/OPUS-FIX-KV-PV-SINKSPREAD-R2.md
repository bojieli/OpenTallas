# OPUS-FIX-KV-PV-SINKSPREAD-R2 handoff (Opus successor of FABLE-FIX-KV-PV-SINKSPREAD; KV pv D29/D30 split form)

Started 2026-11-22 22:35 PST. Predecessor handoff (full method, scripts, facts): lanes/handoff/FABLE-FIX-KV-PV-SINKSPREAD.md (read its
STATE 22:20 block + KEY FINDINGS). Lane root epyc8 /srv/opentallas-scratch2/claude/fable-fix-kv-pv-sinkspread/ (tree tree2 tree3 tree4 w/).
Client logs intel2 ~/tmp/ffkvpv/. Watchers post under the OLD lane name (FABLE-FIX-KV-PV-SINKSPREAD): that is fine, they are mine now.

## Jobs adopted (never duplicate)
- K2 sealed kit kv3_pv_v6n (tree/, plan v6n6v1 33c08323086f, goal route, rt 0890cc9405b7): unit runitem-kv3_pv_v6n on intel2,
  log ~/tmp/ffkvpv/runitem_v6n_k2.log, watcher watch_k2.sh. place rc 0 22:2x, geom running.
  kit epyc8 .../kit-wave/qwen_kvsys/KV-D27d3/private/FABLE-FIX-KV-PV-SINKSPREAD/kv3_pv_v6n_1122181338/gen/kv3_pv_v6n
  spec intel2 ~/coord/autopilot/private_specs/FABLE-FIX-KV-PV-SINKSPREAD/qwen_kvsys_kv3_pv_v6n_1122181350/
  Census at place (w/v6ntaps): 139,670 tap-net regs vs 50,235 plan bins; 42/91 taps over 1000, worst 15,018. Kit keeps 91 taps
  (cap pass re-homes); watch CTS/hold cost. Cancel only on setup < -300 / flat repair / functional bug.
- K3 sealed kit kv3_pv_v12 w piece (tree2, plan 9d9579bd19c9, goal route): unit runitem-kv3_pv_v12, log runitem_v12.log, watcher
  watch_v12.sh. Spec .../qwen_kvsys_kv3_pv_v12_1122220711. DO NOT TOUCH tree2 while it runs.

## Started by me
- K4 lever WITHDRAWN 23:1x (COORD disk URGENT: epyc8 99 GB free). tree4 fork was 156 GB. Unit oth-ubuntu-602244-1795417489 cancelled.
  ot-delete: clone (7) done, tree3 (50) running, tree4 (156) refused by the 07:00Z guard list (captured while chain live): retry loop
  epyc8 <lane>/tmp/del4.sh (log tmp/del_tree4.log, DEL4_END line). Census taps (w/v6ntaps) fold into D30 row B. New forks: intel1/epyc7 only.

## Holding / owed
- Row B (14-type split) = D30. When KV-PLAN-R6 posts the D29 SEAL tree: ot-tree-fork it, base as plan_of_record.base_d28 form,
  re-export lane ref (w/refexp.sh), FF_BASEPLAN = D29 seal plan, w/chain_full3.sh. Carry FIX-SYNC reset f8571aa7760a relay_depth
  rows onto split pieces of v1 v12 v5 v5n v7 (+v3n): FIX-SYNC-KVHEAD (agent a5f88a0259125a0e0) offered the solve: ask it.
  Each of the 28 pieces also needs a census tap row (bins undercount ~3x).
- D29 row 4 = my V3TAPS (ed71a9739295), IN.
- FAIL-CLASS 91fe7a21a9: not mine (routed away).
- Cleanup later (ot-delete): epyc8 <lane>/clone, tree3 after D29 seals, tree2 dirs per predecessor list.

## Log
- 22:35 RESUMED posted. K4 launched.
- 23:1x VIS-KV (agent a87a6c2a4a7f2997b) report on K2 geom: (A) astk_W pad delay line 87k flops = x510-545 column -> D30: move
  i_astk_W_p_2 E window y560-790, fork (520,700), tails in channels; FIFO (ot_meso_fifo) form raised with KV-PLAN-R6. (B) cut legs
  need stations o_pvw__u_TNQN_N_rN_b_d2_p +3, o_pvw__u_ctl_cmd_p +4 (regs_um in VIS-KV msg; scripts epyc8 vis-kv/tmp/pv/). (C) cut bus
  widths from bind (4,028 dead/over-wide E pins). All three -> D30 row B. LOOK-BEFORE-LAUNCH: no pv relaunch w/o placed probe PROBE-PASS.
- 23:2x VIS-KV family report (13 renders, cov files rtx-pro scratchpad viskv/): D30 row B scope widened: channel >=200 um (trunk out of
  pad column), cland->bin stations/bins near landing, census tap grid cap 1200 + fclk slg leaves split 4+, outliers (pv/v8 N-only pins,
  v4/v4n SW blob, v12/v7 S face). FIFO (ot_meso_fifo) for pad chains ASKED to KV-PLAN-R6 (post 23:2x).
- Disk: tree3 deleted (50 GB), clone deleted (7); tree4 pending guard list 07:30Z rebuild (del4.sh loop).
- 23:4x DISK DONE: tree4 deleted 07:31Z (156.7), total 213 GB freed; epyc8 scratch2 321 GB free. Lane dir = tree, tree2, w (+small).
- Watchers: old watch_k2.sh EXITED on the intermediate result.json (stage chain_probe PASS) -> replaced by watch_k2b.sh (systemd
  user unit watch-k2b-r3) and watch_v12b.sh (unit watch-v12b-r3; old pid 4099926 killed), both skip stage chain_probe. Same state files.
- K2 at CTS (chain goal route attempt 1, 22:41). K3 past gen_lint.
- 01:3x RESUMED after the 5-h limit. K2 CTS runs SPILLED on epyc9 (kit path same on epyc9; files go back to epyc8): tap spread 375 ps.
  K3 in place since 23:44. D30 probe must meet full-cause PROBE-PASS (hub fe8a2a5: whole-type hotspot census, total ovfl <10% base).

## STATE 11-23 02:0x PST (newest; read first) -- COORD 6079af4: D29 = ONE comprehensive KV event, cut 14:00, rows by ~13:00
- Row B now goes INTO D29 (not D30), composed on KV-PLAN-R6's D29 work-tree plan b07a614e4d04 (kw45/src_kv_d29_work_r6, epyc8).
  ASK posted 01:5x to KV-PLAN-R6 (post-compose row form; veto window 30 min).
- epyc7 lane root /srv/opentallas-scratch2/claude/fable-fix-kv-pv-sinkspread: w/ (rsync of epyc8 w/ minus gates/refbind/k4/v3row),
  base_d28_root. tree5 = ot-tree-fork of the D29 work tree (intel2 ~/tmp/ffkvpv/fork_tree5.log).
- Launcher intel2 ~/tmp/ffkvpv/d29b_launch.sh (log d29b_launch.log): after fork OK -> ot-run plan job on epyc7: w/d29b_chain.sh b1 =
  refexp5.sh (lane ref w/ref_base_d29.json from the unsplit D29 bind; moves tree5 plan_of_record -> plan_of_record.base_d28) ->
  chain_full3.sh b1 tree5 <14 types :r1> with FF_LANEREF, FF_BASEPLAN = sealed D28 plan (epyc7 replica), FF_REMAP_OLD = D29 base.
  Gates on epyc7 w/gates/b1*. Composed dir tree5/.../por_d29_all_b1_composed.
- epyc7 w/ changes: gate_bind.sh skips the gatein (deleted) R8 side checks; multi.sh uses fix_bit_sites2.py (also internal_stations
  bit sites + 0.054x0.27 grid + self-check) and runs tools/die_plan/place_precheck.py on all pieces (VIS-KV rc129 ask);
  chain_full3 FF_LANEREF overridable; remap_untouched FF_REMAP_OLD.
- To add on b1 (iteration 2): v6n census taps (w/v6ntaps on epyc8), VIS-KV C (cut bus widths from bind), B (cut-leg stations),
  A-min (astk_W window y560-790) and the channel-widen variant; FIX-SYNC relay_depth LAST on split pieces (ask FIX-SYNC with paths).
- Answered FIX-KV-PV-MESOFIFO (pad FIFO lane, ae1b569fcc8e401ce) 01:5x. VIS-KV wants v6n/v12 renders + ledger rows.
