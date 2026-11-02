# HEAD sixteen load aliases: source diagnosis

The rejected direct `ld#t[0..7] == ld[0..7]` aliases need correspondence of the selected unreset FIFO slot. The exact retained profile lacks all 24 low-bit slot relations per lane. Reset64 establishes the control state, but it cannot initialize those payload slots. The observed native STEP DIFFER and unknown BASE therefore remain rejected candidates; this source diagnosis establishes neither a DUT mismatch nor equivalence.

The subject is the immutable Intel2 `codex-head-lep-wave-1101/kit-wave/s81_head/l48x/items/hd_mesh/attempt_2/gen/hd_mesh` capsule. The bounded native results remain in EPYC2 `codex-head-native-lemma-r3-1102`. This packet only reads the exact source, mapped netlist, maps and retained 12732-relation profile. No native proof, new hint, RTL change, reset change, comparepoint reduction or invalid-cycle policy change was performed.

## The sixteen bits and their actual load cone

For both lanes, the last t3 slice starts at global bit `432 + 7*16 = 544`. Its low eight bits are global frame bits544..551. They are real reserved-zero frame bits, not the seven width-extension pad bits: local bit8 is global552, the constant-one last marker. `ot_s81hd_best64_rx` drives `frame={1'b1,455'd0,body}`. The retained profile already establishes `td_q[0..7]=0` on gold and the transformed gate counterparts. It retains `q0/q1/q2#t[8]` correspondences for the marker bit, but zero low-bit slot correspondences. `retained_profile_extract.json` records this for both lanes.

The source transition is:

```
push = tv_q && n != 3;
send = n != 0 && c != 0;
qj' = push && wp[j] ? td_q : qj;
ld' = (rp[0] & q0) | (rp[1] & q1) | (rp[2] & q2);
lv' = send;
```

`q0/q1/q2`, `td_q` and `ld` are unreset. Reset sets `rp=wp=001`, `n=0`, `c=8`, `tv_q=0`, `lv=0`; it does not write the queue. During a 64-edge idle reset, every-cycle `ld` continues reading arbitrary q0. The concrete mapped bit0 D cone is an INV/OA222 network driven only by the three RP flops and the three unreset q-slot flops; the six exact leaf instances and physical QN connections are in `ld0_mapped_D_cone.json`. No age shift, reset insertion or alternate source was found in that mapped cone.

A direct ld equality does not imply equality of q0/q1/q2 in an induction state. For example, equal current ld values and different selected q0 values make the next ld unequal. This explains why an isolated ld alias can fail STEP despite identical source equations. A concrete native counterexample was not regenerated here.

## A guarded temporal relation to prove

An explicit history predicate `written[j]` can start false on the slice reset and become true after `push && wp[j]` loads a known-zero td_q. It is a proof-history predicate, not a proposed RTL register. For each low bit:

```
written[j] -> qj[i] == 0
selected_written(t) = OR_j (rp[j](t) && written[j](t))
selected_written(t) -> ld[i](t+1) == 0
```

The FIFO occupancy/one-hot/credit obligations must establish `send(t) -> selected_written(t)` and therefore `lv(t+1) -> ld[i](t+1)==0`, after the actual reset and constant-input pipeline settling. A stronger eventual guard is all three slots written: after that point every raw ld value is zero until a new reset invalidates the history. The three-slot write history and the paired control/constant-load relations are the missing prerequisites, not an assumed zero power-up value.

This guard cannot silently close the existing raw invalid-cycle comparisons. Before any slot write, lv is false while ld can remain arbitrary. Every original comparepoint, including invalid-cycle outputs, stays present. To close those raw values, the proof owner needs an accepted correspondence treatment for arbitrary initial payload state or an exact supported native temporal relation. This packet supplies no equality-base assumption and no valid-only waiver.

## Replica relation is separate

In the endpoint source, `rep_ra[0..1]` and `u_k_rep_o.q` have the same D expression `accept_a ? rep_1 : rep_0` and reset value0, but use reset leaves2 and14. A candidate equality needs the actual reset-leaf release/control relation and common-edge obligation; the existing profile only relates gold rep_r to gold u_k_rep_o.q. No new replica relation is accepted here.

Those endpoint replicas control replay selection downstream. They are absent from the direct mapped ld D cone and cannot initialize the three unreset slice payload slots. A proved replica relation may help other load/credit cones; it does not by itself satisfy the sixteen ld BASE obligations.

The next finite proof, if separately authorized, should target the selected-slot load/history guard and retained raw initial-state correspondence. Replaying the same sixteen unconditional aliases with only the replica equality would leave the identified base gap unresolved. The four KEEP and two hunt proofs remain separate evidence and the original failed full verdict remains unchanged.
