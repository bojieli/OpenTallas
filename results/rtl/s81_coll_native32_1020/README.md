# COLL native32 source recovery (gate BLOCKED)

**10-20 S81-COLL4: v8 (`OT_COLL_NATIVE32_OFF`, native_v8/README.md) clears the source blocker: depth 540.1 ps / 14 lv, native max32 (0 > 32, actual-Liberty PASS), 79,994 PASS + 4 causal FAIL, 0 added cycles. Layout still blocked on geometry (native_v8/README.md "Geometry blocker").**

`OT_COLL_NATIVE32` opt-in, default legacy safe4 unchanged. v3 candidate is current source: four complete same-edge10-bit NXT/UNA copy banks; separate same-edge ready-ack copy; separate complete rewind cones for sender state/address/ready; four additional same-depth reset leaves separate UNA compare copies from overloaded reset45 leaf. Balanced reset release unchanged, zero data/schedule edges. Native mappedFF16306 vs gatebaseline16261 (+45);55SRAM storage unchanged.

Native census baseline8roots>32 -> v1one(ok_c33) -> v2one(rewind_sender33) -> **v3zero,max32**. Native helper canonicalizeSYNTH_KEEP_MODULES retained; transparent BUF/INV collapsed census.55macro directions inferred in this scout—not independent pin audit.

v3 depth621.8ps/16levels, sender->replay address. BLOCKED>600: no layout gate, no README waiver. v4 attempted parallel skip-index mux/algebraic rewind equality: REGRESSED686.8ps/17levels and rep_ra0=35loads; rejected, immutable source/census/depth artifact native_v4. Next structural lever is bounded carry-lookahead replay calc or explicit priced static extra stage, after current clockprofile priority. Do not restore rejected v4.

Production boundary miter v1 and v2 nominalPASS79994, four mutantsFAIL (OLDREAD,collision,gearbox select/hold). Exact v3 full5leg rerun active: ep6 /srv/opentallas-scratch/claude/codex-s81-coll-native32v3-bench-1020/runs/m0..m4; sessions64563/67379/10955/62179/61231, units2687267/2687719/2687973/2688347/2688529. Collect logs before any future adoption. Source snapshots prior to v3 remain at own immutable native32,v2,v3,v4 fleet roots; original Claude gates preserved.

Floorplan model: existing paid706.32x540, std band259.2..288.0; effective702x28.8=20217.6um2, std9445 ->46.7%before new45FF. Macroface channel modeled50..66%tracks,55macros lattice>=25.9gap. Previous row-deletion-only GPL used fullcore density envelope; divergence cause hypothesis requires native hardfence qualification, not accepted as proved. Proposed structural packing binds all std cells to true fullband using native EXCLUSIVE placement group; beforeeveryDP explicit ownership+NEWcells-onlyseed for births, allstd bbox+nativePG/reach/timing checks. Tool API alone verified fixture under fence_api; no fullCOLL placement qualification yet. Never use old fake-core-shrink helper.

Original W_s4/E_s4b GPLfail artifacts live on CTRLpickup branch2087473b2. Original E_s4/W_s4b progress preserved; any WARN still blocked by baselinefanout violations. No submit/REVIEW.

Fresh immutable v3 production witnesses (Verilator 5.050, source1f6bc84e8):
`native_v3/bench/m0.log` PASS79994; mutants m1 FAIL20009,
m2 COLL_COLLISION_UNSAFE, m3 FAIL79775, m4 FAIL79760. All five fleet jobs
terminal. These validate v3 functional behavior only; depth621.8ps remains
BLOCKED and no physical gate is permitted.
