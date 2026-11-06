Q3 routed clock-port rectangle completion — candidate only

Actual fresh canonical A/B route both have exactly3 RECTONLY markers on clk M5.
Actual DEF: unchanged clk BPin is x276000..276480,y168456..168504nm;
M5 access wire atx276120 goes y168480..168600, with VIA45 upper landing
endingy168623. Their union is a T. Actual local signal/PG DEF neighborhood
contains no foreign M5 metal; the nearby PG stripes are several microns west.

The construction appends only one M5 rectangle x275976..276480,
y168456..168960nm (504x504nm) on the existing clk dbWire. It preserves every old wire
operation/junction/property index, BPin, cell, net and endpoint/phase identity.
No RTL or pin-cycle change. Exact source BPin/access coordinate guards refuse
other geometries; decoded result must equal old operations plus this rectangle.
The metal ends exactly at the existing die edge, never beyond it.

Image q3_clockport_rectangle_review.png was viewed before construction/P&R:
PASS-COND for this bounded measured correction and ordinary targeted data ECO.
The full plan/actual density review for the source A remains in its GEOM_REVIEW.

Source A: epyc5 /srv/opentallas-scratch2/claude/codex-q3-pinphase-1106/kits/vA/
ot_hfd_coll_q3_edge_link_9413579a381a, actual6_final.odb, TT+110.51,
FF-19.40/100, slew31TT/23FF, DRC3. Original failure remains unchanged.
Source B has same3clockmarkers, TT+27.04/FF-14.18, slew32TT; retained.

Own Intel2 dedicated candidate /srv/opentallas-scratch2/claude/codex-q3-clockport-1106/kit_A.
After successful construction, an ordinary targeted-data ECO takes a NEW full
clock freeze from the corrected source; no existing data-ECO check is weakened.
Use existing targeted slew300ps/maxwire100, hold margin0, final TT setup>=0,
FF hold>=0 at25ps uncertainty, allDRV/DRC/PG/clock and actual routedLEC gates.
No blanket pad change, no algorithm/gate/constraint relaxation, no adoption
until the actual physical result passes. E5 ClockC targeted job stays untouched.

Pre-route correction: the initial480x168nm rectangle captured in490253d
was never routed. Actual M5 LEF58 WIDTHTABLE allows24,120,216,...504nm;
168nm is not allowed. Both dimensions of the corrected rectangle are504nm.
The initial construction DB is retained as rectangle168.unqualified; original
Q3 A/B failures remain immutable. Enlarged actual local M5/PG window is clear.

Current Intel2 target dev66307 differs from root66306. E6 memory waiters
were canceled NOT_RUN and its168nm candidate directory renamed
kit_A.rectangle168_REJECTED, so stale waiters cannot route that geometry.
Correct504 construction passed unit1537447-1793974958; ordinary24GB/8thread
targeted data ECO runs via ot-run localhost with the new clock freeze.
