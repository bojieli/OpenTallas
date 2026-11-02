"""Prepare live calendar -> native control -> SU, with actual transformer table delivery.

Fixture scope: cold VM payloads and CALR request timing; no scalar/station arithmetic.
"""
import argparse,json,re,subprocess,sys,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--flat',type=Path,required=True);p.add_argument('--closure',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
subprocess.run([sys.executable,str(Path(__file__).with_name('mu_native_probe.py')),'--manifest',str(a.manifest),'--flat',str(a.flat),'--closure',str(a.closure),'--out',str(a.out)],check=True)
flat=a.flat.read_text();project=a.out/'native_su_component.sv';s=project.read_text()
inst=re.compile(r'^    (\w+)\b(?:(?!;).)*?\b(u_\w+)\s*\(.*?;\n',re.M|re.S)
extra=[m.group(0) for m in inst.finditer(flat) if m.group(2) in ('u_fdn','u_rp','u_ctl')]
assert len(extra)==3
s=s.replace('    assign su_cmd={cmd_i[0] && cmd_i[3:1]==3\'d1,cmd_i[12:4]};','')
s=s.replace('    assign rp_tw_we=tw_we,rp_tw_kind=tw_kind,rp_tw_addr=tw_addr,rp_tw_data=tw_data;','')
s=s.replace('endmodule',''.join(extra)+'\nendmodule');project.write_text(s)
tb=a.out/'tb_mu_native.sv';t=tb.read_text().replace('reg rst_n=0;reg[115:0]cmd=0;','reg rst_n=0;wire[115:0]cmd;')
t=t.replace('reg[1023:0]pairs[0:3];','reg[8:0]treq=0;wire lw;wire[1:0]lk;wire[23:0]la;wire[1023:0]ld;wire lf,lb,ldone;\nreg[1023:0]pairs[0:3];')
t=t.replace('force dut.tw_we=tv;force dut.tw_kind=2\'d3;force dut.tw_addr=ta;force dut.tw_data=td;',"force dut.tw_we=lw;force dut.tw_kind=lk;force dut.tw_addr=la;force dut.tw_data=ld;")
t=t.replace("cmd=116'd15;@(negedge ck);cmd=0;repeat(16)@(negedge ck);",'repeat(16)@(negedge ck);')
start=t.index('  wv=0;tv=1;');end=t.index('\n end\n repeat(64)',start)
t=t[:start]+'''  wv=0;treq={1'b1,6'd1,2'(u)};@(negedge ck);treq=0;
  repeat(128)@(negedge ck);if(lf)$fatal(1,"LIVE_LOADER_FAULT user%0d",u);
'''+t[end:]
t=t.replace("  cmd=(116'(11+128*u)<<4)|116'd3;\n  if($test$plusargs(\"MUT_PIDX\")&&u==1)cmd=(116'd11<<4)|116'd3;\n  @(negedge ck);cmd=0;",'  cu=2\'(u);cs=1;@(negedge ck);cs=0;')
t=t.replace('MU_NATIVE_XA_PASS','MU_CALENDAR_NATIVE_XA_PASS')
t=t.replace('repeat(16)@(negedge ck);\n for(u=0;', 'repeat(16)@(negedge ck);\n load_calendar;\n for(u=0;',1)
block='''
reg pv=0,dv=0,cs=0;reg[9:0]pa=0;reg[2:0]da=0;reg[63:0]pd=0,dd=0;reg[1:0]cu=0;
wire[1:0]issued_user;wire cf,ready;wire[5:0]fc;reg[63:0]pw[0:1023];reg[127:0]entry;reg[115:0]word_cmd;integer x,issued=0; // low16 calendar words, high16 native decoded words
qfd_dv_cmd_cal_mu #(.NU(4),.UVM_STRIDE(4096),.PIDX_STRIDE(128),.TABLE_USER_RELOC(1),.BTAB_COMPACT(1),.UFOLD(1)) cal(
 .ck(ck),.rst_n(rst_n),.pw_v(pv),.pw_addr(pa),.pw_data(pd),.dw_v(dv),.dw_addr(da),.dw_data(dd),
 .start(cs),.stage(6'd1),.start_user(cu),.start_rng(1'b0),.start_first(10'd0),.start_cnt(10'd0),
 .cmd(cmd),.cmd_user(issued_user),.image_ready(ready),.fault(cf),.fault_code(fc));
qfd_dv_slice_tload #(.SLICE(0),.CAPTURE_STAGE(0),.LOCAL_JOIN(0),.NWC(34)) load(
 .ck(ck),.rst_n(rst_n),.treq(treq),.s_we(1'b0),.s_kind(2'd0),.s_addr(24'd0),.s_data(1024'd0),
 .tw_we(lw),.tw_kind(lk),.tw_addr(la),.tw_data(ld),.busy(lb),.done(ldone),.fault(lf));
task load_calendar;
 begin
 for(x=0;x<1024;x=x+1)pw[x]=0;
 // Real ROOT/STN words travel the native control decode. Their arithmetic
 // engines are excluded; the XA command is the actual native data witness.
 word_cmd=(116'd1344<<11)|(116'd1500<<36)|116'd7;entry=(128'd16<<116)|128'(word_cmd);pw[0]=entry[63:0];pw[1]=entry[127:64];
 word_cmd=(116'd4<<15)|(116'd1600<<26)|116'd5;entry=(128'd16<<116)|128'(word_cmd);pw[2]=entry[63:0];pw[3]=entry[127:64];
 word_cmd=(116'd11<<4)|116'd3;if($test$plusargs("MUT_PIDX"))word_cmd=(116'd9<<4)|116'd3;
 entry=(128'd16<<116)|128'(word_cmd);pw[4]=entry[63:0];pw[5]=entry[127:64];
 entry=(128'd16<<116)|128'd15;pw[8]=entry[63:0];pw[9]=entry[127:64];
 for(x=0;x<1024;x=x+1)begin pv=1;pa=10'(x);pd=pw[x];@(negedge ck);end
 pv=0;repeat(8)@(negedge ck);
 for(x=0;x<8;x=x+1)begin dv=1;da=3'(x);dd=(x==0)?64'h43414c4400000005:((x==2)?64'd3:((x==4)?64'h0000000000040001:64'd0));@(negedge ck);end
 dv=0;repeat(16)@(negedge ck);if(!ready||cf)$fatal(1,"CAL_SEAL ready%b fault%b code%h",ready,cf,fc);
 end
endtask
always @(negedge ck)if(rst_n)begin
 if(cf)$fatal(1,"LIVE_CAL_FAULT %h",fc);
 if(dut.sc_cfg[100])begin
 issued=issued+65536;
 if(active<0||dut.sc_cfg[91:68]!==24'(1344+4096*active)||dut.sc_cfg[66:43]!==24'(1500+4096*active))$fatal(1,"NATIVE_ROOT_DECODE");
 end
 if(dut.stn_cfg[28])begin
 issued=issued+65536;
 if(active<0||dut.stn_cfg[16:8]!==9'(4+((active==0)?0:200+72*active)))$fatal(1,"NATIVE_STN_DECODE");
 end
 if(dut.su_cmd[9])begin
 issued=issued+65536;
 if(active<0||dut.su_cmd[8:0]!==9'(11+128*active))$fatal(1,"NATIVE_SU_DECODE");
 end
 if(cmd[0])begin
 if(cmd[3:1]!=7)issued=issued+1;
 case(cmd[3:1])
 3:if(cmd[34:11]!==24'(1344+4096*issued_user)||cmd[59:36]!==24'(1500+4096*issued_user))$fatal(1,"LIVE_ROOT_BANK");
 2:if(cmd[23:15]!==9'(4+((issued_user==0)?0:200+72*issued_user))||cmd[52:51]!==issued_user)$fatal(1,"LIVE_STN_BANK");
 1:if(cmd[12:4]!==9'(11+128*issued_user))$fatal(1,"LIVE_SU_PIDX");
 7:if(cmd!==116'd15)$fatal(1,"LIVE_BOOT_SETID");
 default:$fatal(1,"LIVE_UNEXPECTED_CMD");
 endcase
 end
end
'''
t=t.replace('initial begin\n force',block+'\ninitial begin\n force')
t=t.replace('if(dut.su_fault||dut.vm_fault)', 'if(dut.su_fault||dut.vm_fault||cf||lf||dut.st_c[69]||dut.rp_fault)')
t=t.replace('$display("MU_CALENDAR_NATIVE_XA_PASS', 'if(issued!=786444)$fatal(1,"CAL_COMMAND_COUNT %0d decoded%0d",issued&65535,issued>>16);\n $display("MU_CALENDAR_NATIVE_XA_PASS')
tb.write_text(t)
# Resolve selected dependencies again, now including actual control/calendar/loader.
files=[(a.closure/z).resolve() for z in (a.closure/'files.f').read_text().splitlines()]
files += [a.source/'rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv',a.source/'rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv',a.source/'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v',project,tb]
files=list(dict.fromkeys(files));clean={};mods={}
for path in files:
 text=re.sub(r'/\*.*?\*/|//[^\n]*',' ',path.read_text(),flags=re.S);clean[path]=text
 for name in re.findall(r'\bmodule\s+(\w+)',text):mods.setdefault(name,path)
