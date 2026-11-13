CBF R8 corridor source candidate (2026-11-13)

Source: tools/die_plan/core_input_chain.tcl (opt-in OT_NK_R8_COUNT_CHAIN=1;
OT_NK_R8_COUNT_SITE_REGEX=u_t_0_2_n_b_in_f$ for the measured bank).
It discovers fixed r/q aliases, kept count bank, actual PC and mux data cone.
Verified source output anchor and PC face-file identity are mandatory. Static count
logic stays in place. All eligible bits preflight before any new pass locations.
It rejects macro crossings, diagonal fallbacks and minimum-count hops over405um.
It never changes gate topology, counts or latency.

Coherent plan event: tools/die_plan/cbf_inner_event.py
  python3 tools/die_plan/cbf_inner_event.py PLAN CLEAN_BIND R8_TABLE CB16_TABLE NEW_EXTRA --report REPORT
It raises common fixed depth to4 for cbf_q01/cbf_q01_s2 u_t02 n_b, keeps optional
span1, aligns n_a and affected downstream reduction branches via existing INNER
metadata, preserving IDs/original asbuilt values. Existing Binder._apply_inner and
inner_strap_sites must regenerate RTL and runtime cb16_pads.json. It refuses an
unclean strict seed; no generated/pinned RTL is patched. No event adopted yet.

Focused source tests:7 PASS (unit E7 oth-ubuntu-1828523-1794612329). Includes
actual Binder/inner_strap_sites, released delay RTL 514-bit count0/1 lockstep and
wrong-depth/count/source-bit mutants, Tcl aliases/layout, coherent branch alignment,
and dirty-seed refusal. Final real-ODB probes and visual in this directory are
candidate-only: no ODB written, no production PLACE/GRT result claimed.

Generic anchor dependency is RULES-REACH core_input_anchor.tcl source follow-up:
unique bounded BUF/INV fanin and forward macro endpoint. Actual E4 ODB census:
6148latches =5888surviving PC chains +256constant TIELO tap bits +4reset paths.
Complete in-memory anchor run has6148latches/5888PC/unresolved0. Keep bound6;
constants and resets do not become fictitious pipeline cells.

Actual frozen ODB vehicle:
E4 /srv/opentallas-scratch2/claude/qc-proof-1/runs/qp1s28/cbf_q01/gen/cbf_q01
run/results/asap7/dp_cbf_q01/base/3_4_place_resized.odb
Intel2 logs ~/hqf-codexlog/cbf_{anchor_census3,anchor_layout_final,atomic_final}.log

Required next: clean strict bind seed from parent QC; generate coherent new EXTRA,
rerun strict bind/asbuilt/model event pricing, manifest kit generation, source-faithful
RTL lockstep and review refreshed plan render, then a private PLACE-only pilot.
Do not enable the placer on old fixed3 or route an unpriced/new latency event.
