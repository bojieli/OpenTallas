d4c landscape rp4e plan (H-DIE 10-17 00:15; coordinator-approved landscape after gate-1 portrait failure).
SM rp4e single-row frame B+C 7689.6 x 1807.2 (H-SM: W carve dropped, front 362.88 abutted; be_cmd BE-to-BE hop relay).
so --slim-column: IDX scorer ghosts (not in v16 contract) dropped, lk/ep restacked in a 1.0 mm column, hc_eng 1000 x 9500.
32,343 x 25,437 um = 822.7 mm2; reticle margins 0.66 / 0.56 mm (band row now sets quadrant width); 0 overlaps; gap 100 (incl. 100 um XQL pair channel).
python3 tools/hbm_die_v15/compact_plan.py --layout col --core-at 4 --sfu-at-group 2 --core-w 330.48 --core-h 330.48 --core-column-w 276.48 --band 3400 --su-w 1797.12 --su-h 2825.28 --smw 7689.6 --smh 1807.2 --qw-extra 90 --column 1000 --slim-column --hub-w 480 --fit --carry --sfucore-w 950.4 --sfucore-h 3132 --sfu-store-side --sfus-wh 1020 1412 --sfus-yoff 1866 --hc-links-v16 --hc-x-beats 4 --hc-client-inner --channel 60 --edge 42.4 --gap 100 --out <dir>
Explorer: hbm_d4c_landscape_rp4e (candidate of hbm_d4b_frozen), exported with tools/hbm_die_v15/dataflow_export_d4.py.
UPDATE 10-17 01:25: HC split4 (H-NETLIST/HC a53caaa624d842f3b: stick rejected; 4 pieces 1.2 x 2.5 mm, +0.08% AR) -> centre column 1200,
channels 40, edge 30: 32,478 x 25,435 = 826.1 mm2, margins 0.52 / 0.57 mm. hc_eng in compact.P.json is still the single re-aspected
placeholder (1200 x 7917); gate-2 GEN places the 4 pieces at the quadrant band levels in the column.
--column 1200 --channel 40 --edge 30 (other flags as above)
