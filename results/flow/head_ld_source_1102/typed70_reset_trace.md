# Typed 70-field source candidate and reset trace

This is source evidence for the single bounded diagnostic owned by flow. `UNTRUSTED_typed70_candidate.json` contains exactly54 slot fields (q0/q1/q2 bits0..8, both lanes) and16 load fields (ld bits0..7, both lanes). These are proposed named logical equalities, not accepted native assumptions. Resolve each gold key with the exact replayed L.gp and each gate key with L.tp; their AIG literal polarity is authoritative. Reject missing or changed keys. QN/IQN/#t spelling supplies no logical polarity rule. Existing marker-bit aliases are included in the typed domain, rather than counted as a separate new domain.

All70 fields have exact raw native map records and actual mapped primitive pin records in the candidate. The source and mapped hierarchy use the same positive-edge clock: top wrapper `.ck(clk)` to core, core `.ck(ck)` through lane/t3, and actual kept failing mapped slice `.ck(clk)`. Every qslot and ld primitive is DFFHQNx1 with CLK=ck and no reset pin. The qslot conditional write is implemented in its D cone with feedback; ld has no enable and loads every edge. The existing control state (RP/WP/TV/N/C, resets, clock) remains outside this payload-field bijection and must retain its established native relations and the exact prior context.

## Reset reaches the slice after a synchronous wrapper wave

The wrapper's external `arst_n` is a synchronous data input to an unreset relay chain. It is not an asynchronous reset directly applied to the70 payload fields:

```
edge1: u_rst_in.q = arst_n = 0               (rst_root_n)
edge2: u_rrl_0.q = rst_root_n = 0            (rst_rl_0)
edge3: u_rrl_4.q = rst_rl_0 = 0              (rst_rl_4)
edge4: u_rrl_5.q = rst_rl_4 = 0              (rst_rl_5)
edge5: u_rrl_6.q = rst_rl_5 & run_copy = 0   (rst_n_t5)
```

The core uses rst_n_t5. Each t3 child's own ot_rst_relay_tree3 has asynchronous assertion through root/group/local reset pins and synchronous three-edge release; the failing slice is local leaf7. In RTL event semantics, core reset assertion clears that tree and the slice controls through asynchronous assertion after edge5. Any native clocked encoding must establish its actual settling trajectory in the64-edge image check; no earlier native values are assumed here.

Before the wrapper wave arrives, arbitrary power-up control can cause writes. The payload always block does not test rn:

```
push = tv_q && n != 3;
qj' = push && wp[j] ? td_q : qj;
```

A write can therefore occur in the early reset-wave edges, including an edge whose post-edge reset assertion clears controls. It would be incorrect to model all64 asserted-reset edges as payload holds from arbitrary time-zero q values. The native diagnostic must propagate those actual early updates.

Once the slice controls are reset, tv_q=0, wp=rp=001, n=0, c=8, lv=0, cr_q=0 and ovf=0. As long as asserted reset remains, push=0 and send=0. The three qslots then hold their current arbitrary values; td_q continues to sample its source constants. ld continues to load RP-selected old slots each clock. At the first subsequent payload edge it loads q0, and by the end of64 reset edges:

```
ld_lane[i] = q0_lane[i], i=0..7
```

The remaining slot bits, including marker8, are not reset constants. The source-only expected projected image is54 arbitrary slot variables with these16 load correlations, not an independent70-variable cube. A source surjectivity witness exists by choosing initially quiescent/reset control and relay values so that no early writes happen and any54 initial slot values survive. This witness motivates the candidate; it is not a substitute for the exact native reset-image/surjectivity check.

## Typed compatibility obligations

For each paired qslot field, check positive-edge clock compatibility, no native reset, same effective write-enable/control relation and same logical td_q value (low0..7 are0; marker8 is1 after the actual source pipeline settles). Its feedback state remains arbitrary until a write. For each ld pair, check the same clock/no reset/unconditional update and RP-selected old qslot behavior, with no one-edge age shift. The mapped bit0 cone previously recorded the three distinct RP and three distinct qslot physical leaves.

The finite diagnostic must check the actual paired64-edge projected image, typed bijection/injectivity/surjectivity as required, and transition preservation in the exact retained context. Merely observing None on both sides is not a base check. Do not replace the correlated image with all2^70 assignments, assume initial zeros/equalities, add a reset, alter a failed alias verdict or mask invalid comparisons. The original full failed result and separate proven KEEP/hunt obligations retain their own scope.

If the proposed isomorphism is rejected, preserve that result and inspect whether native input/history/control constraints alter the expected projected image. No source change or wider proof replay is authorized by this packet.
