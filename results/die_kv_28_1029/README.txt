DIE-KV-28 2026-10-29 (KV die owner; successor DIE-KV-27 1c5934d576; plan event26a FROZEN 12.17, gate-failure fixes only). Tools = main 7a77f0bc6 (incl. FLOW-HOLD-1 81f9c6c39e).
Runs intel1:/srv/opentallas-scratch2/claude/die-kv-28-1029 (event27f/, prov/, sta_E_edge, sta_E_cell); probe intel2:/srv/opentallas-scratch2/claude/die-kv-28-1029.

(1) EVENT27 FINAL (COORD 10-29 ruling (a): native START pins = gate-failure fix). mk_event27_np.py:
    plan_e27f = DIE-KV-27 plan_e27 (event26a + ASK-C) + Codex native START/reset pin sites (codex-kv-25-1029 point_native_pins.py ->
    event26/plan_native_pins.json): 139 landing_contract pins (cland_tstart_in/out, cland_raw_reset_out) on 56 types take xy/layer M7/
    native_entry_reference_um; 4 kv3_astk hard cores take astk_index0.json (scalar ck[0]/rst_n[0] ABI). Script asserts plan_e27 == event26
    on every overlaid field and on every non-START landing pin before overlay (no hidden drift). plan_e27f sha256 db8fc720ab16...
    (36 MB, scratch only). Die tree c unchanged.
    START provider reach (main start_provider_plan, native8 source_check_stages): 1528 stages / 1772 edges, 0 errors, max hop 367.47 um
    <= 405, clock access 9.99 [CHECKED-own]. Old event26a pins: 331 boundary edges 582..3213 um -> now 0 > 405.
(2) ALL-CELL PROVIDER (12141 comb relay cells): Codex already packed KV all-cell proposal (intel2 codex-provider-import-1029/proposal_kv6:
    22671/22671 placed = 10530 FF + 12141 comb, 0 failed, 0 soft-OBS overlaps, max anchor move 10.55 um; internal registered reach
    14940 arcs max 351.47 um, 0 >405; 174 boundary arcs unresolved). boundary_reach.py closes those 331 boundary edges (87 start_in,
    87 reset_in, 157 start_out) on the event27 FINAL pins, corner-conservative to the actual placed endpoint cells: max 355.83 um
    (hub_Ei/hub_Eo cland_tstart_out -> b4601/b4643), 0 > 405; upper bound to any cell of the stage 355.83; out launch FF 317.76
    [CHECKED-own, UNCHECKED independent]. Proposal only: apply_cells import into a fresh KV source (islands + PG contacts) NOT RUN.
(3) DIE STA main (gate.sh = DIE-KV-27 recipe, same inputs: proofE, plan_e26a, native6 bind, 4 signed views e1/e2/e5/e6@3e7fccd216):
    12.19 hold judgement: intra hold_status BLOCKED(kits) (0 measured pairs, 28970 unmeasured, 55 partition types without kit view),
    seam BLOCKED(kits) (768 unmeasured; pc/phy types). Diagnostic (not gate): intra all-pair -114.93, real-view -50.98, kit contract +6.64;
    seam kit contract +18.19. Setup intra TT +314.30, seam TT +554.12. CA spice_edge lo TT 104.8 / FF 109.6, 0/3595 <100 PASS; START-skew
    0/1687 TT/FF. spice_cell: CA TT 58.6 (90 <100, inverter-only pc->pc paths -> spice_edge per COORD clock rule) FF 101.6; intra kit
    contract -6.69 (cell, INFO). Numbers identical to DIE-KV-27 (same inputs) [STA UNCHECKED, NUMBER-CHECK REQ].
(4) Strict bind of event27f: WAITS KV-KITS-21 ahub ck[2:0]->ck[6:0] RTL (no askc branch pushed at 07:05).
