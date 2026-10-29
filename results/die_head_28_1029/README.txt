DIE-HEAD-28 2026-10-29 (HEAD die owner; folded HEAD-KITS-11/12 + HEAD-START-4). Results only.
tok_price_hk5_A1.json  hk5 crop (+37 cyc over 13 lanes, hk5_tile->hk5, CHECKED from plans) + hk6 A1 ft (+72 over 30 lanes, hk5->codex hk6 candidate,
                       CHECKED) priced vs HEAD per-token 9313 cyc / window 10357 (TOK-HEAD-LAND-1, UNCHECKED composition): worst case all serial
                       +109 -> 9422 < 10357 (0 tok/s drop; bound 1.17 pct if HEAD alone set the rate) -> no OWNER ASK, A1 stands. COMPOSER-ONLY.
                       Crop fill arithmetic CHECKED: ctl 70508/304571=.232, host 153593/739031=.208, mesh 150990/742017=.203 (synth areas from fork README).
tile_hk4_pd/           epyc2 die-head-25 tile_pd60/pd70 (hk4 windows, superseded) AUTO-GEOM data only (grt off): r2r 402.79/400.95 (0>405),
                       pin_reg_max 154.34, pin_unreg 570 (hk4 W windows; hk5 moved them), channel_h/v 1.78/1.83 + 1.73/1.82 at the y~710 street
                       junction above the CA ring band, clock_reach 867/854. Render viewed. Run data deleted.
serdes_qk_place/       hd_serdes quarter+keep (LEC EQUIVALENT 4217/4217, head-kits-7 unit 1487636) Codex watcher trial PLACE (quarter_keep, 3_place):
                       AUTO-GEOM pin_unreg FAIL 320 (k_L/k_v... = INTERNAL_CORE R2_INTERNAL_TIMED_IN_PARTITION ports, face_guard PASS 943/943),
                       col_v WARN 0.854, GRT0 ov 0 (50 it), fill .501, r2r 232.98, pin_reg_max 48.87, clock_reach 194.49. Render viewed.
lep_v5/                Codex LEP V5 analytic register plan (777.6x492.48, 55 macros) TERMINAL: 1892 captures >405, max 451.22, stalled from it 8;
                       grouped by family (remaining_by_family.txt): fifo g_address->u_m 267, ski head g_bank->ep a_in 220, sko l_data->nk 189, ...
                       = high-fanout regs whose sink span exceeds 2x405 -> per-bank-group register replication (0 cycles) is the next estimate.
