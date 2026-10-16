# HBM visual-audit status: closure-blocking findings
Updated 2026-10-16 10:30 PT by VIS-HBM (round 3). Plan: v5 830.2 mm2 (main 03162300c). OWNER 09:46: closure first; floorplan changes only when they unblock GRT or timing.
Sources: closure-loop verdicts (codex_batches to 09:50), stream logs, my own renders of the odbs, and my own `native_pin_audit.audit_one` runs on the main views. Details are in findings.json. Images: contact_sheet_round3_die.png, contact_sheet_round3_tiles.png.

States: **fixed-routed** (routed, and the cited metric improved), **fix-in-gate** (in a gate or route, no verdict yet), **open** (no geometry change yet), **deferred** (closure-first), **refuted**, **withdrawn**.

| id | sev | finding | owner | state | evidence |
|---|---|---|---|---|---|
| R3-V1 | P0 | VM nat2 q0/q2 CLOSED but native FAIL. The failing outputs are all in the SW corner, farthest from the single N-centre clk | H-SM | **open (helper re-kitting the faces)** | My audit: q0 L258.5 (711 pins) / C207.5 / sp88.3; q2 L250.8 (370 pins) / C194.4. The failing pins are rr3 S x6-68, rr0 W y7-68, rr4 W y72-133 (+ rr2 N on q0). q1 PASSES (L201.9 / C170.0). The 4-face clock gate q0_faces (AGI 093214) failed CTS: core clk still reaches the SRAM clock pins, and the macro channels are 0 um |
| R3-V2 | P0 | SM rp4c: the W/E pins are packed into 500 um of a 1,529 um face; trial GRT stuck | H-SM | **open** | W: 3,710 of 3,759 pins in y 500-1000 (7.4 pins/um, peak 10.4/um); E is the same. M8 is derated 100%, with 233k blockages. GRT was at extra iteration 18/30 at 09:52 after 3.5 h. Placement reg->macro is -309 ps. T6 has moved, not been removed |
| R3-V3 | P0 | vmdel_lane hv15-20b84db92 CLOSED TT +49.22 but native FAIL | H-NETLIST | **open (H-HARDEN v6 successor; old view not bound as native-good)** | L346.6 / C274.2 / sp96.4. Failing: 42 fill_data_i pins on the S face (x 50-245), with clk at the W end (y 40.6); full/pcbad on W; rst_n |
| R3-V4 | P1 | xcal216 r1 CLOSED TT +89.98, native FAIL on rst_n only | H-SM | **open (new)** | C254.0 on rst_n; every other pin passes (L203.9) |
| R3-V5 | P1 | sfucore_split: one clk root drives 18,063 flops (over 15k); rst_n has 13,745 loads | H-SU | **fix-in-gate (gate at GPL)** | The gate's textbook lint. The clock rule needs a measured 300/80, or a split |
| R3-V6 | P1 | F20 calendar: logic packed in a 44-um W block, 23-um N strip empty | H-NETLIST | **fixed-routed (native audit pending)** | f20 220-wide failed with GRT-0232. ww ad9c630eb VT-ECO CLOSED TT +25.04 / FF +12.63 / DRC 0 (29 LVT cells, 0.12%; H-NETLIST 10:40). SRAM-to-N-edge is the successor only if native fails |
| T5 | P1 | COLL vmwrite: clk at the N end of the strip | H-HARDEN | **fixed-routed** | fsw v6 d6d487656 CLOSED TT +8.64 / FF +17.38. My native audit PASSES: L189.8 / C142.1 / R90.9 / sp20.3. 16 E-face bank clocks |
| T6 | P0 | SM tile pins 18.2/um in 203 um | H-SM | **superseded by R3-V2** | rp3 76112f61f EARLY_FAIL_CONGESTION (markers not decreasing). rp4c is 7.4/um in 500 um, still congested |
| T12 | P1 | LK EP: SW-corner pin-flop fields | H-LKEP | **fix-in-gate (route 5)** | Route 4 f24bad869 CLOSED TT +211.98 but native FAIL L259.7 / C221.3 / sp100.8 (my audit agrees). Density image: the red is at the SW corner. Route 5 (19.44-um corner keep-out, sd_tx spread) is regating |
| T3 | P0 | strap q0 | H-SM | **withdrawn (superseded)** | The strap masters are cancelled; die v16 binds the native banks. See R3-V1 |
| T8 | P1 | pc_ctrl_cfg (x128) | H-PCCTRL | **open** | h6 6a9d24cd2 NEEDS_RTL TT -50.14 / FF +16.39; h4 failed with GRT-0116. Run deleted, nothing to render |
| D1 | P0 | die clock buffers inside hard outlines | H-DIE | **fixed in case; d3b GRT running** | d3b (E4, legal clock sites) has 0 buffers inside outlines (my d3b render). GRT was at extra 23/30 at 09:42 after 6.6 h. **d3b is on the OLD compact660_v5 plan (grants v6)**, so it is a diagnostic. d4 on the v5 plan is not launched (42/44 SYNTH) |
| D2 | P2 | die empty area | H-DIE | **deferred (closure-first)** | v5: 165.4 mm2 not in blocks. 4 corner voids beside the PHYs: 10.1 / 9.4 / 7.6 / 7.4 mm2. 4 band strips of about 5.3 mm2 each. Use them for relay/clock homes only if the d4 GRT needs room |
| D3 | P1 | SM_HBM long relays | H-DIE | refuted (as proposed); owner 09:44 lowered the rate target | - |
| T1 | P0 | xload ctl | H-SM | open (ctlw r2 re-kit, 8e0535ed5) | geometry not re-rendered this round |
| T2 | P0 | bdring | H-SM | **fixed-routed** | cl2f CLOSED + native PASS (9eb0a3e8f, Codex 0825) |
| T4 | P1 | VM calendar centred SRAM | H-HARDEN | fixed-routed | xcap native PASS (round 2) |
| T9 | P1 | SU bank6 fill | H-SU | fixed-routed (bank); refuted (reduce) | - |
| T10 | P2 | xload bfq | H-SM | closed (cl2c CLOSED TT +77.02) | - |
| R2-1 | - | LK EP insertion | - | refuted | - |
| T7 | - | smh_bdc d62 | - | withdrawn | - |

Not auditable: HC hc_eng / hc_q have only a wrapper ETM (no odb). The SFU programme store gate (PVE 092026) is at floorplan stage only, with the N band failing (H-SU r4 is live).

Totals: P0 open: R3-V1, R3-V2, R3-V3, T1 (+ D1 awaiting the die GRT). Fixed-routed this round: T5, T2.
