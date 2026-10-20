# BF native32 structural work in progress

Source base 4496f1308 (FOREP/RSTPART). Existing mapped rr strict census has 426 high fanout roots: 31 registered roots (30 p1_sqb bits 33..36 loads + rst_m 46); 395 combinational roots also exceed32 (worst330). No waiver and no layout gate is authorized by these results.

OT_BF_FOREP32 adds eight shifter slices instead of four, each kept shift selector drives at most six result bits. It also gives the 20 capture-enable words two same-edge kept reset copies (20 loads each instead of the rst_m 46-load tree). Added storage: 384 selector bits +2 reset bits, no pipeline edge, same source/capture phases. No memory capacity change. Kept-copy feed-ins and actual mapped loads must still be checked; the residual combinational cones need structural duplication before the binding census passes. Full physical kit/T-OUT composition is pending that check.

The new macro requires OT_BF_FOREP + OT_BF_RSTPART + OT_BF_TILE_FREECLK. Default and old FOREP behavior retained (NSH4). Bench uses the established production BF exactness vehicle on Verilator5.050, with new selector mutant and old add negative control. No pass claimed yet.
