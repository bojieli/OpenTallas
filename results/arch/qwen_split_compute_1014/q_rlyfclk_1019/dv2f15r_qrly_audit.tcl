read_db /work/ckpt_grt.odb
source /work/fclk_audit.tcl
array unset ot_die_rep_fclk_old
set f [open /work/pre_insts.txt]; while {[gets $f l] >= 0} { set ot_die_rep_fclk_old($l) 1 }; close $f
puts "SNAP [array size ot_die_rep_fclk_old]"
# fix: GEN-derived forwarded-capture payload contract (tools/qwen_split/fclk_data_ports.py)
source /work/fclk_data_ports.tcl
ot_die_rep_fclk_audit /work/fix.fclk {{n_fck_*}} {{BUFx8_ASAP7_75t_R}}
