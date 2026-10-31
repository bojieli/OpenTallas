# DIE-QC-51: plan_qc52 = the LAST QC plan event (OWNER 12.22, COORD 18:54 + 20:43)

plan_of_record/plan_qc52.json (sha256 8ab0fb33) = plan_qc50 (dc20ac54, gen50 GEN PASS) +
1. ft stations (12.15c): stm/sc E<->W slots 2->3 (613-um span, face-pinned end stations), su_l0/l1/su_c 1-station slots -> 2;
   219 slots; latency.lanes recomputed by main gen.py latency (184 lanes +1/+2/+4 cycles).
2. density die-clock taps (1200/960/200) on every slice type (87): stm keeps its measured sink bins (plan_qc51),
   others use planned sinks (face/ft registers; core contents not in the plan -> UNCHECKED until kits place). 760 -> 2821 taps.
   Landing data re-derived with the compose_qc50/qc51 rules (79/87 reproduce the base exactly; 8 st_a types differ only by
   relay xy drift of the current reset_tree, re-derived).
3. BTAB P8eco bind (option a): qfd_dv_s8x_btab 293.76x155.52, pins cores/su/qfd_dv_s8x_btab_pins_p8eco.json (1318 pins
   from the signed P8eco 6_final.def; 1317/1318 == f3b, ck moved), ck tap xy + insertion from the signed view (283.6/230.4).
4. collector_spread.py: slice collectors whose near() box holds >=5 landing groups get their own adjacent 4.32-um box
   (landing_contract.group_rects_um; sle_ctl tap-13 class, QC-KITS-AC 20:26); 40 collectors / 28 types, 0 fails.
Scripts: compose_qc52.py, btab_p8eco.py, collector_spread.py; reports *_report.json. Gates: g0c (intel2 die-qc-51/g0c),
strict bind (bind52.sh), die clock GEN gen52 (gen52_config.yaml, intel2 die-qc-51/gen52).
