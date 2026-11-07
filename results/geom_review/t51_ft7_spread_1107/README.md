# T51 FT7 ring pose spread: one PLACE pilot

CLASS: DRIVE_AND_WIRE plus local N-edge density. Actual M5/M6+120um E CTS has7bins>.7,max.761 in FT7ring, while its TT setup estimate is+132.24ps and FFhold−51.16ps. No GRT was released.

REDESIGN: spread1417 existing native FT7ring sequential poses in1160..1188um downward into adjacent free legal rows, while keeping x/pins/clock roots/RTL and23402 other poses unchanged. Exact original sourcepose hash is asserted in the receipt; expected exact cohort count fails closed. The row allocator checks all other native poses and already allocated targets for overlap. Maximum vertical displacement26.46um. Reset-release source cells outside this ring cohort are unchanged. Orientation follows existing0.27um alternating rows.

Model: added single-end wire reach<=26.46um; at conservative3ps/um budget this is~79.4ps against preexisting+132ps setup estimate (not timing proof). Existing120um repair mechanism remains active. An area model moving only these FFs in actualCTS and leaving all combinational cells frozen reduces density peak.761→.6713 and7→0bins>.7. Actual GPL/resize may differ: no density/route qualification claimed. View t51_ft7_spread_planned.png; source gray combinational geometry retained only for comparison. No macros/PG changes, no PINcycles added. Existing all-signal M5-M6 profile is retained, not per-net routing.

Pilot one PLACE only from exact original kit inputs+1_* synth checkpoint; keep all prior forms. Inspect actual density/pose/hops/clock and legal-site counts before CTS or GRT. This is a new physical structure, not an unchanged P&R retry. No sibling/batch release.
