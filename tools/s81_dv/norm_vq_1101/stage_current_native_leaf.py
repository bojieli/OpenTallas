from pathlib import Path
import re,json,hashlib,shutil,sys
ROOT=Path('/srv/opentallas-scratch2/claude/wt/codex-s81b-1101');B=Path('/srv/opentallas-scratch2/claude/codex-s81-1101/bind_t48_pg/out');R=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101/native_leaf_ece_v2');R.mkdir(exist_ok=False);(R/'.keep').write_text('critical current native VP norm component; preserve\n')
sys.path[:0]=[str(ROOT/'tools/die_plan'),'/srv/opentallas-scratch2/claude/codex-ds-norm-1101/code']
import bind_elab as E
from layer_prog.emitted_norm_source import _params
from layer_prog.emitted_leaf_routes import Wiring
ab=json.loads((B.parent/'asbuilt.json').read_text());top=(B/'rtl/s81_bound_top.sv').read_text();part='s_0S_L0'
h=re.search(r'^\s*(\w+)(?:[ \t]+#\(([^\n]*?)\))?[ \t]+'+part+r'\s*\(',top,re.M);assert h,part
native=B/'rtl'/(h[1]+'.sv');body=native.read_text();ports_header=body[body.index(') (')+3:body.index('\n);')]
inputs=re.findall(r'input\s+wire\s*(?:\[(\d+):0\])?\s+(\w+)',ports_header)
nb=re.search(r'^\s*ot_s81sl_vn_b\s+#\(([^\n]*?)\)\s+(\w+)\s*\((.*?)^\s*\);',body,re.M|re.S);assert nb
np=_params(nb[3]);reset=re.fullmatch(r'leafdn_i0_q\[(\d+)\]',np['rst_n']);assert reset,np['rst_n'];resetbit=int(reset[1])
raw=json.loads((B/'bind_latency.json').read_text());dn=next(r for r in raw['buses']if r['lane']=='dn_'+part);up=next(r for r in raw['buses']if r['lane']=='up_'+part)
fields={p:[]for p in ('c_v','c_d','sw_v','sw_a','sw_m','sw_d')}
ch=re.search(r'^\s*(\w+)(?:[ \t]+#\(([^\n]*?)\))?[ \t]+'+re.escape(dn['src'])+r'\s*\(',top,re.M);assert ch
ctext=(B/'rtl'/(ch[1]+'.sv')).read_text();cw=Wiring(ctext)
xr=re.search(r'^\s*ot_s81sl_xrt[13]\s+#\(([^\n]*?)\)\s+\w+\s*\((.*?)^\s*\);',ctext,re.M|re.S);assert xr
xp=_params(xr[2]);targets={}
for field in fields:
 for j,bit in enumerate(cw.bits(xp[field])):
  if field in ('c_v','sw_v')and j!=0:continue
  targets[bit]=(field,j)
terminals={n for n,j in targets};expr,width=cw.outputs[dn['bus_out']]
for i,bit in enumerate(cw.bits(expr)):
 try:n,j,age=cw.trace(bit,terminals)
 except ValueError:continue
 if(n,j)in targets:
  field,k=targets[n,j];fields[field].append((i,k))
