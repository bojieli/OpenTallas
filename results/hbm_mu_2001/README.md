# HBM single-user versus multi-user continuation

Claude's exact probe source is retained in scripts/mu_probe_claude.py. Collected fixed-bound results with H4320/4665.6/5184 pass its plan cut model; H3525.12/3784.32 do not. H4043.52 was still running at takeover.

These are diagnostic area and cut estimates, not production capacity or timing qualification. The original source adds 8 FUSED lanes per hub (16 total). The fork FUSED top has 32 eight-word lanes for D5120/NM20. The original probe therefore does not establish full FUSED workload coverage. It also omits R13 direction and multicast.

scripts/mu_r13_probe.py continues the same unit additions with the R13 lane resolver, face-affine replicas and one affinity iteration (as current single-user planS2). Four independent single-hub probes cover H4043.52/H4320 at the original 8 FUSED lanes/hub. A second self-contained runtime copy mu32_r13 changes only the FUSED loop to 16 lanes/hub and covers H4320/H4665.6. It retains the actual 32-lane coordinate width; controller area, complete programme/reduction correctness and throughput remain open.

Runtime: epyc1:/srv/opentallas-scratch2/claude/codex-hbm-2001/{mu_r13,mu32_r13}; h<height>_<nw|ne>.otrun.log files contain scope ID and eventual JSON. Jobs use ot-run 8 GB / 1 thread. Root owns the SU/MU capacity and scope comparison; TOK-HBM owns the complete price and bandwidth audit.

The published planS2 0.89/0.60/4.19 percent figures are conditional incremental hub latency only. Its baseline already contains bank k4 serialization, not charged by the original r25gq schedule; no complete SU or MU speed claim follows from those rows.
