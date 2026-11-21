# OPUS-FIX-S81-BKSEL-R4 (11-20 18:5x PST): u_c A3P sign-off, bk_sel__t2 placed hops, OT_BKSEL_L4 RTL links

Predecessor: lanes/handoff/OPUS-FIX-S81-BKSEL-R3.md (rows, u_c TKR). Consumer: S81-J6-ASSEMBLY (cut 11-21 13:00).
Lane dir epyc7 `/srv/opentallas-scratch2/claude/opus-fix-s81-bksel-r4` (repo = lane clone, branch claude/opus-fix-s81-bksel-r4);
hub `~/opus-fix-s81-bksel-r4` (ot-run client logs). R3 jobs still log in hub `~/opus-fix-s81-bksel-r3`.

## 1. u_c A3P (rfda3pt) -- SIGNED, view on main cb8972158c
R-MINIMAL SIGNED 03:44 UTC: DRC 0, TT -2.87, FF hold +11.38, LEC EQUIVALENT, PIN_AUDIT 5513/5513 (R3 lane dir
ucore/dsdv_bksel_c_rfda3pt/signoff/signoff.json). Spooled on epyc7 for AUTO-EXPORT (spool 17ca282c4edd85e8.json; the hub drain
does AGIdock + rtx-pro). View physical/die_plan/s81/cores/views/bksel_c_a3pt_1120/dsdv_bksel_c (export_view.py, complete).
J6 row: hard_cores u_bk_sel.u_sel.u_c lef/lib -> that view.

## 2. Placed hop max -- waiting
R3 geom_r3a (status otrun-tolerant-swine-2592551) and gen_r3b (otrun-tolerant-swine-2645833) queued on epyc7 memory.
Then: pilot_r3b run_kit.sh place 48 16, geom_check.sh, r2r scan (fable-fix-s81-bksel-r2/r2r.py geom.tsv 300 70).

## 3. OT_BKSEL_L4 (RTL, inert unless defined) -- written (lane clone working tree, diff ../l4_rtl.diff), proof PASS, bench queued
Files: rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_sel.sv (dsdv_bk_rrd + per-core relays u_rst_relay_q/c/g),
physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_l20s.sv (vmtx: u_rst_relay_tx, u_lpd, u_dsp, u_fsp; helpers
dsdv_bk_lpd / dsdv_bk_fsp / dsdv_bk_dsp). Both files define the OT_BKSEL_L4 macro defaults.
- RRD 6: every hard core gets its own 6-flop reset relay; core reset release +6 cycles (all 7 equal).
- LPS 4: loop lane lp_q -> u_vm.i_l +4 edges (compiler: vmux LAT_L +4).
- DSP 3: dst/lpe load 3 edges later, routing unchanged (first lo >= CTL + 4); window beat -> sticky dwf into the fault ring.
- FSP 3: tx_st[0] | dwf -> fq +3 edges.
Proof proof_l4/ (yosys sat -tempinduct, l4_miter.sv): ok SUCCESS; mutw (OT_BKSEL_MUT_DSPW) FAIL, muts (3-stage loop) FAIL.
Bench bench_l4.sh (hub bench_l4.otrun.log): sel a3p/l4 PASS + l4rrdm (OT_BKSEL_MUT_RRD) FAIL wanted; vmtx seqhost bk bench base/L4.
Rows rows_l4.json (rows_l4.py): 2,024 relay_sites keys + verilog_defines += OT_BKSEL_L4.
Private bind mk_tree_r4.sh (tree_r4 = cp -al of R3 tree_r3b + 2 RTL files + plan_r4) -> build_r4 (hub build_r4.otrun.log).
