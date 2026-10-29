# BF G2 ICG control isolation: hook + intervention proof (CORES-EARLY-9, 2026-10-29)

Problem: BF G2 GRT-only trial (codex/bf-gap-0255-1029@6a8b07259, intel1 codex-flow-bf-gap-0255/kit) failed in 3_3 timing-driven
GPL: RSZ-3006, repair cannot insert a buffer before `mp_ck_T01004_icg/ENA` (whole ICG dont_touch), net `g_tcg.u_tc.u_cg.en`.

Fix (structural, no clock change): one BUFx2 between every ICG enable pin (ENA, SE) and its existing control net. The ICG,
its CLK/GCLK nets, master and site stay untouched and dont_touch; the repairer sees touchable BUF inputs.
Plan = Codex packer `enable_isolation.json` (2504 buffers, max 1.161 um from target, legal native sites), converted by
`mk_tsv.py` to `bf_enable_isolation.tsv` (sha256 2aa60725...). Hook `bf_enable_isolation.tcl` applies it in ODB, fail-closed.

Intervention proof (`prove.py`, run on the failed 3_3 checkpoint which already holds the planned core infra; `run_test.tcl`):
PASS. 2504 buffers on 2504 distinct ICG pins = ALL ENA/SE pins of all 1252 ICGs (0 missed); each BUF A on the pre-hook
net of its pin, Y a private net whose only load is that pin; all other 1,299,518 pin->net connections unchanged; 64,967
CLOCK-net pins identical; 0 overlaps of the FIRM buffers with fixed cells/macros. So the netlist is the pre-hook netlist
modulo 2504 identity buffers (exact, not sampled). Not applied to any physical trial yet.
