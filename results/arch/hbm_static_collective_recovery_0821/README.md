# Current HBM static collective recovery

Actual component positive and hardware-mutant gates, source pinned in each receipt. These prove component behavior only; no physical, full-token or die qualification is inherited.

- Issuer: E4 unit5236-1792077823, 131184 instructions, three actual mapped SRAM models, 64 rows, 1536-bit payload, 2048 repeats. Data mutant rejects exact mismatch.
- ARGMAX: E4 unit5391-1792077824, G96 five rounds exact; tie mutant returns17 instead of5 and rejects.
- VM writer: AGI unit380514-1792077825, 77 checked outputs, 23 full-bank cycles, RGX4x512 and TKW568, low C+1/high C+2; payload mutant rejects.

Source runner run_current_leaf_gate.py accepts issuer/argmax/vmwrite and an absolute output directory. Heavy work is through ot-run with8GB and2threads. All three jobs have finished. Initial precompile runner name typo was corrected in51afc824a; these receipts are from corrected literal testbench names.

Current v15 die still binds q3/q2 V1: this differs from the V4 host candidate in endpoint width596 versus612, TX3 versus TX6/RX2, host programme interface and clock roots. They cannot be deduplicated as replicas. V4 remains candidate until actual die adoption. Current source issuer/writer are shared components; ARGMAX is V4 successor only.

No current v15 physical leaf slot grant is confirmed. Old v14 ot_hgi_coll_pring_state and add_lane grants do not name actual static_state_lane and static_add_lane. Physical owner requested current grants from HBM die lead. Do not launch guessed rectangles. Existing capture prototype CLOSED is preserved.

Claude full-shape TKM re-proof remains independently live E4 PID3932887 (local ot-run3949887), /srv/opentallas-scratch/claude/hcoll-tkm-full2-1015. Read-only recovery found g1_n100_k2048 PASS200words348cycles and partial-port case PASS34words264cycles, while own-list NaNFFFFFFFF remains fault-missing OPEN. IDX producer validation owner has received exact source and fixture pointers.
