`timescale 1ns/1ps
// KV-PARAMS4 10-20 (K.STA.PARAMS): structurally safe native-32 successor of ot_qwen_tp8_pv_join_t #(J_LAT 7, RESET_PIN 1),
// default-off (new master; ot_qwen_tp8_pv_join_t and ot_qwen_tp8_pv_join_cold_t untouched).  Same ports and token timing.
//  - reset: ot_rst_relay_bounded32 #(101) (async assertion, release 3 edges after rst_n; legacy RESET_PIN 1 released 1
//    edge after) -> +2 boot reset-release edges for the static boot calendar, 0 token edges.  Leaves <= 32 endpoints:
//    48 data words (xr / yr / y, cleared like COLD_INIT=1: no unreset datapath is captured at the reset edge), 16 x 3 lane
//    leaves (operand-select copies / adder control / adder y), 4 group leaves (write-enable + control copies), 1 tile
//    control leaf.
//  - adders: ot_hdc_fp32_add_lat_ncr (native-32 kept-copy LAT-7 adder, rtl/hdc/ot_hdc_fp32_qkh_ncr.sv).
//  - operand select: decoded one edge ahead (as before) but registered ONE-HOT per lane, per operand, per 16-bit half
//    (each copy bit drives 16 AND legs; the 3-bit js code drove 64 mux bits + the issue).
//  - write enables of xr / yr / y: next-state decode registered per 16-bit half-word (each copy drives 16 enables; the
//    shared jrun && jage == k term drove 512).
//  - t_r (4096 b) are the registered input pins (checklist item 1), not runtime-indexed storage (item 5 n/a).
module ot_qwen_tp8_pv_join_s32_t #(parameter integer MUT=0, J_LAT=7, RESET_PIN=1)(
 input wire clk,rst_n,input wire[1023:0] ts0,ts1,ts2,ts3,
 input wire join_go,input wire[7:0] sf,
 output reg[511:0] y,output reg y_valid,output reg fault
);
 generate if(J_LAT!=7 || RESET_PIN!=1)begin:g_bad_shape ot_qwen_tp8_pv_join_s32_t_requires_7_1 u_trap(); end endgenerate
 localparam integer NR=101;
 wire[NR-1:0] rr;
 ot_rst_relay_bounded32 #(.REGIONS(NR)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 wire[47:0] data_rst_n=rr[47:0];        // xr word d: rr[d]; yr: rr[16+d]; y: rr[32+d]
 wire[15:0] sel_rst_n=rr[63:48], add_rst_n=rr[79:64], addy_rst_n=rr[95:80];
 wire[3:0]  we_rst_n=rr[99:96];
 wire       ctl_rst_n=rr[100];
 wire[4095:0] ts={ts3,ts2,ts1,ts0};
 localparam integer J_OUT=3*J_LAT+3;
 reg[4095:0] t_r;reg go_r;reg[7:0] sf_r;
 always @(posedge clk)t_r<=ts;
 always @(posedge clk or negedge ctl_rst_n)if(!ctl_rst_n)begin go_r<=0;sf_r<=0;end else begin go_r<=join_go;sf_r<=sf;end
 wire[511:0] tb[0:7];
 genvar g,h;
 generate for(g=0;g<8;g=g+1)begin:g_t assign tb[g]=t_r[512*g+:512]; end endgenerate
 reg jrun;reg[4:0] jage;reg[511:0] xr,yr;
 wire[511:0] jy;wire[15:0] jv;wire[31:0] jerr;
 // Control copies: group k (lanes 4k..4k+3, half-words 8k..8k+7) runs its own kept copy of (go_r, jrun, jage), updated
 // exactly like the master below, and decodes its own next-state select / write enables (a shared decode drove 64 / 32
 // flop D pins).  Copies sit on we_rst_n[k] (24 + 7 endpoints).
 wire[4*3-1:0] gsel; wire[4*6-1:0] gsoh; wire[3:0] gwx,gwy,gwo;
 generate for(g=0;g<4;g=g+1)begin:g_ctl
  (* keep="true",dont_touch="true" *) reg gc,rc; (* keep="true",dont_touch="true" *) reg[4:0] ac;
  always @(posedge clk or negedge we_rst_n[g])begin
   if(!we_rst_n[g])begin gc<=0;rc<=0;ac<=0;end
   else begin
    gc<=join_go;
    if(gc)begin rc<=1;ac<=0;end
    else if(rc)begin ac<=ac+1'b1;if(ac==5'(J_OUT))rc<=0;end
   end
  end
  wire nrun=gc?1'b1:(rc&&ac!=5'(J_OUT));
  wire[4:0] nage=gc?5'd0:(rc?ac+5'd1:ac);
  reg[2:0] nsel;
  always @*begin
   nsel=3'd0;
   if(nrun)case(nage)
    5'd0:nsel=3'd1;
    5'd1:nsel=3'd2;
    5'd2:nsel=3'd3;
    5'd3:nsel=3'd4;
    5'(J_LAT+1):nsel=3'd5;
    5'(J_LAT+3):nsel=3'd5;
    5'(2*J_LAT+3):nsel=3'd6;
    default:;
   endcase
  end
  assign gsel[3*g+:3]=nsel;
  for(h=1;h<=6;h=h+1)begin:g_oh assign gsoh[6*g+h-1]=(nsel==3'(h)); end
  assign gwx[g]=nrun&&(nage==5'(J_LAT)||nage==5'(J_LAT+2));
  assign gwy[g]=nrun&&(nage==5'(2*J_LAT+1));
  assign gwo[g]=nrun&&(nage==5'(J_OUT));
 end endgenerate
 (* keep="true",dont_touch="true" *) reg[31:0] we_x,we_y,we_o;   // one per 16-bit half-word
 generate for(g=0;g<4;g=g+1)begin:g_we
  always @(posedge clk or negedge we_rst_n[g])
   if(!we_rst_n[g])begin we_x[8*g+:8]<=0;we_y[8*g+:8]<=0;we_o[8*g+:8]<=0;end
   else begin we_x[8*g+:8]<={8{gwx[g]}};we_y[8*g+:8]<={8{gwy[g]}};
`ifdef PVJ32_MUT3
    we_o[8*g+:8]<={8{gwx[g]}};                    // bench mutant 3 (must FAIL): the output word written at the xr slot
