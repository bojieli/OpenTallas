d4c landscape rp4e plan (H-DIE 10-17 00:15; coordinator-approved landscape after gate-1 portrait failure).
SM rp4e single-row frame 7755.84 x 1807.2 (H-SM measured: 16 x 457.92 + 345.6 front + carve). 4 SM per die row = 31.02 mm,
so --slim-column: IDX scorer ghosts (not in v16 contract) dropped, lk/ep restacked in a 1.0 mm column, hc_eng 1000 x 9500.
32,428 x 25,435 um = 824.8 mm2; reticle margins 0.57 / 0.57 mm; 0 overlaps; gap 100 (incl. 100 um XQL pair channel).
python3 tools/hbm_die_v15/compact_plan.py --layout col --core-at 4 --sfu-at-group 2 --core-w 330.48 --core-h 330.48 --core-column-w 276.48 --band 3400 --su-w 1797.12 --su-h 2825.28 --smw 7755.84 --smh 1807.2 --qw-extra 0 --column 1000 --slim-column --hub-w 480 --fit --carry --sfucore-w 950.4 --sfucore-h 3132 --sfu-store-side --sfus-wh 1020 1412 --sfus-yoff 1866 --hc-links-v16 --hc-x-beats 4 --hc-client-inner --channel 60 --edge 42.4 --gap 100 --out <dir>
Explorer: hbm_d4c_landscape_rp4e (candidate of hbm_d4b_frozen), exported with tools/hbm_die_v15/dataflow_export_d4.py.
