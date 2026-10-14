Diagnostic only. Production RTL, constraints, and clock phase were unchanged.
The gate path_classes readback loaded dumped 4_cts.sdc, which contains the plain
166.667ps input/output delays; the flow had applied its numeric die boundary.
Also, rerunning the pin-flop median after hold repair sees12 rather than180
input pin flops and selects q13 rather than the original q87. Exact replay uses
the actual runtime q87 reference and WC=TT/BC=FF, with original90/50ps budgets.
It reproduces setup+1.868ps, hold+8.585ps, regout+6.531ps; actual flow report is
setup+1.868ps/hold+10.05ps. q87 actual clock arrival max416.033/min314.053ps.
These diagnostic files are never sourced by production route or signoff.
