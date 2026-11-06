# h9b routed-proof correspondence repair

The physical h9b_vB core is SIGNED; its routed proof originally had 177 differences,
then 173 after the existing no-widen retry. It remains unqualified until an official
released proof passes. No RTL or physical constraints change here.

Two missing induction relationships explain the captured failure:

* `last[0:2]` all reset to zero and load the same constant when `desc_n=0`.
  Synthesis keeps one bit, renamed by the frontend. Late cross-side correspondence
  anchors that representative after initial merged-register discovery. The generic
  `anchored_word_proposals` closure exposes its siblings, then the existing reset
  filter and joint induction validate them and downstream structural closure.
* The unreset `wq_older[p*32+p]` diagonal is zero only after its own queue entry
  becomes valid. `lec_hints.json` proposes the source invariant under
  `wq_pv[p] || ent_q[p]`; both validity bits reset to zero. The age bit remains free
  outside this guard. The existing `loaded_base` and simultaneous induction must
  prove every supplied hint; none is trusted or assumed.

The exact captured RTL controller SHA is in diagnostic.json. Its
`physical_write_act` loop writes diagonal zero on the entry's push; the queue-valid
and physical ACT-valid updates carry that fact. There is no initialization of the
age matrix and no change to the 64-edge reset contract.

On the captured final no-widen AIG, automatic anchored-word and structural closure
reduced 173 differences to 37. All 32 own-entry loaded guards proved and the final
miter proved 25,567/25,567 points. Moving every guard to the adjacent queue entry
rejected all 32 guards and restored the same 37 differences. The toy anchored-word
regression exhaustively rejects wrong-output and wrong-alias mutants.

These results diagnose the existing proof, rather than certify a new released tool
bundle. Official certification should use a fresh private directory with the exact
captured RTL and routed netlist, the released patched tool bundle, and these hints
through the existing `--hints` option. Preserve the failed original proof unchanged.
