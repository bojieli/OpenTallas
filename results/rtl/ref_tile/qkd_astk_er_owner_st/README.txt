Distributed owner-local ASTK e-read component, 2026-10-18 Codex takeover.
Eight real qkd_astk_ep_s and their 32 mapped e SRAM macros are instantiated.
The benchmark supplies external write rows on each actual EP's ri pins.
Expected answers use the independent word(owner,row,quad) function. No DUT
internal memory or arithmetic is supplied by a reference or force statement.

Production shape: N4, 8 owners, 512 consecutive issue cycles, 2048 exact reads.
RL1 = 28 edges; RL2 = 35 edges; RL3 = 42 edges, all measured PASS.
Fixed compiler calendar: local aso offset 2 + owner*(2+RL); final response
7 + 7*(2+RL). Request and response forwarding are both 2 pin-register edges.
All stage links use resettable qkd_astk_rly_296 wrappers (qkd_astk_phys.sv).

Mutant 1 removes local committed-group visibility check: FAIL 1 error.
Mutant 2 substitutes adjacent owner in valid insertion: FAIL sticky fault.
Mutant 3 bypasses esi input register: FAIL 1984 data errors.
Witness logs pin Verilator5.050 and positive/negative result strings.
This is a native component gate; full ASTK expansion geometry, routed masters,
clock pair budgets and die production token/layer integration remain required.
Initial gate failure was a sparse staging dependency omission (orfs_allcorner_spef.py),
not an RTL/timing failure. Its failure log/source manifest are retained.
