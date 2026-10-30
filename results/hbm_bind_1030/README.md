# HBM binding continuation, 2026-10-30 03:39 PDT

Latest: the original ordered HH candidate is GEOM FAIL (mandatory seam pin waypoints omitted), never routed. Current native DMA provider audit is FAIL_R7_SOURCE. The new six-format decode component is an unbound research coupon, not a production provider. See the correction and source sections below.

No plan/source adoption or physical signoff claim. Current d32q physical tables and d31t binding retain 81 UNPLANNED pairs / 57,312 bits, zero EMIT.

## NW glue count failure

The reported 726,958 legal cells / 288,741 FFs did not exclude every planned hard child. The DIE-HBM-32 script read `hard_stubs.sv` first, then read files containing soft dependencies. Those files also define hard children, and Yosys explicitly replaces their blackbox definitions with logic.

Affected hard module types: `ot_hgi_sm_xload_cl2_ctlx`, `ot_hgi_sm_xload_cl2_bdring`, `ot_hgi_coll_gq_issue`, `ot_hgi_coll_gq_land`, `ot_hbm_su_static_cxport_ij_q`. Their six top instances contain 92,599 pre-optimization FF bits in the preserved hierarchy. This is substantial contamination, not evidence that NW glue requires two regions. The original failed count is retained; a corrected count is required before choosing a split.

`hub/correct.ys` reapplies the unchanged hard stubs with `read_verilog -overwrite` after all source dependencies, before hierarchy. The corrected hierarchy lists all five module types as direct blackbox cells. It then runs the same flattened synth and dfflegalize as the original. Corrected run completed rc0 on intel1 under ot-run (48GB,1thread), directory `/srv/opentallas-scratch2/claude/codex-hbm-bind-1030/hub`, container `codex-hbm-bind1030-correct`; check `correct.rc`, `correct_generic.txt`, `correct_legal.txt`. Result: **375,373 total legal cells, 223,589 FFs**, below the 400,000-cell cap; the count-driven requirement to split NW hub is cleared. Actual geometry/timing/die-route gates remain open. Original and corrected scripts and pre-synth hierarchy and final statistics are included here. No P&R/STA submitted.

## Collar pin mismatch

The current root `u_col_idx` plan entry selects `c_done -> c_done__W` and marks the N-face `c_done` unused under the historical superset-face-master policy. Native RTL has one active INPUT `c_done`; the emitted root drives only `.c_done(w_u_hb_idx_ctl_done[0])`. There is no second source input or `.c_done__W` connection. The logical input captures completion into `done_q`.

The die owner received the exact fix proposal: preserve the W physical site `(0.096,52.968)` under logical name `c_done`, remove the stale N entry and redundant select/unused declarations in the next plan event. Do not delete the selected W site or invent independently driven input aliases. Zero RTL cycles change.

## Remaining source/bind ownership

The native row1 split proof and shared-bank SFU hierarchy proof from `codex/hbm-bind-2249` are retained without reruns. They remain unadopted pending physical plan and cycle composition. Current far hub-to-hub demand is primarily real ring traffic (NE->NW 2,775 bits includes VMS ccw 2,170 and collective ring cw/ccw 280 each), not a map-only error. The retained b30p all-bit census differs only in the separately rejected eight-reg map and is used for these unchanged source buses only.

## Ordered hub detour station solver

`lane_force_ordered.py` patches only the die-local lane-add invocation. The shared solver searched the union of free partition sites, then rejected non-monotone owners; nearest-point snapping also failed at ~406um. The new DP restricts every stage to its specified slot owner and applies Manhattan dilation before backtrace. FF homes are global 4.32um lattice points, outside hard-core halos. Every resulting hop is asserted <=the unchanged364.5um computed reach, and every slot keeps its required station count.

Actual d32q detour candidate `intel1:/srv/opentallas-scratch2/claude/codex-hbm-bind-1030/hh_ordered_event` builds both full-width lanes (5505bits), zero macro hits, worst hop362.88um:

- L700 NE_hub->NE_b112->root->NW_b112->NW_hub:2775bits, counts[4,5,5],14stations,16natural cycles.
- L701 NW_hub->NW_b112->root->NE_b112->NE_hub:2730bits, counts[5,5,6],16stations,18natural cycles.

No station growth was needed. The strict original-cycle control correctly rejects these paths: existing pair L4/L4m(width2816) have11cycles and L96/L96m(width22) have12cycles. The event flag only emits an UNADOPTED candidate with those mismatches recorded. For all lanes to match16/18, NE->NW L4m needs+5 and L96m+4; NW->NE L4 needs+7 and L96+6. The die owner owns padding/coherence, TOK pricing, clock/crossing updates and adoption. G0 PASS0errors; G0C FAIL8errors/128pending exactly the inheritedd32q error set (new/removederrors0). Worstglobalcut0.1673, worstsegment0.5995 at baselineNW_b101. No P&R/STA run.

## Current fused recipe facts

`current_fused_facts.json` comes from CURRENT d31t `b31t/out/asbuilt.json` (g4 compose), not old e2 defaults. Top instance `u_mu_fused_programme` has module `ot_hnx_fused_host_program`, TARGET225,DELIVERED_RESET1; the name fused_programme is an instance, not a separate module. All30current `ot_hnx_fused_tnode` cells explicitly override DELIVERED_RESET1,LA6,UW271,DW173 (master default reset0 must not be used). The core lane has these facts for new recipes.

