from pathlib import Path
import json,gzip,re,hashlib
ROOT=Path('/srv/opentallas-scratch2/claude/codex-head-1105/parent_head_union_exact6')
PREP=ROOT.parent/'prep_head_union_exact6'
OUT=Path('/srv/opentallas-scratch2/claude/codex-head-token-1106/phase_control3');OUT.mkdir(exist_ok=False)
PLAN=json.loads((PREP/'source_plan.json').read_text());ST=json.loads((PREP/'source/start_stages.json').read_text())
ARR=Path('/srv/opentallas-scratch2/claude/codex-head-ca-origins-1106/wt/results/codex_head_ca_0840/arr_TT.txt.gz')
a={}
with gzip.open(ARR,'rt') as f:
 for line in f:
  p=line.split()
  if len(p)>=4 and p[0] in {'T','F','N','M'}:a[p[0],p[1]]=float(p[2])
parts={p['name']:p for p in PLAN['partitions']};types=PLAN['partition_types'];phase={};models=[];ctrl={};allports={};counter=0
# Nominal source law is the shared single-arrival convention: STA max at
# the selected corner, never a midpoint/epsilon. Internal latency is declared,
# not measured here. START source clocks use the manifest's actual driving cell.
def clock(name,rise,fall,basis):
 if name in phase:assert phase[name]['rise_ps']==rise and phase[name]['fall_ps']==fall;return
 assert 416.5+fall-rise>0 and 416.5+rise-fall>0,(name,rise,fall)
 phase[name]=dict(rise_ps=rise,fall_ps=fall,basis=basis)
 models.extend([f'reg {name}=0;',f'initial begin #{(416.5+rise)/1000:.9f} {name}=1; forever begin #{(416.5+fall-rise)/1000:.9f} {name}=0; #{(416.5+rise-fall)/1000:.9f} {name}=1; end end'])
for s in ST['stages']:
 if s['clock_source_root']:rise=fall=0.0
 else:rise=a['N',s['clock_source_cell']];fall=a['M',s['clock_source_cell']]
 clock(s['clock_port'],rise,fall,dict(kind='manifest_source',cell=s['clock_source_cell'],from_pin=s['clock_from']))
for n,p in parts.items():
 typ=types[p['type']];ins=float(typ['clock']['insertion_ps']);rise=a['T','t_'+n+'__clk']+ins;fall=a['F','t_'+n+'__clk']+ins
 clock('pc_'+n,rise,fall,dict(kind='physical_part_input+declared_internal',tap='t_'+n+'__clk',internal_ps=ins))

PRIMS={'ot_dp_rrelay','ot_dp_rgate','ot_dp_rsync','ot_dp_rsync_s2','ot_dp_rsync_s3','ot_dp_head_raw_export_pair','ot_dp_landing_origin_s','ot_dp_landing_root','ot_dp_landing_relay','ot_dp_origin_export_ff'}
OUTP={'q','export_q','start','start_d','sync_rst_n'}
INST=re.compile(r'^\s*(ot_\w+)\s+(\w+)\s*\(\n(.*?)^\s*\);',re.M|re.S)
CONN=re.compile(r'\.(\w+)\(([^()]*)\)')
ID=re.compile(r'\b[A-Za-z_]\w*\b')
def refs(expr):return ID.findall(re.sub(r"\d+'[sS]?[bBdDhHoO][0-9a-fA-FxXzZ_]+",'',expr))
def getports(s):
 h=s[s.find('module '):s.find(');')+2];return {m[3]:(m[1],m[2] or '') for m in re.finditer(r'\b(input|output|inout)\s+(?:wire\s+|reg\s+|logic\s+)?(\[[^\]]+\]\s*)?(\w+)',h)}
