# AHUB6 semantic storage HOLD

core-c D4 logical history family5444bits exceeds2kb; two-bit implementation chunks are not an exemption

|Landing|Net|Writer→reader clock|W|D|Payload history bits|Read/write ports|Role|
|---|---|---|---:|---:|---:|---|---|
|0|amw_c|ck_c→ck_w|72|4|288|1R/1W|Selected history; no parallel-compute exemption|
|1|ame_c|ck_c→ck_e|72|4|288|1R/1W|Selected history; no parallel-compute exemption|
|2|fr_epoch_i|ck_c→ck_w|16|4|64|1R/1W|Selected history; no parallel-compute exemption|
|3|fr_rz_i|ck_c→ck_w|128|4|512|1R/1W|Selected history; no parallel-compute exemption|
|4|fr_valid_i|ck_c→ck_w|1|4|4|1R/1W|Selected history; no parallel-compute exemption|
|5|ape|ck_e→ck_c|86|4|344|1R/1W|Selected history; no parallel-compute exemption|
|6|apw|ck_w→ck_c|86|4|344|1R/1W|Selected history; no parallel-compute exemption|
|7|zo0|ck_z0→ck_c|68|4|272|1R/1W|Selected history; no parallel-compute exemption|
|8|zo1|ck_z1→ck_c|68|4|272|1R/1W|Selected history; no parallel-compute exemption|
|9|zo2|ck_z2→ck_c|68|4|272|1R/1W|Selected history; no parallel-compute exemption|
|10|zo3|ck_z3→ck_c|68|4|272|1R/1W|Selected history; no parallel-compute exemption|
|11|zi0|ck_c→ck_z0|268|4|1072|1R/1W|Selected history; no parallel-compute exemption|
|12|zi1|ck_c→ck_z1|268|4|1072|1R/1W|Selected history; no parallel-compute exemption|
|13|zi2|ck_c→ck_z2|268|4|1072|1R/1W|Selected history; no parallel-compute exemption|
|14|zi3|ck_c→ck_z3|268|4|1072|1R/1W|Selected history; no parallel-compute exemption|

|Logical writer family|W total|Payload history|Epoch history|Valid history|Physical history total|Reader roots|Verdict|
|---|---:|---:|---:|---:|---:|---:|---|
|ck_c|1361|5444|8172|2724|16340|6|HOLD_NEEDS_REAL_SRAM_BACKEND|
|ck_e|86|344|516|172|1032|1|UNDER_2KB_PAYLOAD_FAMILY|
|ck_w|86|344|516|172|1032|1|UNDER_2KB_PAYLOAD_FAMILY|
|ck_z0|68|272|408|136|816|1|UNDER_2KB_PAYLOAD_FAMILY|
|ck_z1|68|272|408|136|816|1|UNDER_2KB_PAYLOAD_FAMILY|
|ck_z2|68|272|408|136|816|1|UNDER_2KB_PAYLOAD_FAMILY|
|ck_z3|68|272|408|136|816|1|UNDER_2KB_PAYLOAD_FAMILY|

The 903 two-bit implementation chunks do not change these logical families. The 7220 payload-ring FF bits plus1805 reader output bits and29799 replicated metadata FFs give38824 mapped landing FFs. Replicated epoch/valid arrays are also indexed history and remain subject to storage audit:10836 epoch bits and3612 valid bits, including ck_c8172 epoch+2724 valid bits. Physical ck_c payload+epoch+valid history is16340bits. A real backend must also replace this metadata history or prove/remap redundant metadata; none is automatically exempt because it is duplicated. None of this inventory grants a storage exemption.

The core-c family requires a real SRAM backend or a reviewed architecture change. It has six simultaneous related-root reader domains (w,e,z0..z3). A single1R SRAM cannot serve six independent read clocks by assertion; a banked real macro solution must bind ports/clocks and prove the unchanged D4/K2 edge/reset behavior. An existing software/model backend is insufficient.

The R0 lattice proposal preserves exact immutable LEF bytes, bbox origins and logical pin→net mappings. It physically reorients three children and therefore changes their actual global pin rectangles, all recorded in r0_lattice_proposal.json. It does not cosmetically edit an abstract. The proposal is not applied to a kit and no gate is authorized.

Named mapped-band densities: c15511.662/48288.96=32.12%; w1564.624/6894.72=22.69%; e1038.038/6428.16=16.15%; each Z1504.773/6531.84=23.04%. Unnamed logic742.545um2 is unallocated at source; putting all in c raises its conservative source density to33.66%. Post-CTS/repair actual fence fill remains unmeasured.
