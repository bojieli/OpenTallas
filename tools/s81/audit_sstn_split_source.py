#!/usr/bin/env python3
"""Replay an immutable extracted die source graph against actual SSTN split view contacts.

This is a source and pin-set audit. It does not prove routing, PG, clock delivery,
or equal-age production schedules. Run with OT_S81_DIAGNOSTIC_CLOSED_VIEWS=1
when the input table contains diagnostic CLOSED views.
"""
import argparse,gzip,json,sys,hashlib
from pathlib import Path
from types import SimpleNamespace
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
import dsrom_s81_fulldie as G
from s81 import sstn_split as S
from s81 import orientation_qualify as Q
ap=argparse.ArgumentParser(description=__doc__)
for name in ('model','placement','map','views','out'):ap.add_argument('--'+name,required=True)
ap.add_argument('--clock-out', help='Write all literal child clock entries, source nets and actual insertion receipts')
a=ap.parse_args()
M=Path(a.model);mapping=Path(a.map);outpath=Path(a.out)
G.VIEW_BINDING=a.views
views=G.bound_views();d=json.load(gzip.open(M));p=json.load(Path(a.placement).open())['placed']
insts=[SimpleNamespace(name=r[0],master=r[1],kind=r[2],region=r[3],domain=r[4],x=p[r[0]][1],y=p[r[0]][2],w=r[7],h=r[8],orient=r[9])for r in d['insts']]
m=dict(insts=insts,buses=[(b[0],b[1],b[2],[tuple(e[:2])for e in b[3]])for b in d['buses']]);use=G.port_usage(m);oldnet=[(b[0],b[1],b[2])for b in m['buses']]
S.expand(m,use,json.load(mapping.open()),views)
assert oldnet==[(b[0],b[1],b[2])for b in m['buses']]
newuse=G.port_usage(m);summ={};actualpins={}
for mst,ports in [('ot_s81_sstn_base566',S.BASE_PORTS),('ot_s81_sstn_payload536',S.PAYLOAD_PORTS)]:
 v=views[mst];macro=SimpleNamespace(name=mst);S.populate(G,macro,ports)
 expected={p if w==1 and p in v['pins'] else f'{p}[{i}]' for p,(_,w) in ports.items()for i in range(w)}
 actual=set(v['pins']);assert actual==expected,(mst,actual^expected)
 actualpins[mst]={p:v for p,v in G.real_lef(v['lef'])['pins'].items()}
 summ[mst]=dict(job=v['job'],w=v['w'],h=v['h'],signal_pins=len(actual),lef=v['lef'])
rules={}
for master in summ:
 mac=Q.parse_lef(G.real_lef(views[master]['lef'])['text'],master)
 rules[master],bad=Q.track_rule(mac,'R0')
 if bad:raise ValueError('Actual child pins have no common track origin: '+master)
selected=[i for i in m['insts'] if i.master in ('ot_s81_sstn_base566','ot_s81_sstn_payload536')]
assert len(selected)==2238
for i in selected:assert newuse[i.name]==(S.BASE_PORTS if i.master.endswith('base566')else S.PAYLOAD_PORTS)
track_failures=[];clocks=[];clock_nets={}
for bid,cls,width,eps in m['buses']:
 for name,port in eps:
  if port=='ck':clock_nets[name]=bid
for i in selected:
 for axis,value in [('x',i.x),('y',i.y)]:
  period,residues=rules[i.master][axis]
  if round(value*Q.DBU)%period not in residues:track_failures.append([i.name,axis,value])
 if i.orient!='R0':raise ValueError('Actual split child orientation is not R0')
 layer,rect=actualpins[i.master]['ck']
 clocks.append(dict(instance=i.name,master=i.master,source_bus=clock_nets[i.name],clock_pin='ck',layer=layer,actual_xy_um=[i.x+(rect[0]+rect[2])/2,i.y+(rect[1]+rect[3])/2]))
if track_failures:raise ValueError('Actual split child pin tracks fail at '+str(track_failures[:10]))
if a.clock_out:
 receipts={}
 for master in summ:
  f=Path(views[master]['lef']).parent/'insertion.json'
  receipts[master]=dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),actual_insertion=json.loads(f.read_text()))
 Path(a.clock_out).write_text(json.dumps(dict(scope='ACTUAL_CLOCK_ENTRY_AND_INSERTION_CENSUS_NO_DIE_DISTRIBUTION_OR_PHI_R_QUALIFICATION',entries=clocks,master_receipts=receipts),indent=1)+'\n')
out=dict(actual_clock_entries=len(clocks),actual_pin_track_failures=len(track_failures),scope='ACTUAL_PUBLISHED_VIEW_SOURCE_GRAPH_AND_LITERAL_PINSET_REPLAY_ONLY_NOT_INCIDENT_ROUTING_CLOCK_PG_OR_STATIC_CALENDAR_QUALIFICATION',view_table_sha256=hashlib.sha256(Path(a.views).read_bytes()).hexdigest(),placement_sha256=hashlib.sha256(Path(a.placement).read_bytes()).hexdigest(),source_model_sha256=hashlib.sha256(M.read_bytes()).hexdigest(),map_sha256=hashlib.sha256(mapping.read_bytes()).hexdigest(),instances=len(insts),source_buses=len(oldnet),split_parents=m['sstn_split']['instances'],children=len(selected),unchanged_all_bus_name_class_width=True,child_abi_mismatches=0,missing_actual_signal_pins=0,neutral_role_input_instances=len(m['neutral_role_inputs']),masters=summ)
outpath.parent.mkdir(parents=True,exist_ok=True)
outpath.write_text(json.dumps(out,indent=1)+'\n')
print(json.dumps(out,indent=1))