def control(mod):
 if mod in ctrl:return ctrl[mod]
 src=(ROOT/(mod+'.sv')).read_text();ports=getports(src);drivers={};objects=[]
 for m in re.finditer(r'^\s*(?:\(\*[^\n]*?\*\)\s*)?(ot_dp_\w+)(?:\s*#\([^\n]*\))?\s+(\w+)\s*\((.*?)\);',src,re.M|re.S):
  if m[1] not in PRIMS:continue
  conn=dict(CONN.findall(m[3]));obj=dict(text=m[0],deps=[q for p,e in conn.items() if p not in OUTP for q in refs(e)],outputs=[e for p,e in conn.items() if p in OUTP and e])
  for p,e in conn.items():
   if p in OUTP and e:
    assert re.fullmatch(r'\w+',e),(mod,p,e);assert e not in drivers,(mod,e);drivers[e]=obj
 for m in re.finditer(r'^\s*assign\s+(\w+)\s*=\s*([^;]+);',src,re.M):
  if m[1] not in drivers:drivers[m[1]]=dict(text=m[0],deps=refs(m[2]))
 targets=[p for p,(d,w) in ports.items() if d=='output' and p.startswith(('rst_o_','start_o_','rst_start_raw_','fclk_out_','cland_fstart_out_'))]
 used=set();need=set();primary=set()
 def walk(n):
  if n in need:return
  need.add(n)
  if n in ports and ports[n][0]=='input':primary.add(n);return
  if n not in drivers:raise ValueError(f'{mod}: no exact control driver for {n}')
  obj=drivers[n];used.add(id(obj));need.update(obj.get('outputs',[]))
  for d in obj['deps']:walk(d)
 for p in targets:walk(p)
 chosen=[];seen=set()
 for obj in drivers.values():
  if id(obj) in used and id(obj) not in seen:chosen.append(obj['text']);seen.add(id(obj))
 name='control_'+mod;pp=[f'input wire {ports[p][1]}{p}' for p in sorted(primary)]+[f'output wire {ports[p][1]}{p}' for p in targets]
 lines=[f'module {name}(', ',\n'.join(pp),');']
 # Primitive outputs and aliases in this exact cone are all scalar controls.
 lines += ['wire '+n+';' for n in sorted(need-set(primary)-set(targets))]
 lines += chosen+['endmodule'];ctrl[mod]=(name,sorted(primary)+targets,'\n'.join(lines));return ctrl[mod]

parent=(ROOT/'s81_head_top.sv').read_text();hdr=parent[:parent.find(');')+2];pp=getports(parent)
# Retain every global wire declaration so physical top net names stay literal.
decls=[]
for line in parent[parent.find(');')+2:].splitlines():
 if re.match(r'^\s*wire\b',line):decls.append(line)
body=[];mapping={}
for m in INST.finditer(parent):
 mod,n,b=m.groups();conn=dict(CONN.findall(b))
 if n=='u_die_start_stages':body.append(m[0]);continue
 if n not in parts:raise ValueError((mod,n))
 cn,ps,src=control(mod);cs=[]
 for p in ps:
  e=conn[p]
  if p=='clk' or p.startswith('clk_t'):e='pc_'+n
  cs.append('.'+p+'('+e+')')
 body.append(cn+' '+n+'('+','.join(cs)+');');mapping[n]=dict(module=mod,ports=ps)
# The preserved 1251 START clock connections now see the actual source clocks.
lines=['`timescale 1ns/1fs','module phase_control_tb;','reg rst_n=0;reg refclk=0;always #0.4165 refclk=~refclk;integer cycles=0;', 'always@(negedge refclk)begin cycles++;if(cycles==64)rst_n=1;end']
for n,(d,w) in pp.items():
 if n=='rst_n' or n in phase:continue
 if n.startswith('clk_region_'):continue # every real control instance gets its own physical clock
 lines.append('wire '+w+n+(' = 1\'b0;' if n=='start' else ';'))
lines+=decls+models+body
# The decisive native path is ctl_nstrip.unit_ft_o -> LEP.unit_i0.
unit=next((p for p in PLAN['ports'] if p.get('dst',{}).get('part')=='lep0N' and p.get('dst',{}).get('bus')=='unit_i0'),None)
# Literal parent connections are authoritative for the writer clock/FSTART and K.
lep_inst=next(m for m in INST.finditer(parent) if m[2]=='lep0N');lc=dict(CONN.findall(lep_inst[3]));k=lc['strap_ca_k_unit_i0'];fc=lc['fclk_in_unit_i0'];fs=lc['cland_fstart_in_unit_i0']
lines+=['wire ready,fault;wire[47:0]q;reg[47:0]data=0;',f'always@(negedge {fc})data<=data+1;',f'ot_dp_clk_landing_cas #(.W(48),.DEPTH(4)) check_unit(.fclk({fc}),.t_rst_n({fs}),.clk(pc_lep0N),.rst_n(lep0N.cland_start),.strap_k({k}),.d(data),.q(q),.ready(ready),.fault(fault));']
# cland_start is an internal exact-cone wire, retained because the exports depend on it.
lines+=['always@(negedge refclk)if(cycles==800)begin $display("PHASE_CONTROL ready%0d fault%0d",ready,fault);if(!ready||fault)$fatal(1,"actual-phase control window");$finish;end','endmodule']
(OUT/'tb.sv').write_text('\n'.join(lines)+'\n')
(OUT/'controls.sv').write_text('\n'.join(v[2] for v in ctrl.values())+'\n')
(OUT/'profile.json').write_text(json.dumps(dict(scope='TT single STA max + declared internal budgets; literal START/reset control only, no physical signoff',arrival=str(ARR),phase=phase,parts=mapping),indent=1)+'\n')
print('PHASE_CONTROL_PREPARED',len(phase),len(mapping),len(ctrl))