## Geometry correction: original ordered detour is NOT physically closed

The die owner rendered the candidate before route and found that the DP omitted mandatory seam pin waypoints. Its FF homes stayed near y10400 while intermediate pin windows were at y11170/11640, so direct FF distances understated via-pin wire reach (about1700um). The saved G0 PASS is a flow undercheck receipt, not a physical chain closure. The candidate is **GEOM FAIL / UNADOPTED**, never routed. Parent owns a revised solver that constrains first/last FFs at each seam and checks actual via-pin hops. No old verdict overwritten.

## Static LOAD source priority

`current_dma_r7.json` records the current emitted-source failure without rewriting the historical G0 receipt: internal production `hb_dbk_SW__rq` and `hb_dbk_SE__rq` (136bits each) are emitted as external die inputs, with no matching native DMA instance, and no production generic LOAD provider is instantiated. Only two static BACK engines exist, NE/NW, both stack strap2. The audited raw top and bound wrapper paths are in the receipt. Generic Python descriptor replay is not a provider.

Root selected plan-first reuse of the existing `ot_hbm_svc_vmdel_lane_load_static` NPC2 with the actual owned PHY windows, its 62-bit command format and a compact descriptor/calendar translator. TOK's source proposal owns window inversion, actual traffic amplification, VM DQ slot6, epoch/slot binding, all-eight-leaf release commands and the new destination routing/dispatch. Current physical source only has stack2 PC0..31; stack3 scratch/dispatch stays unbound. Parent owns the necessary type/plan event. No generic mover is silently adopted.

`static_load/` is the explicitly UNUSED alternative decode coupon built before that reuse decision: three registered stages (input face capture, source extraction, conversion/output), II1 for one coalesced micro-op. It preserves all six actual static LOAD formats: FP32/BF16/FP8E4M3/INT8/U32/UE8M0. FP4/reserved formats, misalignment, empty/overlapping ownership and missing scheduled sectors fault. There is no internal ready/credit/retry. Its schedule date is input_date+3; a burst of N operations costs N+3 pipeline slots including fill/drain, not three cycles per element. It is not inserted into the production model or RTL.

Final coupon evidence: strict Verilator lint0; actual native serial/static conversion lockstep 74,533cycles,74,521scheduled operations,595,968checked words,25rejected operations. BF16 covers65,536payloads; FP8/INT8/UE8 each coverall256codes, checked against independent IEEE truth tables; FP32/U32 use bit-pattern random words. Wrong FP8 subnormal-zero mutant is caught with8mismatches. Generic synth:10,233cells,938FF,633port bits. Actual nonfake RVT TT cell areas give an analytic replacement estimate1699.84square-area units (unmapped), not timing/signoff. A60.48x60.48um candidate gives about46.5percent stdcell fill if units match the physical library; pin proposal256dataW,282outputE,90controlsN is below6pins/um at0.192pitch. No lot is reserved, no current hard core changes, and no P&R/STA runs. The production plan's lot fit belongs to the existing vmdel LOAD type event, not this unused coupon. Arbitrary-stride LOAD traffic must count each distinct source sector; the datapath's32VMbytes/cycle peak is not a whole-provider rate.

Additional exact source facts supplied to core owners: VM query NW usesVM_RT_EXTRA173; NE/SE/SW use171 (currentmaster default4 is wrong for all). Current pinned selector master has onlyMUT, noSTRUCTparameter: nativeSTRUCT1 cannot be inferred from an old trial kit.

## Actual eight-leaf LOAD ownership vehicle

`static_load/ot_hbm_static_load_quad_vehicle.sv` instantiates eight unchanged current `ot_hbm_svc_vmdel_lane_load_static` NPC2 leaves. This logical vehicle broadcasts begin and full-window fills, emits dated per-leaf62bit commands, and merges exactly one scheduled source through one registered281bit VM packet output. Simultaneous source packets or mismatched native destination sidebands fault; there is no arbitration, ready or retry. Raw-start is inactive only in this LOAD-specific vehicle. This is not production NTOP wiring or a physical route implementation.

Baseline PASS: three buffer/epoch phases (bank0epoch7,bank0epoch8,bank1epoch9),144 scheduled commands and144 observed writes across all six formats,1026 checked words. Measured command-to-packet latency is fixed7cycles including the merge register. The missing-release mutant releases only the last leaf; the next begin faults exactly the other seven owners (`leaf_fault=7f`). Actual window input is32KiB per quad, not a32B demand fetch. Build and simulations ran via ot-run intel1; only the result-grep command failed because remote `rg` was absent, corrected to portable `grep`. No simulation failure is hidden. Complete production target/programme dates, loop capacity, runtime addresses, PHY arrival epochs, four-stack coverage, scratch ownership and plan/clock/route remain mandatory open integration tasks.

The original released r18h5 source already straps NE BACK to stack2 with target107, NW to stack2 with target106, SE to stack0 with105, SW to stack0 with104. Thus target104+quadrant is not itself evidence that `stk` must equal quadrant. No NE strap change was made from this observation; current WB/PHY reach must establish any new coverage.
