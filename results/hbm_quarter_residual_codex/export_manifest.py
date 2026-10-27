from pathlib import Path
import argparse,json,re,hashlib,collections,subprocess
ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--run',type=Path,required=True);ap.add_argument('--out',type=Path);args=ap.parse_args()
r=args.source_root.resolve();base=args.run.resolve();o=args.out or r/'results/hbm_quarter_residual_codex';o.mkdir(parents=True,exist_ok=True);source_sha=subprocess.check_output(['git','-C',str(r),'rev-parse','HEAD'],text=True).strip()
mods=json.loads((base/'quarter_residual.mapped.json').read_text())['modules'];top='ot_hnx_idxn_quarter_with_keybuf';hard={'ot_hidx_score_hcol','ot_hbm_idx_tail_native'};macro='ot_sram_1r1w_256x256_m2_r2c2';std=collections.Counter();children=[];mem=[]
root_ports=mods[top]['ports'];clk=root_ports['clk']['bits'][0]
def dig(bits):return hashlib.sha256(json.dumps(bits,separators=(',',':')).encode()).hexdigest()
def walk(typ,path,bindings):
 m=mods[typ]
 lookup={}
 for pn,pd in m['ports'].items():
  if pn in bindings:
   assert len(pd['bits'])==len(bindings[pn]),(path,pn)
   lookup.update(zip(pd['bits'],bindings[pn]))
 def resolve(bit):return bit if isinstance(bit,str) else lookup.get(bit,f'{path}:{bit}' if path else bit)
 for name,c in m.get('cells',{}).items():
  ct=c['type'];cp=f'{path}.{name}' if path else name;conn={p:[resolve(b) for b in bs] for p,bs in c['connections'].items()}
  if ct in hard or ct==macro:
   clocks=conn.get('clk_pair',conn.get('clk',[]));assert clocks and all(b==clk for b in clocks),(cp,clocks,clk)
   rec=dict(path=cp,module=ct,parameters=c.get('parameters',{}),clock_bits=clocks,ports={p:dict(bits=len(bs),sha256=dig(bs),first=bs[:3],last=bs[-3:],constants={k:bs.count(k) for k in ['0','1','x','z'] if k in bs}) for p,bs in conn.items()})
   if ct=='ot_hidx_score_hcol':
    e,chunk,k,h=map(int,re.search(r'ge\[(\d+)\]\.gc\[(\d+)\].*g_col\[(\d+)\]\.g_half\[(\d+)\]',cp).groups());assert int(c['parameters']['HALF'],2)==h and int(c['parameters']['MUT'],2)==0;rec['native_coordinate']=dict(engine=e,chunk=chunk,key_column=k,half=h);rec['key_input_port_age_edges']=3+2*chunk;rec['key_p_capture_age_edges']=4+2*chunk
   (mem if ct==macro else children).append(rec)
  elif '_ASAP7_' in ct:
   std[ct]+=1
  elif ct in mods:
   walk(ct,cp,conn)
  else:
   raise AssertionError((ct,cp))
walk(top,'',{p:d['bits'] for p,d in root_ports.items()})
assert len(children)==66 and len(mem)==17
hcols=[a for a in children if a['module']=='ot_hidx_score_hcol'];assert len(hcols)==64
for e in range(2):
 for c in range(4):
  for k in range(4):
   a=[a for a in hcols if a['native_coordinate']==dict(engine=e,chunk=c,key_column=k,half=0)][0];b=[a for a in hcols if a['native_coordinate']==dict(engine=e,chunk=c,key_column=k,half=1)][0]
   assert a['ports']['key']['sha256']==b['ports']['key']['sha256'],(e,c,k)
