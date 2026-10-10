# Qwen fmt3 balanced element clock plan: correct actual routed FF neighbour
# insertion, with H1 sender minimum50ps minus50ps IO uncertainty=0ps.
source /src/physical/common_flow/nbr_clk_measured.sdc
set_output_delay -min 0 -clock nbr_clk [all_outputs]
