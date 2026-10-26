# S81 head CUT-A: corrected SK7 component replay

The existing CUT-A binary passes all 253 production tile cases. Each tile's 128
logits matches its golden values: 32384 logits total, bundle latency 8345 stream
edges, tile fault 0. The causal wrong-ROM case fails as intended: tile
`u_t_S01Er3` reads `u_t_N00Wo0` images and returns row 21993 instead of 21946.

This is **PARTIAL head evidence**. CUT-B was not executed in this collection;
the original full-head `raw/result.json` therefore keeps `ok:false`. It is
copied byte-for-byte and never rewritten to PASS. `receipt.json` separately
states the narrower CUT-A component result. No complete head, layer, token,
current die binding, or physical qualification is claimed.

The replay fixes the inherited image skew 8 to the actual NC1 FP32 adder LAT 7
profile. Source recovery is 72bea18b900ec722de4d5ee9d56dbabd481db83b.
The original compiled binary is reused unchanged, SHA256
`ef0e1d076b96233b8a1559b1fdf85a035edacea9a4e39ac2dbe653f82d98845d`.
No compile or new replay was launched by this collector.

The original PVE1 invocation could not load its system GLIBC/GLIBCXX versions;
All 253 original failure logs remain under `original_environment_failure/a/`.
The successful replay used a task-local gold1 loader and four shared libraries
through the collected `runtime_runner.sh`. No executable or shared library is
committed. Their exact identities are retained in `compat_identity.sha256` and
`identity.json`, alongside the source/ROM/fixture/strict-bind hashes. Original
build source identities and generated Verilator build metadata are retained.
The source continuity assertions check the original bound RTL, testbenches,
die.v and port_bind.json against the collected current source hashes.

Successful job: gold1 unit `oth-ubuntu-659357-1792640255`, exit 0. Its complete
client log is `compat.otrun.log`. The aggregate runner prints `HEAD_CUT FAIL`
because its full-head report requires CUT-B; the separately checked actual
CUT-A and mutant verdicts are preserved verbatim.

`raw/` contains a.json, original result.json, rec.hex, all 253 tile logs, the
mutant log, exact file lists and run input hashes. `identity.json` includes
the corrected image inventory, original build metadata hashes, source paths,
resolved paths and binary/runtime identities. The raw golden fixture remains
at the pinned fleet path; its checksum is in that inventory.

Validation: `python3 results/token_pass/s81_head_cut_a7_2000/validate.py` checks
the existing logs, counts, latency, causal rejection and identity continuity,
then writes only the scoped receipt. This is evidence collection, not an
additional qualification campaign.
