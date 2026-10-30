# Current KV native cell census

Seven types now carry complete measured `type.cells` counts, so the estimator does not double-add analytical clock-landing rings. Six existing KV32/b27f synthesis results match the actual current kit RTL wrapper, bound module, complete filelist closure, parameters and stock SYNTHESIS define; the attached closure receipt records that comparison. No new synthesis was launched for those six.

Current SYS_C synthesis contributes147573 native standardcells: actual hierarchy total147579 minus four SRAM, one PHY and one ROM instance. Its current TXDP is03039da9; current frontgates pass and LEC remains live. Cell measurement provides no LEC or physical signoff credit.

| Type | Complete standardcells |
|---|---:|
| kv3_hroot |80413|
| kv3_hub_Ei |289525|
| kv3_io_cor |116471|
| kv3_io_cor_v1 |119885|
| kv3_io_ft |38472|
| kv3_io_ft_v1 |38398|
| kv3_sys_c |147573|

Only seven cell-estimate metadata fields change; all geometry, public pins, macro views, clock/reset, RTL and cycles remain identical.

Actual current-source G0C result unit472716: errors43→36, warnings2056→2056. Seven missing-cell errors removed; only summary text changes cells43→36, no new substantive finding. Remaining36 types need actual measurement.
