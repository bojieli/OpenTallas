# HARD-REVIEW 10-18: qfd_d2d_static (Qwen compute D2D) vs qkd_d2d_static (Qwen KV D2D)

Post-mortem only. Nothing was submitted or edited.

## Verdict (short)

- **On the current die: YES.** The compute die (dv2f14bn/dv2f14bf) binds the CLOSED r8c view. The KV die binds the twin through the qkd_d2ds frame. kvs14p carries `.NTX(3)`, but the r7t view is not bound yet; KV-PLAN5 says a fix is owed.
- **Root cause.** One TritonCTS root enters on the E face, which carries 4% of the pins. It feeds about 3.6k pin flops spread round a perimeter of about 1.5 mm, with a 2x2 block of SRAM banks (40% of the area) in the middle. TT insertion is 510-550 ps, so the 80 ps spread limit allows only about 15% path imbalance. Any pin-flop group in a corner behind an SRAM breaks that limit once real wire RC is counted.
  - In the compute tile that group is the NW N-face group (544 flops above g_bank[2], fed up the 46 um W channel).
  - The placement-RC gate cannot see the extra trunk wire. Compute grows +29 ps from gate to route, KV +12 ps.
- **KV did nothing structurally different.** RTL, outline, SRAMs and clock entry are the same. KV passed on two things:
  - die top-down assigned pins (`assigned_pins.tcl`), where compute lets PPL cluster its pins;
  - one CTS knob (sink clusters 20 / 40 um).
  KV's routed spread is 75.0 / 67.6 ps, only 5 ps under the limit. **The twin has the same structural fragility.**
- **Verdict: CAN CONVERGE. Do not abandon.** The RTL, cycles and timing are fine: four routes closed TT/FF. Only the pin-flop spread rule fails. One change should get there: assign the compute N-face pins top-down, moving the NW-corner group to x ≈ 120-400 at ≤ 6 pins/um and the `ck` pin to the N-face centre over the SRAM column channel, then apply the r9h CTS recipe and judge on **routed** spread, not gate spread. A more robust option, a macro re-shape, is in §4.
- **Risk: MED.** It is critical and on the die path. Twelve routes and 21 gate kits so far, and the evidence shows a seesaw between capture and spread.
- **Cost: 0 cycles, 0 area.** The compute die must re-plan the N-face links in GEN, which it does on every iteration anyway, then one re-route.

## (a) Every route attempt

The closure daemon records are in `/home/ubuntu/.local/state/closure_loop/jobs/q[fk]d_d2d_static*.json`. The native audits are in `origin/main:results/arch/qwen_link_native_1640/native_audit.json` and in `origin/claude/qlink-1815-d2d:results/arch/native_pin_audit_qd2d_1017/qfd_d2d_static_r8c.json`.

### qfd_d2d_static (compute)

