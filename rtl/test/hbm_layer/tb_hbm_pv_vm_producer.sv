`timescale 1ns/1ps
module tb_hbm_pv_vm_producer;
reg clk=0; always #1 clk=~clk;
reg rst_n=0,cfg_v=0,desc_v=0,launch_v=0,clear_v=0,read_v=0;
reg [11:0] cfg_addr=0; reg [255:0] cfg_data=0; reg [6:0] read_addr=0;
wire configured,fault,active,rn;
wire [135:0] rq; wire [2055:0] rr;
wire [1023:0] cd; wire [3:0] wce; wire mhi,mlo; wire [6:0] wa,ra;
wire [7:0] rce,ed5; wire [16:0] ede;
wire bqv,bql;wire [6:0] bqa,bqb;wire qvlo,qvhi;
localparam [63:0] RL={8'd45,8'd43,8'd55,8'd53,8'd29,8'd27,8'd40,8'd37};
ot_hgi_sm_xload_cl2_ctlx #(.PMAX(8),.RD_LAT(RL),.NR(32),.LEAD(8)) ctl(
.clk(clk),.clk_cal(clk),.rst_n(rst_n),.tgt(8'd100),.cfg_v(cfg_v),.cfg_target(8'd100),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
.desc_v(desc_v),.desc_base(12'd0),.desc_limit(13'd128),.desc_loops(16'd1),.launch_v(launch_v),
.configured(configured),.fault(fault),.active(active),.rq(rq),.rr(rr),.rn_o(rn),
.c_d(cd),.c_wce(wce),.c_mhi(mhi),.c_mlo(mlo),.c_wa(wa),.r_ce(rce),.r_a(ra),.l_d_o(),
.qv_lo(qvlo),.qv_hi(qvhi),.qo_lo(1'b0),.qo_hi(1'b0),.qf_lo(1'b0),.qf_hi(1'b0),
.r_wsel(),.zlo(),.zhi(),.bsel(),.lane_en(),.eg_ed5(ed5),.eg_ede(ede),.eg_bqv(bqv),.eg_bqlast(bql),.eg_bqaddr(bqa),.eg_bqb(bqb));
// The omitted quantizer/BD boundary is inactive in format0, and asserted below.
reg [31:0] vm [0:262143]; reg [31:0] probs[0:127];reg [15:0] gold[0:127];reg [17:0] src[0:127];
integer errors=0,beats[0:1],reqs=0,cyc=0,mut=0;integer first_rq=-1,first_xw=-1,launch_edge=-1,first_cmd=-1,first_start=-1,first_write=-1,last_xw=-1;
integer read_valid[0:1];
always @(posedge clk)cyc<=cyc+1;
generate for(genvar b=0;b<8;b=b+1)begin:VB
 localparam integer L=(RL>>(8*b))&255;
 reg [256:0] pipe[0:L-1];
 always @(posedge clk)begin
  pipe[0]<=0;
  if(rq[b*17+16])begin
   if(rq[b*17+15] || rq[b*17+:3]!=3'(b))$fatal(1,"VM_BANK_ID");
   pipe[0][256]<=1;
   for(integer k=0;k<8;k=k+1)pipe[0][k*32+:32]<=vm[{rq[b*17+:15],3'(k)}];
  end
  for(integer j=1;j<L;j=j+1)pipe[j]<=pipe[j-1];
 end
 assign rr[b*257+:257]=pipe[L-1];
end endgenerate
wire [1:0] pv,pf;wire [255:0] pd;
generate for(genvar p=0;p<2;p=p+1)begin:P
 wire [1023:0] rw;
 for(genvar q=0;q<4;q=q+1)begin:Q
 ot_hgi_sm_xload_cl2_bfqg bf(
 .clk(clk),.clk_n(clk),.clk_s(clk),.clk_ctrl(clk),
 .clk_m0(clk),.clk_m1(clk),.clk_m2(clk),.clk_m3(clk),.clk_m4(clk),.clk_m5(clk),.clk_m6(clk),.clk_m7(clk),
 .clk_l0(clk),.clk_l1(clk),.clk_l2(clk),.clk_l3(clk),.clk_l4(clk),.clk_l5(clk),.clk_l6(clk),.clk_l7(clk),
 .rst_n(rn),.c_d(cd),.wce(wce[q]),.mhi0(mhi),.mhi1(mhi),.mhi2(mhi),.mhi3(mhi),.mhi4(mhi),.mhi5(mhi),.mhi6(mhi),.mhi7(mhi),
 .mlo0(mlo),.mlo1(mlo),.mlo2(mlo),.mlo3(mlo),.mlo4(mlo),.mlo5(mlo),.mlo6(mlo),.mlo7(mlo),
 .wa(wa),.r_ce(rce),.r_a(ra),.rwq(rw[q*256+:256]));
 end
 wire en,last,done;wire [6:0] addr,grp;wire [2047:0] data;
 ot_hgi_sm_xload_xq_pegress #(.PMAX(8),.NR(32)) eg(
 .clk(clk),.clk_w(clk),.clk_s(clk),.clk_e(clk),.clk_c(clk),.rn(rn),.ed5(ed5),.ede(ede),
 .bq_v(bqv),.bq_last(bql),.bq_addr(bqa),.bq_b(bqb),.rwq(rw),.bq_d(2048'd0),
 .x_done(done),.xw_en(en),.xw_last(last),.xw_addr(addr),.xw_grp(grp),.xw_data(data));
 ot_hbm_sm_attn_pstore ps(.clk(clk),.rst_n(rst_n),.clear_v(clear_v),.xw_en(en),.xw_addr(addr),.xw_grp(grp),.xw_data(data),
 .read_v(read_v),.read_addr(read_addr),.p_v(pv[p]),.p_data(pd[p*128+:128]),.fault(pf[p]));
 always @(posedge clk)if(rst_n && en)begin
  beats[p]=beats[p]+1;
  if(first_xw<0)first_xw=cyc;
  last_xw=cyc;
  if(grp!=127 || !last || |data[2047:128] || data[127:0]!=={8{gold[addr]}})begin
   if(errors<5)$display("PVROW_MISMATCH pair%0d cyc%0d row%0d grp%0d data%h gold%h",p,cyc,addr,grp,data[127:0],gold[addr]);
   errors=errors+1;
  end
 end
end endgenerate
always @(posedge clk)if(rst_n)begin
 if(ctl.u_w.x_v && first_cmd<0)first_cmd=cyc;
 if(ctl.u_w.u_ctl.start && first_start<0)first_start=cyc;
 if(P[0].ps.wce && first_write<0)first_write=cyc;
 for(integer pp=0;pp<2;pp=pp+1)if(pv[pp])read_valid[pp]=read_valid[pp]+1;
 if(qvlo||qvhi||bqv)$fatal(1,"PVROW_INACTIVE_BOUNDARY");
 for(integer b=0;b<8;b=b+1)if(rq[b*17+16])begin reqs=reqs+1;if(first_rq<0)first_rq=cyc;end
end
initial begin
 if(!$value$plusargs("MUT=%d",mut))mut=0;
 for(integer i=0;i<262144;i=i+1)vm[i]=0;
 $readmemh("p_fp32.hex",probs);$readmemh("p_bf16.hex",gold);$readmemh("p_addr.hex",src);
 for(integer i=0;i<128;i=i+1)vm[src[i]]=probs[i];
 beats[0]=0;beats[1]=0;read_valid[0]=0;read_valid[1]=0;
 repeat(5)@(negedge clk);rst_n=1;repeat(20)@(negedge clk);
 clear_v=1;@(negedge clk);clear_v=0;
 for(integer i=0;i<128;i=i+1)begin
  cfg_v=1;cfg_addr=12'h800+i;
  cfg_data={116'd0,7'(i),2'd0,((mut==1)?2'd1:2'd2),32'd0,4'd1,21'd1,40'(src[i]^((mut==2)?1:0)),32'(64+i*256)};
  @(negedge clk);cfg_v=0;repeat(3)@(negedge clk);
 end
 repeat(8)@(negedge clk);desc_v=1;@(negedge clk);desc_v=0;repeat(8)@(negedge clk);
 if(!configured || fault)$fatal(1,"PVROW_CONFIG");
 launch_v=1;launch_edge=cyc;@(negedge clk);launch_v=0;
 repeat(33000)@(negedge clk);
 if(beats[0]!=128||beats[1]!=128||reqs!=1024||fault||active||pf!=0)begin
  $display("PVROW_COUNTS beats%0d/%0d reqs%0d fault%b active%b pf%b",beats[0],beats[1],reqs,fault,active,pf);errors=errors+1;
 end
 for(integer i=0;i<128;i=i+1)begin
  read_addr=7'(i);read_v=1;@(negedge clk);read_v=0;repeat(5)@(negedge clk);
  if(pd!=={16{gold[i]}})begin if(errors<5)$display("PVROW_READ row%0d actual%h gold%h",i,pd,gold[i]);errors=errors+1;end
 end
 if(read_valid[0]!=128||read_valid[1]!=128)errors=errors+1;
 $display("PVROW_BOUNDARY cmd%0d start%0d xw%0d write%0d last_xw%0d readvalid%0d/%0d",first_cmd,first_start,first_xw,first_write,last_xw,read_valid[0],read_valid[1]);
 $display("PVROW_TIMING launch%0d first_rq%0d first_xw%0d delta_rq%0d delta_xw%0d",launch_edge,first_rq,first_xw,first_rq-launch_edge,first_xw-launch_edge);
 if(errors||pf||fault) $display("PVROW FAIL errors%0d pstorefault%b ctlfault%b",errors,pf,fault);
 else $display("PVROW PASS rows128 pairs2 columns8 request1024 pstore_reads256");
 $finish;
end
endmodule
