from pathlib import Path
import json
p=Path('.')
vec=json.loads((p/'record23_profile/vectors.json').read_text())
pre={x['sector']:x['value'] for x in vec['preload']}; gold={x['sector']:x['value'] for x in vec['checks']}
base=Path('release18_tb.sv').read_text()
# Preserve actual CKgen, producer, host leaf and CP96 installation from prior native test.
base=base[:base.index('wire[7:0] b_fault')]+'''wire[1:0] pfault; wire sfault,lfault;wire[33:0] rq;wire[561:0] wq;wire[513:0] rr;wire[1:0] dn;
ot_hbm_su_static_pgslice_lg #(.QID(0),.G(0),.READ_RETURN(18),.WRITE_RETURN(15),.MLAT(4),.ALAT(3),.LEAF(1),.MULTIRATE(1),.COLLPORT(1),.RF_LOCAL(1)) slice(
.pg_clk(stream),.clk_lane({256{clk}}),.clk_insert({128{clk}}),.rst_lane_n({32{rq}}),.clk_bcast({4{clk}}),.rst_bcast_n({4{rq}}),.clk_bank({32{clk}}),.clk_bank_macro({192{clk}}),.clk_ctl(clk),.clk_side({6{clk}}),.rst_n(rq),.bridge_rst_n(br),.control(command[2421:680]),.vmr_cmd(command[499:440]),.vmw_cmd(command[205:128]),.rf_bword(128'b0),.rf_bcmd(36'b0),.rf_dsec(256'b0),.red_sel(12'b0),.tree_cmd(12'b0),.inj_rd(2'b0),.inj_addr(160'b0),.dw_v(2'b0),.dw_row(18'b0),.dw_d(1024'b0),.fault(sfault),.lg_fault(lfault),.lg_rq(rq),.lg_wq(wq),.lg_rr(rr),.lg_w_done(dn),.lg_read(lr[1:0]),.lg_write(lw[1:0]),.far_rq(34'b0),.far_wq(562'b0));
integer checked=0;integer fills=0;
always @(posedge clk)if(slice.u_slice.fr_v[0] || slice.u_slice.fr_v[1])begin fills=fills+1;$display("FILL qt=%d data=%h",qt,slice.u_slice.fr_dat[0]);end
for(genvar b=0;b<2;b++)begin:B
wire[16:0] nrq;wire[280:0] nwq;wire[256:0] nrr;wire ndn;
// Exact expanded GEN2c+l12 source depths: read4/3 and5/2; write3/4.
source_lane #(17,3,b+1,0) rq_lane(stream,rs,rq[17*b+:17],nrq);
source_lane #(281,3,0,0) wq_lane(stream,rs,wq[281*b+:281],nwq);
source_lane #(257,3-b,0,(b==0)) rr_lane(stream,rs,nrr,rr[257*b+:257]);
wire ack_pad;source_lane #(1,3-b,0,(b==0)) done_relays(stream,rs,ndn,ack_pad);hbfd_pad #(.W(1),.N(b+1)) done_lane(.ck(stream),.rs(rs),.i(ack_pad),.o(dn[b]));
reg[280:0] hostw=0; reg[16:0] hostr=0;wire[256:0] hostrr;wire hostdone;
wire[2:0] ws=(st<200)?3'd1:wslot[3*b+:3];wire wv0=(st<200)?(|hostw):wv[b];
wire[2:0] rsel=(st>=3740)?3'd1:rslot[3*b+:3];wire rv0=(st>=3740)?hostr[16]:rv[b];
hfd_vms_bank_native_q0_faces vm(.rq0(nrq),.rr0(nrr),.rq1(hostr),.rr1(hostrr),.rq2(17'b0),.rq3(17'b0),.rq4(17'b0),.wq0(nwq),.wq_done0(ndn),.wq1(hostw),.wq_done1(hostdone),.bid(3'(b)),.sid(2'b0),.clk(stream),.clk_n(stream),.clk_s(stream),.clk_e(stream),.clk_w(stream),.clk_macro0(stream),.clk_macro1(stream),.clk_macro2(stream),.rst_n(rs),.rslot_v(rv0),.rslot(rsel),.wslot_v(wv0),.wslot(ws),.dq(281'b0),.kq(281'b0),.xq(276'b0),.xq2(276'b0),.pq(285'b0));
reg[255:0] expected[0:1];integer seen=0;
initial begin
'''
# rq naming conflict above: reset wire rq already exists. Rename data bus.
base=base.replace('stream,rs,rq[', 'stream,rs,lgrq[')
base=base.replace('wire[33:0] rq;', 'wire[33:0] lgrq;').replace('.lg_rq(rq)', '.lg_rq(lgrq)').replace('stream,rq[17*b+:17]', 'stream,lgrq[17*b+:17]')
for b in [0,1]:
 base+=f'if(b=={b})begin\n'
 for i,sec in enumerate([280+b,288+b]):base+=f"expected[{i}]=256'h{gold[sec]:064x};\n"
 base+='end\n'
