# Causal calendar replay on the WN rank circuit

The corrected 241-stage calendar admits 50 AR users and six MTP users. This packet replays selected exact LINK5 resource timelines on the real four-lane WN rank A/B circuit with PHY, relay and landing legs. It does not qualify an entire stage or token. Idle gaps and all six MTP positions are preserved.

The three positive runs passed with zero data, tag or deadline errors: AR R001->R002 (32,000 beats), MTP R001->R002 (23,040), and MTP R120.A->R121.B (5,760). A causal same-user busy-slot injection creates a 326-cycle planned collision and the RTL replay flags 235 late beats in message1 while data and tags stay clean. The checker-only negative also faults.

The common 36-source manifest is pinned in each build/sources.sha256, with Verilator5.050 and the original binary hashes recorded in receipts. Compressed run logs preserve their original hashes. collection_check.json verifies the copied plan, run log and source manifest identities. Original jobs ran on ot-pve1 under /srv/opentallas-scratch/claude/tokb-rate1-1021/out_*. No build was repeated during collection.

The source update reads pipeline_graph directly, carries each message's graph receive bounds to the bench and adds explicit causal collision injection. The source-local calendar result remains MODEL evidence until current release RTL programmes complete. Use 47,642 aggregate AR and17,780 aggregate MTP as the calendar rates; no ten-user MTP or speculative split credit.
