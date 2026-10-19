# P3 safe landing and alignment storage

The 2,069-bit related-region crossing previously held four runtime-addressed
flop words (8,276 bits). Four already characterized dual-clock 16x546 macros
replace that storage. Each macro binds `wclk` directly to the source root and
`rclk` directly to the destination root. The existing fixed write/read counters
select four SRAM rows; macro native read capture replaces the old output capture.
The component preserves the original output edge and one word per cycle.

The source and destination ports are separate native macro interfaces. There is
no new dual-clock macro model and no flop-bank storage exception. The standard
four-phase calendar keeps a word stable between write and destination read;
component comparisons at destination phase -0.2T/0/+0.2T measure minimum write
ages1.8T/2T/2.2T. Wrong bank selection and wrong write phase are separate negative
controls. Their committed witnesses accompany passing comparisons. Repeated
reset is included; old SRAM contents are masked until the phase is valid again.

Native macro SS read clk-to-q is386.445ps; min period392.270ps. SS/TT/FF libs
all declare distinct wclk/rclk and timing arcs to both; downstream read paths
must use the destination read-clock reference. These are characterized inputs,
not routed parent timing results. Physical closure remains required.

The 818-bit three-edge pad uses seven smaller existing32x128 macros, with the
native synchronous read already counted. Its 26-bit companion uses a small
addressed flop ring. Both preserve the previous alignment and II. See sizing.json
for installed capacity, area and outstanding physical obligations.

A proposed no-growth floorplan is being analyzed separately. The interim
630.72x2289.6 four-large-pad-macro layout on this branch is superseded and must
not be gated or bound; final exact macro placement follows the analysis.
