HBM-REFORM-B9 part 27 log-depth lgroup2 form (rtl/.../reform_1105s/opstore/ot_hgi_su_lgroup2_lf.sv) vs ot_hgi_su_lgroup2 (lg2_orig.sv = copy of
rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv module at 3d13a31480), tile params N16 M16 LWB15 AW24 NLW0 NS8, banks replaced by lbank_fake.sv
(registers every bank input and exposes them on rd, so rd observes both read and write selects).
tb_lg2.sv: 200k-cycle random lock-step, reset every 64 cycles, address locality modes for hits and collisions:
  verilator --binary --top-module tb tb_lg2.sv gold_top.sv gate_top.sv lbank_fake.sv lg2_orig.sv <lf.sv>
  form: LG2 LOCKSTEP PASS errs=0; mutant (lowest stage lane wins instead of highest): FAIL errs=20674.
eq.ys: yosys equiv_simple/equiv_induct (447 rd bits proved, long tail not finished in 30 min).
