# HBM binding continuation, 2026-10-30 03:39 PDT

No plan/source adoption or physical signoff claim. Current d32q physical tables and d31t binding retain 81 UNPLANNED pairs / 57,312 bits, zero EMIT.

## NW glue count failure

The reported 726,958 legal cells / 288,741 FFs did not exclude every planned hard child. The DIE-HBM-32 script read `hard_stubs.sv` first, then read files containing soft dependencies. Those files also define hard children, and Yosys explicitly replaces their blackbox definitions with logic.

Affected hard module types: `ot_hgi_sm_xload_cl2_ctlx`, `ot_hgi_sm_xload_cl2_bdring`, `ot_hgi_coll_gq_issue`, `ot_hgi_coll_gq_land`, `ot_hbm_su_static_cxport_ij_q`. Their six top instances contain 92,599 pre-optimization FF bits in the preserved hierarchy. This is substantial contamination, not evidence that NW glue requires two regions. The original failed count is retained; a corrected count is required before choosing a split.

`hub/correct.ys` reapplies the unchanged hard stubs with `read_verilog -overwrite` after all source dependencies, before hierarchy. The corrected hierarchy lists all five module types as direct blackbox cells. It then runs the same flattened synth and dfflegalize as the original. Job is running on intel1 under ot-run (48GB,1thread), directory `/srv/opentallas-scratch2/claude/codex-hbm-bind-1030/hub`, container `codex-hbm-bind1030-correct`; check `correct.rc`, `correct_generic.txt`, `correct_legal.txt`. Original and corrected scripts and pre-synth hierarchy are included here. No P&R/STA submitted.

## Collar pin mismatch

The current root `u_col_idx` plan entry selects `c_done -> c_done__W` and marks the N-face `c_done` unused under the historical superset-face-master policy. Native RTL has one active INPUT `c_done`; the emitted root drives only `.c_done(w_u_hb_idx_ctl_done[0])`. There is no second source input or `.c_done__W` connection. The logical input captures completion into `done_q`.

The die owner received the exact fix proposal: preserve the W physical site `(0.096,52.968)` under logical name `c_done`, remove the stale N entry and redundant select/unused declarations in the next plan event. Do not delete the selected W site or invent independently driven input aliases. Zero RTL cycles change.

## Remaining source/bind ownership

The native row1 split proof and shared-bank SFU hierarchy proof from `codex/hbm-bind-2249` are retained without reruns. They remain unadopted pending physical plan and cycle composition. Current far hub-to-hub demand is primarily real ring traffic (NE->NW 2,775 bits includes VMS ccw 2,170 and collective ring cw/ccw 280 each), not a map-only error. The retained b30p all-bit census differs only in the separately rejected eight-reg map and is used for these unchanged source buses only.
