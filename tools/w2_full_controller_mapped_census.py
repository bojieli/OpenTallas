#!/usr/bin/env python3
"""Mapped CW/state/area census; explicit unknown dynamic power and timing."""
import argparse,collections,gzip,hashlib,json,re
from pathlib import Path

def groups(text,kind):
 for match in re.finditer(r'\b'+kind+r'\s*\(\s*"?([^"()\s]+)"?\s*\)\s*\{',text):
  start=match.end();level=1;quoted=False;escape=False;end=start
  for end in range(start,len(text)):
   c=text[end]
   if quoted:
    if escape:escape=False
    elif c=='\\':escape=True
    elif c=='"':quoted=False
   elif c=='"':quoted=True
   elif c=='{':level+=1
   elif c=='}':
    level-=1
    if not level:break
  if level:raise ValueError('unclosed liberty '+kind)
  yield match.group(1),text[start:end]
def value(text,key):
 m=re.search(r'\b'+re.escape(key)+r'\s*:\s*([-+0-9.eE]+)\s*;',text)
 return float(m.group(1)) if m else None

def liberty_facts(paths):
 cells={};libs={}
 for p in paths:
  b=p.read_bytes();t=gzip.decompress(b).decode() if p.suffix=='.gz' else b.decode()
  t=re.sub(r'/\*.*?\*/','',t,flags=re.S)
  leak=re.search(r'leakage_power_unit\s*:\s*"([^"]+)"',t)
  cap=re.search(r'capacitive_load_unit\s*\(\s*([0-9.eE]+)\s*,\s*(\w+)\s*\)',t)
  factors={'W':1.,'mW':1e-3,'uW':1e-6,'nW':1e-9,'pW':1e-12};power_scale=None
  if leak:
   q=re.fullmatch(r'([0-9.eE]+)([munp]?W)',leak.group(1));power_scale=float(q[1])*factors[q[2]] if q else None
  cap_scale=float(cap[1])*{'ff':1.,'pf':1000.}[cap[2].lower()] if cap else None
  for name,body in groups(t,'cell'):
   pins={}
   for pn,pb in groups(body,'pin'):
    dr=re.search(r'\bdirection\s*:\s*(\w+)\s*;',pb)
    cp=value(pb,'capacitance')
    pins[pn]={'direction':dr[1] if dr else None,'cap_fF':cp*cap_scale if cp is not None and cap_scale is not None else None}
   lp=value(body,'cell_leakage_power')
   cells[name]={'area_um2':value(body,'area'),'sequential':bool(re.search(r'\bff\s*\(',body)),'latch':bool(re.search(r'\blatch\s*\(',body)),'pins':pins,'leakage_W':lp*power_scale if lp is not None and power_scale is not None else None}
  libs[str(p)]={'SHA256':hashlib.sha256(b).hexdigest(),'leakage_power_unit':leak[1] if leak else None,'cap_unit':cap[0] if cap else None}
 return {'cells':cells,'libraries':libs}

def census(netlist,facts):
 modules=netlist['modules'];tops=[(n,m) for n,m in modules.items() if m.get('attributes',{}).get('top') in ('00000000000000000000000000000001',1,'1')]
 if len(tops)!=1:raise ValueError('unique mapped top required')
 name,top=tops[0];book=facts['cells'];counts=collections.Counter(c['type'] for c in top['cells'].values());unknown=set(counts)-set(book)
 if unknown:raise ValueError('nonproduction/unmapped cells '+str(sorted(unknown)))
 drivers={};seq=set();latches=[]
 for cn,c in top['cells'].items():
  typ=c['type'];f=book[typ]
  if f['sequential']:seq.add(cn)
  if f['latch']:latches.append(cn)
  for pn,bits in c['connections'].items():
   if f['pins'].get(pn,{}).get('direction')=='output':
    for bit in bits:
     if type(bit)==int:drivers[bit]=(cn,pn)
 def state_owner(bit,seen=None):
  if type(bit)!=int:return None
  seen=set() if seen is None else seen
  if bit in seen:return None
  seen.add(bit);pair=drivers.get(bit)
  if pair is None:return None
  cn,pn=pair;c=top['cells'][cn]
  if cn in seq:return cn
  if c['type'].startswith(('INV','BUF')):
   ins=[b for p,bs in c['connections'].items() if book[c['type']]['pins'].get(p,{}).get('direction')=='input' for b in bs]
   return state_owner(ins[0],seen) if len(ins)==1 else None
  return None
 cw={n:x['bits'] for n,x in top['netnames'].items() if re.search(r'(?:^|[.])cw\[\d+\](?:\[\d+\])?$',n.lstrip('\\'))}
 cwbits=[b for bs in cw.values() for b in bs];owners=[state_owner(b) for b in cwbits]
 area=sum(count*book[t]['area_um2'] for t,count in counts.items())
 leakage=None if any(book[t]['leakage_W'] is None for t in counts) else sum(count*book[t]['leakage_W'] for t,count in counts.items())
 clock_caps=[book[top['cells'][n]['type']]['pins'].get('CLK',{}).get('cap_fF') for n in seq]
 clock=None if any(v is None for v in clock_caps) else sum(clock_caps)
 cwseq=len({v for v in owners if v is not None});passed=len(cwbits)==15768 and cwseq==15768 and all(v is not None for v in owners) and not latches
 return dict(schema='w2.full219.mapped-census.v1',top=name,cells_total=sum(counts.values()),cell_counts=dict(counts),area_um2=area,body_mm2=area/1e6,actual_flop_cells=len(seq),latch_cells=len(latches),cw_logical_bits=len(cwbits),cw_distinct_flop_cells=cwseq,cw_nonstate_or_constant_bits=sum(v is None for v in owners),full219_storage_census_PASS=passed,
  replication1280={'mapped_body_mm2':area/1e6*1280,'50pct_placement_before_PG_CTS_routes_mm2':area/1e6*2560,'mapped_flops':len(seq)*1280,'CW_flops':cwseq*1280,'F0_replacement_credit':None},
  power={'SS_cell_leakage_W':leakage,'1280_SS_cell_leakage_W':None if leakage is None else leakage*1280,'clock_pin_cap_fF':clock,'clock_pin_CV2f_only_W':None if clock is None else clock*1e-15*.63**2*1.2e9,'scope':'Library leakage at SS100C/0.63V; clock-pin CV2f only if1.2GHz reached. Actual state/activity, internal/signal dynamic, CTS/PG/route power unknown; no total-chip power claim.'},
  latency={'source_II_sameclient':19,'source_II_differentclient':10,'source_repair_II':9,'target_period_ps':2500/3,'mapped_or_physical_slack':None,'actual_service_cycles_or_whole_token_delta':None,'scope':'Mapping changes area only; no new pipeline or source cycle change. Functional equivalence, loaded timing and provider-bound service still separate.'},
  decision='MAPPED_SOURCE_FULL_STORAGE_CENSUS_PASS_NOT_PHYSICAL_OR_FUNCTIONAL_QUALIFICATION' if passed else 'MAPPED_SOURCE_STORAGE_CENSUS_FAIL',libraries=facts['libraries'])

def main():
 p=argparse.ArgumentParser();p.add_argument('--extract-libs',nargs='+',type=Path);p.add_argument('--netlist',type=Path);p.add_argument('--facts',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 d=liberty_facts(a.extract_libs) if a.extract_libs else census(json.loads(a.netlist.read_text()),json.loads(a.facts.read_text()))
 a.out.write_text(json.dumps(d,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()
