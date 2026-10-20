# Compile condition inventory and legality epoch

No global SYNTHESIS flag is used. Every compiled Verilog source and every
conditional directive is inventoried with exact hashes in the adjacent JSON.

OT_TKM_EXTERNAL_EPOCH_ASSERT disables only the existing generic-rg simulation
q_conv_g[0] && p_v assertion, which otherwise fires on arbitrary power-up state
before any clear can arrive. The actual-parent bench re-enables this exact
property after observing the causal first clear capture, checks all320kept
selector copies on both declared clear edges, and retains precontract trace.
Parameter/shape admission checks remain compiled. The bench itself refuses
anything other than KMAX64/TP192/FAN32=1. This is an observer epoch, not a warm
mask for DUT output checks: actual parent w_v and independent golden determine
which output is legally usable, unchanged from the existing parent bench.

OT_MEM_NO_INIT removes only the SRAM model's artificial initial array-zero
loop. The array and every read/write/spare/repair behavior remain present;
OT_MEM_FAULTS stays off as before. Constructor randreset2 seeds17/1020 make
unreset state and memory independently arbitrary. No black-box selection,
read_liberty cell model or unsupported-parameter bypass is used. rst_relay
supported-parameter checks also remain active. Parent buffer must actually
write data before reading it; early-read/omitted-clear mutants retain the same
independent O/R golden and must produce actual numeric/valid failures.

Logical tile roots are the actual parent tile_clk[t] aliases. Physical source
arrival, skew and setup/hold are not qualified by this RTL scope.
