Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
cd /fv/dflt
$Y -q -p "read_verilog -sv gate/ot_hgi_coll_amerge.sv gate/ot_hgi_coll_argmax_static.sv gate/ot_hgi_coll_edge_pr.sv gate/ot_hfd_coll_q3_edge_arg.sv; hierarchy -top ot_hfd_coll_q3_edge_arg; proc; flatten; opt_clean; write_verilog -noattr gate_flat.v" || exit 3
sed "s/g_base\.//g" gate_flat.v > gate_flat_n.v; grep -c "g_base\|g_fp" gate_flat_n.v
cat > eq2.ys <<EOY
read_verilog -sv gold/ot_hgi_coll_amerge.sv gold/ot_hgi_coll_argmax_static.sv gold/ot_hgi_coll_edge_pr.sv gold/ot_hfd_coll_q3_edge_arg.sv
hierarchy -top ot_hfd_coll_q3_edge_arg
proc; flatten; async2sync; opt_clean; rename ot_hfd_coll_q3_edge_arg gold; design -stash gold
read_verilog gate_flat_n.v
hierarchy -top ot_hfd_coll_q3_edge_arg
proc; async2sync; opt_clean; rename ot_hfd_coll_q3_edge_arg gate; design -stash gate
design -copy-from gold -as gold gold; design -copy-from gate -as gate gate
equiv_make gold gate eq; hierarchy -top eq; async2sync; equiv_simple -seq 5; equiv_induct -seq 5; equiv_status -assert
EOY
$Y -q -l eq2.log -s eq2.ys > /dev/null 2>&1; echo rc $?
