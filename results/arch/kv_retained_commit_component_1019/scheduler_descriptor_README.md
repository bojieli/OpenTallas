# Accepted descriptor error race regression

The private scheduler source frozen in `8858a45b0` (SHA256 `acf1208a092735df94d7555f76b19c9971b9ae4701e9dcbdc96c02a8ab5b14c2`) passes 30 positive cases: the prior 26 H12 cases unchanged and four new H40 descriptor overlap cases. The default-off miter compares all 57 original output ports; six prior causal mutants, one new descriptor-drop mutant and four invalid configuration refusals all pass. See `scheduler_descriptor_receipt.json` and `scheduler_descriptor_evidence.tar.gz` for exact files, hashes and fleet units. All simulations used fleet Verilator 5.050, 32 GB admission and eight build threads.

This is conditional scalar SU component evidence. NSLOT1/ENG_CTX1/MODE0/MU_OUT0/NW18/PLB13/FMT1 remain selected. New cases use fixed H40/deadline8 to retain an actual accepted step while the genuine second SQ descriptor finishes DMA validation. No force, deposit, hierarchical setup or altered DUT state is used. Hierarchical reads observe event admission, pending state and priority. The independent DMA responder legally delays the final second-descriptor word in case27 until the fixed cutoff; all other source inputs use actual CSR/DMA/engine interfaces. Original 26 cases retain H12/deadline8.

| Case | Result |
|---|---|
| 26 | Second accepted clienttag1235 reaches D_ERR with slot0 busy and an owned pending step; exactly one ST_SLOT completion plus one healthy owner completion. Error enqueue edge58, error word0 edge64, owner word0 edge95. |
| 27 | Legal delayed descriptor data causes actual D_ERR plus certified engine event priority at edge89, dp_ok false. Descriptor holds and enqueues exactly once edge90; owner completion precedes the one ST_SLOT completion. |
| 28 | Foreign-tag descriptor error CQ word1 stalls, then health fault arrives. Its offered word0 converts to ST_FAULT, does not consume the owner report; the owner1234 subsequently emits its own one fault report. |
| 29 | Same fault interleaving with both descriptors clienttag1234. Explicit per-event owner record distinguishes them; the descriptor error cannot consume the actual owner report despite equal tags. |

The immediately preceding source `26a737ff9c0e325baa45846abbcf4246fd93290f8f87b958f0070d8f065cde42` passes26–28 but fails29 at edge67 with `DESC_FOREIGN_CONSUMED_REPORT`; its source, bench, build and all four logs remain under `scheduler_descriptor_history_26a737/` in the archive. This is a causal source regression witness for the owner marker. Earlier source `547f8188db0df993799272336b6745c1e2f56a8429107dc9d8d81d5d43bc4416` and its full history remain in predecessor commit `c7dfb37e8` and its `scheduler_run_receipt.json`; no earlier results were overwritten.

The new mutation restores the faulty D_ERR condition that exits on temporary !admission_ok. Case27 records `DESC_PRIORITY_COLLISION` at89, one healthy owner commit at97 and no `DESC_PUSH`, then fails `DESC_MISSING_ACCEPTED_ERROR`. Its source/bench and failure log are committed inside the archive. The timeout is a finite bench observation bound, not a build resource limit.

Reproduce by placing the frozen source at `private/ot_host_if_pb2_observed_rc.sv`, then run `bash scheduler_descriptor_run.sh`, `python3 scheduler_descriptor_mutant.py`, and `python3 scheduler_descriptor_collect.py` via unpinned ot-run. The unchanged original module snapshot and all renamed baseline runners are included. Remote completed run: `/srv/opentallas-scratch/claude/scheduler-descriptor-regression-1019` on ot-epyc6. The archive excludes compiled objects; the remote objects remain available for pickup.

Still OPEN: native health/identity binding, production phase and H/deadline, full retirement plane, MU4, physical indexed SRAM/reset/fanout/timing, complete transaction-language proof, and actual host/cache transport retention. These functional component results establish no production, native or physical qualification.