for p,width in [('c_v',1),('c_d',160),('sw_v',1),('sw_a',10),('sw_m',8),('sw_d',256)]:assert len(fields[p])==width,(p,len(fields[p]))
pv=[(i,d)for i,d in enumerate(up['source_bits'])if len(d)==4 and d[0]=='leaf'and d[2]=='p_v'];assert len(pv)==1
pd=[(i,d[3])for i,d in enumerate(up['source_bits'])if len(d)==4 and d[0]=='leaf'and d[1]==pv[0][1][1]and d[2]=='p_d'];assert len(pd)==32
stage=json.loads(Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101/nx_network/stage.json').read_text());seed=[ROOT/p for p in stage['source_sha256']]+[B/'rtl/bind_cells.sv',ROOT/'rtl/common/ot_dp_clk_landing.sv',native]+list((B/'rtl/native_glue').glob('*.sv'))
files=list(seed)
for name in ab['files']:
 p=ROOT/name
 if name.endswith('_bb.v')and name.startswith('physical/'):
  full=p.with_name(p.name.replace('_bb.v','.v'))
  if full.is_file():p=full
 if p.is_file():files.append(p)
idx=E.module_index([],list(map(str,files)),ROOT)
closure,missing=E.closure([h[1]],idx,list(map(str,seed)))
if missing:raise ValueError('actual native closure missing '+str(missing))
manifest={};relative=[]
for k,name in enumerate(closure):
 p=Path(name);rel=Path('source')/(str(k)+'_'+p.name);dest=R/rel;dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest);relative.append(str(rel));manifest[str(rel)]=dict(source=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(R/'source.f').write_text('\n'.join(relative)+'\n');(R/'defines.f').write_text('\n'.join('+define+'+d for d in ab['defines'])+'\n')
shutil.copyfile('/srv/opentallas-scratch2/claude/codex-ds-valid-partial-1030/entry.memh',R/'entry.memh')
sv=['`timescale 1ps/1fs','module tb_current_native_leaf;','reg ck=0;always #416.5 ck=~ck;reg arst_n=0;reg['+str(dn['width'])+':0]packet=0;wire['+str(up['width'])+':0]returned;integer cyc=0,which=0,pin=-1,nseen=0,ng_seen=0,mseen=0,pubseen=0,age0=-1,errors=0,mut=0;reg[143:0]image[0:3919];']
conn={name:('ck'if name=='clk'or name.startswith(('clk_t','fclk_in_'))else'arst_n'if name=='arst_n'else'packet'if name=='leafdn_i0'else"1'b1"if name.startswith('cland_dn_ready')else"'0")for width,name in inputs}
conn['leafup_o0']='returned';sv.append(h[1]+' dut('+','.join('.'+n+'('+v+')'for n,v in conn.items())+');')
sv+=['function automatic['+str(dn['width'])+':0]pack(input bit cv,input[159:0]cd,input bit swv,input[9:0]sa,input[7:0]sm,input[255:0]sd);reg['+str(dn['width'])+':0]p;begin p=0;p['+str(dn['width'])+']=1;p['+str(resetbit)+']=1;']
vars_={'c_v':'cv','c_d':'cd','sw_v':'swv','sw_a':'sa','sw_m':'sm','sw_d':'sd'}
for field,mapping in fields.items():
 for i,j in mapping:sv.append(f'p[{i}]='+vars_[field]+(f'[{j}]'if field not in('c_v','sw_v')else'')+';')
sv+=['pack=p;end endfunction','task tick(input integer n);repeat(n)begin @(posedge ck);#5;end endtask','task command(input integer op,input integer a0,input integer a1,input integer family);reg[159:0]cd;begin cd=0;cd[3:0]=4\'(op);cd[13:4]=10\'(a0);cd[23:14]=10\'(a1);cd[31:24]=8\'(family);packet=pack(1,cd,0,0,0,0);tick(1);packet=pack(0,0,0,0,0,0);end endtask']
cmdexpr="{"+','.join('dut.leafdn_i0_q['+str(next(i for i,j in fields['c_d']if j==k))+']'for k in reversed(range(4)))+'}'
cv=fields['c_v'][0][0];pwire=np['p_v'];dwire=np['p_d'];ng=np['n_go']
vq=re.search(r'^\s*ot_s81sl_vq\s+#\(([^\n]*?)\)\s+(\w+)\s*\(',body,re.M);assert vq
mi='dut.'+vq[2]
sv+=['always @(posedge ck)begin cyc=cyc+1;#2;',f'if(arst_n&&dut.leafdn_i0_q[{cv}]&&{cmdexpr}==4\'d7)begin pin=cyc;$display("NATIVE_PIN mode%0d cycle%0d",which,cyc);end',f'if(arst_n&&pin>=0&&dut.{nb[2]}.n_go)begin ng_seen++;$display("NATIVE_NGO mode%0d age%0d",which,cyc-pin);end',f'if(arst_n&&pin>=0&&{mi}.m_v)begin mseen++;if({mi}.m_i!==8\'(which==0?0:128)||{mi}.m_q!==(which==0)||{mi}.m_b!==(which==1))errors++;$display("NATIVE_MODE mode%0d index%0d q%0d b%0d",which,{mi}.m_i,{mi}.m_q,{mi}.m_b);end',f'if(arst_n&&pin>=0&&dut.{nb[2]}.p_v)begin nseen++;if(dut.{nb[2]}.p_d!==32\'h3fc9a62e)errors++;if(age0<0)age0=cyc-pin;else if(cyc-pin!=age0)errors++;$display("NATIVE_PARTIAL mode%0d age%0d data%08h",which,cyc-pin,dut.{nb[2]}.p_d);end',f'if(arst_n&&pin>=0&&returned[{pv[0][0]}])begin pubseen++;$display("NATIVE_PUBLIC_PARTIAL mode%0d age%0d",which,cyc-pin);end','end']
sv+=['reg[255:0]data_;initial begin mut=$test$plusargs("mut_payload");$readmemh("entry.memh",image);for(which=0;which<2;which++)begin arst_n=0;packet=0;pin=-1;nseen=0;ng_seen=0;mseen=0;pubseen=0;tick(64);arst_n=1;packet=pack(0,0,0,0,0,0);tick(64);for(integer j=0;j<49;j++)begin data_={128\'d0,image[j][127:0]};if(mut&&j==0)data_[14]=~data_[14];packet=pack(0,0,1,image[j][137:128],8\'h0f,data_);tick(1);packet=pack(0,0,0,0,0,0);tick(1);end tick(8);command(3,0,0,0);tick(40);command(1,64,0,0);tick(30);command(7,1008,which==0?0:128,which==0?1:2);tick(160);if(nseen!=1||ng_seen!=1||mseen!=1||pubseen!=1)errors++;$display("NATIVE_CASE mode%0d partial%0d ngo%0d meta%0d public%0d",which,nseen,ng_seen,mseen,pubseen);end $display("CURRENT_NATIVE_LEAF_RESULT age%0d errors%0d clock833",age0,errors);if(errors==0)$display("CURRENT_NATIVE_LEAF_PASS");else $fatal(1,"CURRENT_NATIVE_LEAF_FAIL");$finish;end','endmodule']
(R/'tb_current_native_leaf.sv').write_text('\n'.join(sv)+'\n')
(R/'stage.json').write_text(json.dumps(dict(source_top_sha256=hashlib.sha256((B/'rtl/s81_bound_top.sv').read_bytes()).hexdigest(),native_part=part,native_module=h[1],native_file=str(native),sources=manifest,defines=ab['defines'],packet_fields=fields,reset_packet_bit=resetbit,public_partial_valid_bit=pv[0][0],public_partial_data_bits=pd,clock_ps=833,physical_phases_qualified=False,full_token=False),indent=1)+'\n')
print('STAGED_CURRENT_NATIVE',h[1],len(closure),'files',sum(Path(p).stat().st_size for p in closure))
