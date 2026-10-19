# Qwen hybrid D8 source and lifecycle contract

MODEL ONLY. This packet binds the selected six small direct FF rings and three complete wide SRAM lanes to archived production source. It does not implement D8, recompile the schedule, qualify a macro, or clear any of the 109 effective-age failures. `ledger.json` retains every prior ordered chain, historical K/E/G/R0, actual producer/hop-0/landing/consumer port binding, and explicit unknowns. `derive.py` regenerates it from pinned Git objects; its local check is extraction/inventory integrity, not a simulation.

| Complete lane | W | Actual producer → receiver roots | Storage | Historical E/K |
|---|---:|---|---|---|
| W5 ag → CTLM | 10 | r135 → r54 | FF direct | 16/7 |
| W5 dd → native59 | 548 | r135 → r54 | 9 SRAM | 19/2 |
| W5 ss → CTLM | 107 | r135 → r54 | FF direct | 16/7 |
| collective cmd_free → SYSFACE | 1 | coll → d2d | FF direct | 19/5 |
| collective fault → SYSFACE | 1 | coll → d2d | FF direct | 18/4 |
| collective shared_fault → SYSFACE | 1 | coll → d2d | FF direct | 19/5 |
| native59 dr → W5 | 520 | r54 → r135 | 9 SRAM | 19/6 |
| CTLM cmd → W5 | 116 | r54 → r135 | FF direct | 18/5 |
| CTLM hr → W5 | 453 | r54 → r135 | 8 SRAM | 19/6 |

These K values are historical D4 straps, never proposed D8 constants. D8 requires four genuine K pins and mod16 counters/epochs. Source-derived physical epoch and first-use proof is missing; all nine adoptable K values remain NULL. Actual chain cardinality is recorded separately from historical `n`: shared_fault has27 instances against historical n26, dr has27/n26, and cmd has25/n24. Neither number is silently substituted for the other.

The exact 1757 original payload bits remain in order. For each independent lane, the proposed record has payload in `[W-1:0]`, four write-epoch bits in `[W+3:W]`, and written-valid in `[W+4]`. Wide records use consecutive64-bit slices over complete lanes; high unused bits are padding. The original payload's semantic valid, mask, user and command controls remain payload, distinct from transport validity. External eight slot-valid bits clear asynchronously because the SRAM has no reset. Macro-valid alone cannot suppress stale startup state. Mod16 epoch equality also aliases after16 writes; it does not replace an explicit bounded-age and reset lifetime proof.

Source field ownership is concrete where the archived source supplies it:

- `ag`: registered OR of upstream status and `{stn_busy,any_fault,su_fault,vm_fault,stn_fault,sc_fault,stm_fault,port_fault,!su_idle,sc_busy}`; no payload valid bit can be invented.
- `dd`: `[547]v,[546:545]kind,[544:537]mask,[536:345]eight24-bit addresses,[344:89]eightFP32 words,[88:0]reserved`. Both pass-through and local words enter the same registered `ch_dn_o` output. All bits remain in the ring.
- `ss`: `[106]ar_v,[105:74]token value,[73:70]sid,[69:63]faults,[62]su_idle,[61]sc_busy,[60:45]su_prog,[44:29]su_rows,[28]rank2,[27:26]MU user or rank,[25]last,[24]token-valid,[23:0]token index`. The source expression and MU interpretation are preserved verbatim.
- `dr`: `[519]valid,[518]group,[517:512]beat/index,[511:0]data`. Attention group0 explicitly forces bit517=0; embedding group1 carries the six-bit index and scale/data selection. Do not treat the whole six-bit field as attention beat.
- `hr`: `[452]go,[451:73]379-bit permuted IB,[72:1]XPF,[0]hv`. Upper380bits come from the separately clocked hard-head publication plus a combinational permutation; lower73bits are a separate CTLM NBA register. The full453-bit word must stay coherent; the previous low73 proof does not certify the upper origin.
- `cmd`: complete116-bit calendar word; `[115:112]destination,[3:1]kind,[0]issue`, with kind-dependent controls preserved. The archived CTLM delegates to `qfd_dv_cmd_cal_mu`; this packet does not invent its missing production source publication/first-use contract.
- Collective `cmd_free` is the combinational `cmd_free_next` prediction, including captured command controls and current collective state, rather than a proven output FF. Production `fault` is an OR of collective/shared/20CDC/5abort signals from multiple roots. `shared_fault` is delegated through the transport hierarchy. A top-level `coll` connection alone cannot prove one root/epoch for these cones.

