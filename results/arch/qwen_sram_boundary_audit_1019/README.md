# Hybrid D8 native SRAM boundary audit

Native clocked storage is a valid **conditional** endpoint for payload, address, enable and mask in the exact `ot_sram_1r1w2c_32x64_m1` model. This audit provides no reason to insert another 1,521 input FFs or shift the write event. Production boundary permission remains **HOLD**: source clock/edge ownership and lifetime are unbound, and the exact LEF clusters contacts above the required local face density.

This is a read-only source/view audit of hybrid model `dee8d6b3a`, following `fd363bb2c` and `cdf9e0528`. No RTL, simulation, synthesis, new macro, prototype, gate or default binding was created. The existing D4 and CTLM age-failure evidence is preserved. The exact seven macro views and six compiler/calibration hashes match the hybrid ledger; hashes and complete numeric arc tables are in `ledger.json`. Run `python3 results/arch/qwen_sram_boundary_audit_1019/audit.py` to reproduce this bounded inspection.

| Pin group, each macro | Contacts | Native related clock | Storage/event result |
| --- | ---: | --- | --- |
| `wd_in[63:0]` | 64 | `wclk` | Payload updates selected cells only on enabled rising write edge and enabled bit mask |
| `w_addr_in[4:0]` | 5 | `wclk` | Selected write address sampled at that same event |
| `w_ce_in` | 1 | `wclk` | Write enable controls that event; disabled write preserves storage |
| `w_mask_in[63:0]` | 64 | `wclk` | Each mask bit controls its write bit at the same event |
| `r_addr_in[4:0]` | 5 | `rclk` | Selected read address sampled on enabled rising read edge |
| `r_ce_in` | 1 | `rclk` | Disabled read holds previous output |
| `rd_out[63:0]` | 64 | `rclk` | Registered read output, rising-edge clk-to-Q arcs |
| `wclk`, `rclk` | 2 | separate clocks | Real macro contacts; no root alias or phase assumption |
| `VDD`, `VSS` | 2 | none | Real LEF rails; parent access/connection remains unknown |

All six input groups have both `setup_rising` and `hold_rising` arcs to the listed clock in **TT, FF and SS**. These are actual Liberty input/bus groups, expanded to the exact bit contacts in the ledger. There is no write-data-to-read-output combinational arc. The behavioral source calls `word_write(w_addr_in, wd_in, w_mask_in)` only inside `always @(posedge wclk) if (w_ce_in)`; the mask applies inside the selected word write. Reads use `always @(posedge rclk) if (r_ce_in) rd_out <= word_read(r_addr_in)`. Source helper functions are internal; they create no combinational output bypass. The synthesis BB has identical 206 signal/clock port bits. The BB by itself is not evidence of storage; the matched behavior, timing arcs and exact physical pin ledger establish the modeled storage endpoint.

| Corner | Setup table range, ps | Hold table range, ps | Min clock period, ps | Min high/low pulse, ps |
| --- | ---: | ---: | ---: | ---: |
| TT | -3.2438 to 107.0062 | -57.1497 to 53.1003 | 243.788 | 97.515 |
| FF | -6.8052 to 103.4448 | -59.0778 to 51.1722 | 196.063 | 78.425 |
| SS sensitivity | 8.3005 to 118.5505 | -48.6760 to 61.5740 | 318.128 | 127.251 |

These ranges cover the full 5/20/80/160/320ps constrained/related slew grid, both transition directions, and are identical among the six input groups. They are **not slack**, selected operating-point constraints, a phase guarantee, or silicon characterization. The macro compiler supplies an analytical calibrated abstract. Actual TT setup/FF hold must use propagated source/receiver clocks, actual pin slews, original uncertainty/reserves, extracted wires and the exact library operating point. No negative table entry grants a timing exception.

The physical ledger reveals a discrepancy in the inherited model: **103 contacts / 17.304um = 5.95238 per um is only a full-face average.** Each W/E contact population runs from center y=0.780 to10.572um at **0.096um pitch**, giving **10.41667 contacts per um** within the populated interval. The rest of the face is unused. This does not establish full-face <=6/um distribution. Each signal contact is on M4 with a real rectangle; both clock contacts are W-side near the bottom, not centered by assumption. The LEF supplies M4 PG rails and M1–M4 obstructions; no 26-bank escape, contact-via, PG overlap/short, clock placement, parent slot or access qualification exists. The original single-clock and dual-clock geometries are distinct and cannot be substituted by name. Any new spread-pin geometry must explicitly model its internal leads, TT/FF timing, energy, PG and compiler provenance before views or a build are authorized.

`candidate_contacts.csv` enumerates **5,408 total candidate contacts** (5,356 signal/clock +52 PG), retaining empty actual-instance/binding/access columns. `clock_contacts.csv` enumerates exactly **52** candidate clock contacts; the inherited ten-bank/20-clock example is not the hybrid inventory. Candidate IDs describe proposed storage and are not instantiated hierarchical names.

| Complete lane | Full record bits | Banks | Macro clocks | Inactive physical bits per row |
| --- | ---: | ---: | ---: | ---: |
| `dvs_W5.dd_wo -> native59.dd_i` | 553 | 9 | 18 | 23 |
| `native59.dr_o -> dvs_W5.dr_wi` | 525 | 9 | 18 | 51 |
| `tt_ctlm.hr -> dvs_W5.hr_wi` | 458 | 8 | 16 | 54 |

All1,521 payload bits plus12 epoch and3 stored-written bits are accounted for. Partial high bank bits are inactive by explicit future mask ownership; no live field can be tied away. Proposed write addresses zero-extend the three-bit row index to the physical five-bit address. Their top constants, enable copies, mask constants and driver fanout still require exact physical ownership. Source/receiver root names in the old lane inventory are historical context only; they are not the actual last forwarded `wclk`, receiving `rclk`, phase or production K certificate. Every candidate bank therefore keeps actual instance, root nets, K, reset epoch, first-use and access **NULL**.

The sampled write event stays **W** only if actual incoming payload/address/enable/mask reach their own native clocked macro contacts with legal setup/hold. An upstream arithmetic bypass, unclocked macro variant, unsupported control pin, or a physical pin with no matched native endpoint remains HOLD and could require a separately priced capture stage. The present audit does not authorize that addition or change any edge. Macro read samples at **R**, then the separately modeled output FF captures the prior macro result at **R+1**. This can match the gated candidate read-bank/output split, while legacy direct output atR remains a different contract. Expected epoch, returned data, stored written bit, row index and external-valid evidence must refer to the same preedge transaction; their actual alignment is unproved.

Use `OT_MEM_NO_INIT`: neither array content nor `rd_out` is reset by the macro. Eight asynchronously invalidated external valid bits per lane remain necessary; a stored written flag alone cannot certify first-use. Same-address simultaneous cross-clock read/write is **FORBIDDEN**, without any OLD ordering assumption. The audit cannot derive a safe separation window, address lifetime, stop/restart recovery, epoch-wrap bound, reset pulse, K or native phase from the behavioral source. Fixed finite calendars and source-aligned invalidation must prove these before implementation; no waiting, backpressure or invented phase may fill the gap.

Recommendation: retain the selected hybrid as a conditional model, accept the exact macro's modeled clocked-storage endpoint semantics, and keep both production binding and physical release blocked. The next source/model owner needs complete producer/control/root/reset/read/output-edge manifests and a properly spread-pin dual-clock macro model. A standalone macro bench would only repeat the explicit edge statements and would not resolve the missing production ownership or geometry, so this audit starts no simulation. No extra FFs, write/read retiming, gate or token-rate claim is authorized by this packet.