| route id | date | variant | verdict | class | key number |
|---|---|---|---|---|---|
| r1-76739d6b0 | 10-15 | r1 | REFUSED | flow | stale source binding |
| r1-22b94cc1c | 10-15 | r1 (no pin regs) | NEEDS_RTL | setup+hold (boundary) | TT -79.09 / FF -32.56 |
| r1-87cafef19 | 10-15 | r1 | EARLY_FAIL_HOLD | **spread** | hold -52 ps; obstruction-aware CTS made the S band +76 ps late |
| r1-r2-f390ec7fe | 10-15 | r2 | REFUSED | flow | STRUCTURE_REPEAT |
| r1-r3-cb4ec1b91 | 10-15 | r3 no-obstruction CTS + 40 um repeaters | EARLY_FAIL_CONGESTION | congestion | GRT-0116, 20 um centre channel |
| r1-r4-f779ceecf | 10-16 | r4 pin-registered + 40.8 um channel + 2-level clusters | CLOSED | (native: reset capture 468.8) | TT +19.23 / FF +25.00; gate spread 123.5 -> 77 |
| r5-99ecb9ed4 | 10-16 | r5 pins over every face, ck at S centre | CLOSED | (native: reset capture 491.3; all-sink spread 129.4) | TT +49.62 / FF +3.28 |
| r6-7cb615b24 | 10-16 | r6 local reset capture (4 anchors) | EARLY_FAIL_HOLD | **spread** | hold stuck -24 on ~2,800 late-clock boundary flops; spread 99/123 |
| r7f-e0b9ef21f | 10-16 | r7e por-only anchor + 43.2 um SRAM channel, inhold pads | CLOSED | **capture** | TT +49.58 / FF +10.80; native spread **59.2 PASS**, capture **239.9 FAIL** (pads) |
| r8-r8b-32e1d1d80 | 10-17 | r8b pre-built clock spine | NEEDS_RTL | hold / **spread** | FF -48.99; spread 24.7 (CTS) -> **110** routed; insertion ~702 |
| r8c-021a205b1 | 10-17 | r7f clocking + recipe 4 flop-first (no pads) | CLOSED | **spread** | TT +26.67 / FF +3.94; native capture 162.3 PASS, spread **91.7 / 84.0 FAIL** |
| (gate) r9a / r9b | 10-18 | ck at N centre (range) | FAIL | flow | io_place PPL-0086 (range splits the N face) |
| (gate) r9c | 10-18 | obstruction-aware CTS | FAIL | spread | 95.8 / 83.5 |
| (gate) r9d | 10-18 | ck at N, no range | FAIL | spread | 91.3 / 82.8 |
| (gate) r9e | 10-18 | ck at S centre | FAIL | spread | 93.4 / 82.3 |
| (gate) r9f / r9g | 10-18 | regional BUFx24 root (LOCAL_SPLIT box) at NW | FAIL | spread | **117.1 / 102.3** (worse) |
| (gate) r9h | 10-18 | r8c + KV r7t recipe (clusters 20/40, PD 0.6, MEG) | WARN | spread | 63.9 / 57.3, GRT 0; REVIEW queued |
| (gate) r9i | 10-18 | clusters 12/30 | FAIL | spread | 97.1 / 89.4 |

Some gate-only kits (r7c/d/e/g/m, r8, r8d) were never routed. One of them, r7d, read native spread 66.9 PASS but por_n capture 234.7 (r8c structural_change text).

### qkd_d2d_static (KV twin)

| route id | date | variant | verdict | class | key number |
|---|---|---|---|---|---|
| r1-76739d6b0 | 10-15 | r1 | REFUSED | flow | stale source binding |
| r1-7ab4004a2 | 10-15 | r1 (no pin regs) | EARLY_FAIL_SETUP | setup (boundary) | -434 ps, 4,510 endpoints |
| r1-87cafef19 | 10-15 | r1 | NEEDS_RTL | setup | TT -90.96 / FF -14.0 |
| r1sp-r3sp-19298aba3 | 10-15 | spine kit | EARLY_FAIL_CONGESTION | congestion | GRT-0116, 20 um centre channel (SRAM pins on both faces) |
| r2sp-r4sp-331b4b5e2 | 10-16 | 59 um channel | NEEDS_RTL | setup/hold/DRC | TT -49.5 / FF -12.45 / DRC 1 |
| r7q-c0d027277 | 10-16 | 43.2 um channel | EARLY_FAIL_HOLD | flow (false stuck-scan) | hold -24.1 |
| r7q-0b9807474 | 10-18 | r7q | NEEDS_RTL | DRC | TT +29.45 / FF +9.97 / DRC 2 (M4 clock net vs SRAM edge) |
| r7q-…-arg1 | 10-18 | r7q | NEEDS_RTL | DRC | DRC 2 |
| r7q-…-arg2 | 10-18 | r7q | CLOSED | **spread + capture** | TT +12.27 / FF +1.91; native spread 83.4, capture 204.5 FAIL |
| r7q-a7ebc3be5 | 10-18 | r7q-drc | REFUSED | flow | CLOSED_STANDS |
| r7t-53d2981a7 | 10-18 | NTX=3 + clusters 20/40 + io_hold 0.010 | NEEDS_RTL | flow | bench vvp killed (over-committed host) |
| r7t-a1440c7f6 | 10-18 | r7t | NEEDS_RTL | hold + DRC | FF -11.83 / DRC 2 |
| r7t-9a373179e | 10-18 | r7t-hd (io_hold 0.025, MEG 2.4) | NEEDS_RTL | hold + DRC | FF -1.03 / DRC 2 |
| r7t-28642e9aa | 10-18 | r7t-hd2 (io_hold 0.030, MEG_OUT 1.2) | CLOSED | — | TT +22.73 / FF +10.31; spread **75.0 / 67.6 PASS** (gate 63.2 / 57.7) |

