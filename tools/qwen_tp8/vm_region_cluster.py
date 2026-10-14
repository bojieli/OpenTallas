#!/usr/bin/env python3
"""Full closed-leaf VM region plus every planned lane stage; no sampled bays or substituted traffic."""
import collections,json,re
from pathlib import Path
from vm_bay_cluster import MOD,VIEW,WID,alias
ROOT=Path(__file__).resolve().parents[2]; P='rtl/qwen_sys/vm_plane_20261013'
CORE_VIEW={m:'physical/ref_tile/'+kit+'/views/'+m for m,kit in [('ot_qfd_vm_rr4_t','qfd_vm_rr4_t'),('ot_qfd_vm_rr2_t','qfd_vm_rr2_t'),('ot_qfd_vm_bank_t','qfd_vm_bank_t'),('ot_qfd_vm_bctl_t','qfd_vm_bctl_t'),('ot_qfd_vm_xfifo8_t','qfd_vm_xfifo8_codex'),('ot_qfd_vm_su_t','qfd_vm_su_t'),('ot_qfd_vm_sctl_t','qfd_vm_sctl_t'),('ot_qfd_vm_su1024_t','qfd_vm_su1024_codex'),('ot_qwen_tree_delay1_t','qfd_tt_delay1'),('ot_qwen_tree_delay2_t','qfd_tt_delay2')]}
# Resolve delay views by closed master, independent of kit aliases.
for m in ('ot_qwen_tree_delay1_t','ot_qwen_tree_delay2_t'):
 hits=list((ROOT/'physical/ref_tile').glob('*/views/'+m)); assert hits,m;CORE_VIEW[m]=str(hits[0].relative_to(ROOT))
def core_inst(n,r):
 s=n.removeprefix(f'vm_g{r}_')
 if s.startswith('rr4_'):return 'u_core.g_r4['+s[-1]+'].u_r4'
 if s=='rr2':return 'u_core.u_r2'
 if s.startswith('ans'):return 'u_core.g_su_leaf['+s[-1]+'].u_su'
 if s.startswith('su'):
  i=int(re.match(r'su(\d+)',s)[1]);base=f'u_core.g_c[{i//2}].g_j[{i%2}]';return base+('.g_sd.u_sd' if s.endswith('_in') else '.u_sc' if s.endswith('_ctl') else '.u_st')
 i=int(re.match(r'b(\d+)',s)[1]);base=f'u_core.g_b[{i}]'
 if '_xf' in s:return f'u_core.g_fifo16[{2*i+int(s[-1])}].u_fifo'
 return base+('.g_wd.u_wd' if s.endswith('_in') else '.u_bc' if s.endswith('_ctl') else '.g_bx.u_bx' if s.endswith('_bx') else '.u_bt')
