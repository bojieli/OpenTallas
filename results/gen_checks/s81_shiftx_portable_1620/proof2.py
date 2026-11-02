import sys,json,re,subprocess,importlib.util,hashlib
from pathlib import Path
from types import SimpleNamespace as NS
R=Path('/srv/opentallas-scratch2/claude/codex-s81-shiftx-1620/proof2');SRC=Path('/srv/opentallas-scratch2/claude/codex-s81-wave-1131/src');sys.path.insert(0,str(SRC/'tools/die_plan'))
sp=importlib.util.spec_from_file_location('NG',R/'bind_native_glue_candidate.py');NG=importlib.util.module_from_spec(sp);sp.loader.exec_module(NG)
gold=json.load(open(R/'primitive.json'));name=next(iter(gold['modules']));primitive=gold['modules'][name]['cells']['primitive'];actual=NS(ytype=primitive['type'],yparams=primitive['parameters'],ports=primitive['connections'],dirs=primitive['port_directions'])
original_map=NG.SHIFTX_PORTABLE_MAP

def emit(cell,where,mapper=None):
 NG.SHIFTX_PORTABLE_MAP=mapper or original_map
 old=list((R/where).glob('*.sv')) if (R/where).is_dir() else []
 if old:
  assert len(old)==1
  mapper_file=next((R/where).glob('*_shiftx_map.v'))
  assert mapper_file.read_text()==(mapper or original_map)
  data=json.load(open(old[0].with_suffix('.json')));prim=next(iter(data['modules'].values()))['cells']['primitive']
  assert prim['parameters']==cell.yparams
  return old[0]
 n=NG.NativeGlue(R/where,['$shiftx']);n.emit(cell,{p:p for p in cell.ports},'u');assert len(n.files)==1;return n.files[0]

sv=emit(actual,'actual');actual_json=json.load(open(sv.with_suffix('.json')));assert actual_json==gold,'primitiveJSON or ABI changed';print('ACTUAL_PRIMITIVE_JSON_EXACT',name,flush=True)
mut=emit(actual,'mutant',original_map.replace('index = base + PAD','index = -base + PAD'))
zero=emit(actual,'zero_fill_mutant',original_map.replace("1'bx","1'b0"))


def params(aw,bw,yw,bs,asign=0):return {k:format(v,'032b') for k,v in dict(A_WIDTH=aw,B_WIDTH=bw,Y_WIDTH=yw,A_SIGNED=asign,B_SIGNED=bs).items()}
def generic(aw,bw,yw,bs,asign=0):
 p=dict(A=list(range(2,aw+2)),B=list(range(aw+2,aw+bw+2)),Y=list(range(aw+bw+2,aw+bw+yw+2)))
 return NS(ytype='$shiftx',yparams=params(aw,bw,yw,bs,asign),ports=p,dirs=dict(A='input',B='input',Y='output'))

cases=[('actual',32,34,128,1,0,True,sv)]
for k,(aw,bw,yw,bs,asign) in enumerate([(32,34,128,1,0),(128,34,32,1,0),(13,6,37,1,0),(13,6,37,0,0),(1,1,1,1,0),(9,5,9,0,0)]):cases.append((f'generic{k}',aw,bw,yw,bs,asign,False,emit(generic(aw,bw,yw,bs,asign),f'generic{k}')))

def tb(aw,bw,yw,bs,const,module):
 iw=max(bw,aw.bit_length(),yw.bit_length())+3
 ai=f"{aw}'h"+('f'*((aw+3)//4)) if const else 'A'
 conns='.B(B),.Y(U)' if const else '.A(A),.B(B),.Y(U)'
 return f'''module tb;reg[{aw-1}:0]A;reg[{bw-1}:0]B;wire[{yw-1}:0]U;reg[{yw-1}:0]G;reg signed[{iw-1}:0]base,idx;integer bad=0,checks=0,seed=237,j;wire[{aw-1}:0]REF_A={ai}; {module} u({conns});
 task check;begin
 #1;G='x;
 if((^B)!==1'bx)begin
 base={"{{"+str(iw-bw)+"{B["+str(bw-1)+"]}},B}" if bs else "{{"+str(iw-bw)+"{1'b0}},B}"};
 for(j=0;j<{yw};j=j+1)begin idx=base+j;if(idx>=0&&idx<{aw})G[j]=REF_A[idx];end
 end
 checks=checks+1;if(G!==U)begin bad=bad+1;if(bad<6)$display("DIFF B=%h G=%h U=%h",B,G,U);end
 end endtask
 initial begin A='1;B=0;check;
 for(integer k=-({yw}+4);k<=({aw}+4);k=k+1)begin B={bw}'(k);check;end
 for(integer k=0;k<256;k=k+1)begin A=$random(seed);B=$random(seed);check;end
 A='x;B=0;check;A='1;A[0]=1'bx;B=0;check;A[0]=1'bz;check;
 A='1;B='x;check;B='z;check;B=0;B[0]=1'bx;check;B=0;B[{bw-1}]=1'bx;check;
 B={{1'b0,{{{bw-1}{{1'b1}}}}}};check;B={{1'b1,{{{bw-1}{{1'b0}}}}}};check;B='1;check;
 $display("SHIFTX_CASE checks=%0d errors=%0d",checks,bad);if(bad)$fatal(1,"shiftx mismatch");$finish;end endmodule'''

results=[]
for label,aw,bw,yw,bs,asign,const,file in cases+[('wrong_shift',32,34,128,1,0,True,mut),('zero_fill',32,34,128,1,0,True,zero)]:
 text=file.read_text();module=re.search(r'\bmodule\s+(\w+)',text)[1];d=R/('sim_'+label);d.mkdir(exist_ok=True);(d/'tb.sv').write_text(tb(aw,bw,yw,bs,const,module))
 cmd=['iverilog','-g2012','-o',str(d/'sim'),str(file),str(d/'tb.sv')];p=subprocess.run(cmd,capture_output=True,text=True);(d/'build.log').write_text(p.stdout+p.stderr);assert p.returncode==0,(label,p.stderr[-1500:])
 p=subprocess.run(['vvp',str(d/'sim')],capture_output=True,text=True);(d/'run.log').write_text(p.stdout+p.stderr);is_mut=label in ('wrong_shift','zero_fill');assert (p.returncode!=0)==is_mut,(label,p.stdout+p.stderr);results.append(dict(case=label,rc=p.returncode,summary=p.stdout.strip().splitlines()[-2:]));print(label,results[-1],flush=True)
NG.SHIFTX_PORTABLE_MAP=original_map
(R/'report.json').write_text(json.dumps(dict(actual_primitive_json_exact=True,module=name,cases=results),indent=1)+'\n')
