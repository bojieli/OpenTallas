from pathlib import Path
import sys,json,hashlib,re
D=Path('/srv/opentallas-scratch/claude/hbm-native-record23-clock-1019');R=Path('/srv/opentallas-scratch/claude/hbm-record23-repair-1019');O=Path.cwd()
sys.path[:0]=[str(D/'tools'),str(D/'tools/hbm_static'),str(D/'tools/hgi_adapters'),str(D)]
from native_su_calendar import compile_calendar
words=[int(x,16)for x in (R/'production/quarter.mem').read_text().split()]
cw=[(x&~(((1<<180)-1)<<500))&~(((1<<234)-1)<<206)for x in words]
c,m=compile_calendar(cw,first_serial=2975,bridge_serial=2675,bridge_stream=3567,host_launch=3900,rows=160,request_lane_edges_by_bank=[4,5,0,0,0,0,0,0],write_lane_edges_by_bank=[3,3,0,0,0,0,0,0])
assert c==[int(x,16)for x in (R/'calendar.mem').read_text().split()]
(O/'second_calendar_model.json').write_text(json.dumps(m,indent=2))
model=dict(scope='two serialized independent requests on ONE SU instance, no hardware user tags or resident user contexts',descriptor_rearm=dict(stream_pulse=3850,same_resident_image=True,source='ot_static_program_target: one descriptor arms one launch',added_command_count=1),hardware_unchanged=True,rtl_reelaboration=False,testbench_only_cpp_overlay=True,requests=[dict(owner=0,first_command_capture_serial=2675,programme_publication_counter=2674,host_reads=[3750,3770],acceptance=3800),dict(owner=1,first_command_capture_serial=2975,programme_publication_counter=2974,host_reads=[4150,4170],acceptance=4200,input='permute original two finite host-input sectors within each bank',gold='same original sector permutation')],clock_ps=dict(serial=1112,stream=834,ratio='3:4'),reservation_edges=73,start_separation_serial=300,start_separation_stream=400,start_separation_ps=333600,extra_over_control_reservation_edges=227,extra_over_reservation_ps=252424,source_phase_restart_modulo=3,minimum_phase_aligned_restart_separation=75,minimum_qualified_separation=None,full_su_token=False,full_mu_token=False,hardware_user_policy='release SU only; next-release P3 MU not exercised',no_backpressure=True)
(O/'composition_model.json').write_text(json.dumps(model,indent=2))
# Executable SV counterpart of cached compiled testbench overlays. All RTL source
# is identical; acceptance0 assertions remain before this bounded extension.
s=(D/'native_record23_tb.sv').read_text()
s=s.replace('repeat(4000)@(posedge stream)','repeat(4400)@(posedge stream)').replace('after4000 stream edges','after4400 stream edges')
s=s.replace('(st<200)?','((st<200)||(st>=3800&&st<3900))?').replace('(st>=3740)?','((st>=3740&&st<3800)||st>=4140)?')
p='''integer reqmut=0;
$value$plusargs("REQMUT=%d",reqmut);
$display("REQUEST0_ACCEPT stream3800 original32words unchanged");
n=0;first=-1;fills=0;checked=0;
B[0].seen=0;B[1].seen=0;
begin reg[255:0] temp;
 temp=B[0].expected[0];B[0].expected[0]=B[0].expected[1];B[0].expected[1]=temp;
 temp=B[1].expected[0];B[1].expected[0]=B[1].expected[1];B[1].expected[1]=temp;
end
while(st<3805)@(negedge stream);
B[0].hostw={1'b1,16'd264,256'h3df69e453e3068863dd706293d91d4593ec18c363f0f5f843e659ae23ec05ff4,8'hff};
B[1].hostw={1'b1,16'd265,256'h3d85f0423e1c163b3e07d37a3ddb711a3e8a28463e8c8e853dfab5ef3e4f398a,8'hff};
while(st<3806)@(negedge stream);B[0].hostw=0;B[1].hostw=0;
while(st<3818)@(negedge stream);
B[0].hostw={1'b1,16'd272,256'h3ea0e35f3e8f2d283e0b309c3e1874323e087e3c3dcdb42f3e22152f3e471b6a,8'hff};
B[1].hostw={1'b1,16'd273,256'h3de8c4703eb80cb23e76cd7e3dc445983ea82b4c3e0454cf3e42ae3e3e2caef6,8'hff};
while(st<3819)@(negedge stream);B[0].hostw=0;B[1].hostw=0;
while(st<3850)@(negedge stream);if(reqmut!=2)dv=1;
while(st<3851)@(negedge stream);dv=0;
while(st<3900)@(negedge stream);lv=1;
while(st<3901)@(negedge stream);lv=0;
while(qt<(2965+(reqmut==4)))@(negedge clk);start=1;
while(qt<(2966+(reqmut==4)))@(negedge clk);start=0;
while(st<4150)@(negedge stream);B[0].hostr={1'b1,16'd280};B[1].hostr={1'b1,16'd281};
while(st<4151)@(negedge stream);B[0].hostr=0;B[1].hostr=0;
while(st<4170)@(negedge stream);B[0].hostr={1'b1,16'd288};B[1].hostr={1'b1,16'd289};
while(st<4171)@(negedge stream);B[0].hostr=0;B[1].hostr=0;
while(st<4200)@(negedge stream);
$display("RESULT second commands=%d checked=%d fills=%d producer=%b slice=%b tap=%b target=%b cal=%b release=%b",n,checked,fills,fault,sfault,lfault,tf,cf,brfault);
if(n!=N || checked!=4 || fills!=2 || fault||sfault||lfault||tf||cf||brfault)$fatal(1,"ARITHMETIC FAIL final second");
$display("SERIAL_REQUESTS2 PASS contexts=1 requests=2 start_offset_serial=300 acceptance_stream=3800,4200");
$finish;'''
a='$display("NATIVE_RECORD23 PASS original32words sourceGEN2c+l12 diagnostic current53cb arithmetic");$finish;'
assert a in s;s=s.replace('integer st=-1,qt=-1;', 'integer reqmut=0;integer st=-1,qt=-1;')
p=p.replace('integer reqmut=0;\n','')
s=s.replace(a,a.replace('$finish;',p))
s=re.sub(r"(?m)^(B\[[01]\]\.hostw=\{.*?;)$", r'if(reqmut!=1)\1',s)
s=s.replace("16'd280};B[1].hostr={1'b1,16'd281}","16'(280+(reqmut==3?8:0))};B[1].hostr={1'b1,16'(281+(reqmut==3?8:0))}").replace("16'd288};B[1].hostr={1'b1,16'd289}","16'(288-(reqmut==3?8:0))};B[1].hostr={1'b1,16'(289-(reqmut==3?8:0))}")
(O/'two_request_tb.sv').write_text(s)
print('EXACT_PHASE_ALIGNED_CALENDAR_EQUAL PASS first_serial2975 host_launch3900; explicit separation333600ps')
