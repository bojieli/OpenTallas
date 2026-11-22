
## OPEN-RELAYS from HEAD-START-R17 (stand-down 2026-11-21 19:46 PST)
Unanswered failure classes; post RESULT or ACK naming the class id (fail_route accepts the whole owner chain).
- FAIL-CLASS 8070467972 head/waiter RESULT FAIL: open 708 min, 1 item(s): OPUS-FIX-HEAD-SERDES-R4@06:09; owner chain FABLE-FIX-HEAD-LEP0N-R2 > HEAD-START-R17; NEEDS-LANE posted

# HEAD-START-R18 handoff (2026-11-21 21:xx PST, Fable; successor of HEAD-START-R17)

## START transport bench: CLOSED on r16 p6
- tr29 PASS 329/329 (epyc7 `/srv/opentallas-scratch2/claude/head-start-r18/tr29`; plan 58f896b3fcbe, sidecar facc71b93198, provider_p6r).
  192-199 checked cycles per lane, 0 errors; 358 part origins = n_nominal in the own-edge frame.
- Mutants all FAIL: st_bypass 12 lanes (-1), st_double 12 (+1), k_plus1 1, oracle 1, bit_swap 264 (dirs tr29_<mutant>).
- Tool on main e468efe8432 (tools/s81_head/head_transport_depth.py + test). Recipe: epyc7 head-start-r18/tr28.sh (env TAG, MUTANT).
  Hub logs intel2 ~/head-start-r18/*.otrun.log.
- No plan change. Codex's 53 K values (tr21/tr22) are void.

## Why every earlier run was void (tr11-tr27)
1. Verilator 5.050 folds `always @(clk) x <= #(D) clk` to D mod T/2 once D >= T/2 (epyc7 head-start-r18/dly, chain).
   Phases 0.9-7.7 T collapsed into [0, T/2), so START origins looked phase-free ("root frame" was this artefact).
   Fix: one free-running generator per phased clock.
2. Frame: region edge k is at k T + phase; a_v, n_nominal and lane cycles count each part's OWN edges
   (count_align_plan.py header, ot_dp_clk_landing_ca.sv, bind latency_frame). Stubs count own edges (default).
3. Oracle: fixed_cycles realised as wrapper stations (types with realize_internal_stations: hd_spn, hd_spn_end, hd_ctl;
   38 lanes) stay in the bench depth. Derived from plan internal_stations rows; equals Codex's tr13 table.

## e1b = p6 START delta on e1a plan 00b2abf6e7a6 (r17a contained v2, file sha 62edabc647ac)
Lane dir epyc10 `E=/srv/opentallas-scratch2/claude/head-start-r18` (README there).
- E/p6 + E/prep_e1b: plan 18f3c0c7c0c1, sidecar facc71b93198 (compose.py of R16 with bind2; same 5 lanes +1, K changed 125).
- Gates GREEN (unit oth-ubuntu-1720360-1795322477, E/gates.sh TAG=e1b): schema 0, strict bind PASS, cohort 26/26,
  LATCHECK 329/329, receipt, G0 0 errors / 219 warnings.
- Provider: E/provider_e1br (start_reset.py + relay_over.py): 1389 stages, 969 reset ports, 9 relays, span 72 + 4 <= settle 88;
  start_stages.sv byte-equal to p6r. Published wrappers 26/26 equal to prep_e1b/published.
- Tool trees: E/src = v2 tree (hardlinks, writable tools). E/repo -> E/rtree2 = R16's tools (main 625a0f6f0e) + v2 assets.
  The v2 tree's own tools (745c8f11) fail start_reset.py: after reset_tree.wf_plan() the relay numbering of hd_tile /
  hd_turn_b trees shifts, so declared exports no longer match. Use rtree2.
- Bench on e1b: E/e1b_2.sh (env TAG, MUTANT), tb1 = hub log intel2 ~/head-start-r18/e1b_tb1.otrun.log.
- NOT done: the apply. The LEP0N lane owns it (R7 posted DIED; ask COORD who applies). Hand them E/prep_e1b plan + sidecar,
  E/provider_e1br, and the gates/bench records above.

## Side item hd_host_e he_epc M7 check: BLOCKED (posted 20:0x)
- Hand-built kit (epyc7 opus-fix-head-serdes-r4/host_e_access1415_retry/gen_access) is refused: exit 14 ENV-PROVENANCE.
- private-spec (autopilot/private_specs/HEAD-START-R18/s81_head_hd_host_e_1121195741) fails at kit_rtl: the r16 wave plan
  names sink_bins files in snap tree s81_head_r4_s0, which was deleted on all hosts. Needs the flow owner: restore
  prep/NF6/assets at that path, or switch the HEAD wave to the contained r17a v2 tree. Then rerun run-item.
