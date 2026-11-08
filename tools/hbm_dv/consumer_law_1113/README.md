Private HBM absolute consumer law
================================

Run `check.py results/token_pass/hbm_consumer_law_1113` to read existing
records only. No bind, RTL simulation or physical flow is launched.

Inputs are actual E5 scratch3 `codex-hbm-lat-1113/r8_vB` landing table and
`bind_lat_vC/param_regen.json`, for private R8 candidate source
codex/hbm-lat-1113@a0fc89b543. Current accepted plan59659c65f22a remains
unchanged. Landing table is compacted to actual loops/legs/cost and includes
the SHA of the full existing artifact; actual param_regen is unmodified.

All four LG variants on both NW/NE independently sum their actual SFU tap
return plus actual C request/return legs to external125read/122write.
The real K2/2 bridge consumes absolute127read/124write. The gate checks
the derived variant law AND actual changed[] emitted parameter records.
Old145/142 and blanket97-added parameters are rejected. Maxpad97 and
1,872,747 pad flops are cost facts, not a token-cycle increment.

Native K2/2 mechanism proof is separately published on canonical
codex/hbm-kcls-1113 (29c3/d503 source), results/hbm_sfu_bridge_1113/results.json:
good has fault_first−1/bad_stage_data0; stale boundary145 has fault129 and
5435bad words. The gate does not relabel that native proof as full finalLAT.
FRRDX91 is another operand loop2+41+48; its final LAT join remains open.
No candidate adoption, production schedule change or final bind closure is
claimed here. The owning HBM lane retains the healthy final-LAT bind.
