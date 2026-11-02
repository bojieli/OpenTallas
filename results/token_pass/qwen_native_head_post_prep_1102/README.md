Selected native HEAD post/STN numerical consumer SOURCE PREP only.

The smallest arithmetic cone is one actual two-lane pair: sender
sl_W5_st_a.u_u_r0 uses qfd_dv_s8_station_tail1_nb0; receiver
sl_W4_st_a.u_u_r0 uses qfd_dv_s8_station_tail1. The sender has no neighbor input
and emits mode3 L8 data. The receiver has the real64b neighbor input/control2b,
mode2 held-own-L8 plus neighbor addition, and shared genuine BF16 BTAB multiply.
Selected parameters are ADD7/SCALE7/SKEW14/JB8/PIN_IN1/BT_LAT1. One selected
qfd_dv_s6_btab owns the shared256b scale read, through s5_btab_s4/s5_btab_safe
and four real128x256 SRAMs; region0 takes bits31:0. This is an actual two-lane
numeric boundary. Full16-lane AMAX requires all eight station regions, coherent
valid/index/last, actual per-user ctl context, then the scalar up/root interface.

The native station source68f56e2ee establishes298 STN commands, KC8 and receivers
1,3,5,6,8,10 with six receiver-only clears. The preparation reads encoded actual
commands, checks all149 receiver blocks, and chooses two concrete fixtures:
block0 rows0..127, receiver1/sender0, sbase72,nwords8; and block148 rows18944..18991,
receiver8/sender9, sbase264,nwords3. Three actual kind2 BTAB boot records cover
their scale addresses. Every used256b word was checked against the genuine
recovered rank0 BF16 scale image: words0..7 and1184..1186. The records are committed
without replacing storage by direct scale constants.

Station inputs must be actual L6 collector partials, not tile0's TG4 output.
Each own station receives fs/ns/fn/nn, combines(fs+ns) and(fn+nn), then combines
them into L8. The receiver combines that held L8 with the neighbor L8. At the
full split512 geometry, the eight L6 streams together cover all4096 columns;
tile0 covers only32 columns. Exact stream-to-column membership/tree order must
be recovered from selected collector wiring before producing numerical input.

KC8 is an essential boundary: station counters select the last K block after
eight blocks of slot-ordered raw words. The native PART1 output valid is not a
last-K-only signal. Ordinary nwords8 needs64 incoming valid words per L6 stream;
the tail station nwords3 contract needs24. Actual collector masking/publication
of those tail valid words must be traced; no production arrival lease is implied.
The existing leaf golden data covers only finalK7 partials and cannot stand in
for these complete intermediate-prefix streams or full logits.

The source/readset and explicit remaining fixture requirements are in
post_fixture_requirements.json. Next numerical preparation needs canonical H4096,
genuine full-column code rows for the two blocks, selected L6 port/group mapping,
real neighbor/BTAB response timing, and full eight-region assembly for AMAX.
No generic PART2 engine, ME ready/result response, numerical data, execution date,
RTL simulation, heavy dispatch or whole-chain qualification was fabricated.