## (b) Geometry, RTL and kit facts

The two tiles are identical apart from the faces each port goes to.

| fact | compute (r8c / r9h) | KV (r7t) |
|---|---|---|
| outline | 475.2 x 280.8 um (aspect 1.69) | same |
| macros | 4x ot_sram_1r1w_64x512 (2x2), x 45.792 / 257.904 (**off** the 43.2 um lattice), y 41.04 / 162.0, 41 um column channel | x 36.72 / 267.192, 59 um column channel |
| fill | 44% = SRAM 53,294 + std cells **6,141 um² (4.6% of outline)** | 45%, std cells 6,316 |
| pins | 3,834 total: S 1,242 on 220 um (46% of face, 5.6/um); N 1,673 on 275 um (58%, **6.1/um**); W 810 on 195 um; **E 109 (4%)** | 5,045 total: S 2,291 on 331 um (6.9/um); N 1,170; W 1,251 (8.3/um); E 333 |
| pin placement | `--pin-region` per face; PPL clusters them (partial faces, NW corner group + middle group on N) | top-down `assigned_pins.tcl` + `pin_source_receipt.json` (die tool) |
| clock entry | `ck` at E face, just below mid-height | `ck` at E face, above mid-height |
| clock | one root, 10,925 sinks incl. 4 SRAM clk pins; TT insertion 510-516, FF 420 | one root, 11,580 sinks; TT 549 / FF 451 |
| boundary (pin) flops | 3,617 | 4,865 |
| widest buses | N: native_tx_payload 548 + prog_tx_record 548 (inputs); S: fdi_tx_flit / fdi_rx_flit 583; W: x3 524 + 59 identity + results | S: att_tx_payload / record_tx / rx_payload 548; N: FDI 583; W: emb_tx_payload 548 + KVN 512 |
| high fanout | resets: u_core.u_st.rst_n 325 loads, rst_n[1] 300 loads (WARN; not timing-critical) | rst_n[1] 300 |
| logic depth | none critical: reg->reg slack +20..+50 at 833 ps | same |
| CDC | single domain (core_clk 1.2 GHz); PHY handled outside | same |
| GRT | 0 overflow (r8c routed congestion PNG all clean) | 0 |

Images I viewed:

- r9h gate floorplan: `/home/ubuntu/wt/qd2dclk-1018/physical/ref_tile/qfd_d2d_static_r9h/gate_layout/floorplan.png`.
  - N pins in two clumps: x ≈ 5-65 at the NW corner and x ≈ 170-280.
  - S pins at x ≈ 110-245.
  - The E half of the N and S faces is empty.
  - The clock is a single red pin mid-E.
- r9h gate density: `.../qfd_d2d_static_r9h/gate_layout/density.png`.
  - The register mass is thin strips: N band (NW corner red), S band (x 110-250, red), W band, and the centre crossroads between the SRAM rows.
  - The E half is empty.
