#!/usr/bin/env python3
"""Small receiver lockstep gate: default vs pinned legacy; opt-in valid v1 vs stripped legacy; malformed v1 caught."""
import argparse,re,subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
r=Path(__file__).resolve().parents[3];a.out.mkdir(parents=True,exist_ok=True)
src='rtl/qwen_sys/d2d_static_20261015/'
old=subprocess.check_output(['git','-C',str(r),'show','36a3c3c56a07d642a78ade72bb406e1966488c88:'+src+'ot_qwen_d2d_safe_fo.sv'],text=True)
old=re.search(r'module ot_qwen_d2d_status_rx_sf #.*?\nendmodule',old,re.S).group().replace('module ot_qwen_d2d_status_rx_sf #','module legacy_status_rx #',1)
(a.out/'legacy.sv').write_text(old+'\n')
ports={'vm_drained':1,'collective_drained':1,'collective_busy':1,'crom_fault':1,'execution_active':1,'admit_ready':1,'status_fresh':1,'result_v':1,'result_done':1,'result_fault':1,'result_cause':4,'result_tag':59,'result_gen':2,'result_token':18,'result_value':32,'result_cycles':32,'fault':1}
w=sum(ports.values());t=f'''module tb;
reg ck=0,rst_n=0,ev=0,slot=0,epoch_begin=0;
reg [15:0] epoch16=16'h1234;
reg [547:0] payload=0;
wire [547:0] masked={{payload[547:512],356'd0,payload[155:0]}};
wire [{w-1}:0] q[0:3];
'''
for i,(module,param,pay) in enumerate([('ot_qwen_d2d_status_rx_sf','#(.NG(10))','payload'),('legacy_status_rx','#(.NG(10))','payload'),('ot_qwen_d2d_status_rx_sf','#(.NG(10),.OBS1_COMPAT(1))','payload'),('legacy_status_rx','#(.NG(10))','masked')]):
 con=['.ck(ck)','.rst_n(rst_n)','.epoch16(epoch16)','.rx_event(ev)','.rx_slot(slot)',".ev_c({10{ev}})",".rs_c({10{slot}})",f'.rx_payload({pay})','.epoch_begin(epoch_begin)'];off=0
 for name,n in ports.items():
  con.append(f'.{name}(q[{i}][{off} +: {n}])');off+=n
 t+=f'{module} {param} u{i}('+','.join(con)+');\n'
fault=w-1
t+=f'''integer checks=0,i,j; reg [207:0] good;
task tick; begin #1;ck=1;#1;ck=0;#1;checks=checks+1;if(q[0]!==q[1])$fatal(1,"DEFAULT_LOCKSTEP");end endtask
task reset_rx; begin rst_n=0;ev=0;slot=0;tick;rst_n=1;tick;end endtask
task header; begin payload=0;payload[542:539]=15;payload[538:533]=63;payload[532:517]=epoch16;end endtask
initial begin
reset_rx;
for(i=0;i<200;i=i+1)begin
 if(i%20==0)reset_rx;
 header;for(j=0;j<5;j=j+1)payload[j*32+:32]=$random;payload[159:156]=0;
 ev=(i%3!=0);slot=ev;epoch_begin=(i%7==0);tick;
 if(q[2]!==q[3])$fatal(1,"LEGACY_COMPAT_LOCKSTEP");
end
for(i=0;i<200;i=i+1)begin
 if(i%20==0)reset_rx;
 header;for(j=0;j<17;j=j+1)payload[j*32+:32]=$random;
 ev=1;slot=(i%5!=0);tick;
end
for(i=0;i<16;i=i+1)begin
 reset_rx;header;good=0;good[207:204]=1;
 if(i[0])begin good[203]=1;good[202:201]=2;good[186:185]=2;end
 if(i[1])begin good[141]=1;good[137]=1;end
 if(i[2])begin good[94]=1;good[92:61]=1;end
 if(i[3])begin good[94]=1;good[93]=1;good[92:61]=32'hffffffff;end
 payload[511:304]=good;for(j=0;j<4;j=j+1)payload[j*32+:32]=$random;payload[155:128]=$random;ev=1;slot=1;tick;
 if(q[2]!==q[3]||q[2][{fault}])$fatal(1,"V1_LOCKSTEP");
 if(!q[0][{fault}])$fatal(1,"LEGACY_MUST_REJECT_V1");
 ev=0;slot=0;tick;if(q[2]!==q[3])$fatal(1,"V1_CAPTURE_EDGE");
end
for(i=0;i<8;i=i+1)begin
 reset_rx;header;payload[511:304]=0;payload[511:508]=1;
 case(i)
 0:payload[511:508]=2;
 1:payload[304]=1;
 2:payload[156]=1;
 3:payload[507]=1;
 4:payload[445]=1;
 5:payload[398]=1;
 6:begin payload[398]=1;payload[397]=1;payload[396:365]=1;end
 7:payload[532:517]=epoch16+1;
 endcase
 ev=1;slot=1;tick;if(!q[2][{fault}])$fatal(1,"MALFORMED_V1_ESCAPED case %0d",i);
end
$display("STATUS_OBS_COMPAT PASS checks=%0d legacy=400 valid_v1=16 malformed=8 added_cycles=0",checks);$finish;
end endmodule
'''
(a.out/'tb.sv').write_text(t)
cmd=['verilator','--binary','--timing','-j','2','-Wno-fatal','-Wno-TIMESCALEMOD','--top-module','tb','--Mdir',str(a.out/'obj'),str(a.out/'tb.sv'),str(a.out/'legacy.sv'),str(r/src/'ot_qwen_d2d_safe_fo.sv'),str(r/src/'ot_qwen_status_observers_v1.sv')]
with (a.out/'build.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
with (a.out/'run.log').open('w') as f:subprocess.run([str(a.out/'obj/Vtb')],stdout=f,stderr=subprocess.STDOUT,check=True)
print((a.out/'run.log').read_text())
