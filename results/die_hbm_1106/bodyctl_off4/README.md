# BODYCTL off32 same-edge fallback

Measured Fri Nov 6 06:57:27 PST 2026. Standalone characterization only; no production RTL/recipe changes, no P&R, no git operations.

Recommendation: use `off32_split` in standalone.sv with leaf.v as the measured implementation for integration consideration. It computes low32(iteration32 * step16), preserves the native three capture edges, and accepts a new unrelated input pair every cycle. At edge1 capture 26 nibble products i=0..7,j=0..3,i+j<8. At edge2 bit-column Wallace reduction (130 full adders, five layers) produces two rows; resolve their low16 addition, retain low16/carry16 and two high16 rows. At edge3 retain low16 and add high16 + high16 + carry16 modulo16. No reset was added (native multiplier pipeline has no reset).

All measurements use actual ASAP7 RVT TT Liberty mapping, existing abc_speed.script, -D833 and original dont_use filters, OpenROAD ideal combinational timing, input delays0, output delays0, load1. Values are capture-cone combinational arrival; they exclude clk->Q, setup, real wires, clock/reset trees. This is evidence for a fallback, not timing sign-off.

| Form / capture edge | Delay ps | Mapped cells | Liberty area |
| --- | ---: | ---: | ---: |
| Native edge1 input capture | 0.00 | 0 | 0.00000 |
| Native edge2 seven byte products, retained widths | 469.31 | 1984 | 229.64958 |
| Native edge3 canonical off function | 476.06 | 415 | 49.35330 |
| Nibble edge1, retained widths | 228.79 | 1898 | 203.49306 |
| Split edge2 compressor + low16 CPA | 317.00 | 455 | 65.98908 |
| Split edge3 high16 + carry16 | 217.79 | 93 | 12.37842 |
| Pure edge2 two CS32 rows | 235.49 | 397 | 59.38434 |
| Pure edge3 full32 CPA | 316.75 | 161 | 20.98062 |

Split edge3 improves native by258.27ps and pure by98.96ps. Split edge2 remains57ps below the prior isolated8x8 full16 reference374ps. Largest split cone317ps vs native476.06ps. Pure largest316.75ps is effectively the same stage budget, but split gives more edge3 margin and saves8 FFs. Retained stage1 output widths matter: products on i+j=7 capture only4 bits. Likewise native last byte products capture only8 bits. Full-output exploratory records remain in the root directory: baseline edge2 450.12ps/2379cells/275.28498area, nibble edge1 247.08ps/1964cells/205.68006area. Use retained/ records in table above for actual retained capture cone areas.

Total retained combinational area native279.00288, split281.86056 (+1.02%), pure283.85802 (+1.74%). Total cells native2399, split2446, pure2456. Variable captured-bit counts native48+96+32=176, split192+48+32=272, pure192+56+32=280; one split2 output and eight pure2 outputs are constant after mapping. These are variable output-bit counts, not a fully mapped sequential area measurement. Illustrative DFFHQNx1 area0.2916/bit gives native330.32448 vs split361.17576 (+9.34%) for logic+FF area; excludes clock/reset overhead and optimization across capture edges.

Exactness: tb.sv compares old canonical three-edge byte-product stream with split and pure streams on200040 back-to-back input pairs:40 directed maxima/ones/shifts and200000 deterministic xorshift64 vectors. Zero mismatches. Dropped carry16 mutant caught67032 times; wrong input phase caught200040; actual partial-product p0[0] flip before compressor caught200040. Carry16 asserted67033 times. sim.log is the exact observed result. Tests intentionally operate on the smallest multiplier vehicle.

Files: gen.py regenerates leaf.v; tb.sv is the independent saved stream fixture; wrappers.py regenerates standalone.sv; map.sh reproduces eight full-output cones; retained/map.sh reproduces retained native/new first-product cones; results.py sums cell areas from the exact TT Liberty files and collects mapped cells/timing. run.sh expects host Icarus and runs simulation then ORFS mapping. Invoke heavy work through ot-run. Intel2 authoritative path: /srv/opentallas-scratch2/claude/codex-off32-edge3-1106. Local source/result mirror: /home/ubuntu/coord/tmp/codex-off32-edge3.

Infrastructure failures preserved: first map job attempted Icarus inside openroad/orfs:asap7lock (absent); bash proceeded to mapping and all mapping cones succeeded. Initial host compile found `pure` was an SV keyword; renamed fixture variable pureres and reran once. Authoritative passing host simulation job oth-ubuntu-2382615-1793976850 exited0. No design/timing failures were discarded or overwritten.

Production integration boundary requested by parent: `ot_bodyctl_off32_split_d.sv` is self-contained, has exactly two internal capture edges and a combinational `out_d`. The parent must retain its original edge3 output register and use out_d as its D input. No extra output register is present inside this helper. helper.py regenerates it from the identical characterized split2 body; helper_tb.sv checks the helper with a separately supplied output capture against native off32_old. Helper SHA256 e44fe63f42fc3568eede51e70e4cd6006ff6fed48dcf2e7e7f9a8d8ec3e86d6b.

Exact supplied-helper confirmation PASS: HELPER_EXTERNAL_EDGE3 samples=200040 mismatch=0. Host simulation job oth-ubuntu-2501468-1793977118 exited0; helper_sim.log contains authoritative vector result. The helper itself has no output capture; the bench supplies it.
