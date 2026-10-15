from pathlib import Path
import json,re,collections,hashlib
P=Path(__file__).parent
N=collections.defaultdict(list); I={}
for line in (P/'connections.tsv').read_text().splitlines():
 a=line.split('\t');N[a[0]].append(a)
for line in (P/'instances.tsv').read_text().splitlines():
 a=line.split('\t');I[a[0]]=(a[1],int(a[2]),int(a[3]))
hard=lambda m:m.startswith(('qkh_','qwen_glue_','ot_qwen_tile_'))
phys=lambda m:m.startswith('TAPCELL')
buf=lambda m:m.startswith('BUF')
tie=lambda m:m.startswith('TIE')
p={n:n for n in N}
def find(n):
 while p[n]!=n:p[n]=p[p[n]];n=p[n]
 return n
def union(a,b):p[find(a)]=find(b)
bi=collections.defaultdict(list)
for n,cs in N.items():
 for a in cs:
  if buf(a[3]):bi[a[2]].append(n)
for ns in bi.values():
 for n in ns[1:]:union(ns[0],n)
C=collections.defaultdict(list)
for n,cs in N.items():C[find(n)]+=cs
bits=json.loads(Path('/tmp/qce-residual-prune/residual_bits.json').read_text())['modules']['qfd_tile_nk_banked_v1']['netnames'];aliases=collections.defaultdict(list)
for name,r in bits.items():
 for k,b in enumerate(r['bits']):
  if isinstance(b,int):aliases[b].append(name)
def sourcegroups(name):
 n=name.replace('\\','');m=re.match(r'(.+)\[(\d+)\]$',n);key=m[1]if m else n;k=int(m[2])if m else 0
 if key in bits and k<len(bits[key]['bits']):
  aa=aliases[bits[key]['bits'][k]]
 else:aa=[n]
 groups=[]
 for a in aa:
  if a.startswith('u_logic.'):
   a=a[8:];g=a.split('.')[0];groups.append(g)
 return sorted(set(groups))
rows=[];feed=[];clocks=[];constants=[]
for root,cs in C.items():
 names=sorted(set(a[0]for a in cs));hs=[a for a in cs if hard(a[3])];rs=[a for a in cs if a[2]!='@PARENT'and not hard(a[3])and not buf(a[3])and not tie(a[3])and not phys(a[3])];ts=[a for a in cs if tie(a[3])];ps=[a for a in cs if a[2]=='@PARENT']
 if not hs:continue
 if any(a[1]in ('POWER','GROUND','CLOCK')for a in cs)or any(a[4]in ('clk','ck','CLK')for a in hs)or any(a[4]=='ck'for a in ps):clocks.append(names);continue
 if ts and not rs:constants.append(names);continue
 if not rs:feed.append(names);continue
 hi=any(a[5]=='INPUT'for a in hs);ho=any(a[5]=='OUTPUT'for a in hs)
 gr=sorted(set(g for n in names for g in sourcegroups(n)))
 rows.append({'nets':names,'residual_input':ho,'residual_output':hi,'groups':gr,'hard_pins':[{'instance':a[2],'pin':a[4],'direction':a[5]}for a in hs],'residual_pins':[{'instance':a[2],'master':a[3],'pin':a[4],'direction':a[5]}for a in rs]})
std={i:r for i,r in I.items()if not hard(r[0])and not phys(r[0])};seq={i:r for i,r in std.items()if r[0].startswith('DFF')};comb={i:r for i,r in std.items()if not r[0].startswith('DFF')}
g=collections.Counter()
for r in rows:
 for k in r['groups']or['unresolved_alias']:g[k]+=1
summary={'source':'actual85 3_2_place_iop.odb','hard_children':sum(hard(r[0])for r in I.values()),'residual_stdcell_count':len(std),'residual_ff_count':len(seq),'residual_comb_count_including_ties_buffers':len(comb),'residual_stdcell_master_area_um2':sum(r[1]*r[2]/1e6 for r in std.values()),'residual_ff_area_um2':sum(r[1]*r[2]/1e6 for r in seq.values()),'unique_residual_hard_signal_components_after_buffer_collapse':len(rows),'residual_input_port_bits':sum(r['residual_input']for r in rows),'residual_output_port_bits':sum(r['residual_output']for r in rows),'bidirectional_components':sum(r['residual_input']and r['residual_output']for r in rows),'excluded_pure_hard_feedthrough_components':len(feed),'excluded_constant_components':len(constants),'excluded_power_clock_components':len(clocks),'groups_nonexclusive':dict(g),'minimum_pin_perimeter_at_0p096um_pitch_no_corners_um':len(rows)*.096,'notes':['Buffer chains collapsed electrically; inverter gates retained as logic.','Ports count unique actual residual-to-hard net components, not endpoint multiplicity.','Includes no top-level residual-only ports yet; actual source aliases attach group names, may overlap.','Master area sums are placed standard-cell master geometry, not a proposed outline or utilization allowance.','No hardleaf outline/pin placement/route is qualified.']}
(P/'cut_ports.json').write_text(json.dumps(rows,indent=2)+'\n');(P/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
parent_rows=[];full=[]
for root,cs in C.items():
 hs=[a for a in cs if hard(a[3])];rs=[a for a in cs if a[2]!='@PARENT'and not hard(a[3])and not buf(a[3])and not tie(a[3])and not phys(a[3])];ps=[a for a in cs if a[2]=='@PARENT']
 if not rs or not (ps or hs):continue
 if any(a[1]in ('POWER','GROUND','CLOCK')for a in cs)or any(a[4]in ('clk','ck','CLK')for a in hs)or any(a[4]=='ck'for a in ps):continue
 names=sorted(set(a[0]for a in cs));ri=any(a[5]=='OUTPUT'for a in hs)or any(a[5]=='INPUT'for a in ps);ro=any(a[5]=='INPUT'for a in hs)or any(a[5]=='OUTPUT'for a in ps)
 row={'nets':names,'input':ri,'output':ro,'parent_pins':[a[4:]for a in ps],'hard_endpoint_count':len(hs)}
 full.append(row)
 if ps:parent_rows.append(row)
(P/'parent_port_components.json').write_text(json.dumps(parent_rows,indent=2)+'\n')
(P/'complete_monolithic_ports.json').write_text(json.dumps(full,indent=2)+'\n')
summary['parent_signal_components_touching_residual']=len(parent_rows)
summary['parent_only_signal_components_touching_residual']=sum(not r['hard_endpoint_count']for r in parent_rows)
summary['complete_monolithic_signal_ports']=len(full)
summary['complete_monolithic_input_bits']=sum(r['input']for r in full)
summary['complete_monolithic_output_bits']=sum(r['output']for r in full)
summary['complete_perimeter_lower_bound_0p096_pitch_um']=len(full)*.096
(P/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('COMPLETE',len(full),sum(r['input']for r in full),sum(r['output']for r in full),'parent',len(parent_rows),'parentonly',sum(not r['hard_endpoint_count']for r in parent_rows))
