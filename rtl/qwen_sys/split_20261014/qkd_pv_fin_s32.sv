`timescale 1ns/1ps
// Default-off SRAM successor of qkd_pv_fin_s. Same ports, arithmetic and
// command ages; regional reset leaf releases after three edges. Shipping
// adds two plain reset landing edges; first legal start capture is E6.
// Four 32x128 SRAMs replace the runtime-indexed 16kb sum flop bank.
// Read at MUL_AGE-2; kept operand capture at MUL_AGE-1; both collision
// edges forward. MUT4/5 suppress the early/final forwarding respectively.
// Source/correctness/native status: results/rtl/kv_pvfin_sram_1020/README.md
module qkd_pv_fin_s32 #(
 parameter integer ADD_LAT=7,
 parameter integer MUL_LAT=6,
 parameter integer SKEW=2,
 parameter integer MUT=0
)(
 input wire ck,rst_n,
 input wire start,input wire [15:0] epoch,input wire [47:0] cal,
 input wire p0_valid,input wire [4:0] p0_beat,input wire [15:0] p0_epoch,input wire [511:0] p0_data,
 input wire p1_valid,input wire [4:0] p1_beat,input wire [15:0] p1_epoch,input wire [511:0] p1_data,
 input wire rz_valid,input wire [15:0] rz_epoch,input wire [127:0] rz,
 output reg out_valid,output reg [4:0] out_beat,output reg [15:0] out_epoch,output reg [511:0] out_data,
 output reg fault
);
 // Bounded reset farms: 16 lanes x (2 add + 21 multiply) plus control leaves.
 wire [255:0] rr0,rr1;
 ot_rst_relay_bounded32 #(.REGIONS(256)) u_rr0(.clk(ck),.rst_n_in(rst_n),.rst_n(rr0));
 ot_rst_relay_bounded32 #(.REGIONS(256)) u_rr1(.clk(ck),.rst_n_in(rst_n),.rst_n(rr1));
 wire [511:0] rr;
 assign rr[239:0]=rr0[239:0];assign rr[479:240]=rr1[239:0];
 assign rr[495:480]=rr0[255:240];assign rr[511:496]=rr1[255:240];
 wire rc=rr[448];
 // pin registers (control); the data pins land in tap 0 of the operand lines
 reg start_q,p0v_q,p1v_q,rzv_q;reg [15:0] epoch_q,p0e_q,p1e_q,rze_q;(* keep="true",dont_touch="true" *) reg [47:0] cal_q;reg [4:0] p0b_q,p1b_q;reg [127:0] rz_q;
 always @(posedge ck or negedge rc)
  if(!rc)begin start_q<=0;p0v_q<=0;p1v_q<=0;rzv_q<=0;end
  else begin start_q<=start;p0v_q<=p0_valid;p1v_q<=p1_valid;rzv_q<=rz_valid;end
 always @(posedge ck)begin epoch_q<=epoch;cal_q<=cal;p0b_q<=p0_beat;p1b_q<=p1_beat;p0e_q<=p0_epoch;p1e_q<=p1_epoch;
  rze_q<=rz_epoch;rz_q<=rz;end
 reg active;reg [15:0] age,ep,P0,P1,RA,MUL_AGE;
 wire [15:0] LASTP=(P0>P1)?P0:P1;
 wire [15:0] D0=LASTP-P0,D1=LASTP-P1;
 // Command-time dates remove the runtime max-word distribution.
 (* keep="true",dont_touch="true" *) reg [15:0] ADD_AGE,SUM_AGE;
 (* keep="true",dont_touch="true" *) reg [15:0] PRODUCT_AGE,PRODUCT_AGE_PRED;
 (* keep="true",dont_touch="true" *) reg [15:0] age_operand,age_header,age_product,age_sum,age_mulissue;
 (* keep="true",dont_touch="true" *) reg [15:0] mul_operand,mul_header;
 wire [15:0] no=age_operand+16'd1,nh=age_header+16'd1,np=age_product+16'd1,ns=age_sum+16'd1,ni=age_mulissue+16'd1;
 wire [15:0] lane_active_vec;
 // Independent counter feedback prevents main-age input redistribution.
 // Kept start/active images are same-phase original controls, not new stages.
 always @(posedge ck or negedge rr[480])if(!rr[480])age_operand<=0;
  else if(command_accept[0])age_operand<=0;
  else if(!command_start[0]&&lane_active_vec[0]&&!fault)age_operand<=age_operand+16'd1;
 always @(posedge ck or negedge rr[481])if(!rr[481])age_header<=0;
  else if(command_accept[1])age_header<=0;
  else if(!command_start[1]&&lane_active_vec[1]&&!fault)age_header<=age_header+16'd1;
 always @(posedge ck or negedge rr[482])if(!rr[482])age_product<=0;
  else if(command_accept[6])age_product<=0;
  else if(!command_start[6]&&lane_active_vec[2]&&!fault)age_product<=age_product+16'd1;
 always @(posedge ck or negedge rr[487])if(!rr[487])age_sum<=0;
  else if(command_accept[7])age_sum<=0;
  else if(!command_start[7]&&lane_active_vec[3]&&!fault)age_sum<=age_sum+16'd1;
 // Separate issue counter/date from SRAM-prefetch address arithmetic.
 always @(posedge ck or negedge rr[490])if(!rr[490])age_mulissue<=0;
  else if(command_start[8])begin
   if(!lane_active_vec[4]&&!cal_bad)age_mulissue<=0;
  end else if(lane_active_vec[4]&&!fault)age_mulissue<=age_mulissue+16'd1;
 // Each shared acceptance controls original8 +two duplicated8 payload bits.
 generate for(genvar mh=0;mh<2;mh=mh+1)begin:g_mul_date_capture
  always @(posedge ck or negedge rr[483])if(!rr[483])mul_operand[8*mh+:8]<=8'hff;
   else if(command_accept[8+mh])mul_operand[8*mh+:8]<=command_mulage[8+mh][8*mh+:8];
  always @(posedge ck or negedge rr[484])if(!rr[484])mul_header[8*mh+:8]<=8'hff;
   else if(command_accept[8+mh])mul_header[8*mh+:8]<=command_mulage[8+mh][8*mh+:8];
 end endgenerate
 wire [15:0] n=age+16'd1;                                  // the edge that ends this cycle
 function automatic win(input [15:0] x,input [15:0] lo);win=(x>=lo)&&(x<lo+16'd32);endfunction
 wire p0_slot=active&&win(n,P0),p1_slot=active&&win(n,P1),r_slot=active&&n==RA;
 wire add_slot=active&&win(ns,ADD_AGE),sum_slot=active&&win(ns,SUM_AGE);
 wire mul_slot=active&&win(ni,MUL_AGE),product_slot=active&&win(np,PRODUCT_AGE);
 wire [4:0] b_p0=5'(n-P0),b_p1=5'(n-P1),b_prod=5'(np-PRODUCT_AGE);
 // calendar of a new command (checked on the start edge)
 wire [15:0] c0=cal_q[15:0],c1=cal_q[31:16],cr=cal_q[47:32];
 wire [15:0] c_lastp=(c0>c1)?c0:c1;
 wire [15:0] c_last=(MUT==3||c_lastp>cr)?c_lastp:cr;          // max(P0, P1, R)
 wire [15:0] c_skew=(c0>c1)?(c0-c1):(c1-c0);
 // R9 (KV-PARAMS5): mux-free command check, exactly equal to
 //   (c0<1)||(c1<1)||(r<1)||(|c0-c1|>SKEW)||(max(c0,c1[,r unless MUT3])+64+ADD_LAT+MUL_LAT>0xffff):
 // max(..)>T == any operand >T and |a-b|>S == a>b+S || b>a+S, so no shared compare drives a 16-bit
 // max/abs mux (R8 native census: the command_cal[3] compare node drove 37 loads).
 localparam [16:0] OVF_T=17'h0ffff-17'd64-17'(ADD_LAT+MUL_LAT);
 function automatic cal_bad_f(input [15:0] a,input [15:0] b,input [15:0] r);
  cal_bad_f=(a<16'd1)||(b<16'd1)||(r<16'd1)||({1'b0,a}>{1'b0,b}+17'(SKEW))||({1'b0,b}>{1'b0,a}+17'(SKEW))||
            ({1'b0,a}>OVF_T)||({1'b0,b}>OVF_T)||((MUT!=3)&&({1'b0,r}>OVF_T));
 endfunction
 wire cal_bad=cal_bad_f(c0,c1,cr);
 // operand tap lines: tap 0 = the pin register (= this cycle's registered input), tap k = the beat k edges older
 reg [511:0] t0[0:SKEW+1],t1[0:SKEW+1];
 integer k;
 always @(posedge ck)begin
  t0[0]<=p0_data;t1[0]<=p1_data;
  for(k=1;k<=SKEW+1;k=k+1)begin t0[k]<=t0[k-1];t1[k]<=t1[k-1];end
 end
 wire [15:0] D0m=(MUT==2&&D0<SKEW)?D0+16'd1:D0;
 wire [511:0] opa,opb;
 (* keep="true",dont_touch="true" *) reg [15:0] start_lane;
 // R10 (KV-PARAMS5): the operand-select decodes are lane-invariant, so one shared decode node drove all
 // 64 select flops (R9 census). Each group of four lanes now decodes its own kept copy of cal[31:0]
 // (captured on the same edge as cal_q), mux-free: max(a,b)-a==0 <=> a>=b; ==j (j>=1) <=> b==a+j.
 (* keep="true",dont_touch="true" *) reg [31:0] cal_sel_q[0:3];
 generate for(genvar sg=0;sg<4;sg=sg+1)begin:g_cal_sel
  always @(posedge ck)cal_sel_q[sg]<=cal[31:0];
 end endgenerate
 function automatic sel_eq(input [15:0] a,input [15:0] b,input integer j);   // (max(a,b)-a)==j
  sel_eq=(j==0)?(a>=b):({1'b0,b}=={1'b0,a}+17'(j));
 endfunction
 genvar sl;
 generate for(sl=0;sl<16;sl=sl+1)begin:g_start_lane
  always @(posedge ck)start_lane[sl]<=start;
  (* keep="true",dont_touch="true" *) reg [SKEW:0] select0[0:1],select1[0:1];
  wire [15:0] g0=cal_sel_q[sl/4][15:0],g1=cal_sel_q[sl/4][31:16];
  wire [15:0] c_d0=((g0>g1)?g0:g1)-g0;
  wire [15:0] c_d0m=(MUT==2&&c_d0<SKEW)?c_d0+1:c_d0;
  for(genvar part=0;part<2;part=part+1)begin:g_select_part
   for(genvar jt=0;jt<=SKEW;jt=jt+1)begin:g_select
    wire s0=(MUT==2)?(c_d0m==jt):sel_eq(g0,g1,jt);
    always @(posedge ck)if(start_lane[sl])begin
     select0[part][jt]<=s0;select1[part][jt]<=sel_eq(g1,g0,jt);
    end
   end
  end
  reg [31:0] a_sel,b_sel;
  integer jt;
  always @* begin
   a_sel=0;b_sel=0;
   for(jt=0;jt<=SKEW;jt=jt+1)begin
    for(integer pt=0;pt<2;pt=pt+1)begin
     a_sel[16*pt+:16]=a_sel[16*pt+:16]|(t0[jt+1][32*sl+16*pt+:16]&{16{select0[pt][jt]}});
     b_sel[16*pt+:16]=b_sel[16*pt+:16]|(t1[jt+1][32*sl+16*pt+:16]&{16{select1[pt][jt]}});
    end
   end
  end
  assign opa[32*sl+:32]=a_sel;assign opb[32*sl+:32]=b_sel;
 end endgenerate
 reg [4:0] wptr,rptr;reg [127:0] rzr;   // sums of this command, beat order
 // SRAM prefetch at multiply-2, then three independent same-edge operand
 // captures at multiply-1. Forward writes at either edge (the earliest
 // legal multiply is SUM_AGE+1); no read-before-write payload is observed.
 wire read_slot=active&&win(no,mul_operand-16'd2);
 wire capture_slot=active&&win(no,mul_operand-16'd1);
 wire [4:0] read_addr=5'(no-(mul_operand-16'd2));
 wire [4:0] capture_addr=5'(no-(mul_operand-16'd1));
 wire [511:0] ram_sum;
 reg [511:0] forward_sum;
 (* keep="true",dont_touch="true" *) reg [31:0] early_hit,direct_hit;
 always @(posedge ck)forward_sum<=sum;
 genvar oc,ol;
 (* keep="true",dont_touch="true" *) reg [511:0] operand_sum[0:2];
 generate for(ol=0;ol<32;ol=ol+1)begin:g_operand_lane
  always @(posedge ck)begin
   early_hit[ol]<=read_slot&&sum_slot&&(read_addr==wptr);
   direct_hit[ol]<=active&&win(no+16'd1,SUM_AGE)&&win(no+16'd1,mul_operand-16'd1)&&(SUM_AGE==mul_operand-16'd1);
  end
  wire [15:0] read_sum=(early_hit[ol]&&MUT!=4)?forward_sum[16*ol+:16]:ram_sum[16*ol+:16];
  wire [15:0] capture_sum=(direct_hit[ol]&&MUT!=5)?sum[16*ol+:16]:read_sum;
  for(oc=0;oc<3;oc=oc+1)begin:g_operand_copy
   always @(posedge ck)operand_sum[oc][16*ol+:16]<=capture_sum;
  end
 end endgenerate
 wire [511:0] saved_sum=operand_sum[0];
 genvar bank;
 generate for(bank=0;bank<4;bank=bank+1)begin:g_sram
  ot_sram_1r1w_32x128_m1_p192_pvfin u_mem(.clk(ck),.r_ce_in(read_slot),.r_addr_in(read_addr),.rd_out(ram_sum[128*bank+:128]),
   .w_ce_in(sum_slot),.w_addr_in(wptr),.wd_in(sum[128*bank+:128]),.w_mask_in({128{1'b1}}));
 end endgenerate
 wire [2:0] hb=(MUT==1)?3'(({1'b0,rptr}+6'd1)>>3):3'(rptr>>3);
 wire [31:0] rzh=(hb==3'd0)?rzr[31:0]:(hb==3'd1)?rzr[63:32]:(hb==3'd2)?rzr[95:64]:rzr[127:96];
 // Predict the head used on the following multiply edge; each lane has
 // three kept copies so both live-operand normalisers have bounded drivers.
 (* keep="true",dont_touch="true" *) reg [31:0] reciprocal_lane[0:15][0:2];
 wire [4:0] header_rptr=5'(nh+16'd2-mul_header);
 wire [2:0] header_hb=(MUT==1)?3'(({1'b0,header_rptr}+6'd1)>>3):3'(header_rptr>>3);
 (* keep="true",dont_touch="true" *) reg [3:0] head_select[0:15];
 genvar rl,rx;
 generate for(rl=0;rl<16;rl=rl+1)begin:g_recip_lane
  always @(posedge ck)begin
   head_select[rl][0]<=header_hb==0;head_select[rl][1]<=header_hb==1;
   head_select[rl][2]<=header_hb==2;head_select[rl][3]<=header_hb>=3;
  end
  wire [31:0] selected=(rzr[31:0]&{32{head_select[rl][0]}})|(rzr[63:32]&{32{head_select[rl][1]}})|
   (rzr[95:64]&{32{head_select[rl][2]}})|(rzr[127:96]&{32{head_select[rl][3]}});
  for(rx=0;rx<3;rx=rx+1)begin:g_copy
   always @(posedge ck)reciprocal_lane[rl][rx]<=selected;
  end
 end endgenerate
 wire [511:0] sum,product;wire [15:0] av,mv;wire [31:0] ae,me;
 genvar l;
 generate for(l=0;l<16;l=l+1)begin:g_lane
  (* keep="true",dont_touch="true" *) reg add_land,mul_land,lane_active;
  always @(posedge ck)begin
   add_land<=active&&!fault&&win(ns+16'd1,ADD_AGE);
   mul_land<=active&&!fault&&win(ni+16'd1,MUL_AGE);
  end
  assign lane_active_vec[l]=lane_active;
  always @(posedge ck or negedge rr[462+l])if(!rr[462+l])lane_active<=0;else lane_active<=active_d;
  ot_hdc_fp32_add_lat_ncr #(.LAT(ADD_LAT)) u_add(.clk(ck),.rst_n(rr[28*l]),.rst_y(rr[28*l+1]),.rst_y2(2'b11),.y2(),.valid_in(add_land&&lane_active),
   .a(opa[32*l+:32]),.b(opb[32*l+:32]),.y(sum[32*l+:32]),.err(ae[2*l+:2]),.valid_out(av[l]));
  ot_hdc_fp32_mul_lat_pvfin #(.LAT(MUL_LAT)) u_mul(.clk(ck),.rst_v(rr[28*l+2+:26]),.a_nrm({operand_sum[2][32*l+:32],operand_sum[1][32*l+:32]}),.valid_in(mul_land&&lane_active),
   .a(saved_sum[32*l+:32]),.b(reciprocal_lane[l][0]),.b_nrm({reciprocal_lane[l][2],reciprocal_lane[l][1]}),.y(product[32*l+:32]),.err(me[2*l+:2]),.valid_out(mv[l]));
 end endgenerate
 wire bad=(p0v_q!=p0_slot)||(p1v_q!=p1_slot)||(rzv_q!=r_slot)||
          (p0_slot&&(p0b_q!=b_p0||p0e_q!=ep))||(p1_slot&&(p1b_q!=b_p1||p1e_q!=ep))||(r_slot&&rze_q!=ep)||
          (av!={16{sum_slot}})||(mv!={16{product_slot}})||(sum_slot&&|ae)||(product_slot&&|me);
 // Independent command pin images bound the 80-bit command-capture
 // enable. Each local acceptance result controls only eight payload flops.
 (* keep="true",dont_touch="true" *) reg [47:0] command_cal[0:9];
 (* keep="true",dont_touch="true" *) reg [9:0] command_start,command_active;
 wire [9:0] command_accept;
 // R14 (KV-PARAMS6): R13 native census FAIL 48/4 = command_accept[2..5] each enabled 24 payload flops (P0/P1 8 +
 // ADD/SUM date 8 + product date 8, 2 mux contacts per bit). Each of the three 8-bit payload groups now has its own
 // acceptance node: P0/P1 keep command_start[cg]; the dates use same-phase kept start_lane[8..15] images (start_lane[k]
 // <= start on the same edge as command_start[cg], so every acceptance value is unchanged: no new stage, no new edge).
 wire [5:2] command_accept_d,command_accept_r;
 wire [15:0] command_mulage[0:9];
 (* keep="true",dont_touch="true" *) reg [47:0] command_payload[0:1];
 generate for(genvar pc=0;pc<2;pc=pc+1)begin:g_command_payload
  always @(posedge ck)command_payload[pc]<=cal;
 end endgenerate
 generate for(genvar cg=0;cg<10;cg=cg+1)begin:g_command
  always @(posedge ck)begin
   command_cal[cg]<=cal;command_start[cg]<=start;command_active[cg]<=active_d;
  end
  wire [15:0] x0=command_cal[cg][15:0],x1=command_cal[cg][31:16],xr=command_cal[cg][47:32];
  wire xb=cal_bad_f(x0,x1,xr);
  assign command_accept[cg]=command_start[cg]&&!command_active[cg]&&!xb;
  if(cg>=2&&cg<=5)begin:g_accept_split
   assign command_accept_d[cg]=start_lane[8+2*(cg-2)]&&!command_active[cg]&&!xb;
   assign command_accept_r[cg]=start_lane[9+2*(cg-2)]&&!command_active[cg]&&!xb;
  end
  if(cg>=8)begin:g_value
   (* keep_hierarchy="yes" *) ot_qkd_pvfin_calendar_value #(.C(ADD_LAT+2),.IGNORE_R(MUT==3)) u_value(
    .p0(command_payload[cg-8][15:0]),.p1(command_payload[cg-8][31:16]),.r(command_payload[cg-8][47:32]),
    .y(command_mulage[cg]));
  end else begin:g_no_value
   assign command_mulage[cg]=16'd0;
  end
 end endgenerate
 wire [15:0] date_add,date_sum;
 (* keep="true",dont_touch="true" *) reg [31:0] date_cal[0:1];
 generate for(genvar dc=0;dc<2;dc=dc+1)begin:g_date_cal
  always @(posedge ck)date_cal[dc]<=cal[31:0];
 end endgenerate
 (* keep_hierarchy="yes" *) ot_qkd_pvfin_calendar_value #(.C(1),.IGNORE_R(1)) u_add_date(
  .p0(date_cal[0][15:0]),.p1(date_cal[0][31:16]),.r(16'd0),.y(date_add));
 (* keep_hierarchy="yes" *) ot_qkd_pvfin_calendar_value #(.C(ADD_LAT+1),.IGNORE_R(1)) u_sum_date(
  .p0(date_cal[1][15:0]),.p1(date_cal[1][31:16]),.r(16'd0),.y(date_sum));
 generate for(genvar dh=0;dh<2;dh=dh+1)begin:g_date_capture
  always @(posedge ck or negedge rr[485])if(!rr[485])ADD_AGE[8*dh+:8]<=0;
   else if(command_accept_d[2+dh])ADD_AGE[8*dh+:8]<=date_add[8*dh+:8];
  always @(posedge ck or negedge rr[486])if(!rr[486])SUM_AGE[8*dh+:8]<=8'(ADD_LAT>>(8*dh));
   else if(command_accept_d[4+dh])SUM_AGE[8*dh+:8]<=date_sum[8*dh+:8];
 end endgenerate
 // Distinct observation/prediction dates avoid carry redistribution
 // through one global live MUL_AGE register. Original unsummed selection.
 (* keep="true",dont_touch="true" *) reg [47:0] product_cal[0:1];
 wire [15:0] product_date[0:1];
 generate for(genvar pd=0;pd<2;pd=pd+1)begin:g_product_date
  always @(posedge ck)product_cal[pd]<=cal;
  (* keep_hierarchy="yes" *) ot_qkd_pvfin_calendar_value #(.C(ADD_LAT+MUL_LAT+2),.IGNORE_R(MUT==3)) u_value(
   .p0(product_cal[pd][15:0]),.p1(product_cal[pd][31:16]),.r(product_cal[pd][47:32]),.y(product_date[pd]));
 end
 for(genvar ph=0;ph<2;ph=ph+1)begin:g_product_date_capture
  always @(posedge ck or negedge rr[488])if(!rr[488])PRODUCT_AGE_PRED[8*ph+:8]<=8'((MUL_LAT-1)>>(8*ph));
   else if(command_accept_r[2+ph])PRODUCT_AGE_PRED[8*ph+:8]<=product_date[0][8*ph+:8];
  always @(posedge ck or negedge rr[489])if(!rr[489])PRODUCT_AGE[8*ph+:8]<=8'((MUL_LAT-1)>>(8*ph));
   else if(command_accept_r[4+ph])PRODUCT_AGE[8*ph+:8]<=product_date[1][8*ph+:8];
 end endgenerate
 reg active_d;
 reg [15:0] age_d;
 reg [15:0] ep_d;
 reg [15:0] P0_d;
 reg [15:0] P1_d;
 reg [15:0] RA_d;
 reg [15:0] MUL_AGE_d;
 reg fault_d;
 reg [4:0] wptr_d;
 reg [4:0] rptr_d;
 always @* begin
  active_d=active;
  age_d=age;
  ep_d=ep;
  P0_d=P0;
  P1_d=P1;
  RA_d=RA;
  MUL_AGE_d=MUL_AGE;
  fault_d=fault;
  wptr_d=wptr;
  rptr_d=rptr;
   if(start_q)begin
    if(active||cal_bad)begin fault_d=1;active_d=0;end
    else begin active_d=1;age_d=0;ep_d=epoch_q;P0_d=c0;P1_d=c1;RA_d=cr;MUL_AGE_d=c_last+16'(ADD_LAT+2);wptr_d=0;rptr_d=0;end
   end else if(active&&!fault)begin
    age_d=n;
    if(bad)begin fault_d=1;active_d=0;end
    else begin
     if(sum_slot)wptr_d=wptr+5'd1;
     if(mul_slot)rptr_d=rptr+5'd1;
     if(np==PRODUCT_AGE+16'd31)active_d=0;
    end
   end else if(!active&&(p0v_q||p1v_q||rzv_q))fault_d=1;
 end
 always @(posedge ck or negedge rr[449]) if(!rr[449]) active<=0;else active<=active_d;
 always @(posedge ck or negedge rr[450]) if(!rr[450]) age<=0;else age<=age_d;
 always @(posedge ck or negedge rr[451]) if(!rr[451]) ep[0+:8]<=8'd0;else if(command_accept[0]) ep[0+:8]<=epoch_q[0+:8];
 always @(posedge ck or negedge rr[451]) if(!rr[451]) ep[8+:8]<=8'd0;else if(command_accept[1]) ep[8+:8]<=epoch_q[8+:8];
 always @(posedge ck or negedge rr[452]) if(!rr[452]) P0[0+:8]<=8'hff;else if(command_accept[2]) P0[0+:8]<=command_cal[2][0+:8];
 always @(posedge ck or negedge rr[452]) if(!rr[452]) P0[8+:8]<=8'hff;else if(command_accept[3]) P0[8+:8]<=command_cal[3][8+:8];
 always @(posedge ck or negedge rr[453]) if(!rr[453]) P1[0+:8]<=8'hff;else if(command_accept[4]) P1[0+:8]<=command_cal[4][16+:8];
 always @(posedge ck or negedge rr[453]) if(!rr[453]) P1[8+:8]<=8'hff;else if(command_accept[5]) P1[8+:8]<=command_cal[5][24+:8];
 always @(posedge ck or negedge rr[454]) if(!rr[454]) RA[0+:8]<=8'hff;else if(command_accept[6]) RA[0+:8]<=command_cal[6][32+:8];
 always @(posedge ck or negedge rr[454]) if(!rr[454]) RA[8+:8]<=8'hff;else if(command_accept[7]) RA[8+:8]<=command_cal[7][40+:8];
 always @(posedge ck or negedge rr[455]) if(!rr[455]) MUL_AGE[0+:8]<=8'hff;else if(command_accept[8]) MUL_AGE[0+:8]<=command_mulage[8][0+:8];
 always @(posedge ck or negedge rr[455]) if(!rr[455]) MUL_AGE[8+:8]<=8'hff;else if(command_accept[9]) MUL_AGE[8+:8]<=command_mulage[9][8+:8];
 always @(posedge ck or negedge rr[456]) if(!rr[456]) fault<=0;else fault<=fault_d;
 // R9 (KV-PARAMS5): the output update (valid / beat / epoch) uses three kept copies of `active`
 // (same D, reset leaves of the same farm -> equal to `active` after reset), so no single take node
 // drives all 22 output enables (R8 native census: 34 loads). Same edge, same values as the R8 else-if:
 // take = !start_q && active && !fault && !bad && product_slot.
 (* keep="true",dont_touch="true" *) reg [2:0] out_active;
 wire [2:0] out_take;
 generate for(genvar oa=0;oa<3;oa=oa+1)begin:g_out_active
  always @(posedge ck or negedge rr[457+oa]) if(!rr[457+oa]) out_active[oa]<=0;else out_active[oa]<=active_d;
  assign out_take[oa]=out_active[oa]&&!start_q&&!fault&&!bad&&win(np,PRODUCT_AGE);
 end endgenerate
 always @(posedge ck or negedge rr[457]) if(!rr[457]) out_valid<=0;else out_valid<=out_take[0];
 always @(posedge ck or negedge rr[458]) if(!rr[458]) out_beat<=0;else if(out_take[1]) out_beat<=b_prod;
 always @(posedge ck or negedge rr[459]) if(!rr[459]) out_epoch<=0;else if(out_take[2]) out_epoch<=ep;
 always @(posedge ck or negedge rr[460]) if(!rr[460]) wptr<=0;else wptr<=wptr_d;
 always @(posedge ck or negedge rr[461]) if(!rr[461]) rptr<=0;else rptr<=rptr_d;
 (* keep="true",dont_touch="true" *) reg [31:0] product_land;
 (* keep="true",dont_touch="true" *) reg [7:0] reciprocal_land;
 generate for(genvar oi=0;oi<32;oi=oi+1)begin:g_output_lane
  always @(posedge ck)product_land[oi]<=active&&win(np+16'd1,PRODUCT_AGE_PRED);
  always @(posedge ck)if(product_land[oi])out_data[16*oi+:16]<=product[16*oi+:16];
 end
 for(genvar ri=0;ri<8;ri=ri+1)begin:g_rz_capture
  always @(posedge ck)reciprocal_land[ri]<=start_q?(!active&&!cal_bad&&cr==16'd1):(active&&(nh+16'd1==RA));
  always @(posedge ck)if(reciprocal_land[ri])rzr[16*ri+:16]<=rz_q[16*ri+:16];
 end endgenerate
endmodule
