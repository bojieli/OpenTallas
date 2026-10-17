d4c portrait plan (H-DIE 10-16 22:10; coordinator decision (b) portrait SM + band 3.30): 31,411 x 24,771 = 778.1 mm2,
0 overlaps / 0 outside, blocks 574 mm2 (portrait SM frame 2782.08 x 3697.92 ASSUMED, not built). Band row sets the
quadrant width (~14 mm); SU slice re-aspected 1612.8 x 3150 (same area). Plan only -- relay-inclusive GEN gate open.
python3 tools/hbm_die_v15/compact_plan.py --layout col --core-at 4 --sfu-at-group 2 --core-w 330.48 --core-h 330.48 --core-column-w 276.48 --band 3300 --su-w 1612.8 --su-h 3150 --smw 2782.08 --smh 3697.92 --sm-portrait --qw-extra 2500 --column 3050 --hub-w 480 --fit --carry --sfucore-h 3150 --sfu-store-side --sfus-wh 1020 1412 --sfus-yoff 1866 --hc-eng-mm2 9.5 --hc-links-v16 --hc-x-beats 4 --hc-client-inner --channel 450 --edge 42.4 --out <dir>
