# Native private return-station proof

The public qfd_tt_ctlm_head module is byte-identical to b5b8ee4a8 (SHA256 4ed49b6a30b942c2231c5a54f59c12fdfbb21d75a6568d0b28a02569c04d8737). Only the private tree predictor return station uses its existing native ec. Head CE and tree gate sample the same pre-edge enable; original station depth remains one and return epochs remain equal. No clock or enable crosses leaves.

Actual flat and split native AUD33975, G3072, MEREG3, PSRAM1 are compared every cycle, including all exposed outputs and program word. Strict: 59839 cycles, 3387 events each, no mismatch; 59838 pre-edge enable and complete95-bit station comparisons. Argmax:20639 cycles,14 completions each,113 events each,20638 station/enable comparisons. Repeated resets/startup, random supply stalls, operation drain and full operation/18-bit row stimulus retain the original production benchmark. Valid command tiles-bit mutant produces52960 mismatches.

Explicit actual fab_fault injection every token at offset50 passes59839 cycles and3431 events each, with22269 active fault comparisons; zero fault checks would fail. All station/enable assertions also pass. This supplements strict normal operation, not a substitute for operation coverage.

Actual u_tree.local_en clock activity matches flat:21279 enabled edges;30814 idle cycles and154 enabled idle edges. Moving95 private station bits onto native gate reduces the labeled clock-pin toggle estimate by95*(30814-154)=2912700 idle FF clock edges versus the previous CE shadow. Physical dynamic/leakage power remains unmeasured.

These are functional/activity receipts only. Native related-clock ENA setup/hold, both clock domains, actual physical sink counts and overall setup require a fresh source-bound gate. Previous b5b8ee4a8 root/spread PASS remains unqualified:ENA setup−202.84ps and overall setup−549.15ps.