def main(r=6):
 alias(); plan=json.loads((ROOT/'results/arch/qwen_tp8_1012/vm_leaf_plan_claude.json').read_text()); T=json.loads((ROOT/'results/arch/qwen_tp8_1012/vm_bay_tiles_claude.json').read_text())
 x0,y0=plan['slot']['region_origins'][str(r)];W,H=plan['slot']['region_um'][r%4];top=f'ot_qfd_vm_rg{r}';name=f'qfd_vm_rg{r}'
 core=[c for c in plan['children'] if c.get('region')==r];assert len(core)==72
 B={b['n']:b for b in plan['x_relay_bays']};cb={b['n']:b for b in B.values() if b.get('region')==r};C={c['n']:c for c in plan['children']}
 children=[dict(view=CORE_VIEW[c['m']],count=1,inst=core_inst(c['n'],r),at=[round(c['x']-x0,4),round(c['y']-y0,4)],orient=c['orient']) for c in core]
 tiles={}; clocks=[]
 for i,c in enumerate(core):clocks.append('ck_c'+str(i))
 for bn,b in cb.items():
  for t in T['bay_tiles'].get(bn,[]):
   ix=len(children);inst='u_'+bn+'_t'+str(t['slot']);tiles[(bn,t['slot'])]=dict(t,inst=inst,ck='ck_t'+str(ix-72),width=WID[t['kind']]);clocks.append(tiles[(bn,t['slot'])]['ck']);children.append(dict(view=VIEW[t['kind']],count=1,inst=inst,at=[round(b['x']-x0+t['slot']*21.6,4),round(b['y']-y0,4)],orient='R0'))
 def face(peer):
  o=B.get(peer,C.get(peer));assert o,peer
  x=o['x']+o['w']/2;y=o['y']+o['h']/2
  # Adjacent region seams follow the boundary crossed, not a single bay's axis.
  if x<x0:return 'w'
  if x>x0+W:return 'e'
  if y<y0:return 's'
  if y>y0+H:return 'n'
  dx=x-(x0+W/2);dy=y-(y0+H/2);return ('e' if dx>0 else 'w') if abs(dx)>abs(dy) else ('n' if dy>0 else 's')
 ni=collections.Counter();no=collections.Counter();segments=[];assign=[];used=collections.defaultdict(set)
 for lane,unordered in T['lane_chain'].items():
  ch=sorted(unordered,key=lambda c:c['visit']);assert [c['visit'] for c in ch]==list(range(len(ch)))
  src,pl=lane.split('>'); local_source=C[src].get('region')==r; bit=8*int(pl[1:]);bank=int(re.search(r'_b(\d+)',src)[1]);fi=int(src[-1]);srcbit=bank*512+fi*256+bit
  runs=[];start=None
  for j,v in enumerate(ch):
   if v['bay'] in cb:
    if start is None:start=j
   elif start is not None:runs.append((start,j));start=None
  if start is not None:runs.append((start,len(ch)))
  if local_source and (not ch or ch[0]['bay'] not in cb):runs.insert(0,(0,0))
  for a,z in runs:
   local=a==0 and local_source
   if local:prev=f'xo[{srcbit} +: 8]';input_pin=None
   else:
    peer=ch[a-1]['bay'] if a else src;f=face(peer);input_pin=[f'd_{f}',8*ni[f]];ni[f]+=1;prev=f'{input_pin[0]}[{input_pin[1]} +: 8]'
   initial=prev;stage_list=[]
   for v in ch[a:z]:
    for st in v['tiles']:
     key=(v['bay'],st['slot']);t=tiles[key];inst=t['inst'];lo=st['bit0'];assert not set(range(lo,lo+8)) & used[key],(lane,key,lo)
     used[key].update(range(lo,lo+8));assign.append(f'    assign d_{inst}[{lo} +: 8] = {prev};');prev=f'q_{inst}[{lo} +: 8]';stage_list.append(dict(bay=v['bay'],slot=st['slot'],bit0=lo,stages=st['stages'],visit=v['visit']))
   peer=ch[z]['bay'] if z<len(ch) else f'vm_xcol_{pl[1:]}';f=face(peer);op=[f'q_{f}',8*no[f]];no[f]+=1;k=len(segments)
   # Mutant 1 removes the final physical leaf of the first non-empty chain.
   if stage_list and not any(s.get('mutant_target') for s in segments):mut=True
   else:mut=False
   if mut:assign.append(f'    assign {op[0]}[{op[1]} +: 8] = (MUT == 1) ? {initial} : {prev};')
   else:assign.append(f'    assign {op[0]}[{op[1]} +: 8] = {prev};')
   segments.append(dict(lane=lane,source=src,source_bits=srcbit,local_source=local,input=input_pin,output=op,stages=sum(s['stages'] for s in stage_list),path=stage_list,mutant_target=mut,peer=peer))
 coreports={'rst_n':1,'me_in':1,'re':8,'ra':64,'we':8,'wl':64,'wm':128,'wd':4096,'xv':1,'rq':1,'rqb':3,'sre':6,'sra':60,'sv':3,'swe':2,'swl':20,'swm':32,'swd':1024,'pop':1};outports={'ro':512,'so':3072,'ovf':1}
 ports=[('input',c,1) for c in clocks]+[('input',p,w) for p,w in coreports.items()]+[('input','lane_me',len(cb))]+[('input','d_'+f,ni[f]*8) for f in 'wesn' if ni[f]]+[('output',p,w) for p,w in outports.items()]+[('output','q_'+f,no[f]*8) for f in 'wesn' if no[f]]
 V=['// Generated full region: 72 closed core leaves + every planned region relay/pad tile.','// Clock entries align individual boundary arrivals at phi - R_i. No parent clock tree.',f'module {top} #(parameter integer MUT=0) (',',\n'.join('    '+d+' wire '+(f'[{w-1}:0] ' if w>1 else '')+p for d,p,w in ports),');','    wire [4095:0] xo;','    ot_qfd_vm_region_leaf #(.DEPTH(174), .LAW(8), .DEPTHS(695), .LAWS(10), .USE_MACRO(0), .CLOCK_ENTRIES(1), .LEAF_MUT((MUT == 2) ? 1 : 0)) u_core (',"        .clk(1'b0), .leaf_clocks({"+', '.join(reversed(clocks[:72]))+'}),',',\n'.join('        .'+p+'('+p+')' for p in list(coreports)+list(outports)+['xo']), '    );']
 bnindex={b:i for i,b in enumerate(cb)}
 for key,t in tiles.items():
  inst=t['inst'];w=t['width'];V += [f'    wire [{w-1}:0] d_{inst}, q_{inst};','`ifndef OT_QFD_VM_HARD',f'    {MOD[t["kind"]]} #(.W({w}),.MEREG(1)) {inst} (','`else',f'    {MOD[t["kind"]]} {inst} (','`endif',f'      .clk({t["ck"]}),.me_e(lane_me[{bnindex[key[0]]}]),.d(d_{inst}),.q(q_{inst}));']
  unused=sorted(set(range(w))-used[key]);V += [f"    assign d_{inst}[{u}] = 1'b0;" for u in unused]
 V+=assign+['endmodule'];od=ROOT/P/'region';od.mkdir(exist_ok=True);(od/(top+'.sv')).write_text('\n'.join(V)+'\n')
 # Extend the existing independent flat-region bench, retaining its full bank/SU/row/FIFO/stall/overflow nonvacuity checks.
 tb=(ROOT/P/'tb_qfd_vm_region_leaf.sv').read_text().replace('module tb_qfd_vm_region_leaf;',f'module tb_qfd_vm_rg{r};').replace('parameter integer DEPTH = 8, LAW = 3, DEPTHS = 8, LAWS = 3','parameter integer DEPTH = 174, LAW = 8, DEPTHS = 695, LAWS = 10')
 sta=tb.index('    ot_qfd_vm_region_leaf #(');end=tb.index('    ot_qfd_vm_region_quarter #(',sta)
 portbind=[f'.{p}(clk)' for p in clocks]+[f'.{p}({p})' for p in coreports]+[f'.{p}({p})' for p in outports]+[f'.lane_me({{{len(cb)}{{me_in}}}})']+[f'.d_{f}(d_{f})' for f in 'wesn' if ni[f]]+[f'.q_{f}(q_{f})' for f in 'wesn' if no[f]]
 decl=['    parameter integer MUT=0;']+[f'    reg [{8*ni[f]-1}:0] d_{f}=0;' for f in 'wesn' if ni[f]]+[f'    wire [{8*no[f]-1}:0] q_{f};' for f in 'wesn' if no[f]]+[f'    {top} #(.MUT(MUT)) candidate ('+', '.join(portbind)+');','    assign xo = candidate.xo;']
 tb=tb[:sta]+'\n'.join(decl)+'\n'+tb[end:]
 # Each contiguous region segment gets an independent reference shift register driven by the flat core reference or external traffic.
 refs=['    reg lane_me_prev=0;','    integer lane_checks=0, lane_nonzero=0;','    always @(posedge clk) begin lane_me_prev <= me_in; end']
 for k,s in enumerate(segments):
  inp=f'r_xo[{s["source_bits"]} +: 8]' if s['local_source'] else f'{s["input"][0]}[{s["input"][1]} +: 8]';D=s['stages'];op=f'{s["output"][0]}[{s["output"][1]} +: 8]'
  if D:
   refs += [f'    reg [{D*8-1}:0] ref{k}=0;',f'    always @(posedge clk) if (lane_me_prev) ref{k} <= '+ ('{ref'+str(k)+f'[{D*8-9}:0], '+inp+'};' if D>1 else inp+';')];expected=f'ref{k}[{8*(D-1)} +: 8]'
  else:expected=inp
  refs += [f'    always @(posedge clk) begin #1; if (cyc > 40) begin lane_checks=lane_checks+1; if ({expected} != 0) lane_nonzero=lane_nonzero+1; if ({op} !== {expected}) begin errors=errors+1; if (errors<4) $display("region lane mismatch segment {k} lane {s["lane"]}"); end end end']
 # External lane randomization uses independent xorshift stream, no dependence on candidate outputs.
 external=[f'            for (w=0;w<{ni[f]};w=w+1) d_{f}[8*w +: 8]=rnd(0);' for f in 'wesn' if ni[f]]
 tb=tb.replace('            me_prev = me_in;','\n'.join(external)+'\n            me_prev = me_in;');tb=tb.replace('    // xorshift64', '\n'.join(refs)+'\n    // xorshift64')
 tb=tb.replace('PASS qfd_vm_region_leaf',f'PASS qfd_vm_rg{r}').replace('FAIL qfd_vm_region_leaf',f'FAIL qfd_vm_rg{r}');tb=tb.replace('        $finish;',f'            $display("region lanes segments={len(segments)} stage_bits={sum(s["stages"]*8 for s in segments)} checks=%0d nonzero=%0d",lane_checks,lane_nonzero);\n            if (lane_checks < 1000 || lane_nonzero < 100) $fatal(1,"lane coverage vacuous");\n            $finish;')
 (od/f'tb_qfd_vm_rg{r}.sv').write_text(tb)
 sources=[str((od/(top+'.sv')).relative_to(ROOT)),f'{P}/ot_qfd_vm_region_leaf.sv',f'{P}/bay/ot_qfd_vm_xrelay_w.sv',f'{P}/ot_qfd_vm_xplane.sv',f'{P}/ot_qfd_vm_xpad2.sv','rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_answer_tiles.sv','rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_xfifo8_t.sv','rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv','rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv','rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv','rtl/hdc/ot_hdc_delay.sv','rtl/physical/ot_qwen_tree_delay.sv','rtl/physical/ot_qwen_tree_delay_tiles.sv']
 defines=['OT_QFD_VM_HARD','OT_QFD_VM_DELAY1_MOD=ot_qwen_tree_delay1_t','OT_QFD_VM_DELAY2_MOD=ot_qwen_tree_delay2_t']
 pins={'S':list(coreports)+['lane_me']+clocks,'N':list(outports),'W':[],'E':[]}
 for f,F in [('w','W'),('e','E'),('s','S'),('n','N')]:
  if ni[f]:pins[F].append('d_'+f)
  if no[f]:pins[F].append('q_'+f)
 vb='mkdir -p {RUN}/bench && $HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -O1 --output-split 20000 --output-split-cfuncs 2000 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -Wno-PINMISSING -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -j 4 --top-module tb_qfd_vm_rg'+str(r)+' %ARGS% --Mdir {RUN}/bench/%NAME% '+str((od/f'tb_qfd_vm_rg{r}.sv').relative_to(ROOT))+' '+' '.join(sources)+' rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_region_quarter.sv > {RUN}/bench/%NAME%.build.log 2>&1 && {RUN}/bench/%NAME%/Vtb_qfd_vm_rg'+str(r)+' > {RUN}/bench/%NAME%.log 2>&1; tail -4 {RUN}/bench/%NAME%.log; grep -q "^PASS qfd_vm_rg'+str(r)+'" {RUN}/bench/%NAME%.log'
 benches=[dict(name=n,cmd=vb.replace('%NAME%',n).replace('%ARGS%',a),expect=e,threads=4,peak_ram_gb=8,needs=['verilator']) for n,a,e in [('rg_ok','-GSEED=1','pass'),('rg_mut_lane','-GMUT=1','fail'),('rg_mut_core','-GMUT=2','fail')]]
 spec=dict(name=name,top=top,kind='cluster',sources=sources,params={},clock='entries',clock_ports=clocks,clock_port=clocks[0],reset_ports=['rst_n'],hard_define='OT_QFD_VM_HARD',defines=defines,outline=dict(w=W,h=H,exact=True),child_lattice_um=2.16,children=children,abut_plan=dict(channel_um=2.16,edge_um=2.16,why='full region pilot routes every real core and lane tile at the accepted planned placement; measurement required before release'),pins=pins,inter=['*'],refglob='*',signal_max_layer='M9',pg_layer='M7',layer_cap_grant='el1011-qwen-tp8.log 19:11 rectangle M9 cluster grant; die M8/M9 PG only width.48 pitch9.091 core origin0',route=dict(pd=.5,period_ps=770,threads=16,peak_ram_gb=32,hold_margin_ns=.03),job=dict(owner='Codex:qwen_vm_region',branch='codex/qwen-vm-rg6',tag='rg6p1',hold_merge='full region physical pilot until measured channel routing and assigned die pins are verified',purpose='full rg6 core+all lane tiles, no sampled bays; exact flat reference core plus every region lane path with two mutants',extra_paths=[P,'rtl/qwen_sys/vm_me_20261008','rtl/qwen_sys/vm_die_split_20261012','rtl/qwen_sys/rtl_finish_20261007','rtl/hdc','rtl/physical','results/arch/qwen_tp8_1012/vm_rg6.json'],benches=benches))
 (ROOT/f'physical/ref_tile/{name}.spec.json').write_text(json.dumps(spec,indent=1)+'\n')
 rec=dict(schema='opentallas.qwen.vm-region.v1',region=r,top=top,origin_um=[x0,y0],outline_um=[W,H],core_leaves=72,lane_tiles=len(tiles),bays=len(cb),clock_entries=len(clocks),ports=[dict(direction=d,name=p,bits=w) for d,p,w in ports],children=children,core_names=[c['n'] for c in core],bay_names=list(cb),segments=segments,stage_bits=sum(8*s['stages'] for s in segments),pdn=dict(local_top='M7',die_only_pg=['M8','M9'],width_um=.48,pitch_um=9.091,die_core_origin_um=[0,0],origin_um=[x0,y0],starts_with='GROUND'),pin_assignment='current contract provisional until die decomposes VM rectangle; no waiver')
 (ROOT/f'results/arch/qwen_tp8_1012/vm_rg{r}.json').write_text(json.dumps(rec,indent=1)+'\n');print({k:rec[k] for k in ('core_leaves','lane_tiles','bays','clock_entries','stage_bits')})
if __name__=='__main__':main()
