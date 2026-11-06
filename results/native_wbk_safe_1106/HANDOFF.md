# WBK native adapter — parked WIP, no physical adoption

Claude resumed; no further launches. This branch is a reviewable experiment, not a production recipe. RAW/default modules remain unchanged. Shared preexisting-face/hold-output hooks are prototypes; their production generation path is NOT qualified. No parent route/adoption is authorized by these results.

## Results

- Actual old OUT independent ready/valid/data face FFs fail literal native ready/valid: sent32, got34, bad28. Bare source passes32/32/0. Old p25 rdy2 bookkeeping hid this gap; no ready-lead authority was found.
- Candidate elastic OUT reuses existing head/tail data FFs, adds16 valid FFs and samples ready at negedge. Current common-clock native Kshare readiness is posedge state-derived. Minimal literal test passes32/32/0; wrong-phase and overwrite mutants fail. This is NOT arbitrary-phase readiness support; half-cycle STA is owed.
- Whole family four actual ROOT wrappers + safe MAIN HREG2/GIN1 + candidate OUT versus bare RAW: m0/east37772 writes each, slow39304, all48 reservations per mode complete, no data/order/window/fill/fault errors. Warm reset/abort quarantine and negedge-ready stability checks pass. Window observed +2 edges; completion lag varies, not a constant. Proof uses native Kshare u_e input-skid mechanism, not sealed physical partner.
- Component FF counts: old13826/new9250, delta-4576, new16 negedge-ready FF. External-only face checks4608/4608 pass with strict own-D feedback; native peer ports explicitly excluded. Fourteen ownership and six preexisting-manifest controls pass. Mapped area and physical STA were not run.
- Crucial remaining failure: captured physical Kshare candidate's exact four WB face statements plus native u_e accepts32/link32/receives32 but bad10. RAW reference32/32/32/bad0. Actual Kshare shell independently flops both directions too. Native physical activation stays HELD.

## Exact sources and evidence

Candidate RTL: rtl/hbm_accel/cores_split/reform_1106/ot_wbk_native_safe.sv, ot_wbk_native_safe_children.sv, ot_wbk_native_elastic_out.sv. Distinct default-off RAW-compatible module; hierarchy u_fcore.u_core.u_r0..3 and u_sw.u_main/u_out. Default WOPEN0/MUT0/STACK_SECTORS703125000 only; current t11 all stream/hbm/fifo clocks share PLLstream[0], resets share por_stream[0]. No async or full parameter-space claim.

Evidence logs are in evidence/. Full retained runs: E5:/srv/opentallas-scratch2/claude/codex-native-wbk-family-v2-1106 and codex-native-wbk-elastic-1106; E6:/srv/opentallas-scratch2/claude/codex-native-wbk-fffaces-1106 and codex-native-wbk-ksharefaces-1106. Existing jobs completed; no active job changed.

Captured Kshare candidate (NOT SIGNED, GRT was active): E5:/srv/opentallas-scratch2/claude/codex-hbm-forms-1105/eco/kshare_v8/i2/face_shell.json and rtl/ot_hbm_svc_vm_kshare_splitstrap__v8e478a__{wrap,fshell}.sv. Four tuple FFs: input addr120, valid4, data1024; output ready4, all hbm_clk. Full shell7339 FF/+1inputs/+1outputs/reset0. Our diagnostic is tuple+native u_e only, not full sealed controller.

ROOT B remains physically unqualified (GRT113512 overflow), E5:/srv/opentallas-scratch2/claude/hbm-gaps-5-cong/ot_wbq_root_vB. New8store root belongs to gaps/986d2288bf3 and is outside this adapter. MAIN/OUT captured from intel2 codex-wbq-production/gen-p36-candidate3-27d8 and out-p36-eastbands-candidate4. Safe source41ba3e486d3 / reform_1105b. All old kits/views preserved.

## Recommended next step — design only, not implemented

Prefer true same-parent internally timed reciprocal K seams preserving existing OUT and Kshare input-skid state and removing both blind face banks. HBM confirmed q_hub_nw/ne each contains u_vmks_Q0/Q2/Q3 master v700685 and Q1 v8e478a; OUTq1 is in same parent. NWq0 constant-stalled branch remains separate.

Existing native_seams peer/port schema cannot describe one wide OUT port to four Kshare peers. Extend with exact instance/master/port plus own and peer bit ranges, reciprocal direction/width checks, disjoint complete coverage, exact parent and no master-name ambiguity. HBM owns actual declaration/profile/event. Long physical spans require protocol-aware elastic relays and independently priced completion paths, not independent handshake FFs. Strict guard/context review and actual sealed partner proof precede physical activity. Current51.84x544.32 OUT resite51 geometry is unadopted.

Published unrelated QC fixes are already main: typed landing0459→101dbe5c5a5; signoff capture31a→922b67f63e; isolated helper bootstrap81→57c4d5d0f5/QC-ap. This WIP must not be mistaken for those releases.
