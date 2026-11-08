# H9B diagonal age normalization candidate

Default-off define `OT_H9B_WQDIAG` applies the historical WQDIAG mask to the current strap source. Without the define, the original winner expression is retained verbatim. It adds no register, port or clock edge; PIN CYCLES 0. No recipe, source_commit, POR, tag or live kit is changed.

Every push to slot p assigns wq_older[p*WQ+p] zero. The valid mask is reset; the age matrix intentionally is not. The winning row masks invalid slots. The physical netlist already folded the diagonal to zero. This expresses that synthesis-normalized winner function at the source.

Existing full captured cfg evidence at e9bcf0f700 / physical/die_plan/hbm_arch_cores/h9b_wqdiag/proof/result.txt is 16125 equivalent, neighbor-bit mutant32 unproven. That historical proof does NOT prove the current main cfg wholesale. Current routed i2 netlist versus the captured WQDIAG source is EQ25215 with shared OT_LEC_MEM_LANES=1, E4 /srv/opentallas-scratch3/claude/lec-iqn-1/h9b/run_fix/lec.json, mutant77different. This is not POR qualification.

Next: prove current selected cfg under the actual reset contract and source capsule, then an explicit source/recipe adoption packet. The historical recipe currently reads d34578d6f, so adding the define alone to that old source would not select this implementation. No physical rebuild or ECO is needed to test the captured routed function once source and proof-tool adoption are coherent.
