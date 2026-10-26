#!/usr/bin/env python3
"""Allocate candidate sites for every actual techmapped soft FF, preserving source stage counts."""
import argparse,json,re,collections,copy
from pathlib import Path
import cb16_physical_pads as C

def tcl_sites(sites):
 def quote(s):return '{'+s.replace('\\','\\\\').replace('{','\\{').replace('}','\\}')+'}'
 lines=['# Candidate placement of actual mapped FF only; fail closed on any alias or cell-count mismatch.',
        '# Requires the real mapped ODB and ff_put_near from kit; does not create cells or stages.',
        'array set qc_mapped_alias {}; array set qc_mapped_xy {}; array set qc_mapped_seen {}']
 seen={}
 for i,r in enumerate(sites):
  lines.append('set qc_mapped_xy(%d) {%.6f %.6f}'%(i,r['x_um'],r['y_um']))
  for a in r.get('aliases',[dict(name=r['register'],bit=r['bit'])]):
   name=a['name'].replace('/','.').replace('\\','');names=[name+'['+str(a['bit'])+']']+([name] if a['bit']==0 else [])
   for alias in names:
    if alias in seen and seen[alias]!=i:raise ValueError('mapped Q alias identifies multiple FF: '+alias)
    if alias in seen:continue
    seen[alias]=i;lines.append('set qc_mapped_alias('+quote(alias)+') '+str(i))
 # Tcl array indices cannot quote only the index as set arr({key}); use list-safe variable names.
 lines=[re.sub(r'^set qc_mapped_alias\(\{(.*)\}\) (\d+)$',lambda m:'set '+quote('qc_mapped_alias('+m[1]+')')+' '+m[2],x) for x in lines]
 lines += ["set qc_mapped_block [ord::get_db_block]; set qc_mapped_dbu [$qc_mapped_block getDbUnitsPerMicron]","set qc_mapped_found 0; set qc_mapped_unknown {}",r'''foreach qc_i [$qc_mapped_block getInsts] {
 if {![string match "*DFF*" [[$qc_i getMaster] getName]]} continue
 set qc_ids {}
 foreach qc_t [$qc_i getITerms] {
  if {[$qc_t getIoType] ne "OUTPUT"} continue
  set qc_n [$qc_t getNet]; if {$qc_n eq "NULL"} continue
  set qc_name [string map {\\ {} / .} [$qc_n getName]]
  if {[info exists qc_mapped_alias($qc_name)]} {lappend qc_ids $qc_mapped_alias($qc_name)}
 }
 set qc_ids [lsort -unique $qc_ids]
 if {[llength $qc_ids]!=1} {lappend qc_mapped_unknown [$qc_i getName]; continue}
 set qc_id [lindex $qc_ids 0]
 if {[info exists qc_mapped_seen($qc_id)]} {error "mapped FF alias matched multiple cells: $qc_id"}
 set qc_mapped_seen($qc_id) [$qc_i getName]
 lassign $qc_mapped_xy($qc_id) qc_x qc_y
 set qc_ok [ff_put_near $qc_i [expr {round($qc_x*$qc_mapped_dbu)}] [expr {round($qc_y*$qc_mapped_dbu)}]]
 if {$qc_ok eq ""} {error "no legal actual FF site: [$qc_i getName]"}
 incr qc_mapped_found
}''',f'set qc_mapped_expected {len(sites)}',
 'puts "QC_MAPPED_FF_PLACED $qc_mapped_found EXPECTED $qc_mapped_expected UNKNOWN [llength $qc_mapped_unknown]"',
 'if {$qc_mapped_found != $qc_mapped_expected || [llength $qc_mapped_unknown]} {error "actual mapped FF placement incomplete; unknown=[lrange $qc_mapped_unknown 0 9]"}']
 return '\n'.join(lines)+'\n'


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('--type',required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--physical',type=Path,required=True);p.add_argument('--rtl',type=Path,required=True);p.add_argument('--out',type=Path,required=True);q=p.parse_args();q.out.mkdir(exist_ok=False,parents=True)
 raw=json.loads(q.plan.read_text());t=raw['partition_types'][q.type];P=C.schema.Plan(raw);inv=json.loads(q.inventory.read_text());report=json.loads((q.physical/'report.json').read_text());banks=json.loads((q.physical/'banks.json').read_text());by={(b['instance'],b['stage']):b for b in banks};used=[b['box_um'] for b in banks]+[h['box_um'] for h in report['fabric_homes']];homes={h['inst']:h for h in report['fabric_homes']};groups=collections.defaultdict(list);missing=[];sites=[];extra=[];txt=q.rtl.read_text();pinrows=C.gen_phys.type_pins(P,q.type);pinby=collections.defaultdict(list)
 for name,bit,layer,x,y,face in pinrows:pinby[name].append((x,y,face))
 anchors={}
 for name,rest in re.findall(r'\bot_dp_r(?:relay|gate)\s+(\w+)\s*\(([^\n]+)',txt):
  m=re.search(r'@\s*\(([0-9.]+),\s*([0-9.]+)\)',rest)
  if m:anchors[name]=[float(m[1]),float(m[2])]
 anchors['u_rst_in']=C.gen_phys.tap_points(P,q.type)[1];anchors['u_run_in']=[anchors['u_rst_in'][0]+4.32,anchors['u_rst_in'][1]]
 for r in inv['registers']:
  if r['category']=='delay':
   b=by.get((r['delay_instance'],r['stage']))
   if not b or r['bit']>=b['bits']:missing.append(r);continue
   x,y,_,_=b['box_um'];col=r['bit']%b['columns'];row=r['bit']//b['columns'];sites.append(dict(**r,x_um=x+col*C.PITCH_X,y_um=y+row*C.CELL_H));continue
  root=r['register'].split('/')[0].split('.')[0];groups[root].append(r)
 for root,regs in groups.items():
  face='N';region=None
  if root in homes:
   region=homes[root];target=region['center_um'];# existing reserved 40x40 region has space for actual 1032FF
   b=dict(box_um=[target[0]-18.36,target[1]-4.05,target[0]+18.36,target[1]+4.05],columns=17,bits=len(regs))
   if len(regs)>17*30: # use 34columns; 1032FF in 73.44x8.37 doesn't fit40, instead18cols x58rows =38.88x15.66
    b=dict(box_um=[target[0]-19.44,target[1]-7.83,target[0]+19.44,target[1]+7.83],columns=18,bits=len(regs))
   if b['box_um'][3]>region['box_um'][3] or b['box_um'][2]>region['box_um'][2]:raise ValueError('actual fabric FF exceeds declared soft region')
  else:
   if root.startswith(('u_bin_','u_bout_')):
    bus=re.sub(r'^u_b(?:in|out)_','',root);rows=pinby.get(bus,[])
    if not rows:missing.extend(regs);continue
    target=[sum(z[0] for z in rows)/len(rows),sum(z[1] for z in rows)/len(rows)];face=rows[0][2]
   elif root.startswith('u_ft_'):
    m=re.match(r'u_ft_(.+)_o_(\d+)$',root);slot=next((s for s in t['ft_slots'] if m and s['name']==m[1]),None)
    if not slot:missing.extend(regs);continue
    target=slot['regs_um'][int(m[2])];face='N'
   elif root in anchors:target=anchors[root]
   else:missing.extend(regs);continue
   b=C.pack(target,len(regs),face,t['outline_um'],C.boxes(t),used)
  b.update(instance=root,scope='actual mapped soft state',category='feedthrough' if root.startswith('u_ft_') else regs[0]['category']);extra.append(b)
  for i,r in enumerate(regs):
   x,y,_,_=b['box_um'];sites.append(dict(**r,x_um=x+(i%b['columns'])*C.PITCH_X,y_um=y+(i//b['columns'])*C.CELL_H))
 # All candidate density sinks are actual mapped FFs; do not add planned_sinks a second time.
 bins=q.out/'candidate_sink_sites.json';bins.write_text(json.dumps(dict(scope='CANDIDATE sites of actual mapped FF; not placed ODB',bin_um=0,bins=[[s['x_um'],s['y_um'],1] for s in sites]))+'\n')
 candidate=copy.deepcopy(raw);ct=candidate['partition_types'][q.type];ct['clock'].update(tap_mode='density',tap_max_sinks=1500,tap_target_sinks=1200,tap_radius_um=160,sink_sites_um=[],sink_bins_file=str(bins.resolve()));CP=C.schema.Plan(candidate);C.taps._CACHE.clear();density=C.taps.density_taps(CP,q.type)
 summary=dict(scope='CANDIDATE_SITES_FOR_ACTUAL_TECHMAPPED_SOFT_FF; native macro clocks excluded',actual_soft_ff=inv['soft_ff'],located_soft_ff=len(sites),missing_soft_ff=len(missing),categories=inv['categories'],source_declared_delay_ff=sum(b['bits'] for b in banks),mapped_delay_ff=inv['categories'].get('delay',0),optimized_delay_bits=sum(b['bits'] for b in banks)-inv['categories'].get('delay',0),clock_ports=[dict(name=n,x=x,y=y,sinks=k,max_radius_um=r) for n,x,y,k,r in density],clock_port_count=len(density),max_clock_sinks=max(r[3] for r in density),max_clock_radius_um=max(r[4] for r in density),placement_status='CANDIDATE_NOT_DPL',g2='BLOCKED actual hard views and physical clock interface adoption')
 (q.out/'sites.json').write_text(json.dumps(sites)+'\n');(q.out/'place_actual_mapped.tcl').write_text(tcl_sites(sites));(q.out/'extra_banks.json').write_text(json.dumps(extra,indent=1)+'\n');(q.out/'missing.json').write_text(json.dumps(missing,indent=1)+'\n');(q.out/'summary.json').write_text(json.dumps(summary,indent=1)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='clock_ports'}))
if __name__=='__main__':main()
