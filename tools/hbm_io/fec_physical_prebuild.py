#!/usr/bin/env python3
"""Conservative actual-netlist prebuild. Bounds are sizing, never physical closure."""
import argparse,collections,hashlib,json,math,pathlib,time
from fec_clock_census import census,SEQUENTIAL
DEFAULT_CLOCKS=['clk','clk_collect','clk_encode','clk_codeword','pma_rck','rclk_syndrome','rclk_bm0','rclk_bm1','rclk_bm2','rclk_bm3','rclk_chien','rclk_emit']
def integer(v):return int(v,2) if isinstance(v,str) else v
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--netlist',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);ap.add_argument('--clock-manifest',type=pathlib.Path);ap.add_argument('--top',default='hfd_serdes487_chien_linear_window');a=ap.parse_args();start=time.monotonic();clocks=json.loads(a.clock_manifest.read_text())['clocks'] if a.clock_manifest else DEFAULT_CLOCKS
 raw=a.netlist.read_bytes();j=json.loads(raw);m=j['modules'][a.top];res=census(j,a.top,clocks);clock_bits={m['ports'][c]['bits'][0]:c for c in clocks}
 ff={c:{'D':set(),'Q':set(),'cells':0,'bits':0} for c in clocks};comb=[];types=collections.defaultdict(lambda:collections.Counter());largest=[];ops=0
 for name,c in m['cells'].items():
  if c['type'] in SEQUENTIAL:
   f=ff[clock_bits[c['connections']['CLK'][0]]];f['D'].update(b for b in c['connections']['D'] if isinstance(b,int));f['Q'].update(b for b in c['connections']['Q'] if isinstance(b,int));f['cells']+=1;f['bits']+=len(c['connections']['Q']);continue
  if c['type']=='$scopeinfo':continue
  p={k:integer(v) for k,v in c['parameters'].items()};ins=set(b for n,v in c['connections'].items() if c['port_directions'][n]=='input' for b in v if isinstance(b,int));outs=set(b for n,v in c['connections'].items() if c['port_directions'][n]=='output' for b in v if isinstance(b,int));comb.append((name,ins,outs,c['type']));t=types[c['type']];t['cells']+=1;t['input_bits']+=len(ins);t['output_bits']+=len(outs)
  width=p.get('WIDTH',p.get('Y_WIDTH',len(outs)));aw=p.get('A_WIDTH',width);bw=p.get('B_WIDTH',width);estimate=width
  if c['type']=='$pmux':estimate=width*p['S_WIDTH'];t['max_S_WIDTH']=max(t['max_S_WIDTH'],p['S_WIDTH'])
  elif c['type'] in ('$shift','$shiftx','$shl','$shr','$sshl','$sshr'):estimate=max(aw,width)*min(bw,max(1,math.ceil(math.log2(max(aw,width)))));t['max_A_WIDTH']=max(t['max_A_WIDTH'],aw);t['max_B_WIDTH']=max(t['max_B_WIDTH'],bw)
  elif c['type']=='$mul':estimate=aw*bw*6
  elif c['type'] in ('$add','$sub','$neg'):estimate=width*5
  elif c['type'] in ('$eq','$ne','$nex','$lt','$le','$gt','$ge'):estimate=max(aw,bw)*3
  elif c['type'].startswith('$reduce_'):estimate=max(0,aw-1)
  t['scalar_expansion_sizing_units']+=estimate;t['max_output_width']=max(t['max_output_width'],len(outs));ops+=estimate;largest.append((estimate,name,c['type'],p))
 drivers={b:i for i,(_,_,out,_) in enumerate(comb) for b in out};consumers=collections.defaultdict(set)
 for i,(_,ins,_,_) in enumerate(comb):
  for b in ins:consumers[b].add(i)
 def cone(seed,back):
  bits=set(seed);pending=list(seed);cells=set()
  while pending:
   b=pending.pop();links=[drivers[b]] if back and b in drivers else consumers.get(b,()) if not back else ()
   for idx in links:
    if idx in cells:continue
    cells.add(idx);new=(comb[idx][1] if back else comb[idx][2])-bits;bits.update(new);pending.extend(new)
  return bits,cells
 roots={};relations=[]
 for root,f in ff.items():
  ib,ic=cone(f['D'],True);ob,oc=cone(f['Q'],False);rootin={s:len(ib&v['Q']) for s,v in ff.items() if ib&v['Q']};rootout={s:len(ob&v['D']) for s,v in ff.items() if ob&v['D']}
  roots[root]={'flop_bits':f['bits'],'flop_cells':f['cells'],'distinct_D_bits':len(f['D']),'distinct_Q_bits':len(f['Q']),'fanin_comb_cells_conservative':len(ic),'fanout_comb_cells_conservative':len(oc),'registered_source_bits_conservative':rootin,'registered_destination_D_bits_conservative':rootout,'external_input_bits_in_fanin':{p:len(ib&set(v['bits'])) for p,v in m['ports'].items() if v['direction']=='input' and ib&set(v['bits'])}}
  for s,n in rootin.items():relations.append({'source_root':s,'sink_root':root,'source_Q_bits_conservative':n,'same_root':s==root})
 qroot={b:r for r,f in ff.items() for b in f['Q']};aliases=[]
 for name,v in m.get('netnames',{}).items():
  if v.get('hide_name',0):continue
  owned=collections.Counter(qroot[b] for b in set(v['bits']) if b in qroot)
  if owned:aliases.append({'net':name,'declared_bits':len(v['bits']),'registered_Q_bits_by_root':dict(owned),'src':v.get('attributes',{}).get('src')})
 out={'scope':'ACTUAL_FULL_GENERIC_NETLIST_PREBUILD_CONSERVATIVE_CELL_DEPENDENCIES','physical_qualified':False,'native_qualified':False,'input_netlist_sha256':hashlib.sha256(raw).hexdigest(),'tool_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'total_flop_bits':res['total_flop_bits'],'roots':roots,'registered_net_aliases_not_unique_owners':aliases,'cells_by_type':dict(types),'scalar_expansion_sizing_units_not_area':ops,'largest_expansion_cells':[{'sizing_units':n,'cell':name,'type':typ,'parameters':p} for n,name,typ,p in sorted(largest,reverse=True)[:30]],'registered_root_relations_conservative':relations,'limitations':['Cell-level dependencies conservatively couple all input/output bits; exact bit-level cones require techmap','Sizing units are not gate count or library area','No wire lengths, pin faces, CTS or route/timing qualification','Standalone wrapper excludes endpoint gearbox and collective endpoints'],'elapsed_seconds':time.monotonic()-start}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'flops':res['total_flop_bits'],'comb_cells':len(comb),'scalar_expansion_sizing_units':ops,'elapsed':out['elapsed_seconds']}))
if __name__=='__main__':main()