base+='wait(rs); while(st<100)@(negedge stream);\n'
for i,offset in enumerate([264,272]):
 base+=f'if(b==0)hostw={{1\'b1,16\'d{offset},256\'h{pre[offset]:064x},8\'hff}};else hostw={{1\'b1,16\'d{offset+1},256\'h{pre[offset+1]:064x},8\'hff}};\n@(negedge stream);hostw=0;repeat(12)@(negedge stream);\n'
base+='''while(st<3750)@(negedge stream);hostr={1'b1,16'(280+b)};@(negedge stream);hostr=0;
while(st<3770)@(negedge stream);hostr={1'b1,16'(288+b)};@(negedge stream);hostr=0;
end
always @(posedge stream)if(rs&&hostrr[256])begin
$display("NUM b=%d n=%d got=%h expected=%h",b,seen,hostrr[255:0],expected[seen]);
if(seen>=2 || hostrr[255:0]!==expected[seen])$fatal(1,"ARITHMETIC FAIL b=%d n=%d",b,seen);
seen=seen+1;checked=checked+1;
end
end
initial begin
if(!$value$plusargs("CFG=%s",fn))$fatal;
$value$plusargs("N=%d",N);$value$plusargs("W=%d",W);if(!$value$plusargs("GOLD=%s",goldfile))$fatal;
$readmemh(fn,cfg);$readmemh(goldfile,exp);por_n=0;#100 por_n=1;wait(rq);rst_n=1;repeat(12)@(negedge clk);
for(integer i=0;i<W;i++)begin we=1;bank=cfg[i][279:264];row=cfg[i][262:256];data=cfg[i][255:0];@(negedge clk);end
we=0;while(qt<2665)@(negedge clk);start=1;@(negedge clk);start=0;
while(st<3800)@(negedge stream);
$display("RESULT commands=%d checked=%d fills=%d producer=%b slice=%b tap=%b target=%b cal=%b release=%b",n,checked,fills,fault,sfault,lfault,tf,cf,brfault);
if(n!=N || checked!=4 || fills!=2 || fault||sfault||lfault||tf||cf||brfault)$fatal(1,"ARITHMETIC FAIL final");
$display("NATIVE_RECORD23 PASS original32words sourceGEN2c+l12 diagnostic current53cb arithmetic");$finish;
end
endmodule
'''+Path('release18_tb.sv').read_text().split('module tb_lane')[1].join(['module tb_lane',''])
# Previous expression preserves the exact generic lane definition.
base=base.replace('reg[12:0] dl=160','reg[12:0] dl=160')
(p/'native_record23_tb.sv').write_text(base)

with (p/'native_record23_tb.sv').open('a') as out:out.write("""
module source_lane #(parameter W=1, N=3, PAD=0, SN=0)(input clk,rs,input[W-1:0] d,output[W-1:0] q);
wire[W-1:0] dp;
if(PAD>0)hbfd_pad #(.W(W),.N(PAD)) pad(.ck(clk),.rs(rs),.i(d),.o(dp));else assign dp=d;
wire[623:0] v[0:N];assign v[0]={{(624-W){1'b0}},dp};
for(genvar i=0;i<N;i++)begin:G
if(SN&&i==0)hbfd_rly_624_SN r(.ck(clk),.rs(rs),.i(v[i]),.o(v[i+1]));
else hbfd_rly_624_EW r(.ck(clk),.rs(rs),.i(v[i]),.o(v[i+1]));
end
assign q=v[N][W-1:0];endmodule
""")
