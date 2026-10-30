#!/usr/bin/env python3
"""Diagnostic lane0 wiring proof; explicitly FAIL current-native KIND identity."""
import json,pathlib,re,sys
from boundary_wiring_proof import graph
D=json.load(open(sys.argv[1]))['modules'];m='ot_hbm_su_static_pgslice_lg__lane_exp0_id';g=graph(D[m]);assert g==graph(D[m+'__native_reference']);assert g!=graph(D[m+'__wrong_id_mutant']);assert {k:int(v,2) for k,v in D[m]['cells']['u_core']['parameters'].items()}==dict(ALAT=4,MLAT=4,WCOPY=0)
facts=json.load(open(sys.argv[2]));rows=[r for r in facts if r['local'] in ('u_su_Q0_lane_exp0','u_su_Q1_lane_exp0')];assert len(rows)==4
for r in rows:assert r['module']=='ot_hnx_su_exp__rst3' and r['ids']['lane_lane_id']['value'] in (0,16)
source=pathlib.Path(sys.argv[3]).read_text();assert '.KIND(2)' in source
report=dict(status='DIAGNOSTIC_BOUNDARY_EQUAL_CURRENT_NATIVE_ARITHMETIC_MISMATCH_HOLD',boundary_all_input_graph_equal=True,wrong_id_graph_mutant_rejected=True,explicit_parameters=dict(ALAT=4,MLAT=4,WCOPY=0),native_bound_ids=[dict(path=r['path'],part=r['part'],local=r['local'],value=r['ids']['lane_lane_id']['value']) for r in rows],canonical_KIND=2,current_native_KIND=1,current_native_arithmetic_match=False,physical_adoption='HOLD: actual native rst3 exp cut required, no old FULL2 substitution')
pathlib.Path(sys.argv[4]).write_text(json.dumps(report,indent=2)+'\n');print('PASS boundary graph + wrong-ID control; CURRENT NATIVE KIND IDENTITY FAIL2vs1; HOLD')
