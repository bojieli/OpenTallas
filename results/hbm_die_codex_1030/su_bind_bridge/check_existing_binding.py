"""Exercise existing pre-elab substitute+dissolve and actual constant-output bridge, not RTL behavior proof."""
import json,subprocess,sys,re
from pathlib import Path
ROOT=Path('/srv/opentallas-scratch/claude/wt/codex-hbm-1030');RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools/die_plan'));sys.path.insert(0,str(ROOT/'tools'))
import bind_elab as E,bind as B,die_port_bind as D
get=lambda p:subprocess.check_output(['git','-C',str(ROOT),'show','1f9fe3c3a:'+p],text=True)
abi=json.loads(get('results/hbm_su_native_1030/native_cut_abi.json'))
masters=['ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77','ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526','ot_hnx_su_plain4__7dd6a1bbbf47_rst3__id44'];rows=[]
for master in masters:
 physical=master+'__nocoll';bridge=physical+'__native_bridge';a=next(x for x in abi if x['module']==('ot_hnx_su_plain4__7dd6a1bbbf47_rst3'if'id44'in master else'ot_hnx_su_plain4__lid9_rst3'))
 ports=a['ports'];dirs=a['port_directions'];old=a['module'];out=RUN/master;out.mkdir(exist_ok=True)
 decl=lambda ps: ',\n'.join(f"{dirs[n]} wire "+(f'[{ports[n]-1}:0] 'if ports[n]>1 else'')+n for n in ps)
 orig=out/'original.sv';orig.write_text(f'module {old}(\n{decl(ports)}\n);\nendmodule\n')
 origiface=D.parse_modules(orig.read_text(),str(orig))[0];assert len(origiface.ports)==69
 stub=out/'physical_stub.sv';stub.write_text('(* blackbox *) '+re.search(r'module\b.*?\);',get('physical/die_plan/hbm_arch_cores/wrappers/'+physical+'.sv'),re.S).group(0)+'\nendmodule\n')
 full=get('physical/die_plan/hbm_arch_cores/wrappers/'+bridge+'.sv')
 bf=out/'bridge.sv';bf.write_text(full)
 bm=D.parse_modules(full,str(bf))[0];assert set(bm.ports)==set(ports)
 for n in ports:
  di,ranges=bm.ports[n];w=1
  for hi,lo in ranges:w*=abs(int(hi)-int(lo))+1
  assert(di,w)==(dirs[n],ports[n]),(n,di,w)
 shim,rec=E.make_shim(orig,old,{'module':bridge,'reason':'source-qualified constant output drop'},bf);assert not rec['orig_ports_unmapped'] and not rec['unconnected_inputs']
 (out/'shim.sv').write_text(shim)
 top=f'module coupon(\n{decl(ports)}\n);\n{old} u_native('+','.join('.'+n+'('+n+')'for n in ports)+');\nconsumer u_loaded(.D(lane_coll));\nendmodule\n(* blackbox *) module consumer(input wire [3:0] D);endmodule\n'
 (out/'top.sv').write_text(top)
 for mode in ['nominal','wrong_tie1','undriven_removed_output']:
  text=full if mode=='nominal' else full.replace("assign lane_coll = 4'b0000;", "assign lane_coll = 4'b0001;"if mode=='wrong_tie1'else'// removed assign intentionally')
  (out/'selected.sv').write_text(text)
  ys=f'read_verilog -sv {out}/physical_stub.sv {out}/selected.sv {out}/shim.sv {out}/top.sv\nhierarchy -check -top coupon\nwrite_json {out}/{mode}.json\n'
  (out/'elab.ys').write_text(ys)
  p=subprocess.run(['yosys','-Q','-T','-s',str(out/'elab.ys')],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/(mode+'.log')).write_text(p.stdout);assert p.returncode==0,p.stdout[-1000:]
  F=E.flatten(json.load(open(out/(mode+'.json'))),'coupon');errors=[];G=B.Graph(F,B.Rules({}),errors);sink=next(c for c in F.cells if c.path=='u_loaded');actual=[G.source(n)for n in sink.ports['D']];qualified=all(x[:2]==('const','0')for x in actual)
  assert qualified==(mode=='nominal'),(mode,actual)
  hard=next(c for c in F.cells if c.path=='u_native.u_sub.u_phys');assert hard.module==physical and'lane_coll'not in hard.ports and len(hard.ports)==68
  rows.append(dict(physical=physical,mode=mode,constant_sources=actual,qualification=qualified,physical_leaf=hard.path,physical_ports=len(hard.ports),public_outputs=sum(w for n,w in ports.items()if dirs[n]=='output'),extra_cycles=0))
(RUN/'receipt.json').write_text(json.dumps(dict(scope=__doc__,source='1f9fe3c3a',cases=rows,all_expected_results=True),indent=2)+'\n');print(json.dumps(rows,indent=1))
