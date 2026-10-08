import pathlib,sys,re,hashlib,json,csv,subprocess
import argparse
a=argparse.ArgumentParser();a.add_argument('--root',type=pathlib.Path,default=pathlib.Path('/home/ubuntu/OpenTallas'));a.add_argument('--out',type=pathlib.Path,default=pathlib.Path('/tmp/qwen-vm-parent-native-drain-20261007'));a.add_argument('--me-status',type=pathlib.Path,default=pathlib.Path('/tmp/qwen-vm-native-status-20261007/physical/drain_control.json'));args=a.parse_args();R=args.root;O=args.out;O.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(R/'tools'))
import qwen_rom_rt_core_emit_w12 as E
source=E.emit(E.CORE.read_text());(O/'current_emitted_core.sv').write_text(source)
body=source[source.index('    // -- sequencer'):source.index('    // -- units')]
body=body.replace('    wire       me_ready, me_idle, su_ready, su_idle;','')
body=body.replace('    wire [15:0] su_progress, me_progress, su_rows;','')
head='''module control(input wire clk,rst_n,start,input wire [1023:0] prog_q,
input wire me_ready,me_idle,su_ready,su_idle,input wire [15:0] su_progress,me_progress,su_rows,
output reg done,prog_re,output reg [11:0] prog_addr,output reg [31:0] cycles,
output reg [17:0] next_token,output reg [31:0] next_val);
localparam W=16,G=6144,NW=18,AW=24,PAW=12,INSTR_BITS=1024,HID=4096,HALF=64,HD=128;
localparam KV_VEC_WRITE_BRIDGE=0,KV_HBM=0,W_HBM=0,QWEN_FULLSHAPE=1,INT8_WEIGHT=1,INT8_SCALE_WCS_BASE=1;
localparam LW=$clog2(W),LT=$clog2(W*8);
wire[17:0] token=0,pos=0;wire kv_write_drained=1,kv_ok=1,w_ok=1,emb_ok=1;
wire[63:0] kv_we=0; wire kv_write_flush;reg kvd_v,wd_v;
wire [23:0] wd_wbase,wd_sbase;wire[17:0] wd_tiles,wd_k,wd_nout;
`include "ot_hdc_isa.svh"
'''
# Additional descriptor output aliases within the extracted native region are observation-only.
declared=set(re.findall(r'assign\s+(\w+)\s*=',body));extra=[]
for x in sorted(declared):
 if x.startswith('kvd_'):
  extra.append('wire [31:0] '+x+';')
