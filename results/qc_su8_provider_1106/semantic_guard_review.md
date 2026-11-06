# SU8 arithmetic-zero refinement: narrow admission invariant

Candidate recipe `0316843cf3df5f8db52e86249bdf5fc32e542342` and proof evidence `d4a553623fb` are source-only candidates. No route adoption is claimed. The old failed physical attempt, its source and KEEP FAIL receipt remain intact.

The changed state is exactly 16 always-zero stride-product bits (K2/K6 low bit and K4 low two bits, in each of four 24-bit words), plus `fa[333:332]`, the top two bits of `nvec_r`. For every 18-bit `nin`, `nvec_in = (nin + 7) >> 3 <= 32768`; these two bits are zero on every actual accept load. Multiplication by each constant K has the stated trailing zero bits. Before the first load, the old unreset storage may be unknown; the candidate refines only those values to zero. This is NOT arbitrary-state whole-core equivalence.

The required invariant is: **no admitted output, and no valid/control state, consumes the refined storage before the first corresponding load.** Raw idle `pd1` pins may differ while their emit qualification is false.

The actual rst3 source has `sg0` and `sg1` parallel one-edge copies of the same `c_su`, both under `rst_k[1]`. Every `acc_k` replica copies an `sg0` member; every per-lane 6-bit chunk's `xsel[c]` copies an `sg1` member. They therefore deliver the same accept event on the same cycle to all chunks. The 64-edge boot contract makes the reset controls known before legal programmed traffic.

Relative to a rising edge E0 sampling `c_su=1` after reset has released:

| Edge | State loaded after edge | Consequence |
| --- | --- | --- |
| E0 | all `sg0` and `sg1` copies become 1 | common accept event launches |
| E1 | every `acc_k` and every lane `xsel[c]` becomes 1 | all FA and all stride chunks have their load asserted |
| E2 | all `fa` fields and every stride chunk load; all `act_k` become 1 | all 18 refined bits now equal their structural zero values in the old RTL too |
| E3 | lane `pdr` samples the now-loaded stride/current-address operands; `gvr[2]` samples `emit_c=act_k[NACT-5]` | first correct lane payload and its emit qualifier are produced together |
| E4 | common `u_output_pins` captures `c_pd1` and `c_gv` | first externally emitted `pd1` has already initialized arithmetic state |

An additional legal start pulse does not undo load coverage; warm reset also does not invalidate established arithmetic zero values. The first post-reset accept overwrites the relevant payload again before its newly asserted emit reaches the external pins.

There are two actual cone classes:

- Stride zero bits feed only the four lane offset adders, then `g_lane[*].pdr`, then `c_pd1`, then registered external `pd1`. They do not feed `lv1`, `gvr`, ready/fault/idle/progress or the next command. Their first admitted payload is covered by E2 -> E3 -> E4 above.
- `fa[333:332]` feed only `nvec_r`, then `vl_stepA=(v+2==nvec_r)` and `vl_one=(nvec_r==1)`. Both next-state VL expressions select direct `vl_inA=(nvec_in==1)` on accept. Otherwise the `nvec_r` arms are selected only when the corresponding `act_k` is 1; before the first accept all `act_k` remain their reset value 0. Inactive VL state merely holds. The active bits themselves remain 0 before accept because `act_next` is accept ? 1 : (act && ...) ? 0 : act. Thus refined FA bits cannot alter any control state before the first load.

Parent admission still needs the exact selected native consumer join: external `gvr/gv` is `{emit_c, accept_copy, v_last_copy}`, and lane `lv1` is a live mask rather than a command emit qualifier. The parent must consume the lane payload under its existing emitted-command qualification / static calendar, not from `lv1` alone. The exact selected parent source receipt is being obtained from its owner; source/route adoption stays held until that join is checked.

Existing evidence is deliberately scoped. Native lockstep good and Xinit pass against the original SU7 control projection; the stride mutant is caught. The existing Xinit bench compares full payload only after first start + 40 cycles, so it does not establish the earliest parent admission. The separate actual old/new xlane temporal induction proves every 6-bit chunk equal after its first selection, for K0..7 and arbitrary input/select traffic, and its wrong-zero mutant is rejected. Current standard synth LEC proves 7824/7824 with all 3126 kept register bits physically represented. Those results support this source change but do not replace the parent admission join.
