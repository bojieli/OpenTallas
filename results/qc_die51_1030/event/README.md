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

## Fixes after the first gate pass (DIE-QC-51, 21:00-23:15)
5. G0C v1: 33 stm ft slots had the new 3rd-station centre on stm tload macros -> tools/die_plan/ft_nudge.py (counts kept,
   explicit regs_um, max slide 37.1 um, max hop 221.9 um; ft_nudge_ledger.json); reset root
   start_tree.reset_source.source_part_release_cycles 15 -> 17 (= reset_tree.wf_plan release of sl_E0_fw after the deeper
   fw reset tree).  G0C (g0c_785e877a.log): 0 new ERROR (99 -> 96); 7 su WARN re-worded 1 -> 2 stations.
6. fix_suc.py: compose_qc52 re-derived landing BEFORE the BTAB apply; the 3 su_c types re-derived after it (relays 97->91).
7. Bind: results/qc_die51_1030/bind/sidecar.json = DIE-QC-33 sidecar with collector.types re-synced (sidesync.py) for the
   87 event-changed slice types; bindchain52.sh = DIE-QC-33 canonical chain (probe -> R8 regen -> base -> CB16 -> final).
8. BTAB P8eco RE-SIGNED at flow-20261030-f-qc (rs_btab.sh, build commit 0e115b17c66 from the kit freeze.json repo_rev):
   SIGNED TT +306.81 / FF hold +7.44, DRC 0, LEC EQUIVALENT 7251 (btab_fqc/).
render52_taps_stations.png: density taps (from taps.py) + ft stations + collector boxes for stm/ctl/fw/su_c (viewed).
