Committed text vs the text the kits were proven on (DIE-HBM-101 check).
gold = proven gate_ok.sv (+ fifo.sv): g0 top ot_wbq_root_s7_g0 (G=0), g1 top ot_wbq_root_g1__fcore (G=1), chparam CBREG=SSTOPREG=1, W=288.
gate = committed rtl/hbm_accel/counted_1109/ot_wbq_root_gX/{ot_wbq_root_s7.sv,ot_wbq_root_s7_rr_fifo.sv}, top ot_wbq_root_gX, chparam CBREG=SSTOPREG=1.
Both with -DOT_WBQ_ROOT_S7_RPIPE and the same SRAM stub (stub.sv). yosys equiv_make -inames, equiv_simple -seq 4, equiv_induct -seq 4, equiv_status -assert.
Result g0 and g1: 25391 compare points, 25391 proven, 0 unproven (logs eq_committed_g{0,1}.log.gz). The committed rr_fifo is byte-identical to the proven fifo.sv.
Not run: a mutant on the committed text (the sensitivity of this flow was shown on v8 with the ordinal8 += 16 mutant, eq_mutant_ordinal8_plus16.log.gz).
