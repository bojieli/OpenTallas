# TX FF p37 actual GEN and mapping review

Private optional ELA=2 EFF=1 kit 6a2b7eafa28ceea2 generated with backend efbdb61c3b53e172dad36c9d95840c3678aa4cde and frozen source dc98564b80a03d9e73d824af80053810042efd19. Canonical recipe unchanged. Full native parallel-PMA proof establishes +1 logical edge on 3914 compared 544-bit cohorts after qualified warmup; fault remains same edge. HBM-48 books 0.833 ns per traversal, throughput unchanged. This does not establish arbitrary serial/gearbox/physical-pin arrival.

Actual pins and p37 context images were reviewed. The single clock centre exactly matches canonical raw pins, actual plan_pins and io.tcl, and all five p37 coarse entries at (142.584, 103.68) on M5. No macros. Actual mapped OpenROAD count 110078, area 18173.9 um2, utilization 0.330783. Conservative Yosys count 111698; both below 150000/.45 pre-placement budget. Placement, STA, routing and signoff have not run.

Inherited N pin density reaches 10.5 pins/um (above generic 6 guidance) while occupancy is 0.504 pins/track (<.6); 512-bit TX parent context centre distance is 695.3 um, which is not measured endpoint wirelength. Parent geometry/reach adoption remains pending. Face guard PASS1057/1057, port bind missing0 extra0.

Fresh isolated compiler LEC is running on intel2 in unit oth-ubuntu-2265993-1793976564, exact container txff-p37-lec-2265993, cap48GB/4 CPUs. Read-only actual generated kit and actual mapped netlist are inputs; separate output is /srv/opentallas-scratch2/claude/codex-tx-ff-p37-1106/lec_isolated. No verdict is claimed here. Bulk netlist/checkpoints remain in the preserved generated kit.
