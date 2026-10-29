# NP4 line-sliced IDX key replay buffer

**PASS on the minimum full-payload mechanism**, not a physical or whole-token pass. The packed NP4/RS0 implementation and the new four-slice implementation agree at833ps on13,824 checks over3,456cycles,698writes and1,720replays. The independent model checks all4,396 public data/tag/valid bits. Both `pbase=0` and4 cover every legal address0..170, including127/128 tag carry and170. The bench covers overwrite, same-address actual-SRAM read-before-write, simultaneous PRE(next)/REPLAY(current), reverse replay, clear/live precedence, warm reset retaining memory, and16 malformed-control fault cases.

The three controls are caught: wrong pbase at cycle173, a flipped last meaningful bit of lane2 at cycle1, and a PRE address/phase error at cycle173. Unsupported RS1 fails elaboration at the explicit configuration guard. The actual repository SRAM behavioral macro is used:17 physical macro instances in the golden,20 in the candidate. No substitute memory model appears in the DUT.

The new `ot_hnx_idxn_keybuf_sliced_np4` is opt-in. Existing packed and fixed-eight modules remain unchanged. The new `ot_hnx_idxn_quarter_with_keybuf_sliced` has the identical quarter body after changing only its public module name and the explicit key-buffer selector: scorer RTL, TP, DELIVERED_RESET and port wiring stay byte-identical. The quarter connects `pbase={half,2'b00}`; NW/SW use0 and NE/SE use4.

Each active path is `quarter.keybuf.gp[p].u_line`, p=0..3. It retains the old one-line slice's five256×256 SRAMs and declared lane-id input. Four active slices use20 SRAMs versus17 packed; all four roles use80 versus68 (+17.65%). Replicated per-line have/PRE/fault control costs543 extra FFs/quarter,2,172 total. **Added data, reset and token cycles:0.** No arithmetic, rounding or static schedule changes.

The old physical plan reserved eight slices/role (32total/160SRAMs). The NP4 source needs four/role (16total/80SRAMs), leaving16 previously reserved slots inactive. Keep them reserved until the die owner composes the VP4 joint replan. Two241.92×293.76 slots plus a17.28 street have the501.12×311.04 envelope, but adjacency and actual capacity belong to the die plan, not this proof. No slot was deleted or physically adopted here.

The first independent reference failed at address128 because `8'(integer_index)` made array subscripts signed and negative above127; golden-to-candidate lockstep still agreed. The reference now masks indices to0..255. Original failure/diagnosis logs remain in `failures/`; this needed no RTL fix. `result.json` and the logs contain the final result.

Tested RTL/bench source:92a8e0c50 on main e93e45262. Job:epyc2 `/srv/opentallas-scratch2/claude/codex-keybuf-np4-1029`, ot-run unit `oth-ubuntu-197241-1793260509`, exit0. To reproduce through the fleet admission guard, use the clean source and a fresh output directory with `tools/hbm_b2/run_keybuf_np4_miter.sh`.

Still required: explicit source alias/adoption in the strict bound C25c top, actual four-slice mapping for every role, joint VP4/unused-slot plan composition, normal physical closure and token replay. The current wrapper alone does not establish G5 or a production calendar.
