# B2 actual PG interfaces and native clock/reset mapping, 2026-10-13

The source-pinned VM leaf assembly and preserved SM PG layer case pass pdngen, both rail connectivity checks and nominal PSM. These cases preserve actual PG rectangles from real leaf LEFs, rather than inventing a full-tile PG interface.

| Case | Source PG | Parent tie | Inner VDD drop mV | Inner VSS rise mV | Rail-sum bound mV | Budget mV |
|---|---|---|---:|---:|---:|---:|
| Native VM leaf assembly | bank/rstop/rcl/star M6; hub M5 | M5–M6–M7–M8–M9 | 4.055 | 4.131 | 8.186 | 35 |
| Historical SM, actual extent | M8 | M9 only; no die M8 over SM | 14.729 | 14.894 | 29.623 | 35 |

VM has thirteen real children per slice: eight banks, hub, two ring stops, ring client and star receiver. Their actual PG clips yield 611 current-map tiles no larger than 43.2 µm; no opaque hardened VM parent is created. The assembly is replicated for four B2 slices. The native bit-level component and its placement/cut/seam ledger are in `results/arch/hbm_native_1013/vm`.

The historical SM test retains exact M8 PG from the 2202.77 × 2072.79 µm real view and distributes current among 2448 clipped PG tiles. This proves the M8-to-M9 parent connection can work at its actual extent; it does not legalize the incompatible 3214.08 × 1131.84 µm legacy die slot. The functional native successor comprises sixteen 630.72 × 1252.8 µm M7-PG tile clusters per SM (512 for 32 SMs), plus real front/back units; its full die placement is separate and pending.

Both current cases use the existing explicitly assumed peak densities (VM 1.05 and SM 1.20 W/mm²), not measured switching activity. Inner values exclude a guard of two 63.640 µm per-rail bump pitches. SM full-window VSS rise is 32.852 mV at the cut edge; reporting the guarded inner value follows the S81 window lesson. Internal child-grid IR, actual signal obstructions, complete die coverage, package impedance and external PHY/host/link rails remain unverified. `final_signoff_eligible` remains false.

The old missing-PG census included 17,542 `hfd_ckb` clock buffers and 17,542 `hfd_rrl` registered-reset nodes. These now have explicit mappings to 52,626 real ASAP7 cells: BUFx24 per clock buffer; DFFHQNx1 plus INVx2 per reset register. The actual TT Liberty specifies QN = registered(!D), so the inverter is necessary to preserve the true registered reset. `glue/cell_truth.json` pins the Liberty hashes and verifies these functions. A real 12-cell prototype passes legal placement, pdngen M1–M5, and VDD/VSS connectivity and exports actual M5 PG. This qualifies its cell mapping/PG mechanism, not full die CTS or timing closure of all nodes. Forwarded/data station families remain explicit native RTL work; they are not assigned a guessed flop count.

Full solver cases and real PG-only export LEFs remain on `ot-epyc1tb:/srv/opentallas-scratch/claude/hbmdie-v10/pg_1013/{vm,sm,glue}`. Input/generator hashes are in each manifest. Failed parser, width-table and row-edge attempts remain separately archived there. The progressing authoritative GRT checkpoint was not changed.
