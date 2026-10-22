`timescale 1ns/1ps
// Default-off cold initialization successor; original closed source remains byte-identical.
// Adds 68 kept reset-tree flops and 1536 resettable state bits; +2 boot reset edges, 0 token edges.
module ot_qwen_tp8_pv_join_cold_t #(parameter integer MUT=0, J_LAT=7, RESET_PIN=0, COLD_INIT=0)(
 input wire clk,rst_n,input wire[1023:0] ts0,ts1,ts2,ts3,   // bank tree sums {b1,b0}, {b3,b2}, {b5,b4}, {b7,b6} (one face each)
 input wire join_go,input wire[7:0] sf,
 output reg[511:0] y,output reg y_valid,output reg fault
);
 wire local_rst_n;
 generate if(RESET_PIN)begin:g_reset_pin
  (* keep *)reg rst_q;
  always @(posedge clk)rst_q<=rst_n;
  assign local_rst_n=rst_q;
 end else begin:g_reset_legacy
  assign local_rst_n=rst_n;
 end endgenerate

 // COLD_INIT reset contract: assertion AND release take two clk edges from local_rst_n.
 // The static boot/admission calendar must add two reset edges; issue is forbidden until then.
 // Three first-stage flops each drive at most 22 leaf D pins. Data leaves reset one 32-bit
 // word, lane leaves reset one js/adder, and the last leaf resets the global control.
 wire ctl_rst_n; wire[15:0] lane_rst_n; wire[47:0] data_rst_n;
 generate if(COLD_INIT)begin:g_cold_rst
  (* keep="true", dont_touch="true" *)reg[2:0] root_q;
  (* keep="true", dont_touch="true" *)reg[64:0] leaf_q;
  always @(posedge clk)root_q<={3{local_rst_n}};
  genvar r;
  for(r=0;r<65;r=r+1)begin:g_leaf
   always @(posedge clk)leaf_q[r]<=root_q[r/22];
  end
  assign data_rst_n=leaf_q[47:0];
  assign lane_rst_n=leaf_q[63:48];
  assign ctl_rst_n=leaf_q[64];
 end else begin:g_legacy_rst
  assign data_rst_n={48{local_rst_n}};
  assign lane_rst_n={16{local_rst_n}};
  assign ctl_rst_n=local_rst_n;
 end endgenerate
 wire[4095:0] ts={ts3,ts2,ts1,ts0};
 localparam integer J_OUT=3*J_LAT+3;
 reg[4095:0] t_r;reg go_r;reg[7:0] sf_r;
 always @(posedge clk)t_r<=ts;
 always @(posedge clk or negedge ctl_rst_n)if(!ctl_rst_n)begin go_r<=0;sf_r<=0;end else begin go_r<=join_go;sf_r<=sf;end
 wire[511:0] tb[0:7];
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:g_t assign tb[g]=t_r[512*g+:512]; end endgenerate
 reg jrun;reg[4:0] jage;reg[511:0] xr,yr;wire[511:0] ja,jb;
 wire[511:0] jy;wire[15:0] jv;wire[31:0] jerr;
 // Operand-select slot, decoded ONE edge ahead from the next (jrun, jage) and registered once PER LANE (kept copies):
 // the shared jage decode drove all 1,024 operand-mux bits (3,299 loads, gate 21:06); each copy now drives one lane's
 // 64 mux bits + its adder issue. Slot codes: 1..4 = L5 pairs, 5 = (xr,jy) at J_LAT+1 / J_LAT+3, 6 = (yr,jy) at 2J_LAT+3.
 wire nrun=go_r?1'b1:(jrun&&jage!=5'(J_OUT));
 wire[4:0] nage=go_r?5'd0:(jrun?jage+5'd1:jage);
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
 wire[15:0] jissue;
 generate for(g=0;g<16;g=g+1)begin:g_join
  (* keep = "true", dont_touch = "true" *) reg[2:0] js;
  always @(posedge clk or negedge lane_rst_n[g])if(!lane_rst_n[g])js<=3'd0;else js<=nsel;
  assign jissue[g]=js!=3'd0;
  reg[31:0] la,lb;
  always @*begin
   la=32'd0;lb=32'd0;
   case(js)
    3'd1:begin la=tb[0][32*g+:32];lb=(MUT==1)?tb[2][32*g+:32]:tb[1][32*g+:32];end
    3'd2:begin la=(MUT==1)?tb[1][32*g+:32]:tb[2][32*g+:32];lb=tb[3][32*g+:32];end
    3'd3:begin la=tb[4][32*g+:32];lb=tb[5][32*g+:32];end
    3'd4:begin la=tb[6][32*g+:32];lb=tb[7][32*g+:32];end
    3'd5:begin la=xr[32*g+:32];lb=jy[32*g+:32];end
    3'd6:begin la=yr[32*g+:32];lb=jy[32*g+:32];end
    default:;
   endcase
  end
  assign ja[32*g+:32]=la;assign jb[32*g+:32]=lb;
  ot_hdc_fp32_add_lat #(.LAT(J_LAT),.DRST(0)) u_add(.clk(clk),.rst_n(lane_rst_n[g]),.valid_in(jissue[g]),
   .a(ja[32*g+:32]),.b(jb[32*g+:32]),.y(jy[32*g+:32]),.err(jerr[2*g+:2]),.valid_out(jv[g]));
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
 generate if(COLD_INIT)begin:g_cold_data
  genvar d;
  for(d=0;d<16;d=d+1)begin:g_word
   always @(posedge clk or negedge data_rst_n[d])begin
    if(!data_rst_n[d])xr[32*d+:32]<=0;
    else if(jrun&&(jage==J_LAT||jage==J_LAT+2))xr[32*d+:32]<=jy[32*d+:32];
   end
   if(MUT==2)begin:g_no_yr_clear // negative control: preserve the actual cold-base defect
    always @(posedge clk)if(jrun&&jage==2*J_LAT+1)yr[32*d+:32]<=jy[32*d+:32];
   end else begin:g_yr_clear
    always @(posedge clk or negedge data_rst_n[16+d])begin
     if(!data_rst_n[16+d])yr[32*d+:32]<=0;
     else if(jrun&&jage==2*J_LAT+1)yr[32*d+:32]<=jy[32*d+:32];
    end
   end
   always @(posedge clk or negedge data_rst_n[32+d])begin
    if(!data_rst_n[32+d])y[32*d+:32]<=0;
    else if(jrun&&jage==J_OUT)y[32*d+:32]<=jy[32*d+:32];
   end
  end
 end else begin:g_legacy_data
 always @(posedge clk)begin
  if(jrun&&jage==J_LAT)xr<=jy;                      // L5_0
  if(jrun&&jage==J_LAT+2)xr<=jy;                    // L5_2
  if(jrun&&jage==2*J_LAT+1)yr<=jy;                  // L6_0
  if(jrun&&jage==J_OUT)y<=jy;
 end
 end endgenerate
endmodule
