# Actual FF census negative-path qualification

Two actual ASAP7 FF DFFHQNx1 cells, launch/QN -> capture/D, capture/QN -> output. Ideal shared clk,833ps period,25ps hold uncertainty,10ps transition, no clock skew, no wire parasitics. Topology rendered and viewed before STA. No production graph or physical adoption.

OpenROAD actual path report: launch ctoq32.89291ps, capture hold10.60880ps plus25ps uncertainty gives slack-2.715894ps. Canonical output hold census returns MEASURED n1, worst_ps/TNS=-2.715894, margin_n1. Actual timing-path metrics deliberately corrupted through a narrow get_property wrapper to NaN/empty/unavailable each produce explicit error, not PASS.

Final unit oth-ubuntu-1563558-1792961236 EXIT0. Earlier positive-skew50 diagnostic unit1542995 EXIT0 n1/-52.715893 retained; final zero-skew is the minimal fixture. First linked-netlist attempt unit1518424 EXIT1 lacked technology LEF before STA, fixed by loading actual ASAP7 tech+standard LEFs. An initial admission command using --hosts epyc1 was NOT RUN because hub fleet names itself localhost; corrected exacthost localhost, no inherited work touched.
