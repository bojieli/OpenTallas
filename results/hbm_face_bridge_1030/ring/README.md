# Current-native RING face source bridge — component closure

The actual physical RING has879 input and1345 output face FFs (2224 total). The candidate source wrapper adds those exact per-port FFs around the CURRENT preferred native g4 cut. Clock/reset/strap pass through with zero added edges. This proves the source form of the physical component; it does not claim zero-shift replacement into the old whole-parent calendar.

The first strict comparison exposed a real reference-model bug. `ot_hgi_coll_ring_ag_ctl` used `always @*` around a call to `flit()`, while that function read runtime globals `gath`, `tx_result`, `qid`, `tx_dst`, `tx_ttl`. Hidden function dependencies made outgoing packet headers stale depending on signal-update order/wire presentation. Raw actual g4 failed atcycle7; aggregate/scalar wiring diagnostics still failed. No reset/valid/output masks were added. A one-block `always_comb` diagnostic passed, establishing the sensitivity cause. The final portable fix passes every dependency explicitly, including full-width integer MUT_TAG; it retains `always @*` and all state/reset/clock/cycle statements.

Source fix: `34a669b92ce` on `codex/hbm-face-bridge-0336`, canonical RTL and preferred r18h5 bundle only. HBM independently reviewed the unchanged indexed TTL slice, widths, integer truth values and all statements outside the function/call.

Completed evidence:

- Exact actual old/new flit function expressions mapped by native Yosys0.68+ABC:560/560 output equivalences proved, zero unproven, exit0. All runtime inputs and signed32-bit MUT_TAG are symbolic; d=0 and1 are the actual two loop directions. This is a combinational function proof, not a whole-module formal claim.
- ORIGINAL raw g4 cut with the final pure-function fix, actual native7-define/SYNTHESIS and physicalSYNTHESIS profiles: strict finite full-cut miter passes1600 edges, both actual qid2/3, all1345 public outputs fromedge1, POR66, repeated reset and X/Z stimulus. No valid/startup/payload masks. A changed public fault bit is caught. Source candidate reset behavior is exact per-port composition, not `golden[t-2]` during reset.
- Both actual add-lane instances have LAT7/DRST0 and `.err()` open. The primitive error output has no parent wire. No public-cut output is projected away; public fault is compared. Prior scoped primitive y/valid receipt ad48deccc is separate.
- Preference-first native closure is7 files/10 reachable modules, independently obtained after preprocessing and exact identifier matching. The initial unpublished70-row parser overclosure was rejected before proof. Physical profile has14 modules including its pure wire adapters and face FF primitive.
- `inverse_cut_map.json` is an exact45-port/full-vector inverse of current g4 wiring. API adapters guard NT8/LAT8/AG1/SPLIT1/all mutants0. Actual parent aliases primaryclk plus17 additional clock bits to the same PLL source; these adapters do not qualify independent-phase clocks.

A full mapped controller attempt produced6002/6004 cells but exited1 during `equiv_simple` at cw_o279 without a final result. It is preserved as an incomplete method, not promoted. The exact source-function mapped proof plus unchanged surrounding RTL and strict full-cut miter establish the narrower change evidence above.

Still held: TOK owns the actual issue→RING→land/VM caller, per-traversal dates, link/VM reservations and warm-reset queued-valid commit proof. Their north qid2/3 physical selection and explicit external qid0/1 partners must not be described as four local native instances. Component closure does not qualify the coupled calendar, current whole-parent G3, token rate, START or physical signoff. QUERY/COLLAR remain separate next bridges; QUERY's upper head bits require real startup/context reconciliation before DROP/TIE0.

Runtime source/proof root: intel2 `/srv/opentallas-scratch2/claude/codex-hbm-face-bridge-0336`. Physical jobs and kits remain untouched. No new P&R was launched.
