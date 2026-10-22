#!/usr/bin/env python3
"""Read-only pin/source contract extraction, not an executed RTL proof."""
import pathlib,json,gzip,hashlib
P=pathlib.Path(__file__).resolve().parent;A=P.parent.parent/'s81_hb1_diagnostic_census_1019';M=P.parent.parent/'s81_hb1_fixedpoint_model_1019'
m=json.load(gzip.open(A/'receipt/mapped.json.gz'))['modules']['ot_s81sl_xr3'];x=json.load(gzip.open(M/'correspondence.json.gz'));norm=lambda s:s.replace('\\','');n='u_ot_pr_core.u.rwr[0]$_DFF_PN0_';row=next(r for r in x['rows'] if norm(r['driver'])==n);assign={(norm(d),ci,p):(norm(src),sc,iv) for src,sc,d,ci,p,iv in x['endpoint_assignments'] if d!='PORT'}
rows=[]
for ci in range(row['copies']):
 pins={}
 for pin,bits in m['cells'][n]['connections'].items():
  if pin=='QN':continue
  pins[pin]={'expanded_owner':assign[n,ci,pin]} if (n,ci,pin) in assign else {'same_original_bit':bits[0]}
 rows.append({'native_identity':row['driver'],'copy':ci,'master':m['cells'][n]['type'],'inputs':pins})
assert len({json.dumps(r['inputs']['D'],sort_keys=True) for r in rows})==1
assert len({json.dumps(r['inputs']['CLK'],sort_keys=True) for r in rows})==1
assert len({json.dumps(r['inputs']['RESETN'],sort_keys=True) for r in rows})==1
c={'scope':'READ-ONLY source/pin correspondence; exact rwr[0] family only, not all841FF or parent qualification','copies':rows,'first_event_contract':'One common rising CLK samples shared D into all13 QN; common low RESETN with actualSETN=HI forces QN1. No equalinitialQ assumption.','source_publication':'CTL input captureK, rwr classificationK+1, sw_v/sw_d priority consumesK+2','first_parent_gap':'Default DL4 downrelay has no reset, VPinputvalid own2sync+1relay; actual parent reset minimum/physical binding not pinned here','source_sha256':{str(p.relative_to(P.parent.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [A/'bundle/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv',A/'bundle/rtl/lib/ot_rst_relay.sv',A/'receipt/ot_rst_land_wrapper.v',P/'parent_slice_snapshot.sv',P/'parent_glue_snapshot.sv',P/'consumer_vp_snapshot.sv']}}
(P/'rwr_pin_contract.json').write_text(json.dumps(c,indent=2)+'\n');print('READ_ONLY_RWR0_COMMON_D_CLK_RESET_PIN_JOIN PASS13; parentfirstauthorityHOLD')