assert sum(std.values())==227684
ff=sum(n for t,n in std.items() if t.startswith('DFF'));assert ff==94263
lef=(r/'physical/asap7_memory_macros_v2'/macro/(macro+'.lef')).read_text();w,h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef).groups());area=w*h
files=json.loads((base/'quarter_residual.files.json').read_text())
manifest=dict(schema='opentallas.native-quarter-residual.v1',source_commit=source_sha,rtl_top=top,params=dict(TP=192),external_ports={p:dict(direction=d['direction'],bits=len(d['bits'])) for p,d in root_ports.items()},external_input_bits=sum(len(d['bits']) for d in root_ports.values() if d['direction']=='input'),external_output_bits=sum(len(d['bits']) for d in root_ports.values() if d['direction']=='output'),source_files={f:hashlib.sha256((r/f).read_bytes()).hexdigest() for f in files['files']},mapped_netlist_sha256=hashlib.sha256((base/'quarter_residual.netlist.v').read_bytes()).hexdigest(),mapped_json_sha256=hashlib.sha256((base/'quarter_residual.mapped.json').read_bytes()).hexdigest(),hard_children=children,soft_sram_instances=mem,census=dict(standard_cells=sum(std.values()),standard_area_um2=34909.316820,flop_bits=ff,hard_hcol=64,hard_tail=2,soft_sram=17,sram_area_each_um2=area,sram_area_total_um2=17*area,soft_std_plus_sram_area_um2=34909.316820+17*area,standard_cell_types=dict(std)),historical_baseline=dict(source='physical/die_plan/hbm/over_cap_split/ot_hbm_idx_score_quarter_static.split.json',glue_cells=213320,current_scorer_residual_std_cells=213464,current_keybuf_std_cells=14219,wrapper_std_cells=1,total_delta_cells=14364),added_cycles=0,qualification='SOURCE_BOUND_CENSUS_ONLY_NOT_ROUTED',checks=dict(no_unresolved=not files['unresolved'],no_ambiguous=not files['ambiguous'],all_hard_and_sram_clocks_common=True,paired_hcol_halves_share_identical_key_bits=True,below_400k_standard_cells=True))
(o/'source_binding_profile.json').write_text(json.dumps(manifest,indent=2)+'\n');(o/'quarter_residual.stat').write_text((base/'quarter_residual.stat').read_text());(o/'source_files.json').write_text(json.dumps(files,indent=2)+'\n')
stages=[]
for c in range(4):
 stages.append(dict(chunk=c,quarter_kl_r_age=1,leaf_f_key_age=2+2*c,leaf_g_key_age=3+2*c,core_rkey_age=3+2*c,hcol_input_port_age=3+2*c,hcol_key_p_age=4+2*c,source_registers=[f'scorer.ge[e].gc[{c}].leaf.f_key',f'scorer.ge[e].gc[{c}].leaf.g_key',f'scorer.ge[e].gc[{c}].leaf.core.rkey',f'scorer.ge[e].gc[{c}].leaf.core.g_col[k].g_half[h].u_hc.g_rgn[r].key_p']))
reach=dict(source_commit=source_sha,age_origin='keybuf.key_out value before scorer.kl_r capture edge',added_cycles=0,quarter_capture='scorer.kl_r <= key_lines (quarter_static_h.sv)',stages=stages,pc_mapping='PC p supplies lane0/1: e=p//2, k=2*(p%2)+lane; both h=0,1 share the exact same 544-bit key slice in each c=0..3',key_bit_mapping='quarter key_lines[(p*1099)+11+lane*544 +:544] -> scorer.kl_r same bits -> ge[e].keys[k*544+:544] -> c-stage leaf.f_key -> core.rkey -> HCOL.key -> key_p',successive_chunk_hop='g_key of chunk c (E register) -> f_key of c+1 (W register); two edges per chunk, followed by parallel rkey and g_key capture; no direct SRAM broadcast to all64 HCOL',layout_requirement='Place these EXISTING soft capture/forwarding register banks at legal bays so every physical hop meets405um. Any extra relay is a new model-priced cycle, not implicit.',source_files=['rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_quarter_static_h.sv','rtl/hdc/v41x/ot_hbm_idx_chunk_rt_h.sv','rtl/hbm_next/idxn/ot_hnx_idxn_quarter_with_keybuf.sv'])
(o/'key_reach_stages.json').write_text(json.dumps(reach,indent=2)+'\n');print(json.dumps({k:manifest[k] for k in ['external_input_bits','external_output_bits','census','checks']}))
