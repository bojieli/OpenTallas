import pathlib,subprocess,json,hashlib
import argparse
p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,default=pathlib.Path('/home/ubuntu/OpenTallas'));p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('/tmp/qwen-vm-normalizer-return-20261007'));p.add_argument('--rtl',type=pathlib.Path);args=p.parse_args();R=args.root;O=args.out;O.mkdir(parents=True,exist_ok=True);rtl=args.rtl or R/'rtl/qwen_sys/finite_vm_20261007/ot_qwen_rom_vm_request_normalizer.sv'
if not rtl.exists():rtl=O/'normalizer.sv'
top=(R/'rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_vprm_stream4.sv').read_text();block=top[top.index('    // ---- vector memory'):top.index('    // ---- KV service')]
assert 'a = ({8\'d0, vw_me_addr[vi*24 +: 24]} << 4) + vl;' in block
assert "a = ({8'd0, vw_mx_addr} << 4) + vl;" in block
# Reference uses the exact native widened-address statements, with only port names renamed.
meexpr="({8'd0, vw_me_addr[vi*24 +: 24]} << 4) + vl";mxexpr="({8'd0, vw_mx_addr} << 4) + vl";seqexpr="({24'd0, s_vraddr} << 4) + vl"
assert seqexpr in block
bench=r'''
module tb;
parameter LIM=1048576,ON=1;
reg me_wanted;reg[2239:0] scalar_re;reg[2240*24-1:0]scalar_raddr;
reg seq_re,seq_we;reg[23:0]seq_rword,seq_wword;
reg[48:0]word_we;reg[49*24-1:0]word_waddr;reg[49*16-1:0]word_wmask;
reg[64:0]scalar_we;reg[65*24-1:0]scalar_waddr;
reg[865*32-1:0]data;
wire[2255:0]ren,rzero,rpub;wire[2256*32-1:0]ra;
reg[2256*32-1:0]backend;wire[2256*32-1:0]published;
wire[864:0]wen;wire[865*32-1:0]wa,wd;
ot_qwen_rom_vm_request_normalizer #(.ENABLE(ON),.VWA(24),.VM_ELEMS(LIM))dut(me_wanted,scalar_re,scalar_raddr,seq_re,seq_rword,word_we,word_waddr,word_wmask,scalar_we,scalar_waddr,seq_we,seq_wword,data,rpub,ren,rzero,ra,wen,wa,wd,backend,published);
integer f,i,j,k,s,want,n=0,seen_bad=0;reg[31:0]a;reg[31:0]last_data;integer last_slot;
initial begin
for(f=0;f<12;f=f+1)begin
 me_wanted=f!=8;seq_re=f!=9;seq_we=f!=9;seq_rword=f==1?24'h100000:f==2?(LIM>>4):f==3?((LIM-1)>>4):0;seq_wword=seq_rword;
 scalar_re='1;scalar_we='1;word_we='1;word_wmask='1;
 for(i=0;i<2240;i=i+1)scalar_raddr[i*24+:24]=f==0?i%LIM:f==1?24'hffffff:f==2?LIM:f==3?LIM-1:f==4?i*671:0;
 for(i=0;i<65;i=i+1)scalar_waddr[i*24+:24]=f==0?i%LIM:f==1?24'hffffff:f==2?LIM:f==3?LIM-1:f==4?i*169:0;
 for(i=0;i<49;i=i+1)word_waddr[i*24+:24]=f==0?i%(LIM/16+1):f==1?24'h100000:f==2?(LIM>>4):f==3?((LIM-1)>>4):f==4?i*159:0;
 if(f==5)word_wmask=784'h55555555555555555555555555555555;
 if(f==6)begin scalar_re=0;scalar_we=0;word_we=0;end
 if(f==7)begin scalar_re=2240'h1;scalar_we=65'h1;word_wmask=0;end
 for(i=0;i<865;i=i+1)data[i*32+:32]=32'h55000000+i;
 for(i=0;i<2256;i=i+1)backend[i*32+:32]=32'h12345678+i;
 #1;
 for(i=0;i<2240;i=i+1)begin
  s=i<192?i:i+16;a=scalar_raddr[i*24+:24];want=ON&&scalar_re[i]&&(i<192||me_wanted);
  if(ra[s*32+:32]!==a||rpub[s]!==want[0]||ren[s]!==((want!=0)&&(a<LIM))||rzero[s]!==((want!=0)&&!(a<LIM)))$fatal(1,"scalar read f=%0d slot=%0d",f,s);
  n=n+1;
 end
 for(j=0;j<16;j=j+1)begin
  a=SEQ_R_EXPR;s=192+j;want=ON&&seq_re;
  if(ra[s*32+:32]!==a||rpub[s]!==want[0]||ren[s]!==((want!=0)&&(a<LIM))||rzero[s]!==((want!=0)&&!(a<LIM)))$fatal(1,"seq read f=%0d slot=%0d",f,s);
  n=n+1;
 end
 for(i=0;i<49;i=i+1)for(j=0;j<16;j=j+1)begin
  a=ME_EXPR;s=i*16+j;want=ON&&me_wanted&&word_we[i]&&word_wmask[s]&&(a<LIM);
  if(wa[s*32+:32]!==a||wen[s]!==want[0])$fatal(1,"word write f=%0d slot=%0d address=%h",f,s,a);
  if(f==1&&wen[s])$fatal(1,"high word wrapped into admitted low scalar");
  if(f==1&&!wen[s]&&wa[s*32+:32]==32'h01000000)seen_bad=seen_bad+1;
  n=n+1;
 end
 for(i=0;i<65;i=i+1)begin
  a=scalar_waddr[i*24+:24];s=784+i;want=ON&&scalar_we[i]&&(a<LIM);
  if(wa[s*32+:32]!==a||wen[s]!==want[0])$fatal(1,"scalar write");n=n+1;
 end
 for(j=0;j<16;j=j+1)begin
  a=SEQ_W_EXPR;s=849+j;want=ON&&seq_we&&(a<LIM);
  if(wa[s*32+:32]!==a||wen[s]!==want[0])$fatal(1,"seq write");n=n+1;
 end
 for(i=0;i<2256;i=i+1)if(rpub[i]&&published[i*32+:32]!== (rzero[i]?32'd0:backend[i*32+:32]))$fatal(1,"published invalid read not zero");
 if(wd!==data)$fatal(1,"write-data priority slot permutation");
 if(f==10&&ON)begin
  last_slot=-1;last_data=0;
  for(s=0;s<865;s=s+1)if(wen[s]&&wa[s*32+:32]==0)begin last_slot=s;last_data=wd[s*32+:32];end
  if(last_slot!=849||last_data!=32'h55000351)$fatal(1,"golden last-writer priority");
 end
end
if(seen_bad!=49)$fatal(1,"wrap witness absent");
$display("PASS LIM=%0d ON=%0d checks=%0d highwrap=%0d",LIM,ON,n,seen_bad);$finish;
end
endmodule
'''
bench=bench.replace('ME_EXPR',meexpr.replace('vw_me_addr','word_waddr').replace('vi','i').replace('vl','j')).replace('SEQ_R_EXPR',seqexpr.replace('s_vraddr','seq_rword').replace('vl','j')).replace('SEQ_W_EXPR',seqexpr.replace('s_vraddr','seq_wword').replace('vl','j'))
(O/'bench.sv').write_text(bench)
mutants={'wrap':("wire [31:0] a=(wide_word<<4)+l;","wire [23:0] truncated=(wide_word<<4)+l; wire [31:0] a=truncated;"), 'invalid_read':('assign read_zero[SLOT]=want&&!(a<VM_ELEMS);','assign read_zero[SLOT]=1\'b0;')}
# Wrap mutant also performs the erroneous bound on the already narrowed address.
results=[]
for name in ['positive','disabled','partial','wrap','invalid_read','zero_return']:
 src=rtl.read_text()
 if name=='wrap':
  old,new=mutants[name];assert old in src;src=src.replace(old,new).replace('wire in_bounds=(VM_ELEMS%16==0)?word_in:(a<VM_ELEMS);','wire in_bounds=(a<VM_ELEMS);')
 if name=='invalid_read':
  old,new=mutants[name];assert old in src;src=src.replace(old,new)
 if name=='zero_return':src=src.replace("read_zero[SLOT]?32'd0:backend_read_data[SLOT*32+:32]",'backend_read_data[SLOT*32+:32]')
 d=O/name;d.mkdir(exist_ok=True);(d/'normalizer.sv').write_text(src)
 cmd=['iverilog','-g2012','-s','tb','-o',str(d/'sim'),str(d/'normalizer.sv'),str(O/'bench.sv')]
 if name=='disabled':cmd+=['-Ptb.ON=0']
 if name=='partial':cmd+=['-Ptb.LIM=1048573']
 p=subprocess.run(cmd,text=True,capture_output=True);(d/'build.log').write_text(p.stdout+p.stderr);p.check_returncode()
 p=subprocess.run(['vvp',str(d/'sim')],text=True,capture_output=True);(d/'run.log').write_text(p.stdout+p.stderr)
 assert (p.returncode==0)==(name in ['positive','disabled','partial']),(name,p.stdout)
 results.append(dict(case=name,exit=p.returncode,log=p.stdout));print(name,p.stdout[-250:])
(O/'results.json').write_text(json.dumps(dict(cases=results,source_top_sha256=hashlib.sha256(top.encode()).hexdigest(),source_vm_block_sha256=hashlib.sha256(block.encode()).hexdigest(),scope='Combinational source-semantic requests and zero-read publication flags only. No memory timing, clock binding, numerical engine or physical qualification.'),indent=2)+'\n')