`else
    we_o[8*g+:8]<={8{gwo[g]}};
`endif
   end
 end endgenerate
 generate for(g=0;g<16;g=g+1)begin:g_join
  (* keep="true",dont_touch="true" *) reg[6:1] sa0,sa1,sb0,sb1;    // one-hot select copies: operand a/b, half 0/1
  (* keep="true",dont_touch="true" *) reg iss;
  always @(posedge clk or negedge sel_rst_n[g])
   if(!sel_rst_n[g])begin sa0<=0;sa1<=0;sb0<=0;sb1<=0;iss<=0;end
   else begin sa0<=gsoh[6*(g/4)+:6];sa1<=gsoh[6*(g/4)+:6];sb0<=gsoh[6*(g/4)+:6];sb1<=gsoh[6*(g/4)+:6];iss<=(gsel[3*(g/4)+:3]!=3'd0);end
  wire[31:0] la,lb;
  for(h=0;h<2;h=h+1)begin:g_h
   wire[6:1] sa=h?sa1:sa0, sb=h?sb1:sb0;
   localparam integer B=32*g+16*h;
   assign la[16*h+:16]=({16{sa[1]}}&tb[0][B+:16])|({16{sa[2]}}&((MUT==1)?tb[1][B+:16]:tb[2][B+:16]))|
                       ({16{sa[3]}}&tb[4][B+:16])|({16{sa[4]}}&tb[6][B+:16])|({16{sa[5]}}&xr[B+:16])|({16{sa[6]}}&yr[B+:16]);
   assign lb[16*h+:16]=({16{sb[1]}}&((MUT==1)?tb[2][B+:16]:tb[1][B+:16]))|({16{sb[2]}}&tb[3][B+:16])|
                       ({16{sb[3]}}&tb[5][B+:16])|({16{sb[4]}}&tb[7][B+:16])|({16{sb[5]|sb[6]}}&jy[B+:16]);
  end
  (* keep_hierarchy *) ot_hdc_fp32_add_lat_ncr #(.LAT(J_LAT)) u_add(.clk(clk),.rst_n(add_rst_n[g]),.rst_y(addy_rst_n[g]),
   .valid_in(iss),.a(la),.b(lb),.y(jy[32*g+:32]),.err(jerr[2*g+:2]),.valid_out(jv[g]));
  for(h=0;h<2;h=h+1)begin:g_w
   localparam integer B=32*g+16*h;
   always @(posedge clk or negedge data_rst_n[g])if(!data_rst_n[g])xr[B+:16]<=0;else if(we_x[2*g+h])xr[B+:16]<=jy[B+:16];
   if(MUT==2)begin:g_no_yr_clear
    always @(posedge clk)if(we_y[2*g+h])yr[B+:16]<=jy[B+:16];     // negative control: unreset yr (the base CEX defect)
   end else begin:g_yr
    always @(posedge clk or negedge data_rst_n[16+g])if(!data_rst_n[16+g])yr[B+:16]<=0;else if(we_y[2*g+h])yr[B+:16]<=jy[B+:16];
   end
   always @(posedge clk or negedge data_rst_n[32+g])if(!data_rst_n[32+g])y[B+:16]<=0;else if(we_o[2*g+h])y[B+:16]<=jy[B+:16];
  end
 end endgenerate
 wire jexp=jrun&&(jage==J_LAT||jage==J_LAT+1||jage==J_LAT+2||jage==J_LAT+3||jage==2*J_LAT+1||jage==2*J_LAT+3||jage==J_OUT);
 wire bad=(|sf_r)||(jv!={16{jexp}})||(jexp&&(|jerr))||(go_r&&jrun);
 always @(posedge clk or negedge ctl_rst_n)begin
  if(!ctl_rst_n)begin jrun<=0;jage<=0;y_valid<=0;fault<=0;end
  else begin
   if(bad)fault<=1;
   y_valid<=jrun&&jage==J_OUT;
   if(go_r)begin jrun<=1;jage<=0;end
   else if(jrun)begin jage<=jage+1'b1;if(jage==J_OUT)jrun<=0;end
  end
 end
endmodule
