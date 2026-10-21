# Residual address cone: model only; e5a remains HOLD

Exact arithmetic source aa6cd99fb / b49162d88eb2f47e1dfee5c9036ac08a20ffe9b0796b70a89bb3cb2f0d5d1d63; actual mapped source 4c4b1fa2eca4e65190a0203eea33fb2ff871928c9b5e26cbbef3e4952694fbb6, selected native/wrapper539e8df61. No implementation, mapping campaign, proof campaign or physical retry accompanies this model.

## Current exact path and what it establishes

Completed-map worst eng_waddr[31] starts u_eng.u77846_c0.u_cell (DFFHQN) and has37 scalar levels/1238.6ps, versus frozen1256.9ps/38levels. These are unchanged textbook scalar weights, not STA, wire, slew, load or corner delay. Actual old routed/placed timing failure remains -810.5ps at real1666.667ps, with reported WC/ss labels bound to actual TT overlays. This model does not claim recovery.

Static actual FF capture ancestry binds start to d_data[113], ring bit1. Path16437/16440/16443/16446/16449/16452 AND5 then16456 NAND5 successively covers ring descriptor112:140, followed16580 NOR5 involving remaining ring141:143 and stack/row inputs. It then traverses16582..16604,16846/16860/16861,16946/16948/16976/16977,17125..17277 and19428/19429/19431/19462 to w_addr31. Full master/pin/net chain and growing exact FF capture ancestry are attached. Public equation names were removed by mapping; ancestry is reported instead of fabricated source-net aliasing.

The arithmetic prefix has base descriptor16:45 and stride48:77, gs/stack inputs and rowlow4, but no pitch80:84. This is structurally the IKEY CODE-address family, not the ROWS pitch-product family. This is cone/field provenance, not a transaction sensitization proof. Ring nonzero steers the stack operand before carry propagation; helper-prefix substitution left this global dependency intact.

Using unsigned32 modular arithmetic, original equations are:
 rbase = base + (ring!=0 ? 0 : stack*stride)
 blk = (rbase + (sb<<11)) + (sb<<7)
 code = ((blk + ((1+q[5:2])<<7)) + (q[1:0]<<5)) + ((row&15)<<1)
 code_output = code + phase.
The current changed helpers replace individual add/product boundaries, but preserve this serial equation structure and early ring choice. That explains why local prefix helpers alone did not produce material whole-cone improvement.

## One zero-extra-edge option, not an adopted candidate

Compute complete ring and nonring addresses in parallel; compress all shifted operands in a balanced carry-save tree and perform one final prefix carry, then select the complete ring/nonring result. IKEY nonring has ten operands:base, three possible stack/stride partials, two sb shifts, qgroup, qlow, rowlow and phase. A10->7->5->4->3->2 reduction has five CSA layers followed by five prefix stages. Ring branch omits stack partials. The ring predicate would feed only the late result select rather than all downstream carry stages. ROWS must receive the same complete-branch treatment (base+stack3+pitch5+sector), otherwise it may become the worst path.

This is a materially different dependency model, but there is NO measured mapped gain yet. Current37-level scalar sum cannot be replaced by an optimistic CSA stage count: actual mapped masters, reconvergence, fanout, output mux and synthesis refactoring matter. Existing synthesis module-retention hooks might preserve complete branch boundaries, but their actual use needs qualification. Source4-state semantics must preserve the ORIGINAL conditional merge and every original +/* poison boundary; algebraically distributing a conditional under X is not generally equivalent. No new masks, simulation-only assumptions or inferred initialization are permitted. Therefore this packet does not establish a credible quantitative timing recovery sufficient to authorize another gate. Owner may select a bounded source/map-only experiment separately if this structural option is wanted.

## ONE existing registered alternative: APIPE=1

Existing production APIPE=1 registers s_raddr/k_code/k_scal/ownership into ap_* and gates stream issue by ap_ok. No new opcode or invented stage is needed. Dispatch invalidates ap_ok. On the next edge, the current row address is captured and ap_ok becomes1; earliest first-sector acceptance is the following edge. Relative to APIPE0 this is one address-valid bubble per nonempty ROWS row or IKEY key (including the first after dispatch), independent of the number of sectors in that row/key. Existing unrelated FIFO/backpressure stalls can overlap the bubble, so elapsed-time increment is bounded by, rather than always equal to, the number of affected keys/rows.

ROWS: ap_inval at each accepted st_row_end, then one refill edge before next row. In-row sector issue remains unchanged. IKEY: ap_inval at accepted phase2 unless rowlow4==15, or at accepted phase4 for the group-ending key; there is one refill before the next key. At rowlow4==15, phase2->3->4 scale writes remain contiguous subject to original readiness; no added bubble between phase2 and group scales. RAW explicitly bypasses ap_go and retains its issue timing; QKV has a separate path. Empty/padding paths do not acquire a promised data transaction.

APIPE1 leaves done_v/done_tag unregistered (only APIPE>=2 selects done_q), and n_sectors counts current w_fire (only APIPE>=2 selects wf_q). Thus no additional retirement edge is inserted after a final write; overall done can move later because stream issue moved. For an isolated unstalled nonempty N-row ROWS or N-key IKEY segment, stream progress pays N refill cycles; at1666.667ps this is N*1.666667ns. Programme/compiler static budgets and connected ready/credit schedules must price those bubbles, and whole-die release remains UNQUALIFIED until that owner acceptance. The long arithmetic becomes reg->ap_* rather than reg->OUT; it is not eliminated and still needs actual timing qualification. Historical source comments already record that even APIPE2 once retained41-42 levels, so APIPE1 is an architectural fallback, not a promise of closure.
