KV-PLAN-DELTA-2 hm_r26q4 (CLOCK-KV lane, 2026-10-27). One batched event on hm_r26q3 256600e2 -> hm_r26q4 b5aefbd6.
Real-copy plan dir intel2:/srv/opentallas-scratch2/claude/kv-plan-q4-1027/pd (plan.sha256, cores.sha256 332 files, 0 symlinks).
Assembly q4_assemble.py asserts: only ft_slots regs_um/bit_sites_um/bit_site_cell_um of 5 types change (name/faces/width/
stations equal); hard_cores differ only in pins_file (7 repoints: 6 strap views + ahub); outlines, latency, lanes, ports,
clock, reset byte-identical to q3. No other kitted core pin table/outline changes.

(a) FT re-site, tools/die_plan/ft_corridor.py (KV-KITS-5 158d3b5c6 per-slot jog lanes + this lane):
  - --lane-um-per-bit (gate 0.6 x 32 tr/um -> >= 0.0521; 0.0458 was M5+M7 only), --lane-pack bin|walk
  - Z lanes are packed only into span not used by the other slots' legs (N/S windows) and, with --lane-pack bin, not
    over macros (core-free channels; stations no longer projected onto a core edge as one column).
  - Variant per type chosen by the census (all reproduced byte-identically by the committed tool, CHECKED):
    hub_Ei walk/0.08, hgi_v5 bin/0.08, hgi_v7 bin/0.06, hgi_v8 bin/0.07, hub_Eo bin/0.08. hub_Wi: tool cannot site ft5/ft31
    at the 405 reach (no chain <=403 um) -> q3 sites kept. Counts kept, --margin 1 (403-um budget), max bit hop <= 402.3.
(b) GEOM column census geom_census.py (census_q4.json, census_q3_baseline.json): every bit chain in-pin -> sites -> out-pin;
    per (slot,hop) the bundle takes one route among L(HV), L(VH), monotone Z with bit-ordered spread jogs, chosen greedily
    to minimise overflow over the gate (ROUTE); HV = KV-PLAN-EVAL pessimistic screen. Gate: bits per 10-um column/row
    <= 0.6 x 32 tr/um x 10 = 192 (ratio <= 1.0). ROUTE col10/row10 ratio, q3 -> q4 (CHECKED own runs, renders VIEWED):
      kv3_hub_Ei  unsited -> 0.906 / 0.969  PASS  (no spine: max 174 b/10 um, 234 b/15 um; was 1,648 b/15 um in the event)
      kv3_hgi_v8  5.87 / 1.80 -> 1.94 / 1.43  FAIL (x 237-335 channel: ft4 S->N 1044 b window + ft26 lane)
      kv3_hgi_v5  5.63 / 1.21 -> 1.47 / 1.49  FAIL (x 555-660 channel)
      kv3_hgi_v7  2.35 / 1.25 -> 1.44 / 1.17  FAIL (x 880-975: ft23 S->N 523 b window-bound)
      kv3_hub_Eo  1.70 / 1.31 -> 1.27 / 1.15  FAIL (x 560)
      kv3_hub_Wi  4.0  / 1.70 unchanged       FAIL (x 290 station stack between macros; 2 slots unsitable at 405)
    Residual hgi/hub_Wi hot columns are inter-core channels carrying straight N/S bundles whose PIN WINDOWS already sit in
    the channel at >19.2 b/um, plus Z lanes that cannot leave the channel at 405-um reach: station siting alone cannot
    fix them -> needs window spread / over-core M7 lane credit (plan pin-window change, touches neighbours) -> ASK.
    HV (pessimistic) stays high for all (hub_Ei 1710 b/10 um) because it puts every corner jog in one station column.
(c) R8 landing table regenerated for +210 (fork of this lane; r8/README.txt): pd/r8/{qwen_kvsys_r8_landing,bus_groups}.json
    = r8/qwen_kvsys_r8_landing_q4.json 14c226fc75e1 + bus_groups_q4.json e98491430da3 (digest 7e222cf88151af85); check_r8
    0 errors, 3,819 groups, 0 unequal (CHECKED). Old pd/r8 (v39g) was stale and not reproducible from q2. Bind side:
    bind_r8_position_landing_q4.json, pv_calendar_restore_q4.json: 89 PV members bound +1..+4 / pad -1..-4, 0 calendar
    cycles (CHECKED, two independent routes identical). Reproduces price_rerun 674cd499f r8 block exactly -> latency == eval
    +210; TOK-QK NOT re-priced (-0.012 % direct / <= -0.11 % worst stand). UNCHECKED: kvs_emb emb_tx_slot (L356) per-token?
(d) D-KV-STRAP-FORM-2 (COORD 11:4x): q4_straps.py moves the edge-only strap faces of centre-form views 0.096 um inward
    (kit form). canon_pins sha256 (die_sta_related.canon_pins) old -> new:
      e0 R0   3750faf6 -> 15204698f2a3d3b6fe06e427f52d1dde75879806a47dbb4fd4b7c5861d75f647
      e0 fMX  9731d9e0 -> fd5157a1c4dcd5f4cf3a15b2c5f8e551cb4b2e4ef6cf8f3c779f64f7606d541d
      e2      3a20139b -> ed14b96bb006fd6bf249607fa3fb403387fed181be9c78445de4b51d1351b426
      e6 R0   cea6ec62 -> f604d5d612e1cf55521f3cf8365672cfe5d0c3fdbd96205c77861260c9b89661
      e6 fMX  d9e1c2d8 -> 47549693fde82ac6000e414f63b16b00baf9933c6ef344c1683c70c47e2b4cb4
      astk    55e06416 -> 51f910ba31de777105c299583012ebee678d4591ea0346d49943737c9da0ef17 (strap_corner W: same defect class)
    check.py core_pin_form: ERROR for an edge-only strap_* face in a view that has centre-form faces; edge-only DATA faces in
    mixed views (qkd_hr_cdc_*/core_* , 15 faces, kitted as is) = WARNING. Unit tests 6/6 PASS incl. new mutants.
(e) D-KV-AHUB-ENTRY (KV-KITS-7 ASK 11:32): q4_ahub.py. qkd_ahub entry (302.4,220.32) -> (302.4,241.92) in the free H channel
    y 220.32..263.52 (x = 12.8a centre kept, 4.32 lattice); ck[0]/rst_n[0] pins y -> 241.92 (cores/qkd_ahub_pins_r26q4.json
    sha efb8d4c0); slice cores/qkd_ahub_slice_r26q4.json (f3c99d71): 18 core_tree islands moved to the nearest free lattice
    site clear of the 5 hard children (+1.08 keep-off), max move 82.08 um, no overlaps (asserted). Macro clk pins as sinks
    with signed insertion.json (zh TT 246.3/FF 202.7, recip 224.3/181.6) + direct stubs at 0.20 ps/um (MODEL UNCHECKED):
    zh[0..3] arrive TT 301-305 (+51..+55 vs 250), FF 247-251 (+45..+48); recip TT 239.3 (-10.7). The zh macros' own insertion
    already uses the full 250 budget -> they need early taps (v5.0) upstream of the core entry or a CTS-matched delay on the
    std tree; ledger item for KV-KITS-7 / CLOCK-RESIDUAL.
G0 hm_r26q4 PASS 0E/1866W; G0C PASS 0E/1866W (CHECKED). Finding diff vs q3 baseline report (q3 checker): +15 WARN
core_pin_form (qkd_hr data faces, new warning), 0 removed, nothing else. q3 under the new checker: 10 ERROR core_pin_form
(the strap faces) -> all removed in q4.
