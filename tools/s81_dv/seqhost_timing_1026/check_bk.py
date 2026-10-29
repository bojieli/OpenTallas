#!/usr/bin/env python3
"""Current BK wrapper pin-event transit, with observed sampling offsets retained."""
import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--log',type=Path,required=True);p.add_argument('--sources',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--expect-shift',type=int,default=0);a=p.parse_args()
s=a.log.read_text()
if not re.search(r'^PASS$',s,re.M) or not re.search(r'^BK_TIMING sent=32 seen=32 errors=0$',s,re.M):raise ValueError('real BK wrapper transit did not pass')
v=[int(x) for x in re.findall(r'BK_OUT.*edge_delta=(\d+)',s)]
if len(v)!=32 or len(set(v))!=1:raise ValueError('missing/nonuniform BK transit edges')
# The bench drives on the preceding negedge; pin-event time is the preceding
# posedge, and the actual receiver input flop samples on the next posedge.
pin_edges=v[0]+1
if pin_edges+a.expect_shift!=pin_edges:raise ValueError('TIMING_RECEIPT_MUTANT_CAUGHT shifted BK edge')
r=json.loads(a.sources.read_text());r.update(schema='opentallas.s81.bound_control_local.v1',verdict='PASS',masters={'dsdv_bk_sel_vmtx':dict(source_path='physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_l20s.sv',params=dict(TX_SRAM=1),straps=dict(tap_k=17,sink_k=16,ik=4,ek=5,uid=91,eg_n=0),defines=r['defines'],edges=dict(vi_n_pin_event_to_vo_s=pin_edges,vi_n_to_vo_s=pin_edges,vi_n_sampling_to_vo_s=v[0]))},observed_words=32,edge_convention='Primary edges: input pin valid after posedge -> output pin valid after posedge; sampling offsets are separate',scope='Current atomic BK wrapper CTL transit only; no selection programme/die-clock/bound transport/token claim')
manifest=r.pop('source_manifest','physical/die_plan/s81/bind/asbuilt_b178_coll.json')
r['selection_manifest']=dict(path=manifest,sha256=r['source_sha256'].pop(manifest))
a.out.write_text(json.dumps(r,indent=1)+'\n');print('BK_LOCAL PASS pin_event_edges',pin_edges)
