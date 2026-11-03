module ot_hgi_sfu_store_stripe_leaf_r10 #(
 parameter integer AW=11
)(
 input wire clk,
 input wire rst_a,                  
 input wire in_we,                  
 input wire [AW-1:0] in_addr,       
 input wire [255:0] in_data,
 output wire [AW-1:0] out_addr,     
 output wire [255:0] out_data,
 input wire in_start_v,             
 input wire [AW-1:0] in_start_base,
 input wire in_legal,
 input wire [AW:0] in_span,
 input wire [15:0] in_loops,
 input wire in_loops_one,
 input wire in_cv,                  
 output reg [221:0] out_cal,        
 output wire out_v,out_active,out_done,out_fault,
 output wire [31:0] out_ord,
 output reg [1:0] out_hz,
 output wire out_b26
);
  
 (* keep = "true", dont_touch = "true" *) reg rb;            
 reg we_q,start_v_q,legal_q,loops_one_q,cv_q;
 (* keep = "true", dont_touch = "true" *) reg [AW-1:0] addr_q;
 (* keep = "true", dont_touch = "true" *) reg [255:0] data_q;
 reg [AW-1:0] start_base_q;
 reg [AW:0] span_q;
 reg [15:0] loops_q;
 always @(posedge clk)begin
  rb<=rst_a;we_q<=in_we;addr_q<=in_addr;data_q<=in_data;cv_q<=in_cv;
  start_v_q<=in_start_v;start_base_q<=in_start_base;legal_q<=in_legal;span_q<=in_span;loops_q<=in_loops;
  loops_one_q<=in_loops_one;
 end
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
 (* keep = "true", dont_touch = "true" *) reg [AW-1:0] fwd_addr_q;
 (* keep = "true", dont_touch = "true" *) reg [255:0] fwd_data_q;
 
        

`line 82 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/ot_hgi_sfu_store_stripe_leaf_r10.sv" 0
 always @(posedge clk)begin fwd_addr_q<=addr_q;fwd_data_q<=data_q; end

`line 84 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/generic/peers/ot_hgi_sfu_store_stripe_leaf_r10.sv" 0
 assign out_addr=fwd_addr_q;
 assign out_data=fwd_data_q;
  
 localparam integer W=222, PCLO=234-AW;
 reg running,loops_one;
 reg [AW-1:0] pc,base;
 reg [AW:0] rem,span;
 reg [15:0] loops_left;
 reg [31:0] issued;
 reg valid0,valid1,last0,last1;
 reg [AW-1:0] pc0,pc1;
 reg [31:0] ord0,ord1,ordinal;
 reg [255:0] captured;
 reg [221:0] calendar;
 reg calendar_v,active,done,fault;
 wire busy=running|valid0|valid1;
 wire final_issue=(rem=={{AW{1'b0}},1'b1}) && loops_one;
 wire word_ok=captured[255:240]==16'hc7a1 && captured[233:PCLO]==pc1 &&
              captured[239:234]==0 && captured[PCLO-1:W]==0;
 wire [255:0] page_data[0:3];
 reg [1:0] read_page;
 always @(posedge clk)read_page<=pc[AW-1:9];
 wire [255:0] macro_data=page_data[read_page];
 for(genvar p=0;p<4;p=p+1)begin:g_page
  ot_sram_1r1w_512x256_m1_r2c2 u_program(
   .clk(clk),.r_ce_in(running && pc[AW-1:9]==p),.r_addr_in(pc[8:0]),.rd_out(page_data[p]),
   .w_ce_in(we_q && !busy && !start_v_q && addr_q[AW-1:9]==p),.w_addr_in(addr_q[8:0]),
   .wd_in(data_q),.w_mask_in({256{1'b1}}),
   .rr_en(2'b00),.rr_addr(18'd0),.cr_en(2'b00),.cr_sel(16'd0));
 end
 wire cal_ok=valid1 && word_ok;
 always @(posedge clk)begin
  captured<=macro_data;
  pc0<=pc;pc1<=pc0;ord0<=issued;ord1<=ord0;
  calendar<=cal_ok?captured[W-1:0]:{W{1'b0}};
  out_hz<={cal_ok && |captured[221:188],cal_ok && |captured[221:27]};
  ordinal<=ord1;
 end
 always @(posedge clk)
  if(!rb)begin
   running<=0;issued<=0;
   valid0<=0;valid1<=0;last0<=0;last1<=0;calendar_v<=0;
   active<=0;done<=0;fault<=0;
  end else begin
   valid0<=running;valid1<=valid0;last0<=running && final_issue;last1<=last0;
   calendar_v<=valid1;
   active<=busy;done<=valid1 && last1;
   if(valid1 && !word_ok)fault<=1;
   if(we_q && (busy || start_v_q))fault<=1;
   if(start_v_q)begin
    if(busy || we_q || !legal_q)fault<=1;
    else begin
     running<=1;pc<=start_base_q;base<=start_base_q;rem<=span_q;span<=span_q;
     loops_left<=loops_q;loops_one<=loops_one_q;issued<=0;
    end
   end
   if(running)begin
    issued<=issued+1;
    if(rem=={{AW{1'b0}},1'b1})begin
     if(loops_one)running<=0;
     else begin pc<=base;rem<=span;loops_left<=loops_left-1;loops_one<=loops_left==16'd2; end
    end else begin pc<=pc+1;rem<=rem-1; end
   end
  end
  
 reg [221:0] relay;
 always @(posedge clk)begin
  relay<=calendar;
  out_cal<=cv_q?relay:222'd0;
 end
 assign out_v=calendar_v;
 assign out_active=active;
 assign out_done=done;
 assign out_fault=fault;
 assign out_ord=ordinal;
 assign out_b26=calendar[26];
endmodule
