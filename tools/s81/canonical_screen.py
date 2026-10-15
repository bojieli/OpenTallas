#!/usr/bin/env python3
"""Run the real canonical die generator; retain exact partial evidence on failure."""
import argparse,gzip,hashlib,json,sys,traceback
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'));import dsrom_s81_fulldie as G

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);ap.add_argument('args',nargs=argparse.REMAINDER);a=ap.parse_args();w=a.work.resolve();w.mkdir(parents=True,exist_ok=True)
 p=argparse.ArgumentParser();p.add_argument('mode');p.add_argument('--k',type=int,default=16);G.die_options(p);opts=p.parse_args(a.args);G.apply_options(opts);assert G.CANONICAL_LAYOUT is not None
 live={};old=G.buses_r8
 def capture(m):
  live['m']=m
  # Export the fully populated actual field before trunk placement can fail.
  export(m,'field_before_trunks',False)
  return old(m)
 def export(m,name,complete):
  record=dict(scope='COMPLETE_GENERATOR' if complete else 'PARTIAL_GENERATOR_NOT_RELEASE',die=list(G.DIE),insts=[[i.name,i.master,i.x,i.y,i.w,i.h,i.orient,i.kind,i.region] for i in m['insts']],buses=m.get('buses',[]),frames=m['frames'],regions=m['regions'],port_aliases=G.real_ports(),unbound_supplemental_reservations=m.get('canonical_layout',{}).get('hcp_homes',[]),calendar=m.get('canonical_calendar'),variant=m['variant'])
  with gzip.open(w/(name+'.json.gz'),'wt') as f:json.dump(record,f,default=list)
  (w/(name+'_legality.json')).write_text(json.dumps(G.legality(m),indent=1))
 G.buses_r8=capture
 try:
  m=G.build();G.finalize_r8(m)
  from s81.canonical_layout import trace_calendar
  (w/'actual_flight_calendar.json').write_text(json.dumps(trace_calendar(G,m),indent=1))
  export(m,'canonical_plan',True)
  G.write_lefs(m,1,w/'elements.lef');texts=G.die_lef_texts(m)
  with gzip.open(w/'exact_pins.lef.gz','wt') as f:f.write('\n'.join(texts))
  (w/'pin_align.json').write_text(json.dumps(G.pin_align_gate(m,texts,raise_on_fail=False),indent=1,default=list))
  status={'status':'GEN_COMPLETE','native_qualified':False,'legality':G.legality(m),'calendar':m.get('canonical_calendar')}
 except Exception as ex:
  if 'm' in live:
   export(live['m'],'canonical_partial',False)
   try:
    # A stopped constructor has incomplete hub buses. Keep exact coordinates
    # for source-complete masters only, and enumerate excluded masters.
    G.ALIGN_JOGS=False
    mm=live['m'];G.finalize_r8(mm);excluded={}
    for master in {i.master for i in mm['insts']}:
     ports=mm['pdir'].get(master,{})
     rec=G._assigned_record(master)
     absent=[] if not rec else [pn for pn,spec in rec['ports'].items() if pn not in ports or ports[pn][1]!=spec['bits']]
     if absent:excluded[master]=absent
    subset=dict(mm);subset['insts']=[i for i in mm['insts'] if i.master not in excluded]
    names={i.name for i in subset['insts']};subset['buses']=[b for b in mm['buses'] if all(e[0] in names for e in b[3])]
    texts=G.die_lef_texts(subset)
    with gzip.open(w/'partial_exact_pins.lef.gz','wt') as f:f.write('\n'.join(texts))
    (w/'partial_pin_exclusions.json').write_text(json.dumps(excluded,indent=1))
    export(subset,'canonical_partial_finalized',False)
   except Exception as secondary:
    (w/'partial_pin_export_failure.txt').write_text(repr(secondary))
  status={'status':'GEN_FAIL','error':repr(ex),'traceback':traceback.format_exc(),'native_qualified':False};traceback.print_exc()
 sources=['tools/dsrom_s81_fulldie.py','tools/s81/canonical_layout.py','tools/s81/canonical_screen.py'];status['source_sha256']={x:hashlib.sha256((R/x).read_bytes()).hexdigest()for x in sources};status['capacity_sha256']=G.CANONICAL_LAYOUT['sha256'];(w/'status.json').write_text(json.dumps(status,indent=1,default=list));return 0 if status['status']=='GEN_COMPLETE' else 1
if __name__=='__main__':sys.exit(main())
