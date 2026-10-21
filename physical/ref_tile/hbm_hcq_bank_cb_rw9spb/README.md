# hbm_hcq_bank_cb_rw9spb

Actual placed-clock model in results/arch/hbm_hc_cb_clock_1021/model.json; original WR3 placed ODB and native census SHA-bound. Generic CTS failed clk_w0 TT140.5ps across1035 actual sinks; oldWR4 fallback failedclk_h0 TT111.2ps across1025 and remains diagnostic. This candidate uses WR3 with exact ring witness967833086; no new bench campaign or functional claim.

Topology:32 existing glue roots each retain original input port/clock contract, local symmetric centre-bbox bisection fed by a repeated common trunk,150um clock segments, 40um/4sink leaf partitions. All20 hard entries retain exact original delivery and raw Liberty clock paths. Original outer hybrid wrapper still validates source/root coverage and every strict80ps TT/FF spread; no selected subset, threshold or phase change. Same ports, outline, data/clock edges and source RTL.

SAFE checklist:
1 Pins/reset: unchanged registered faces, two-stage control reset landing and per-consumer kept copies; no new functional flops.
2 Reach: unchanged landed row/data-hop source; common clock trunks segmented150um. Actual clock pin/mass coordinates from3_place.odb are recorded, not inferred from pin aliases.
3 Fanout: original WR3 mapped nativePASS max32 over25856roots SHA-bound in model; new mapped native admission required before layout, no new PASS inferred. Clock-only buffer topology changes.
4 Depth: functional logic unchanged.
5 Storage: existing SRAM/lane hardviews unchanged; no new indexed storage or delay flops.
6 Floorplan: same777.6x734.4 frame/children/pins/bands asCB rw8. Prior actual gate fill47.7percent. Gate PNG/census/fullface/channel review remains required before any submit.
7 Clock: preserve32 declared glue roots/20 hard entries, actual hardchild Liberty refs; actual within-root ALL measured pin/flopTT/FF<=80ps. All32 roots receive distribution repair because original checker aborted before later roots were measured. Original cross-clock and actual data STA must complete, parent/dieSTA mandatory. io_hold_margin0.03.
8 Schedule: static, zero new cycles. Both primary/fallbackWR3, matching committed ring source; WR4 old diagnostic not adopted.

Witness source: results/rtl/hbm_hc_ring_1021_rw8/ring_rw8_m0.log PASS24mix/4outs; m1/m5/m6 fail HC_ENG FAIL. Physical and connected-checkpoint qualification are separate obligations. No root geometry approval invented; critical/multifail packet required before submit.
