KV native slot reservation, planning only

OT_KV_NATIVE_SLOTS=1 reserves complete388.8x388.8 group outlines using the existing collision/keepout/halo-checked free_spot before routing. It reserves the measured SRAM CTL345.6x475.2 portrait instead of the historical1123.2x172.8 strip. Default off. No RTL or clock/constraint relaxation; static edge changes must come from actual regenerated relay routes, never from these dimensions alone. The generated model records qualified=false.

Measured kit inventory: group s3/s4 four p192 SRAMs per group,32 groups =4,837,294.08 um2 total envelopes. CTL native envelope164,229.12 um2 vs194,088.96 legacy (-29,859.84), but height+302.4um requires a different legal home. Existing free_spot refuses occupied/thin channels and reserves a21.6um halo. These are hard-outline planning costs, not physical cell area or a closure claim.

Validation: unpinned fleet unit1450559 onot-epyc5 exit0,3tests: default legacy preservation; oldthin channel accepts oldCTL but refuses realportrait; fullsquare group honors keepout and prior group halo. No full GEN run performed on the newflag, no real placement or relay/calendar/native qualification claimed. Need coherent source/view/census and realplaced-pin relay export before enabling a strict release chain.

Other source blocker discovered independently: current mapped CTLmu6c textbook hf_max_net2357 (OR2),1027(NAND2),572(OR3),384AND3; programme ld flop325loads;18,014flops10SRAMs;635.1ps17levels. Mu6c/d original gates remain active, no submit under native32 rule. Route-period changes do not fix this census. Structural control/decoder/reset distribution is required.
