# SU8 lane-local stride mux repair, 2026-10-20

Original gate actual mapped census FAILmax52 (20697roots); failure netlist/report/snapshot preserved in results/arch/qw_su8_1020/native_repair2252. Backtrace shared xs_nx stride muxes feeding eight lane multiplier cones. R1 plain per-lane mux replication still FAILmax73 because ABC absorbed selects into multipliers; preserved R1failure.

R2 independent kept accept flops and parameter-unique12bit mux module boundaries produce actual ORFS native PASSmax32,22399roots; physical mapped area3416.12um2. V5.050 lockstep11787PASS, x-initial uniquePASS, wrongstride11757fail / earlyaccept23102fail witnesses committed. RTL hashes verified against run candidate.sha256. No added pipeline/command/boot edge; existing c_su6 remains. No layout qualification yet.

Checklist: registered pins/control reset landed2rawcontacts unchanged PASS; outline reach<405PASS; native32PASS; depth checked by textbook candidate receipt; storage control/pipeline only (no table) PASS; pin-bound outline/aspect/density unchanged full std band, measured area~16% PASS by existing fill_reason; clock same root, spread awaits gate; schedule unchanged/static PASS. Gate must recheck timing/clock, geometry, and GRT; no waiver.