- r8c routed views on ot-epyc4: `/srv/opentallas-scratch2/claude/closure-loop/qfd_d2d_static_r8c-r8c-021a205b1/routes/qfd_d2d_static_r8c_r8c_021a205b1/layout/{floorplan,density,congestion}.png`. Local copies are in `/home/ubuntu/scratch/hard-review-qfd/r8c_routed_*.png`. Geometry is the same as r9h, and congestion is 0.
- KV r7t gate floorplan and density: `/home/ubuntu/wt/eg-kv-1018/physical/ref_tile/qkd_d2d_static_r7t/gate_layout/{floorplan,density}.png`. The same 2x2 SRAM block, with pins assigned on S over x 0-330, the full W face, and N at x 30-150 plus the middle.

Checklist against the tile-review rules:

- macros off the 43.2 um lattice: compute FAIL, KV x 36.72 = 0.85 x 43.2, also off;
- one std-cell band: no, the cells form a perimeter ring plus a cross;
- pins on full faces: no, every face is partial;
- clock beside the register mass: no, it enters on the empty E face;
- square-ish: 1.69;
- utilisation: 4.6% std cells.

## (c) Root cause, and which symptoms the retries chased

**Root cause (structural).** The tile is a 2x2 SRAM block with a ring of pin-registered boundary flops round it. Each face's pins are FIRM at the pin because PR=1 puts one flop per port at the pin. One CTS root at the E face serves the whole ring. The E face has 4% of the pins.

- **Clock entry vs pin faces.** The farthest pin-flop group is the NW N-face low bits of native_tx_payload / prog_tx_record at x 10-66, y 267-278: about 475 um of Manhattan distance plus a detour round g_bank[2] from the entry. Its branch goes up the 46 um W channel through one trunk buffer at (42.0, 189.8) (QC diag, `results/arch/qwen_split_compute_1014/eg_qc_1018/d2d_spread/r8c_spread_diag.json` on claude/eg-qc-1018). Depth is 14 levels everywhere, so the excess is trunk wire.
- **One tree across the whole perimeter.** Insertion is about 510-550 ps. The 80 ps limit is about 15% of that, so the tree balances only by luck of where PPL drops the corner groups.
- **Missing landing.** Not the issue. The tile is the landing (pin-registered), and at 0.475 mm it is under the about 1 mm landed-region threshold.

**Why the gate kept lying.** The gate measures spread with placement RC. The NW trunk detour only shows after routing:

| tile | gate spread | routed spread | growth |
|---|---|---|---|
| compute r7f | 42.7 | 59.2 | +16.5 |
| compute r8c | 63.0 | 91.7 | **+28.7** |
| KV r7q | 69.4 | 83.4 | +14 |
| KV r7t | 63.2 | 75.0 | +12 |

**r9h (63.9 at gate) is indistinguishable from r8c at gate (63.0), and r8c routed to 91.7.** The current "fix" is not yet evidence.

**The seesaw the retries chased.** Capture and spread pull against each other through the same pin-flop clock arrivals:

1. **r7f** put inhold pads at the pins. The pin flops relaxed inward: spread 59 PASS, capture 239.9 FAIL.
2. **r8c** removed the pads (flop-first, recipe 4). Capture passed at 162, but the flops pinned hard into the NW corner: spread 91.7 FAIL.
3. KV saw the same coupling: launch + capture sum 426 > 410 at any compensation, from the r7t notes.

The retries also tried:

- moving the clock entry (r5, r9a-e);
- obstruction-aware on/off (r1, r3, r9c);
- a clock spine (r8b, 110);
- a regional BUFx24 root (r9f/g, 117);
- cluster sizes (r9h/i: 20/40 gives 63.9, 12/30 gives 97 — chaotic, not monotone);
- reset anchors (r6/r7d/r7e);
- hold margins and MEG guards.

Each was a knob on the same geometry. None changed where the pin-flop groups sit relative to the clock and the SRAMs.

Symptoms that were not the root cause: GRT-0116 (real, but fixed for good by the ≥40 um channel in r4/r7f), reset-capture misses (fixed by r7e/r8), DRC M4 SRAM-edge shorts (KV, a kit guard), and FF boundary hold (margin tuning).

**KV vs compute.** KV did nothing structural that compute did not. The same RTL family, outline, SRAM block and E-face clock pass at 75.0 / 67.6 because of:

