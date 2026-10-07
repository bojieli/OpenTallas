#!/usr/bin/env python3
"""Validate the immutable candidate interface against 8dd route RTL, not current RTL."""
import json,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
VIEW=Path(__file__).parent/'ot_dsrom_head_bundle_glue'
REC=ROOT/'results/rtl/s81_die_views/hbglue/handoff_8ddc70024'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def groups(s,pattern):
 for m in re.finditer(pattern,s):
  start=m.end();depth=1;i=start
  while depth:
   if s[i]=='{':depth+=1
   if s[i]=='}':depth-=1
   i+=1
  yield m.group(1),s[start:i-1]
def main():
 rtl=(REC/'pinned_route_source/rtl/s81/ot_dsrom_head_bundle_glue.sv').read_text().split(')(\n',1)[1].split('\n);',1)[0]
 expected={}
 for direction,width,names in re.findall(r'(input|output)\s+(?:wire|reg)\s*(\[[^]]+\])?\s*([^\n]+)',rtl):
  bits=list(range(int(width[1:-1].split(':')[0])+1)) if width else None
  for name in names.strip().rstrip(',').split(','):
   name=name.strip()
   for n in ([f'{name}[{i}]' for i in bits] if bits else [name]):expected[n]=direction.upper()
 lef=(VIEW/'ot_dsrom_head_bundle_glue.lef').read_text()
 lports={};layers=set()
 for m in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',lef,re.M|re.S):
  name,body=m.groups();direction=re.search(r'DIRECTION (\S+)',body).group(1)
  if re.search(r'USE (POWER|GROUND)',body):continue
  assert re.search(r'RECT\s+[\d .-]+;',body),name
  lports[name]=direction;layers.update(re.findall(r'LAYER (\S+)',body))
 assert lports==expected,{'missing':sorted(expected.keys()-lports.keys()),'extra':sorted(lports.keys()-expected.keys())}
 size=list(map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',lef).groups()))
 report={'rtl_ports':len(expected),'inputs':sum(v=='INPUT' for v in expected.values()),'outputs':sum(v=='OUTPUT' for v in expected.values()),'lef_ports_match_pinned_rtl':True,'lef_size_um':size,'signal_pin_layers':sorted(layers),'corners':{}}
 for c in ['ss','ff']:
  odb={}
  for line in (VIEW/f'ports_{c}.tsv').read_text().splitlines():
   if line.startswith('#'):continue
   name,direction,kind,n=line.split('\t')
   if kind not in ['POWER','GROUND']:odb[name]=direction;assert int(n)>0,name
  assert odb==expected
  lib=(VIEW/f'ot_dsrom_head_bundle_glue_{c}.lib').read_text()
  pins=dict(groups(lib,r'\bpin\("([^"]+)"\)\s*\{'))
  assert pins.keys()==expected.keys() | {'VDD','VSS'}
  for pg in ['VDD','VSS']:pins.pop(pg)
  missing=[];arc_counts={}
  for name,body in pins.items():
   assert re.search(r'direction\s*:\s*(\w+)',body).group(1).upper()==expected[name],name
   types=re.findall(r'timing_type\s*:\s*(\w+)',body);arc_counts[name]=types
   if name=='clk':assert 'clock : true' in body and {'min_clock_tree_path','max_clock_tree_path'}<=set(types)
   elif name=='rst_n' or name.startswith('row0_b['):assert not types,name
   elif expected[name]=='INPUT':
    if not {'setup_rising','hold_rising'}<=set(types):missing.append(name)
   elif 'rising_edge' not in types:missing.append(name)
   for related in re.findall(r'related_pin\s*:\s*"([^"]+)"',body):assert related=='clk',(name,related)
  sdc=(VIEW/f'effective_{c}.sdc').read_text()
  assert '833.3330' in sdc and '341250' not in sdc and '204950' not in sdc
  assert re.search(r'set_clock_uncertainty -setup 60\.0+',sdc)
  assert re.search(r'set_clock_uncertainty -hold 25\.0+',sdc)
  for cmd,value,edge,count in [('input',591,'max',sum(v=='INPUT' for v in expected.values())-1),('input',155,'min',sum(v=='INPUT' for v in expected.values())-1),('output',-91,'max',sum(v=='OUTPUT' for v in expected.values())),('output',-255,'min',sum(v=='OUTPUT' for v in expected.values()))]:
   lines=[l for l in sdc.splitlines() if l.startswith(f'set_{cmd}_delay ') and f'-{edge}' in l]
   assert len(lines)==count,(cmd,edge,len(lines),count)
   assert all(float(l.split()[1])==value for l in lines)
  log=(VIEW/f'export_{c}.log').read_text();slack=float(re.search(r'OT_WS (\S+)',log).group(1))*1e12
  assert abs(slack-({'ss':74.53,'ff':18.7}[c]))<0.01
  report['corners'][c]={'slack_ps':slack,'odb_ports_match':True,'liberty_ports_match':True,'clock_pin':'clk','clock_name':'core_clk','period_ps':833.333,'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,'missing_dynamic_timing_arcs':missing,'expected_untimed':['rst_n (explicit false path)']+[f'row0_b[{i}] (RTL constant zero)' for i in range(17)],'arc_types_by_pin':arc_counts}
  assert not missing,missing
 report['scope']='candidate component only; die outline/pin compatibility and all-source bench qualification blocked'
 report['files']={str(p.relative_to(ROOT)):digest(p) for p in VIEW.iterdir() if p.is_file()}
 (REC/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ['corners','files']},indent=2))
if __name__=='__main__':main()
