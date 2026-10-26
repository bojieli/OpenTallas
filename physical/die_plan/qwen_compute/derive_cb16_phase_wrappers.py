#!/usr/bin/env python3
"""Source-derived CB16 phase vehicles, never a substitute for a fresh strict bind.

Every non-delay byte is checked against the actual base wrapper. Whole-port payload+epoch delay depth changes
are exactly the approved profile. This exposes physical cell demand while the full source bind is building.
"""
import argparse,copy,hashlib,json,re
from pathlib import Path
import cb16_physical_pads as C

def leafname(s):
 m=re.fullmatch(r'u_t_(\d)_(\d)',s)
 if m:return 'u_t'+m[1]+m[2]
 m=re.fullmatch(r'u_fab\.u_x_(\d)_(\d)',s)
 if m:return 'u_xstn'+m[1]+m[2]
 raise ValueError(s)

def derive(raw,profile,base_report,base_dir,out):
 out.mkdir(parents=True,exist_ok=False);(out/'rtl').mkdir();report=dict(schema='opentallas.cb16.derived_source_vehicles.v1',scope='DERIVED_SOURCE_ONLY_NOT_STRICT_BIND',types={});changes=[]
 for c in profile['classes']:
  tn,family=c['type'],c['family'];t=raw['partition_types'][tn];base=base_report['types'][family]['module'];text=(base_dir/'rtl'/f'{base}.sv').read_text();original=text;reversals=[];extra_ff=0;payload_ff=0
  for v in c['pad_vector']:
   bits=sum(b-a+1 for a,b in v['bits']);extra=v['pad'];target=leafname(v['leaf'])+'.'+v['port'];buses=[b for b in t['buses'] if b.get('leaf')==target and b['dir']=='in']
   if len(buses)!=1:raise ValueError((tn,target,buses))
   b=buses[0];bn=b['name'];actual=next((m for m in C.DLY.finditer(text) if m[3]=='u_lpad_'+bn),None)
   if actual:
    W,D=int(actual[1]),int(actual[2]);before=actual[0];after=before.replace(f'.D({D})',f'.D({D+extra})',1);text=text[:actual.start()]+after+text[actual.end():];reversals.append((after,before));how='extend existing actual delay'
   else:
    W=b['width']+1;D=0
    line=re.search(r'^.*\bu_bin_'+re.escape(bn)+r'\s*\([^\n]+\);[^\n]*$',text,re.M)
    if not line:raise ValueError((tn,bn,'no actual input face driver'))
    old=line[0];driver=old.replace(f'.q({bn}_q)',f'.q({bn}_phase_b)').replace(f'.eq({bn}_eq)',f'.eq({bn}_phase_eb)')
    if driver==old:raise ValueError((tn,bn,'driver shape'))
    inserted=f'    wire [{W-2}:0] {bn}_phase_b;\n    wire {bn}_phase_eb;\n'+driver+f'\n    ot_dp_dly #(.W({W}), .D({extra})) u_lpad_{bn} (.clk(clk), .d({{{bn}_phase_eb, {bn}_phase_b}}), .q({{{bn}_eq, {bn}_q}}));'
    text=text[:line.start()]+inserted+text[line.end():];reversals.append((inserted,old));how='insert actual whole-port delay after face driver'
   if W!=bits+1:raise ValueError((tn,bn,'payload/epoch width mismatch',W,bits))
   extra_ff+=W*extra;payload_ff+=bits*extra;changes.append(dict(type=tn,family=family,bus=bn,width=W,old_depth=D,new_depth=D+extra,extra=extra,actual_added_ff=W*extra,payload_added_ff=bits*extra,how=how))
  if payload_ff!=c['added_ff_max']:raise ValueError((tn,payload_ff,c['added_ff_max']))
  check=text
  for a,b in reversed(reversals):
   if check.count(a)!=1:raise ValueError('ambiguous reverse patch')
   check=check.replace(a,b,1)
  if check!=original:raise ValueError('a non-delay byte changed')
  module='qc_phase_vehicle_'+tn;text=re.sub(r'(?m)^(module\s+)'+re.escape(base)+r'\b',r'\g<1>'+module,text,count=1)
  (out/'rtl'/f'{module}.sv').write_text(text);report['types'][tn]=dict(module=module,base_module=base,payload_added_ff=payload_ff,actual_added_ff=extra_ff,non_delay_bytes='IDENTICAL after reversing explicit patches',source_sha256=hashlib.sha256(original.encode()).hexdigest())
 (out/'bind_report.json').write_text(json.dumps(report,indent=1)+'\n');(out/'changes.json').write_text(json.dumps(changes,indent=1)+'\n');return report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('profiles',type=Path);p.add_argument('--base-bound',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=derive(json.loads(a.plan.read_text()),json.loads(a.profiles.read_text()),json.loads((a.base_bound/'bind_report.json').read_text()),a.base_bound,a.out);print('DERIVED_ACTUAL_CB_PHASE_VEHICLES',len(r['types']))
if __name__=='__main__':main()