1. **Die-assigned pins** (`assigned_pins.tcl`). The N corner group is smaller and its S/W bands are long and contiguous, rather than PPL clumps leaving a dense isolated corner group behind an SRAM.
2. **The sized-cluster CTS knob.** It removed one late leaf strand (65 ps).

The margin is 5 ps. A die re-pin or an RTL change could push KV back over 80.

## (d) Structural fix

**CAN CONVERGE.** Do not abandon: the RTL, schedule and cycles are right, and timing closes.

1. **Single change that should converge it (0 cycles, 0 area).** Use die top-down pin assignment for compute, as KV does.
   - Place the N-face native_tx_payload and prog_tx_record buses over x ≈ 120-400 at ≤ 6 pins/um. 1,673 pins need ≥ 279 um, so there must be no pin group in the NW corner behind g_bank[2].
   - Put `ck` at the N-face centre (x ≈ 237) over the SRAM column channel. Assign it explicitly in `assigned_pins.tcl`; a pin range splits the face (PPL-0086, r9a/b).
   - Then the tree goes down the column channel, with symmetric N and S band branches and no corner group behind an SRAM.
   - Keep the r9h CTS recipe (clusters 20/40, `-no_obstruction_aware`, PD 0.6, MEG 2.4/1.2, io_hold 0.030).
   - **Gate on a routed spread estimate** (trial route plus SPEF insertion), not on the placement-RC gate number.
   - Cost: the compute die re-plans the N-face links in GEN, plus one re-route. This interacts with the open dv2f9 decision to place d2d_rom R0/MX, so do both in the same GEN.
2. **More robust option, if (1) misses** (same outline, 0 cycles).
   - Move the SRAM 2x2 block against the E face (E carries only 109 control pins).
   - Put the N, S and W pin bands and all logic in the W ~280 um. N needs ≥ 279 um at 6/um, which fits exactly.
   - Enter the clock at the W/N corner of that region.
   - The pin-flop radius roughly halves, so insertion falls toward about 300 ps and the 80 ps limit becomes about 25% of insertion instead of 15%.
   - Also snap the SRAMs to the 43.2 um lattice.
   - Cost: macro moves, re-pin, re-route, and a die link re-plan. No RTL change.
3. **Apply the same pin and clock treatment to the KV twin** at its next revision (5 ps margin), so the pair stays matched for the cross-die neighbour boundary.

Do not pursue more regional roots inside the tile, spines or cluster-size sweeps: r8b, r9f/g and r9i already show they make it worse.

## Evidence paths

- Daemon records: `/home/ubuntu/.local/state/closure_loop/jobs/qfd_d2d_static_*.json` and `qkd_d2d_static_*.json`
- Gate kits and results:
  - `/home/ubuntu/wt/qd2dclk-1018/physical/ref_tile/qfd_d2d_static_r{8c,9c,9f,9g,9h,9i}/gate_result.json` (branch claude/qk-d2d-1018 @ce00e4686)
  - `/home/ubuntu/wt/eg-kv-1018/physical/ref_tile/qkd_d2d_static_r7t/`
- PNGs:
  - `/home/ubuntu/wt/qd2dclk-1018/physical/ref_tile/qfd_d2d_static_r9h/gate_layout/floorplan.png` and `density.png`
  - `/home/ubuntu/wt/eg-kv-1018/physical/ref_tile/qkd_d2d_static_r7t/gate_layout/floorplan.png` and `density.png`
  - `/home/ubuntu/scratch/hard-review-qfd/r8c_routed_{floorplan,density,congestion}.png`
- Lanes: `/home/ubuntu/claude-takeover-20261007/lanes/ELEM-GAPS_logs/QC.md`, `lanes/Q-KITS.md`, `lanes/ELEM-GAPS_logs/KV.md`; HANDOFF lines 3347, 3351, 3486, 3952-3953, 4149
- RTL: `rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv` (qfd_d2d_static_core / qkd_d2d_static_core)
