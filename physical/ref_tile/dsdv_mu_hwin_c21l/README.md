# HWIN22l guarded structural successor

No gate authorized until ROOT planning-budget tooling is reviewed/deployed. Production hook fails closed. Source std_area_um2 remains9151.137; separate planning_std_area_um2 is11063.90178 from actual prior c21k CTS cells. The full source RTL/params/domains,84 SRAM origins and public edge counts are unchanged;0 added cycles.

Geometry uses three coarse W/C/E ownership regions instead of13 narrow strips or unrestricted placement. Reset leaf ownership follows actual first consumers; shared selector/config and event6..9 remain central. Fullwidth band y159.84..206.28 expands39.96->46.44um. Placement halo is8.64um (was10.8); macro origins/channels>=22.41um unchanged. South halo ends159.03 and north halo starts207.36, leaving the full band clear.

Exact native source/macro/port graph:59580 initial source identities (mapped source SHA4ea21c9...),567221 conservative complete endpoint-box pairs, zero role errors, max404.124um and zero>405. Native physical fixture confirms172 full-width rows,25880.0832um2 legal band, no halo rowholes. Retained measured-CTS area11063.90178 yields band42.7506%; region W50.0569/C56.2752/E51.0723%. Initial source-only area is not changed to make the sizing validator pass.

Causal proof: deleting one mapped reset FF rejects exact manifest; new unmodelled FF rejects runtime birth ownership;40-buffer chain inherits real WEST FF owner without a depth cap. Original row-hole280fragment/10.8halo model and original39.96band69.6%centre failure remain as rejected planning history.

SAFE: pins/reset landing unchanged and source registered; mapped native max32/zero violations unchanged4ea source; depth546.8ps unchanged; storage84 SRAM/86016bits unchanged; static0edges. Reach/source/native rows PASS planning; new actual placement/clock/pin/PG/GRT/SSFF and actual placed40..60 check still owed. Canonical generator correctly rejects current truthful source-only area until supported ROOT-reviewed planning receipt path is available. No REVIEW approval, route qualification or parent binding claimed.

## HWIN22m (S81-TILES-B, 10-20 05:10): gate on the planning-budget tool
- Branch claude/s81-hwin22m-1020 = 5b1c4a5d6 + Codex tool WIP d8f71e355 (tools/ref_tile/planning_birth_budget.py, ref_tile fill_check planning=True, receipt under results/arch/s81_hwin_birthbudget_1020/proof). Final WIP: test_planning_birth_budget 32 PASS locally.
- spec.planning_birth_budget = proof/approval.json (ROOT-authorized, source-bound, PLANNING ONLY). Guard line removed from hwin_native_fences.tcl. gen: fill WARN (lattice exception + planning budget), no FAIL.
- Submit waits for ROOT to merge the tool to main (submit uses main tools). The actual placed 40..60 band check, spread <=80 TT+FF, GRT0 and native reach <=405 still decide.
