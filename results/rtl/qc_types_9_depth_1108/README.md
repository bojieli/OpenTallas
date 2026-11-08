# QC-TYPES-9/DEPTH 11-08: logic-depth class fixes

## native59: formatter seat decode predecoded (SEAT_HT), exact

Failure: kw26 native59 a5 G2 TT setup -62.21 ps. Path u_formatter.genblk1.g_safe.di[3][54] -> word_data[45], 16 levels.
The path is di/dv -> 8-bit di==seat compare (NAND2/OR4/OR3/AND5 shared partial decodes, fanout 10-11, ~214 ps)
-> hits -> err[3] (seen / multi-hit over 256 seats) -> word_data capture enable (52-fanout buffer) -> D.
TNS -13255.78 ps, so at least 213 endpoints (TNS/WNS). The other two listed misses (-3.37 / -4.81) are
in2reg landing rings (cal_image_ready / control_stores_ready), not this class.

Cause: native59 runs the formatter with LOCAL_CTL=0 (SVC_LOCAL32=0 in u_core), so it gets the g_safe comparator
decode, not the predecoded g_safe32 form.

Fix: new formatter parameter SEAT_HT (default 0 = unchanged for every other user). The g_safe_ht branch
(SAFE!=0, LOCAL_CTL==0, SEAT_HT!=0) registers ht[seg][lane] = (we_q[lane] && ix[7:4]==seg) ? onehot(ix[3:0]) : 0
at the edge that captured di/dv. Then hits[seat][lane] = ht[seat/16][lane][seat%16], which equals dv && di==seat on
every edge (reset 0 == 0). di/dv are not built. qfd_native59_svc_obs1 passes .SEAT_HT(1); with LOCAL32=1 it is
ignored. PIN CYCLES 0. 0 added edges.

Proof (yosys from openroad/orfs:latest on epyc4): gold = formatter at main 3101f800 (SAFE 2, LOCAL_CTL 0), gate =
new SEAT_HT 1. Flow: proc; flatten; async2sync; equiv_make; equiv_simple -seq 2; equiv_induct -seq 2;
equiv_status -assert.
- real: 9410 of 9410 $equiv cells proven, RC=0.
- mutant (one-hot shifted, ixm[3:0]^1 in ht only; mut.diff): 2305 unproven, RC=1 (caught).

Shares the module: ot_qfd_su_kv_static_posted is also used by qfd_native59_compute_service / _svc / _dv_service.
Those keep SEAT_HT 0, so their RTL is unchanged in effect. qfd_native59_svc_obs1 is only under
qfd_native59_dv_headprep_obs1, so on QC only native59 changes.

## tt_ctlm: diagnosis only (fix proposed, not built)

Failure: kw24 tt_ctlm a9 G2 TT -278.65 ps. Path u_gi.u_cal.g_fifo[2].u_fifo rd_out[254] (SRAM access 380 ps) ->
4:1 rs select (AND/AO21 x4) -> fq_word source select -> FIREDQ subtract dq = tcount + 1 - ht (ripple AO21/XOR from
synth -noabc $alu) -> u_7000 (dq FF). 25 levels, period 773 ps.

The master is the frozen HP13 generated netlist qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1 (bmath cells, hash
pinned in tools/qwen_split/headprep_source.py). Its u_cal predates CALREG.

Proposed fix: the existing CALREG[0] FQREG form (rtl/qwen_dv/headprep37/qfd_dv_cmd_cal_mu_head37.sv g_ring). It is
an 8-entry flop ring plus a registered next head nx_q, so a pop loads the head from a register. It removes the
SRAM and the source mux from the FIREDQ cone. It is edge-identical (calr_port lockstep 0 mismatched edges), and
T_0 / the image are unchanged. Head37 records this as the class of "FIFO SRAM -> FIREDQ -780 ps".

Applying it means regenerating native32 + cpub39_1/_2 through the HP13 REPRO pipeline: full_generic_hp13.ys with
the FQREG cal, then construct_hp13_2.py, then hp13_corepub39 generate.py. Then re-pin headprep_source /
headprep_corepub_source and rerun the realcalendar_native lockstep and the HP13 head bench with mutants. That is
more than this 2-h slot. Keep CALREG[1] STARTREG off: it adds 1 edge.
