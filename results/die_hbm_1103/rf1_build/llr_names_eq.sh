cd /t
for W in 20 137 141 306 400; do
for top in ot_qkvd_llr_replay_sram_leaf old_ot_qkvd_llr_replay_sram_leaf; do
yosys -p "read_verilog -sv -DOT_HBM_RW_MACROS stub.sv new.sv old.sv; chparam -set W $W $top; hierarchy -top $top; proc; tee -o /t/names_${W}_$top.txt select -list t:ot_sram_*" >/dev/null 2>&1; echo "W=$W $top: $(grep -v "^$" /t/names_${W}_$top.txt | tr "\n" " ")"
done
yosys -p "read_verilog -sv -DOT_HBM_RW_MACROS model.sv new.sv old.sv; chparam -set W $W ot_qkvd_llr_replay_sram_leaf old_ot_qkvd_llr_replay_sram_leaf; hierarchy -check; proc; flatten; opt_clean; rename old_ot_qkvd_llr_replay_sram_leaf gold; rename ot_qkvd_llr_replay_sram_leaf gate; async2sync; equiv_make gold gate eq; hierarchy -top eq; equiv_simple -seq 3; equiv_induct -seq 3; equiv_status -assert" 2>&1 | grep -E "Found|proven|unproven|ERROR" | tail -2 | sed "s/^/W=$W equiv: /"
done
