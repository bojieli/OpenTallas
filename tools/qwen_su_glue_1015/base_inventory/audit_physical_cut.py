import json,collections,hashlib,argparse
a=argparse.ArgumentParser();a.add_argument("netlist");args=a.parse_args()
p=args.netlist
j=json.load(open(p));m=j['modules']['qfd_sp_su64_sfu_glue_entries']; cells=m['cells']; mods=j['modules']
ff={n:c for n,c in cells.items() if 'DFF' in c['type']}
qowner={b:n for n,c in ff.items() for b in c['connections']['Q']}
seq=collections.Counter()
for n,c in ff.items():
 src=c.get('attributes',{}).get('src','').split('|')[0];seq[src]+=len(c['connections']['Q'])
black={n:c for n,c in cells.items() if mods.get(c['type'],{}).get('attributes',{}).get('blackbox') in ('00000000000000000000000000000001',1)}
logic={n:c for n,c in cells.items() if n not in black}
ld=set();lu=set()
for n,c in logic.items():
 for pn,bs in c['connections'].items():
  (ld if c['port_directions'][pn]=='output' else lu).update(b for b in bs if isinstance(b,int))
external_in=set();external_out=set()
for port_name,v in m['ports'].items():
 (external_in if v['direction']=='input' else external_out).update(b for b in v['bits'] if isinstance(b,int))
for n,c in black.items():
 for pn,bs in c['connections'].items():
  (external_in if c['port_directions'][pn]=='output' else external_out).update(b for b in bs if isinstance(b,int))
bi=external_in&lu;bo=external_out&ld
names={}
for n,v in m['netnames'].items():
 if 'g_grp' in n: names[n]={'width':len(v['bits']),'unique_q_bits':len(set(v['bits'])&set(qowner))}
res={'netlist_sha256':hashlib.sha256(open(p,'rb').read()).hexdigest(),'ff_bits':len(qowner),'ff_source_lines':dict(seq),'blackbox_instances':dict(collections.Counter(c['type'] for c in black.values())),'residual_physical_boundary':{'input_unique_nets':len(bi),'output_unique_nets':len(bo),'total':len(bi|bo)},'group_nets':names,'top_ports':{n:{'width':len(v['bits']),'direction':v['direction']} for n,v in m['ports'].items()}}

qn=collections.defaultdict(list)
for n,v in m['netnames'].items():
 if not n.startswith('$') and not v.get('hide_name'):
  for b in v['bits']:
   if b in qowner:qn[b].append(n)
regs=collections.Counter(min(ns,key=lambda n:(len(n.split('.')),len(n))) for ns in qn.values())
res['register_output_alias_partition']=dict(regs)
group=m['netnames']['u_su.u_su.g_grp[0].g_on.gb']['bits']
res['group_broadcast_bitmap']={'variable_positions':[i for i,b in enumerate(group) if isinstance(b,int)],'constant_bits':{str(i):b for i,b in enumerate(group) if isinstance(b,str)},'independent_ff_bits':len(set(group)&set(qowner))}
# Native low-to-high concatenation at source lines200–201; WR16/NW18.
fields=[('wrom_q',256),('imm2',32),('imm1',32),('i_sfu',3),('cls',3),('ad',3),('red',2),('dst',2),('mb',2),('ma',2),('redsq',1),('md',1),('mc',1),('csrc',1),('bsrc',1),('asrc',1),('dsi',24),('csi',24),('bsi',24),('asi',24),('rrow',24),('fin_th',19),('v',18)]
off=0;res['group_fields_low_to_high']=[]
for name,w in fields:
 bs=group[off:off+w];res['group_fields_low_to_high'].append(dict(name=name,lsb=off,width=w,variable_positions=[i for i,b in enumerate(bs) if isinstance(b,int)],independent_ff_bits=len(set(bs)&set(qowner))));off+=w
assert off==500
def state_of(names):
 return set(b for name in names for b in m['netnames'][name]['bits'])&set(qowner)
parts={
 'crom_input':state_of(['u_su.crq_q0']),
 'crom_kv_output':state_of(['u_su.crom_addr','u_su.crom_re','kv_waddr','kv_wdata','kv_we']),
 'reducer_input':state_of(['u_su.u_su.rd_x','u_su.u_su.rd_addr','u_su.u_su.rd_v','u_su.u_su.rd_mx','u_su.u_su.rd_sq','u_su.u_su.rd_last']),
 'broadcast_merged':state_of(['u_su.u_su.g_grp[0].g_on.gb','u_su.u_su.g_grp[0].g_on.gv','u_su.u_su.g_grp[0].g_on.rg'])}
seen=set()
for name,bs in parts.items():
 assert not (bs&seen),name
 seen|=bs
res['source_natural_cut_ff_bits']={name:len(bs) for name,bs in parts.items()}
res['source_natural_cut_ff_bits']['remaining_control']=len(set(qowner)-seen)
res['admission']=dict(unit='see run_receipt.json',followup='bitmap is same immutable netlist; no synthesis rerun',memory_gb=2,threads=1)
res['scope']='source/netlist sizing only; no physical slot, hardview area, boundary phase/RC or route qualification'
print(json.dumps(res,indent=2))
