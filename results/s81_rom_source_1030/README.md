ROM source candidate on current main c87cfe541c81de125ab0a9fac59b96e083e180a7.

Only two RTL files change. Held class mirrors reload from their actual held unreset source during reset. FP4K defaults0; only the existing tied-FP4 u_l1 enables the representation of the equal decoded field bits. Zero cycles, no arithmetic/pipeline/port/outline change. BF source and all other mixed ancestry omitted.

Functional evidence already completed: full ROM mirror-reset strict locksteps1773914/1806452/1849282cycles, midresets50/42/26, mutant377caught. Exact helper FP4K0vs1 lockstep P0B0/1/2/3 x20000cycles,0mismatch; real wrong-field mutants caught5136..5138. Helper receipt copied here; original integration collection e3e0662f5 retained.

Fresh ordinary main-driver native gate:74608/74608EQUIVALENT,0diff/undecided,6902.5s;1826KEEP=1823physical+3ordinaryconstant-proved points,0missing/removed. Existing declaredreset64/assert66, requestnull/debug{}; no reset or solver override, no trusted hints. Full5533old+31untrustedalias profile applied. FLOW/lec source manifest+receipt included.

Currentmain material review:31/32RTL file bytes match protected qualified kit exactly. The sole mismatch is ot_v41_segtree5.sv (main default-off KEEP_XPOS addition); this module is UNREACHABLE for exact nativeQM5/QX10/FAST1/QPIPE1. The first g_tr5 branch uses only segtree6, whose bytes match. Native gold elaboration logs show only the two segtree6 instances and no segtree5. Currentmain source for every active module matches the native proof. No claim for a different parameter cohort. This avoids reverting shared BF KEEP_XPOS or silently replacing its module.

SOURCE READY for root review only. No physical signoff/TTFFview/parent adoption/count. Existing original151NEQ and later alias residual failures retained; the final native ordinary proof supersedes those source-qualified failures only.
