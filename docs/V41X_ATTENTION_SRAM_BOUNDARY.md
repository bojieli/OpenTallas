# V4.1x attention packed-row SRAM boundary

The adopted attention engine (`ot_hdc_v41x_attn`) already consumes packed KV
rows. At the full H16/D512/T640 configuration each row is 16 × 265 bits:
16 groups of a format flag and 264 payload bits. Four row lanes issue together;
the engine's staging memory is therefore 640 × 4,240 = 2,713,600 logical bits
(331.25 KiB). The q.k and p.v paths read one row from each lane in a cycle,
and the existing read register gives one-cycle latency.

`ot_hdc_v41x_attn_staging` makes that memory a separate, cycle-preserving
boundary. Its behavioural mode keeps the prior row array. Its physical mode
stripes each lane across seventeen compiled ASAP7 256-bit × 256-row 1R1W SRAM
macros, 68 macros in total. The address depth is 160 rows per lane, leaving
unused macro rows and padding 112 bits per physical row. The sum of the macro
LEF footprints is 0.482236 mm² per engine; this is a component inventory,
not a routed engine area or a die area. The macro's TT minimum period in the
library is 380 ps; its output and all surrounding mux, compute, wire and
clock paths still need route and STA at the adopted 920 ps period.

`results/rtl/hdc_v41x_attn_macro_stage.json` compares behavioural and macro
models in the same reduced H4/D64/T72 three-job attention campaign. Both pass
the golden's bit-exact score and p.v checks with identical 444 cycles. The
full H16/D512/T640 macro instance lints; a full-shape engine exact run remains
open. The separate representative D32/NL1/TROWS160 physical attempt measures
one lane and one 265-bit group only. Its macro placement and I/O pin placement
passed, but post-I/O global placement repeatedly cycled through routability
inflation and the attempt was stopped. The physical record is an error, with
no routed setup, hold, DRC or power value. It cannot be scaled into a die
timing or power claim.

The full attention adapter is a distinct blocker. It currently materializes
640 × 512 BF16 elements (5,242,880 bits) in `rowbuf`, then presents four
8,192-bit combinational reads to four `encode_row` trees. That is why the
full adapter elaboration exhausts memory even though the engine packed stage
is bounded. The direct packed path must supply rows in logical attention order
0..W+NSEL−1, with a prefix mask on the last beat: up to 128 FP8 window rows
followed by up to 512 selected FP4 compressed rows. The die's packed window
row is 512 FP8 codes followed by 16 UE8M0 scales; group `g` maps to
`{1'b0, scale[g], codes[32*g +: 32]}`. The compressed-row source must supply
32 FP4 nibbles, two E4M3 scales and `fmt=1` for each group. A source selector
and four-bank read timing must be proven before the BF16 row buffer and
re-encoder can be removed. The current reduced exact gate does not exercise
that direct path.
