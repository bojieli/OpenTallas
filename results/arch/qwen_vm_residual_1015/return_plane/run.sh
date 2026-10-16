set -eu
src=$1
iverilog -g2012 -s tb_return_plane -o positive "$src/ot_qfd_sp_vector_memory_bv.sv" "$src/tb_return_plane.sv"
vvp positive > positive.log
iverilog -g2012 -s tb_return_plane -Ptb_return_plane.MUT=1 -o mutant "$src/ot_qfd_sp_vector_memory_bv.sv" "$src/tb_return_plane.sv"
if vvp mutant > mutant.log 2>&1; then echo 'Mutant unexpectedly passed'; exit 1; fi
grep 'PASS return plane' positive.log
grep 'FAIL return plane' mutant.log
