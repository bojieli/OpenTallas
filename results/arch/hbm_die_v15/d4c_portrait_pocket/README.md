d4c portrait + pocket plan (H-DIE 10-16 23:10; coordinator: portrait SM, band row, pocket = structural fit, spend margin on channels)
32,266.6 x 25,369.9 um = 818.6 mm2; reticle margins 0.73 (W) / 0.63 (H) mm; 0 overlaps / 0 outside; blocks 576.5 mm2,
density incl. ~45 mm2 relays ~0.76. Measured leaves: sfucore k8 950.4 x 3132, pgslice 1797.12 x 2825.28; SM portrait frame
2782.08 x 3697.92 ASSUMED (gate 1 open). Channels: gap 60 everywhere, centre channels 650, edge 150, band 3500.
Pocket: quarter core/COLL stack at the lower SM-row level, SFU store + HC client at the upper level, hub at band level.
v6_eval: cut V 0.738 (NE top edge window, 1 > 0.60) / H 0.453; stages_bw 9.305 (830.2 plan 9.376); SM_X 10.32,
SM_HBM 10.41, COLL_EP 9.56, HC_ENG 7.0, VM_HUB 19.59, COLL_RING 29.88, IDX_COLL 30.0. Plan only; gate-2 GEN open.
python3 tools/hbm_die_v15/compact_plan.py --layout col --core-at 4 --sfu-at-group 2 --core-w 330.48 --core-h 330.48 --core-column-w 276.48 --band 3500 --su-w 1797.12 --su-h 2825.28 --smw 2782.08 --smh 3697.92 --sm-portrait --pocket --qw-extra 2500 --gap 60 --column 3050 --hub-w 480 --fit --carry --sfucore-w 950.4 --sfucore-h 3132 --sfu-store-side --sfus-wh 1020 1412 --sfus-yoff 1866 --hc-eng-mm2 9.5 --hc-links-v16 --hc-x-beats 4 --hc-client-inner --channel 650 --edge 150 --out <dir>
python3 tools/hbm_die_v15/v6_eval.py <dir> --slack 1200 --spread vmh_SW:W:159.84 vmh_NW:W:159.84 vmh_SE:W vmh_NE:W --lanes-mode legs
