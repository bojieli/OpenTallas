# HEAD native clock-domain model PREP

The actual native parent ODB census independently identifies 10,303 FFs on `clk`,
13,509 on `pma_rck[0]`, and 2,086 on `fclk_in_coll_i0`. All four actual macro clock
pins bind `pma_rck[0]`; the hardened KP4 child's own 3,237 FFs remain internal to
that child. `actual_contract_summary.json` is the new strict consumer's receipt.

Inputs were read-only copies of intel2:
`/srv/opentallas-scratch2/claude/codex-head-collect-1030/parent_sizing/domain_census_v2/{parent,child}_clock_contract.json`
and `/srv/opentallas-scratch2/claude/die-head-38/src25r/source_plan.json`, with the
third KP4 instance/module inventory added as proposed by HEAD's geometry event.
The source ODB identities are parent
`1118e078bc2c5e9c908950794050fed56bb66d8b176cfc93614a66795e66a423` and child
`5e0cf83cae9ea31e173e7a25035b6e5749f0905bb8462e6bcd57afe8051e0a0f`.
Complete local witness copies are retained under
`/srv/opentallas-scratch/claude/codex-flow-clock-domains-1030/`.

The optional `clock.native_domains` contract validates complete parent clock-pin
census/counts, actual top module and ODB identity, exact macro instance/master/pin
net roots, and child census/root identity. `core_root` is the generated `clk`
input. A singleton actual `pma_rck[0]` port is represented as `pma_rck`; other
arbitrary aliases fail. The checked binding is consumed by macro entry planning
and recorded in reset-target geometry. It does not change reset RTL clocking.

Optional `planned_sink_sites` maps each root to explicit `[x,y,count]` planning
rows whose totals must equal that root's actual parent FF inventory. The core
planner selects only the `clk` rows. Legacy aggregate sink bins/sites fail closed
when this contract is opted in without qualified per-root planning rows. Native
NONE coordinates never become planning positions. Ordinary plans are unchanged.

No PMA period/source/phase, spatial placement, CDC/reset qualification, or physical
adoption is claimed. Existing PG/track checks are unchanged. Focused tests:
`python3 -m pytest -q tools/die_plan/test_native_clock_domains.py tools/die_plan/test_master_plan.py tools/die_plan/test_reset_tree.py`
passed 61 tests, including false module/master/pin/root/census/count/child/ODB
controls and default behavior equivalence.