todo=[project,tb];selected=set()
while todo:
 path=todo.pop()
 if path in selected:continue
 selected.add(path)
 todo += [mods[n] for n in set(re.findall(r'\b[A-Za-z_]\w*\b',clean[path]))&mods.keys() if mods[n] not in selected]
(a.out/'source.f').write_text(''.join(str(z)+'\n' for z in files if z in selected))
(a.out/'composition.json').write_text(json.dumps(dict(scope='Live calendar/seal/store/FIFO, native FDN/RP/CTL, native SU XA and real table loader; excludes ROOT/STN arithmetic and CALR request producer',table_profile='current0/0/34',TABLE_USER_RELOC=1,files=len(selected)),indent=2)+'\n')

metadata=json.loads((a.out/'source.json').read_text())
metadata.update(projection='Exact native SU/VM/eight heads/SFUs plus FDN/RP/CTL; ROOT/STN arithmetic excluded',
                fixture='Live calendar command/store/seal/FIFO and current0/0 table loader; cold w16 preload and fixture CALR request timing',
                projection_sha256=hashlib.sha256(project.read_bytes()).hexdigest(),
                selected_files=len(selected),selected_bytes=sum(z.stat().st_size for z in selected),
                calendar_source_sha256=hashlib.sha256((a.source/'rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv').read_bytes()).hexdigest())
metadata['kept_instances'] += ['u_fdn','u_rp','u_ctl']
metadata['excluded_instances']=[z for z in metadata['excluded_instances'] if z not in ('u_fdn','u_rp','u_ctl')]
(a.out/'source.json').write_text(json.dumps(metadata,indent=2)+'\n')
