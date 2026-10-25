#!/usr/bin/env python3
"""Connect frame outputs introduced by the plan (p1->p2 and p4->p5).

Usage: frame_forward_bind.py IN.v PLAN.json INSTANCE_MAP.json OUT.v REPORT.json

Existing p2->p3/p5->p6 connections remain intact. True row ends (p3/p6) already
use _nx and have no output. No hard-core source or pin view changes. The binder
replaces these logical edges with the plan's already-priced registered lanes.
"""
import json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'physical/die_plan/s81/bind'))
import asbparse as A
src,pf,mf,dst,rf=sys.argv[1:]
p=json.loads(Path(pf).read_text());im=json.loads(Path(mf).read_text())['frames']
lines,inst=A.parse(src)
report={'added':[],'already_connected':[],'errors':[],'added_hardware_cycles':0}
neww=[]
def frame(part):
 if not part.endswith('_b0'):return None
 q=im.get(part[:-3]);return 'u_'+q if q else None
def conn(d,p):return next((e for n,e in d['conns'] if n==p),None)
for edge in p['ports']:
 if edge['src']['bus']!='xo_o0' or edge['dst']['bus']!='xo_i0':continue
 a,b=frame(edge['src']['part']),frame(edge['dst']['part'])
 if not a or not b:report['errors'].append('missing frame for '+edge['id']);continue
 aa,bb=inst.get(a),inst.get(b)
 if not aa or not bb:report['errors'].append('missing instance '+str((a,b)));continue
 if int(edge['width'])!=1104:report['errors'].append('unexpected width '+edge['id']);continue
 if not aa['module'].endswith('_asb_x'):report['errors'].append('forwarding source is not _x: '+a);continue
 if conn(aa,'xo') is not None:
  report['already_connected'].append({'edge':edge['id'],'s':a,'d':b})
  continue
 old=conn(bb,'x')
 if old is None:report['errors'].append('missing x input '+b);continue
 net='pf_xo_'+edge['src']['part']+'__'+edge['dst']['part']
 aa['conns'].append(['xo',net]);aa['dirty']=True
 bb['conns']=[[n,net if n=='x' else e] for n,e in bb['conns']];bb['dirty']=True
 neww.append('  wire [1103:0] '+net+';')
 lane=next((x for x in p['lanes'] if edge['id'] in x.get('ports',[])),{})
 priced=p.get('latency',{}).get('lanes',{}).get(lane.get('id'),{}).get('cycles')
 if priced is None:report['errors'].append('no priced latency for '+edge['id'])
 report['added'].append({'edge':edge['id'],'s':a,'d':b,'wire':net,'bits':1104,'old_x':old,
                         'plan_lane':lane.get('id'),'priced_cycles':priced})
for n,d in inst.items():
 if d.get('dirty'):lines[d['line']]=A.emit(d['module'],d['params'],n,d['conns'])
if report['errors']:
 Path(rf).write_text(json.dumps(report,indent=1));raise SystemExit(json.dumps(report['errors']))
end=next(i for i,l in enumerate(lines) if l.strip()=='endmodule')
lines[end:end]=neww
Path(dst).write_text('\n'.join(lines));Path(rf).write_text(json.dumps(report,indent=1))
print(json.dumps({'added_links':len(report['added']),'added_bits':sum(x['bits'] for x in report['added']),
                  'already_connected':len(report['already_connected']),'errors':report['errors']}))
