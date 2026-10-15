`default_nettype none
// One stack's actual static16-key scorer. Every issue is a compiler slot;
// tags/partial masks/keeps are checked and never reschedule the arithmetic.
module ot_hbm_idx_score_static #(parameter integer MUT=0)(
 input wire clk_ctl,input wire[3:0]clk_engine,clk_meta,clk_tail,
 input wire[15:0]clk_chunk,input wire[511:0]clk_hslice,input wire rst_n,
 input wire[6:0]rank,input wire[10:0]first_ord,input wire[11:0]nkeys,
 input wire keep_en,input wire[341:0]keep_bitmap,
 input wire ql_v,input wire[7:0]ql_head,input wire[511:0]ql_codes,input wire[31:0]ql_sc,input wire[15:0]ql_w,
 input wire beat_v,input wire[7:0]beat_index,input wire[8791:0]key_lines,
 output wire[609:0]score,output reg fault
);
 wire[3:0]ev,efault;
 wire[15:0]kv,fl;
 wire[255:0]val;
 wire[319:0]idx;
 wire[3:0]last;
 wire[19:0]g0=20'(768)*20'(first_ord)+20'(8)*20'(rank)+20'(1536)*20'(beat_index);
 for(genvar e=0;e<4;e=e+1)begin:ge
  wire[2175:0]keys;
  wire[3:0]valid_keys,keep_keys;
  for(genvar l=0;l<4;l=l+1)begin:gl
   localparam integer lane=4*e+l;
   assign keys[l*544+:544]=key_lines[(lane/2)*1099+11+(lane%2)*544+:544];
   assign valid_keys[l]=({4'd0,beat_index}*12'd16+12'(lane))<nkeys;
   assign keep_keys[l]=!keep_en||keep_bitmap[int'(beat_index)*2+lane/8];
  end
  wire[19:0]first=g0+20'((e/2)*768+(e%2)*4);
  wire[24:0]meta;
  ot_hdc_delay #(.W(25),.D(123)) md(.clk(clk_meta[e]),.rst_n(rst_n),
   .d({(({4'd0,beat_index}+12'd1)*12'd16>=nkeys),first,4'd0}),.q(meta));
  for(genvar l=0;l<4;l=l+1)begin:go
   assign idx[(e*4+l)*20+:20]=meta[23:4]+20'(l);
  end
  assign last[e]=meta[24];
  wire[3:0]pf;
  wire online;
  ot_hbm_idx_engine_static #(.MUT(MUT)) engine(.clk(clk_engine[e]),.clk_tail(clk_tail[e]),.clk_chunk(clk_chunk[e*4+:4]),
   .clk_hslice(clk_hslice[e*128+:128]),.rst_n(rst_n),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),
   .k_valid(beat_v),.k_kv(valid_keys),.k_keep(keep_keys),.k_key(keys),.o_valid(ev[e]),.o_kv(kv[e*4+:4]),
   .o_score(val[e*64+:64]),.o_fault(pf),.cnt_keys_scored(),.cnt_headsums_fused(),.cnt_faults(),.online(online),.protocol_fault(efault[e]));
  assign fl[e*4+:4]=pf|meta[3:0];
 end
 assign score={idx,val,kv,fl,last[0],ev[0]};
 always @(posedge clk_ctl or negedge rst_n)begin
  if(!rst_n)fault<=0;
  else begin
   if((|efault)||(ev!={4{ev[0]}}))fault<=1;
   if(beat_v)begin
    if(nkeys>2736||beat_index>170)fault<=1;
    for(integer p=0;p<8;p=p+1)if(!key_lines[p*1099]||key_lines[p*1099+1+:10]!==10'(int'(beat_index)*8+p))fault<=1;
   end
  end
 end
endmodule
`default_nettype wire
