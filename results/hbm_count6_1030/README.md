# Current native whole-master mapped counts

Count source is the actual BIND469 native instance and b31t preferred reachable module closure, with all seven native defines and exact parameters. The direct wrapper adds no registers, clocks, face shell or latency. All non-memory descendants are real functional source, flattened by synthesis; the only blackboxes allowed are real qualified SRAM providers whose complete functional model file SHA equals the preferred native model. The old canonical provider model matches; V2 model bytes differ and were deliberately excluded. The provider BB/LEF/TT/FF file hashes are recorded in each source.json.

Only official ORFS synthesis is run, using actual RVT TT libraries at833ps; no P&R, LEC or physical qualification. Actual make print-TC_LIB_FILES and print-LIB_FILES both resolved to TT libraries. Counts are official 1_synth.json metrics with mapped netlist SHA and source hashes. The ABI check compares the elaborated actual-parameter child against the actual native cell's complete port/direction/width inventory.

All six requested current counts and the extra actual-preferred RAW count passed:

| Actual instance | Parameters | TT std cells | SRAMs |
|---|---|---:|---:|
| hb_dbk_NE | RR_RT80 | 31499 | 10 |
| vmks_NW0 | KRL1=1,MUT0 | 113718 | 0 |
| ctl_NW_p00 | KREG/KRREG/OREG/QREG/RREG/WPAY all1 | 42694 | 2 |
| wbc_NW | NS4,MUT0 | 345 | 0 |
| vmfc_NW | W89 | 12201 | 1 |
| wbk_NW | WOPEN0,MUT0 | 374772 | 32 |
| vmdel_NW0 | NPC2 | 4554 | 2 |

WBK fresh TT successor completed on intel2 unit1229305-1793377869; its first FF diagnostic attempt is preserved. The exact preferred RAW NPC2 count completed on intel1 unit3017410-1793376889 because the older3074 generic count's literal source hash differs. Different mapped/generic count contexts do not establish a source regression. Every actual count is below400k standard cells, including WBK374772; SRAM count/area remains separate.

The parent requested one additional enabled833 PC profile count after WBK terminal. It uses only the exact approved abdb23bfa h9b/h9 source overrides, all six native flags1, RMUT0,TIMING_8331, actual7defines and two real SRAMs, with no extra outer FF. Source packet pc833/ and fresh runtime intel1:/srv/opentallas-scratch2/claude/codex-hbm-pc833-count-1030. It is progressing and is separate from the current-native default-profile count42694.

First attempt setup failure is preserved: native source/actual-parameter ABI/7defines passed, but the lean driver omitted explicit TC_LIB_FILES/LIB_FILES, so platform-default FF mapping ran then synth_odb stopped at missingTC_LIB_FILES. Those netlists are diagnostic only, not G0C counts or native hardware failures. Fresh tc/ successor directories use the generator's standard TC/BC/LIB_FILES binding. Completed attempt directories are never overwritten.

Job sources/results: intel1 BACK/VMKS/PC and intel2 WBW/VMFC, scratch codex-hbm-count6-1030/tc/<instance>; each count_result.json and source.json copied here. Parent/root owns G0C evidence intake and physical decomposition. No source, arithmetic, latency or plan adoption is implied.
