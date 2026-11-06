# SU native boundary preparation

This is source preparation, not a signed-child parent implementation. No P&R was launched. The retained t11 native SU profile has MLAT4/ALAT4; the current signed lane1 is MLAT5/ALAT3 with physical input/output faces. Their phase contract remains to be measured and composed before child substitution.

The authoritative controller source consumes bank read words0..3 for operands and word5 for drain, while word4 feeds the paired lane VI locally. `su_compact_boundary.py` makes the controller bus160bits/lane, preserving the native local VI connection, and removes only the corresponding explicit compose output references. It also narrows the write-address boundary to18bits: all bank row and identity checks read bits17:0; upper six bits terminate in unused native output wires. Existing narrower cut ABIs remain unchanged. Every affected private module gets an explicit new name.

The actual private compose_t9 cohort contains112 such six-reader cut entries. It is83MB and stays in retained scratch; the helper records its SHA. `prepared_profile.json` names exact original inputs and transformed instances. Original source is preserved in `ot_hbm_su_static_pgslice_s.baseline.sv`. Preparation uses the original source basename when deployed so Yosys primitive source names remain stable.

`boundary_static_miter.v` proves the exact packing for every operand on32lanes, all four drain h/hi selections, and every write-address selection. Yosys SAT passes MUT0 and rejects wrong drain-word MUT1 and swapped operand-word MUT2 (`boundary_proof.json`). The first dynamic-mux formulation was stopped after it unnecessarily used3.7GB; no result is claimed for that formulation. The static exhaustive formulation finishes in seconds.

Actual private deployment is epyc2:/srv/opentallas-scratch2/claude/codex-su-compose-1106/source_candidate_addr. The earlier source_candidate contains VI-only preparation and is superseded. Neither candidate has been elaborated or bound. HBM owns composing this with WBQ/p28 source profiles before one fresh complete asbuilt/bind.

Remaining: exact native pair-to-p17 mapping; physical face retiming; MLAT/ALAT operation phase proof and token pricing; regenerated boundaries and actual16child hierarchy. A blackbox station liveness probe conservatively retained all768bank bits/group, but deeper controller tracing showed word4 is semantically unobserved externally. Do not interpret station liveness as a proof that hiddenVI must be exported.
