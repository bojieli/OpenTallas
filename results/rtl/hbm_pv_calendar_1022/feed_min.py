from pathlib import Path
import re,json,sys
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'repo/tools'))
from hbm_layer_vehicle import att_images as A
from hbm_layer_vehicle import pv_kv_service_1340 as S
from hbm_layer_vehicle import smb_unit as SB
rec,_=A.load_ds(root/'kv',0)
op=next(o[:5] for o in A.plan_d4g(rec)[0] if o[0]=='pv_sm_SW0')
cal,_=A.E.compile_op(rec,op,A.E.DEFAULT_LAT,True,t0=8,runtime_probability_rows={i:i for i in range(8)})
p=root/'feed_min';p.mkdir(exist_ok=True)
src=Path('/srv/opentallas-scratch/claude/hbmc-token2/pv_r18_probe/masters/ot_hbm_svc_sm_group_rel_id.sv').read_text()
m=re.search(r'module ot_smh_static_feed_m78\b.*?endmodule',src,re.S)
assert m
(p/'selected_feed.sv').write_text(m[0]+'\n')
old=[A.E.cmd_word(**c)&((1<<83)-1) for c in cal.cyc]
new=[w&~(1<<25) for w in old]
packets=[cal.pkt.get(c,0) for c in range(len(old))]
for label,vals,width in [('old',old,21),('new',new,21),('packet',packets,275)]:
 (p/f'{label}.mem').write_text(''.join(f'{v:0{width}x}\n' for v in vals))
bad=[i for i,w in enumerate(old) if w>>25&1 and not w>>29&1]
assert bad and all(not (w>>25&1) for w in new)
first=min(cal.pkt);base=84897-first
tb='''module tb;
reg clk=0;always #5 clk=~clk;reg rst_n=0;
reg[82:0] old_cmd=0,new_cmd=0;reg[1098:0] packet=0,bad_packet=0;
wire of,nf,mf;wire[42:0] oe,ne,me;wire[1081:0] a[0:5];wire[569:0] b[0:5];wire[11:0] fm[0:2];
ot_smh_static_feed_m78 o(.clk(clk),.rst_n(rst_n),.command(old_cmd),.packet(packet),.expected_request(oe),.fault(of),.lt0(a[0]),.lt1(a[1]),.lb0(b[0]),.lb1(b[1]),.fm(fm[0]));
ot_smh_static_feed_m78 n(.clk(clk),.rst_n(rst_n),.command(new_cmd),.packet(packet),.expected_request(ne),.fault(nf),.lt0(a[2]),.lt1(a[3]),.lb0(b[2]),.lb1(b[3]),.fm(fm[1]));
ot_smh_static_feed_m78 m(.clk(clk),.rst_n(rst_n),.command(new_cmd),.packet(bad_packet),.expected_request(me),.fault(mf),.lt0(a[4]),.lt1(a[5]),.lb0(b[4]),.lb1(b[5]),.fm(fm[2]));
reg[82:0] oc[0:@N@-1],nc[0:@N@-1];reg[1098:0] pk[0:@N@-1];integer first_old=-1,edge_n=0;
always @(posedge clk) begin if(rst_n&&of&&first_old<0)first_old<=edge_n;edge_n<=edge_n+1;end
initial begin
$readmemh("old.mem",oc);$readmemh("new.mem",nc);$readmemh("packet.mem",pk);
for(integer t=0;t<85510;t++)begin
 @(negedge clk);rst_n=(t>=11);old_cmd=0;new_cmd=0;packet=0;bad_packet=0;
 if(t>=@BASE@&&t<@BASE@+@N@)begin old_cmd=oc[t-@BASE@];new_cmd=nc[t-@BASE@];packet=pk[t-@BASE@];bad_packet=packet;if(t==@BASE@+@FIRST@)bad_packet[1098]=0;end
end
@(negedge clk);
if(!of||nf||!mf)$fatal(1,"FEED_MIN_FAIL old=%b fixed=%b packet_mutant=%b",of,nf,mf);
$display("FEED_MIN_PASS warm_edges=85510 old_matvec_without_packet_fault=%b corrected_attention_fault=%b packet_mutant_fault=%b first_old=%0d",of,nf,mf,first_old);$finish;end
endmodule
'''.replace('@N@',str(len(old))).replace('@BASE@',str(base)).replace('@FIRST@',str(first))
(p/'tb.sv').write_text(tb)
(p/'input_receipt.json').write_text(json.dumps(dict(source='actual selected ot_smh_static_feed_m78',authentic_packet_source='native KV canonical cal.pkt, same PV record and runtime probability profile',warm_edges=85510,first_packet_absolute=84897,calendar_base=base,old_invalid_matvec_cycles=[base+i for i in bad],changed_bits='SVG MATVEC valid25 only; XCAL consume152 unchanged',legacy_reduction_arithmetic_and_fault_guards_unchanged=True),indent=2)+'\n')