The source-reset distinctions are material. All nine lanes use different top-level producer reset, hop-0 enable, landing read reset, and consumer reset nets. For HR these are respectively `n_rst_seq_ctlm__t25`, `n_rst_seq_ctlm__t32`, `n_rst_field__t97`, and `n_rst_field__t1774`. They may share upstream ancestry, but exact net names do not prove coincident release or native phase. Declared `G/R0` remain historical calendar metadata. The complete binding dictionaries are in the ledger, including every auxiliary collective clock.

At source publication S, NBA registers expose the new value after the edge. A simultaneous hop-0 capture observes the old value. Existing forwarded-clock stages invert each clock and retain their source-pinned half-cycle capture ordering. The landing write W stores its pre-edge input into the selected slot and increments its counter. The six direct FF candidates use an8:1 read mux directly into the external output register at R. Their selector fanout, mux depth, reset forest and clock load require their own mapping/timing proof; gated-read native numbers do not apply.

For the wide SRAM candidate, R launches the synchronous native macro read from the pre-edge selected address. R+1 publishes the external registered output with aligned epoch, selected external valid, expected epoch, run and fault. That preserves the *gated candidate's* R-read/R+1-output structure only conditionally. Production direct D4 publishes at R. A receiving source NBA pin register at R+1 observes the old external output, so its consumption is not silently the same event as macro output publication. The parent compiler needs actual consumer edges before any price can be computed. Advancing the SRAM read to R−1 is not justified by the old budget:0.25T−210ps is already−1.667ps before macro setup. The boundary audit a6343c77a supports actual clocked SRAM write storage; no extra1521 input FF or W+1 is mandated by that audit.

Cold and warm reset must asynchronously invalidate all eight external slots even when either clock is stopped; payload/epoch SRAM contents remain arbitrary. Read release, counter/K capture, output zeroing and fault reset must follow actual registered face resets. Eight real writes fill slots, adding four source write opportunities versus D4. This is not a first-use proof or an absolute token delta. A resumed read clock must not accept stale macro output or a prior in-flight read. A restarted producer must not alias an older epoch/slot. A source-derived warm-fill, first legal selected slot and receiver-first-operation ledger remains required.

The exact native macro forbids simultaneous same-address cross-clock R/W. Every proposed capture must prove physical-time exclusion for all legal phase/reset/restart cases. No OLD or WRITE_FIRST assumption is available. Eight slots, a nominal K or an epoch comparator alone does not prove the exclusion. Native TT/FF/SS setup/hold on payload, address, enable and mask to wclk are present; macro contacts are nevertheless a physical HOLD at0.096um pitch=10.4167/um. No substitute view or geometry is introduced here.

The smallest useful next source proof has two distinct architectures: one complete W10 FF lane for direct8:1 R publication and one complete W453 HR SRAM lane for R-read/R+1-publication. The latter must include all380 hard-head command bits plus73 local bits, not a low73 surrogate. Both need source-authorized epochs, real producer/consumer reset release, earliest legal operation and stopped-clock restart. Directed causal controls should change K, one stage, half-edge phase, valid invalidation, pending-read reset, source halt/restart and forbidden collision. A numerical mechanism may intentionally retain the original HR age16-versus20 failure; the witness cannot be edited away. These are proposals requiring a new ROOT grant, with physical source changes still blocked; no proof vehicle was built or launched here.

Inventory remains26 macro instances/52 clock pins/14393.328768um² before soft/PG and4672 declared soft FF. Those are inherited analytical counts, not native implementation measurements. Source first-use, real phase, K, total clock/reset/PG cost and token price are NULL. All109 schedule failures, nine D4 window failures and HR512/512 failure remain HOLD.