head+='\n'.join(extra)+'\n'
body+='\nassign me_en=1; assign am_any=0;assign am_idx=0;assign am_val=0;\nendmodule\n'
(O/'control.sv').write_text(head+body)
manifest={'source':'rtl/hdc/ot_hdc_core_vector_weight.sv','source_sha256':hashlib.sha256(E.CORE.read_bytes()).hexdigest(),'emitter_sha256':hashlib.sha256(pathlib.Path(E.__file__).read_bytes()).hexdigest(),'emitted_sha256':hashlib.sha256(source.encode()).hexdigest(),'extraction':'sequencer through before units; actual fetch, decoded NEXT, dispatch, drain, dynamic offsets and state processes unchanged; ready/idle/progress child inputs exposed; unused arithmetic argmax tied zero; memory supply gates good'}
(O/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
program=(R/'results/rtl/qwen_rom_finite_vm_schedule_20261005/inputs/L20_program.hex').read_text().splitlines();(O/'program.hex').write_text('\n'.join([program[19],program[20],program[25]])+'\n')
rows=[r for r in csv.DictReader((O/'su/trace.csv').open()) if int(r['pc'])==19]; replay=[]
for r in rows:
 age=int(r['cycle'])-5
 if age<0:continue
 bits=(int(r['ready'])<<18)|(int(r['idle'])<<17)|((int(r['vm_we'],16)!=0)<<16)|int(r['progress']);replay.append(f'{bits:05x}')
(O/'su.hex').write_text('\n'.join(replay)+'\n')
me_rows=json.loads(args.me_status.read_text());me_rows=[r for r in me_rows if r['cycle']>=5]
assert all(r['me_clk_en']==1 for r in me_rows)
assert [r['cycle'] for r in me_rows]==list(range(5,5+len(me_rows)))
(O/'me.hex').write_text('\n'.join(f"{(r['ready']<<18)|(r['idle']<<17)|(r['mxwe']<<16)|r['progress']:05x}" for r in me_rows)+'\n')
manifest['me_status_sha256']=hashlib.sha256(args.me_status.read_bytes()).hexdigest()
manifest['me_status_accept_edge']=5
manifest['native_me_idle_age']=next(r['cycle']-5 for r in me_rows if r['cycle']>5 and r['idle'])
(O/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
b='''module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,start=0;wire done,prog_re;wire[11:0] prog_addr;reg[1023:0] prog_q=0;
reg[1023:0] rom[0:2];reg[18:0] replay[0:314];reg[18:0] me_replay[0:694];
integer cyc=0,su_age=-1,me_age=-1,si=0,mi=0;reg early=0;
wire[18:0] s=(su_age<0 || su_age>314)?19'h60000:replay[su_age];
wire[18:0] m=(me_age<0)?19'h60000:me_replay[me_age];
wire true_me_idle=m[17];
wire me_idle=early?1'b1:true_me_idle;
control dut(.clk(clk),.rst_n(rst_n),.start(start),.prog_q(prog_q),.me_ready(m[18]),.me_idle(me_idle),.su_ready(s[18]),.su_idle(s[17]),.su_progress(s[15:0]),.me_progress(m[15:0]),.su_rows(16'd0),.done(done),.prog_re(prog_re),.prog_addr(prog_addr));
always @(posedge clk) begin
cyc=cyc+1;
if(prog_re) prog_q <= prog_addr<3?rom[prog_addr]:1024'd0;
if(rst_n) begin
if(su_age>=0) su_age<=su_age+1;if(me_age>=0) me_age<=me_age+1;
if(dut.su_go)begin $display("ISSUE,%0d,SU,%0d",cyc,dut.pc);su_age<=1;si=si+1;end
if(dut.me_go)begin $display("ISSUE,%0d,ME,%0d,progress=%0d,su_idle=%0d",cyc,dut.pc,s[15:0],s[17]);me_age<=1;mi=mi+1;end
if(s[16])$display("WRITE,%0d,SU,%0d",cyc,su_age);
if(me_age>=491 && me_age<=498)$display("WRITE,%0d,ME,%0d",cyc,me_age);
if(dut.fin) $display("FIN,%0d,me_age=%0d,me_idle=%0d,progress=%0d",cyc,me_age,m[17],m[15:0]);
if(dut.fin && (!true_me_idle || (me_age>=0 && me_age<=498) || !s[17]))$fatal(1,"premature END ignores actual replay busy");
if(done)begin if(si!=1 || mi!=1)$fatal(1,"issue count");$display("PASS,%0d",cyc);$finish;end
end
if(me_age>694)$fatal(1,"native replay exhausted");
if(cyc>1000)$fatal(1,"finite trace failed");
end
initial begin $readmemh("program.hex",rom);$readmemh("su.hex",replay);$readmemh("me.hex",me_replay);early=$test$plusargs("EARLY_IDLE");repeat(3)@(negedge clk);rst_n=1;start=1;@(negedge clk);start=0;end
endmodule
'''
(O/'bench.sv').write_text(b)
p=subprocess.run(['iverilog','-g2012','-I',str(R/'rtl/hdc'),'-s','tb','-o',str(O/'sim'),str(O/'control.sv'),str(R/'rtl/hdc/ot_hdc_dyn_ttiles.sv'),str(O/'bench.sv')],capture_output=True,text=True);(O/'build.log').write_text(p.stdout+p.stderr);p.check_returncode()
for name,args in [('positive_native_drain',[]),('negative_early_idle',['+EARLY_IDLE'])]:
 p=subprocess.run(['vvp',str(O/'sim')]+args,cwd=O,text=True,capture_output=True);(O/(name+'.log')).write_text(p.stdout+p.stderr);print(name,p.returncode,p.stdout[-450:]);assert (p.returncode==0)==name.startswith('positive')
