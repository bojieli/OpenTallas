// STEWARD-HBMd 10-22: SVG S1 consumer copy guard (MVPKT) on the AUTHENTIC PV calendar (v2 programme, bit25 kept) and
// the native KV canonical packets of the same record (inputs from codex feed_min: old.mem = cal.cyc SVG words, packet.mem).
// fixed : MVPKT 0 (svg copy)            -> no fault over 85510 warm edges           (the fix)
// orig  : MVPKT 1 (pre-fix svg copy)    -> faults at the first PV consume edge 84952 (reproduces fs/hleaf sticky source)
// drop  : MVPKT 0, first packet dropped -> faults (packet/command[29] mismatch still caught)
// tagm  : MVPKT 0, packet 5 tag +1      -> faults (tag check still caught)
// nm    : MVPKT 1 normal-mode copy, bit25 issue with no packet injected at an idle edge -> faults (SM normal rule kept)
module tb;
reg clk=0;always #5 clk=~clk;reg rst_n=0;
reg[82:0] cmd=0,cmd_nm=0;reg[1098:0] pk=0,pk_drop=0,pk_tag=0;
wire ff,fo,fd,ft,fn;wire[42:0] e0,e1,e2,e3,e4;wire[1081:0] a[0:9];wire[569:0] b[0:9];wire[11:0] fm[0:4];
ot_smh_static_feed #(.MVPKT(0)) u_fixed(.clk(clk),.rst_n(rst_n),.command(cmd),.packet(pk),.expected_request(e0),.fault(ff),.lt0(a[0]),.lt1(a[1]),.lb0(b[0]),.lb1(b[1]),.fm(fm[0]));
ot_smh_static_feed               u_orig (.clk(clk),.rst_n(rst_n),.command(cmd),.packet(pk),.expected_request(e1),.fault(fo),.lt0(a[2]),.lt1(a[3]),.lb0(b[2]),.lb1(b[3]),.fm(fm[1]));
ot_smh_static_feed #(.MVPKT(0)) u_drop (.clk(clk),.rst_n(rst_n),.command(cmd),.packet(pk_drop),.expected_request(e2),.fault(fd),.lt0(a[4]),.lt1(a[5]),.lb0(b[4]),.lb1(b[5]),.fm(fm[2]));
ot_smh_static_feed #(.MVPKT(0)) u_tagm (.clk(clk),.rst_n(rst_n),.command(cmd),.packet(pk_tag),.expected_request(e3),.fault(ft),.lt0(a[6]),.lt1(a[7]),.lb0(b[6]),.lb1(b[7]),.fm(fm[3]));
ot_smh_static_feed               u_nm   (.clk(clk),.rst_n(rst_n),.command(cmd_nm),.packet(1099'd0),.expected_request(e4),.fault(fn),.lt0(a[8]),.lt1(a[9]),.lb0(b[8]),.lb1(b[9]),.fm(fm[4]));
reg[82:0] oc[0:399];reg[1098:0] pm[0:399];integer first_o=-1,first_f=-1,e=0,n25=0,n29=0,i;
always @(posedge clk) begin if(rst_n&&fo&&first_o<0)first_o<=e;if(rst_n&&ff&&first_f<0)first_f<=e;e<=e+1;end
localparam integer BASE=84878, FIRSTPK=19;
initial begin
 $readmemh("old.mem",oc);$readmemh("packet.mem",pm);
 for(i=0;i<400;i++)begin if(oc[i][25])n25++;if(oc[i][29])n29++;end
 if(n25!=64||n29!=32)$fatal(1,"INPUT_FAIL n25=%0d n29=%0d (expect 64 / 32)",n25,n29);
 for(integer t=0;t<85510;t++)begin
  @(negedge clk);rst_n=(t>=11);cmd=0;pk=0;pk_drop=0;pk_tag=0;cmd_nm=0;
  if(t==2000)cmd_nm=83'h2000000;
  if(t>=BASE&&t<BASE+400)begin cmd=oc[t-BASE];pk=pm[t-BASE];pk_drop=pk;pk_tag=pk;
   if(t==BASE+FIRSTPK)pk_drop[1098]=0;
   if(t==BASE+FIRSTPK+5)pk_tag[1088]=~pk_tag[1088];end
 end
 @(negedge clk);
 if(ff||!fo||!fd||!ft||!fn)$fatal(1,"SVG_ATTN_GUARD_FAIL fixed=%b orig=%b drop=%b tag=%b normal=%b",ff,fo,fd,ft,fn);
 $display("SVG_ATTN_GUARD_PASS edges=85510 issues25=%0d packets=%0d fixed_fault=%b orig_fault=%b first_orig=%0d drop=%b tag=%b normal_rule=%b",n25,n29,ff,fo,first_o,fd,ft,fn);
 $finish;
end
endmodule
