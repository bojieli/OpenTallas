# S81 KV leaf t2 capacity source-cut census

The current capacity number is an estimate, and the current store placement has a direct source-to-capture reach failure. This packet provides a disabled, source-preserving cut/footprint candidate. No canonical plan or RTL changed; no CAD ran.

Inputs: current `physical/die_plan/s81/plan_h2_2249.json`, type `ot_s81sl_kv_leaf__t2`, sole instance `s_3N_L0` at (13089.6,16053.12), outline4328.64×1226.88um; actual bound RTL from intel1 `die-s81-47/bind_ev2/out/rtl/s81p_ot_s81sl_kv_leaf__t2.sv` (hash in source_cut_census.json). The plan has no hard cores and183 SRAM instances:144 store32×64,32 KVQ64×512, and7 ordinary leaf SRAMs.

## Capacity and source cut

`cells_est.json` labels358,423 base cells as `MISSING kv512 leaf; SU KV leaves kve/kvp/kvq/kvr/kvt summed`. The reported462,435 including104,012 landing cells is therefore not a measured mapped-cell count. Do not present it as sizing sign-off or clear G0C by renaming the estimate.

The actual bound source contains all23 ordinary arithmetic/HCPost instances used by the regular KV-leaf cut, with their actual module/parameter lists recorded in source_cut_census.json. This establishes source candidates only; the regular23-cut geometry, clocks and SRAM placement cannot be copied into this special type. It also contains the existing `ot_s81sl_kv_leaf` at `u_g_kv_u_kv`, logical path `u_lf.g_kv.u_kv`, parameters CNIK1/CP1/HARD_RQ0/zero mutants.

Prefer a first sizing candidate that hardens those existing common bodies plus the whole KV bridge at its707 functional-bit boundary (+clk/reset), retaining the native module and calendar. Consider the two remaining ordinary soft arithmetic bodies VN_B/VQ as separate existing cuts if the parent residual remains over budget. Cutting only `u_bank` instead exposes16,914 functional bits and its macro bounding box encloses parent-owned store SRAMs; this is a poor physical boundary. Every hard child and the parent residual still require actual mapped counts/area before a build decision.

## Store geometry diagnosis

Native leaf RTL has16 banks, each9×64-bit SRAMs; `phase==1` executes `packet<=rd[bank]`. Each of the576 packet bits selects directly among16 same-offset R0 SRAM output pins, with no relay. For each word, the minimum achievable Manhattan radius is exactly half the greater range of(x+y) and(x−y) over its16 source origins. Identical LEF pin offsets translate that source set and do not change the radius.

Actual per-word radii are570.24–643.476um: all9 words exceed405um regardless of packet-flop location. This is a structural reach failure, independent of a timing estimate. The source/placement explains why a large outline alone does not close this block.

Repack the same144 macros as4×4 banks, each3×3 words, using the existing42.792um horizontal and34.56um vertical pitches. The complete store footprint is502.704×397.464um. Each word's16-bank source radius becomes348.084um, leaving56.916um of geometric radius for its actual mux/capture placement. This is an analytical placement candidate; actual mux/FF homes and routed timing have not been measured. No extra SRAM, RTL cycle or changed arithmetic is proposed.

## Disabled whole-bridge footprint

`whole_kv_bridge_candidate.json` lists every one of the176 existing KV bridge SRAMs in a relative777.6×1209.6um outline:32 KVQ SRAMs in4 columns×8 rows at190.08×95.04um pitches below, compact store array above. Macro overlap count0; macro area506,067.803um² =53.804% of the outline; soft free area434,517.157um². Soft cell fill and child capacity remain UNMEASURED. No absolute parent site is selected.

Both PNGs were personally viewed. The compact store is bank-coherent and its nine word-capture center targets occupy central streets rather than requiring one long global read leg. The larger KVQ SRAMs have continuous row/column channels, but these macro-only pictures do not qualify pin orientation, channel demand, clock islands or PDN. The current parent FT station/landing/clock/reset reservations must be checked against any absolute child footprint; existing macro_under_ft permission does not permit a new hard-core obstruction or station overlap.

Verdict: current store geometry FAIL structural. Candidate PASS-COND for continued source sizing/plan PREP only; no P&R/STA release. Next: obtain one actual selected-source count/area census for the bridge and parent residual under the proposed existing-body cuts, then compose full parent geometry and clock/reset models, render/look again, and run the normal exactness and physical gates. If the bridge itself is too large, its native KVE/KVQ/reducer/pool boundaries must be measured before choosing smaller cuts; no guessed claim of<=400k.
