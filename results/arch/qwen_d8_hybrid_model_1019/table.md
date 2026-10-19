| Lane | W | Direct FF bits | Gated FF bits | Proposed choice | Macros |
| --- | ---: | ---: | ---: | --- | ---: |
| dvs_W5.ag_wo -> tt_ctlm.ag5 | 10 | 184 | 312 | FF pointer ring | 0 |
| dvs_W5.dd_wo -> native59.dd_i | 548 | 5740 | 10444 | dual-clock SRAM | 9 |
| dvs_W5.ss_wo -> tt_ctlm.ss5 | 107 | 1183 | 2135 | FF pointer ring | 0 |
| io_collective.cmd_free -> sys_face.io_cmd_free | 1 | 103 | 159 | FF pointer ring | 0 |
| io_collective.fault -> sys_face.io_fault | 1 | 103 | 159 | FF pointer ring | 0 |
| io_collective.shared_fault -> sys_face.io_shared_fault | 1 | 103 | 159 | FF pointer ring | 0 |
| native59.dr_o -> dvs_W5.dr_wi | 520 | 5446 | 9910 | dual-clock SRAM | 9 |
| tt_ctlm.cmd -> dvs_W5.cmd_wi | 116 | 1285 | 2317 | FF pointer ring | 0 |
| tt_ctlm.hr -> dvs_W5.hr_wi | 453 | 4759 | 8655 | dual-clock SRAM | 8 |
