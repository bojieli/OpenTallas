# Quant overlap seam row repair

Actual ov1 (qw_ov_ref-ov1-cx-c8c47022e) failed DPL-0033 twice: 1,148 fixed
TAPCELL instances occupied rows removed by the POST_TAPCELL seam blockage.
ODB diagnostics are retained under dpl_probe; the failed attempts remain on EPYC1.

The first stopped-stage experiment moved only the blockage to PRE_TAPCELL. It
still placed all1,148 taps in the seam: ASAP7's native tapcell command cuts macro
halos but ignores dbBlockage. Its failure is preserved under pre_only_1148.

The repair explicitly splits192 native rows before tap/endcap insertion,
preserving their site, origin, direction, orientation and spacing. Left segments
end at270.000um; right segments begin at570.024um (the next .054um site). The same
hard placement blockage continues to reserve x270..570/y336.96..388.8.

Fresh2_3 tapcell checkpoint:10720 rows,43622 taps/caps, zero intersecting rows and
zero intersecting tap/cap bboxes in the seam, with384 legal caps at its boundaries.
The warm stopped-stage experiment reads immutable old3_4, replaces ONLY rows and
TAPCELL fixed instances from the fresh checkpoint into a NEW ODB, and keeps all
161593 logical instances, masters, nets, orientations and placements. Before/after
logical signatures are byte-identical (SHA256 f16a190d2317dbd0013ffcd68045b68bd1443c74ef50bdeba699d620239d8cbc).
It runs actual3_5 detailed-placement and check_placement with the existing config,
not another full synthesis/global-placement run. This checks geometry only;
automatic stage timing metrics are not signoff or a new SS advisory gate.

Fleet evidence: ot-epyc1tb:/srv/opentallas-scratch2/codex/qw-ov-row-cut.
Scripts and geometry logs are included under row_cut_check. The original netlist,
failed databases and trial databases are retained on the fleet.

RTL, outline, macros, IO, clock, SDC, cut budget, link budget and price are unchanged.
The source-exact5.050 proof remains184/168 cycles with3328 exact production words,
skew/RAW controls passing and header/lane/premature-retire mutants failing. The
physical cluster remains unclosed until the new route completes TT/FF/DRC/lint.
