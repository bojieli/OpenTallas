# HOST program service and boot completion source closure candidate

These are RTL source/integration benches, not die physical qualification or full-token qualification.

`qkd_host_program_loader` stages 1024 program words and 8 descriptors in real synthesizable storage, checks ordered addresses/counts plus an explicit trusted external epoch/digest authorization, and replays pr143 on exactly 1032 consecutive cycles. The actual qkd_host_ctl consumes the output and broadcasts the same write fields in HC181. Replay has no credits or ready gating. The digest is transfer integrity, not cryptographic authentication; external auth inputs require an assigned real ingress. Execution must remain held until program_ready has traversed the receiving HC/program-write stages. It is invalid to treat program_ready as proof of remote write visibility. The current die contract lacks an assigned program-service transport producer, so this leaf alone does not close that integration gap.

`qkd_hbm_boot_static_completion` composes the real boot checker and switch with an observation-only ordered ledger at actual ctrl_es launches. qkd_ctrl_pc_host supplies actual WDONE17 column retirement events; er259 is not completion. Four boot retirements and successful pattern readback are required before normal service. Only normal events reach qkd_host_static_pc_emback's owner ledger; its actual host write ACK is checked after physical retirement. The observation ledger has 64 statically sized entries, faults on overflow/ghost/type mismatch, and never gates issue. Its completion output adds one ck cycle. Boot static command and normal response each retain the existing one registered edge. Compiler integration must account for this extra observed-completion stage. Cold boot rearm requires reset; a second boot_go is rejected.

Exact bench: full1024pw8dw loader and actual qkd_host_ctl; real qkd_ctrl_pc_host boot four commands then normal host write/landing read through actual qkd_host_static_pc_emback. PHY return data is the declared external HBM boundary model. No on-chip results or completions are supplied by C++.

Mutants: missing program replay, wrong completion owner, and er259 early-credit substitution each fail observed bench assertions. Clocks/reset/pins, TT setup/FF hold/DRC and final die binding remain required.

Reproduce through ot-run memory admission using tools/qwen_host/program_loader_gate.sh OUT [0|1] and tools/qwen_kv_die/bench_hbm_boot_completion.sh pc OUT [0|1|2]. Mutants intentionally return nonzero. Only small run logs are archived; build products are disposable.
