#!/usr/bin/env python3
"""Run the real canonical die generator; retain exact partial evidence on failure."""
import argparse,gzip,hashlib,json,pickle,sys,traceback
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'));import dsrom_s81_fulldie as G

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);ap.add_argument('args',nargs=argparse.REMAINDER);a=ap.parse_args();w=a.work.resolve();w.mkdir(parents=True,exist_ok=True)
 p=argparse.ArgumentParser();p.add_argument('mode');p.add_argument('--k',type=int,default=16);G.die_options(p);opts=p.parse_args(a.args);G.apply_options(opts);assert G.CANONICAL_LAYOUT is not None
 live={};checkpoint=[0];old=G.buses_r8
 def capture(m):
  live['m']=m
  # Export the fully populated actual field before trunk placement can fail.
  export(m,'field_before_trunks',False)
  result=old(m);m['canonical_buses_complete']=True;return result
 def export(m,name,complete,scope=None):
  record=dict(scope=scope or ('COMPLETE_GENERATOR' if complete else 'PARTIAL_GENERATOR_NOT_RELEASE'),die=list(G.DIE),insts=[[i.name,i.master,i.x,i.y,i.w,i.h,i.orient,i.kind,i.region] for i in m['insts']],buses=m.get('buses',[]),frames=m['frames'],regions=m['regions'],port_aliases=G.real_ports(),unbound_supplemental_reservations=m.get('canonical_layout',{}).get('hcp_homes',[]),calendar=m.get('canonical_calendar'),rsc_repack=m.get('canonical_rsc_repack'),service_paths=m.get('canonical_service_paths'),chain_paths=m.get('chain_paths'),broadcast_trees=m.get('canonical_broadcast_trees'),injectors=m.get('canonical_injectors'),variant=m['variant'])
  with gzip.open(w/(name+'.json.gz'),'wt') as f:json.dump(record,f,default=list)
  (w/(name+'_legality.json')).write_text(json.dumps(G.legality(m),indent=1))
 G.buses_r8=capture
 old_finalize=G.finalize_r8;passes=[0]
 def finalize_capture(m):
  # Retain the full model before any costly final alignment. Public plan JSON
  # omits glue/pdir/spread metadata and cannot safely recreate emitted RTL.
  with (w/f'model_before_finalize{checkpoint[0]}.pickle').open('wb') as f:pickle.dump(m,f,protocol=5)
  checkpoint[0]+=1
  result=old_finalize(m)
  if m.get('canonical_buses_complete') and not m.get('_canonical_snapshot_done'):
   m['_canonical_snapshot_done']=True;name=f'construction_pass{passes[0]}';passes[0]+=1
   export(m,name+'_plan',True,scope='COMPLETE_CONSTRUCTION_BEFORE_HOP_SIGNOFF_NOT_NATIVE')
   try:
    texts=G.die_lef_texts(m)
    with gzip.open(w/(name+'_pins.lef.gz'),'wt')as f:f.write('\n'.join(texts))
    G.write_netlist(m,1,w/(name+'_die.v'))
    (w/(name+'_die_glue.sv')).write_text(G.glue_rtl(m))
   except Exception as ex:
    (w/(name+'_export_error.json')).write_text(json.dumps(dict(error=repr(ex),traceback=traceback.format_exc(),native_qualified=False),indent=1))
  return result
 G.finalize_r8=finalize_capture
 try:
  m=G.build();G.finalize_r8(m)
  from s81.canonical_layout import trace_calendar
  (w/'actual_flight_calendar.json').write_text(json.dumps(trace_calendar(G,m),indent=1))
  export(m,'canonical_plan',True)
  # Export the actual complete structural graph for source-port binding.
  G.write_netlist(m,1,w/'die.v')
  (w/'die_glue.sv').write_text(G.glue_rtl(m))
  G.write_def_floorplan(m,w/'floorplan.def')
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
