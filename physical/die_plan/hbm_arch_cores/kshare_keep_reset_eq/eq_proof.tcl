# DIE-HBM-97/KSHARE EQ proof: RTL (gold, no keep, no merge) vs the kept-reset synthesis (gate: OT_KEEP_WIRES=reset_pipe
# hook as in the kit ot_keep_regs.tcl, then synth -flatten -noabc -nofsm, which runs the opt_merge that folded the syncs in vK).
# -nofsm: FSM re-encoding is orthogonal to the keep change (lec.py on the kit covers the flow netlist); without it the
# state registers keep their RTL names and the name-matched proof is decided by equiv_simple / equiv_induct.
set R /work/rtl
set F "$R/ot_hbm_svc_async_fifo.sv $R/ot_hbm_svc_pc_ctrl_leaf.sv $R/ot_hbm_svc_ring_h9b_ff.sv $R/ot_hbm_svc_vm_kshare_splitstrap.sv $R/ot_reset_sync.sv"
set T ot_hbm_svc_vm_kshare_splitstrap
yosys read_verilog -sv -DSYNTHESIS {*}$F
yosys hierarchy -check -top $T -chparam KRL1 1
yosys proc
yosys flatten
yosys memory
yosys opt_clean
yosys rename $T gold
yosys design -stash gold
yosys read_verilog -sv -DSYNTHESIS {*}$F
yosys hierarchy -check -top $T -chparam KRL1 1
source /eq/keep_hook.tcl
yosys synth -flatten -top $T -noabc -nofsm
yosys opt_clean
yosys tee -o /eq/eq_gate_rp.txt select -count w:*reset_pipe* %ci1 t:\$_*DFF* %i
yosys rename $T gate
yosys design -stash gate
yosys design -copy-from gold -as gold gold
yosys design -copy-from gate -as gate gate
yosys async2sync
yosys equiv_make gold gate equiv
yosys hierarchy -top equiv
yosys equiv_struct
yosys equiv_simple
yosys equiv_induct -seq 1
yosys tee -o /eq/eq_status.txt equiv_status
yosys equiv_status -assert
puts "EQ_PROOF EQUIVALENT"
