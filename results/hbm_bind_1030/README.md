# HBM binding continuation, 2026-10-30 03:39 PDT

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

No station growth was needed. The strict original-cycle control correctly rejects these paths: existing pair L4/L4m(width2816) have11cycles and L96/L96m(width22) have12cycles. The event flag only emits an UNADOPTED candidate with those mismatches recorded. For all lanes to match16/18, NE->NW L4m needs+5 and L96m+4; NW->NE L4 needs+7 and L96+6. The die owner owns padding/coherence, TOK pricing, clock/crossing updates and adoption. G0/G0C checks are pending; no P&R/STA run.

## Current fused recipe facts

`current_fused_facts.json` comes from CURRENT d31t `b31t/out/asbuilt.json` (g4 compose), not old e2 defaults. Top instance `u_mu_fused_programme` has module `ot_hnx_fused_host_program`, TARGET225,DELIVERED_RESET1; the name fused_programme is an instance, not a separate module. All30current `ot_hnx_fused_tnode` cells explicitly override DELIVERED_RESET1,LA6,UW271,DW173 (master default reset0 must not be used). The core lane has these facts for new recipes.
