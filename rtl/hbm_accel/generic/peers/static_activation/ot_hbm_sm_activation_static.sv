`timescale 1ns/1ps
`default_nettype none
// Actual fixed-slot FP32 VM -> exact AQ12 -> mapped fragment SRAM -> original
// NC8/SUB4 SM activation pins. Same compiler edge at every explicit root.
// There is no queue, ready, grant, credit, retry or data-dependent waiting.
module ot_hbm_sm_activation_static #(parameter integer MUT=0)(
 input wire clk_control,input wire [1:0] clk_aq_core,clk_aq_delay,clk_aq_encode,
 input wire [3:0] clk_code,input wire rst_n,epoch_start,
 input wire control_v,input wire [43:0] control,
 output reg [135:0] rq,input wire [2055:0] rr,
 output reg xw_en,output reg [6:0] xw_addr,xw_grp,
 output reg [2047:0] xw_data,output reg xw_last,
 output reg busy,done,retire_fault,output wire fault
);
 wire read_v=control_v&&control[0],emit_v=control_v&&control[23];
 wire [15:0] read_sector=control[16:1];
 wire [2:0] column=control[20:18];wire [1:0] lane=control[22:21];
 wire [4:0] pair_id=control[43:39];wire [6:0] emit_addr=control[31:25];
 wire [3:0] emit_group=control[35:32];
 reg own_fault;reg [15:0] epoch;
 wire [3:0] code_fault;
 assign fault=own_fault||(|code_fault);
 // Expected return metadata travels a fixed eight edges from programme
 // consumption, independently of observed VM valids.
 reg [7:0] rv;reg [25:0] route[0:7];
 reg aq_v;reg [2047:0] aq_x;reg [25:0] aq_tag;
 reg [17:0] qv;reg [25:0] qtag[0:17];
 wire [1:0] aq_vo,aq_fault;wire [511:0] aq_q;wire [19:0] aq_e;
 for(genvar p=0;p<2;p=p+1)begin:quant
  ot_hbm_sm_aq_static aq(.clk_core(clk_aq_core[p]),.clk_delay(clk_aq_delay[p]),
   .clk_encode(clk_aq_encode[p]),.rst_n(rst_n),.v(aq_v),.x(aq_x[p*1024+:1024]),
   .vo(aq_vo[p]),.q(aq_q[p*256+:256]),.e(aq_e[p*10+:10]),.y(),.fault(aq_fault[p]));
 end
 always @(posedge clk_control)begin
  for(integer b=0;b<8;b=b+1)rq[b*17+:16]<=read_sector+16'(b);
  route[0]<={epoch,pair_id,column,lane};
  for(integer i=1;i<8;i=i+1)route[i]<=route[i-1];
  for(integer b=0;b<8;b=b+1)aq_x[b*256+:256]<=rr[b*257+:256];
  aq_tag<=route[7];qtag[0]<=aq_tag;
  for(integer i=1;i<18;i=i+1)qtag[i]<=qtag[i-1];
 end
 // The fragment has1064 meaningful bits/column; 3152-bit column spacing
 // makes each2048-bit beat intersect at most one column.
 function automatic [2:0] group_column(input [3:0] g);
  case(g)
   0:group_column=0;1,2:group_column=1;3:group_column=2;
   4,5:group_column=3;6:group_column=4;7,8:group_column=5;
   9:group_column=6;10,11:group_column=7;default:group_column=0;
  endcase
 endfunction
 reg [16:0] em[0:3];reg [3:0] ev;
 // em={last,address7,group4,buffer1,column3,has_code1}
 always @(posedge clk_control)begin
  em[0]<={control[36],emit_addr,emit_group,control[24],group_column(emit_group),(emit_group<12)};
  for(integer i=1;i<4;i=i+1)em[i]<=em[i-1];
 end
 wire [1063:0] fragment;
 for(genvar j=0;j<4;j=j+1)begin:codes
  reg write_v;reg [3:0] write_row;reg [20:0] write_epoch;
  reg [511:0] write_data;reg [19:0] write_exp;
  reg [1:0] re0,re1,cv;
  reg [3:0] read_row;reg [20:0] read_epoch;
  reg [9:0] exponents[0:1][0:15];reg [20:0] epochs[0:1][0:15];
  reg [15:0] loaded[0:1];reg local_fault;
  wire [511:0] mq;reg [511:0] cap;reg [19:0] exp_q,exp_cap;
  reg [255:0] code_out;reg [9:0] exponent_out;
  assign fragment[j*266+:266]={exponent_out,code_out};
  assign code_fault[j]=local_fault;
  for(genvar p=0;p<2;p=p+1)begin:parity
   for(genvar h=0;h<2;h=h+1)begin:half
    ot_sram_1r1w_32x128_m1 mem(.clk(clk_code[j]),.r_ce_in(re0[p]),
     .r_addr_in({1'b0,read_row}),.rd_out(mq[(p*2+h)*128+:128]),
     .w_ce_in(write_v),.w_addr_in({1'b0,(MUT==2?(write_row^4'b1000):write_row)}),
     .wd_in(write_data[(p*2+h)*128+:128]),.w_mask_in({128{1'b1}}));
   end
  end
  always @(posedge clk_code[j])begin
   write_row<={qtag[17][5],qtag[17][4:2]};
   write_epoch<=qtag[17][25:5];write_data<=aq_q;write_exp<=aq_e;
   read_row<={control[24],group_column(emit_group)};
   read_epoch<={epoch,emit_addr[5:1]};
   for(integer p=0;p<2;p=p+1)begin
    if(write_v)begin
     exponents[p][write_row]<=write_exp[p*10+:10];
     epochs[p][write_row]<=write_epoch;
    end
    if(re0[p])exp_q[p*10+:10]<=exponents[p][read_row];
    if(re1[p])begin cap[p*256+:256]<=mq[p*256+:256];exp_cap[p*10+:10]<=exp_q[p*10+:10];end
   end
   code_out<=({256{cv[0]}}&cap[255:0])|({256{cv[1]}}&cap[511:256]);
   exponent_out<=({10{cv[0]}}&exp_cap[9:0])|({10{cv[1]}}&exp_cap[19:10]);
  end
  always @(posedge clk_code[j] or negedge rst_n)begin
   if(!rst_n)begin write_v<=0;re0<=0;re1<=0;cv<=0;loaded[0]<=0;loaded[1]<=0;local_fault<=0;end
   else begin
    write_v<=qv[17] && ((MUT==1?(qtag[17][1:0]^2'b01):qtag[17][1:0])==2'(j));
    for(integer p=0;p<2;p=p+1)begin
     re0[p]<=emit_v&&emit_group<12&&emit_addr[0]==p;
     re1[p]<=re0[p];cv[p]<=re1[p];
     if(write_v)loaded[p][write_row]<=1;
     if(re0[p] && (!loaded[p][read_row]||epochs[p][read_row]!=read_epoch))local_fault<=1;
    end
   end
  end
 end
 function automatic [2047:0] beat(input [1063:0] f,input [3:0] g);
 begin beat=0;case(g)
  0:beat[0+:1064]=f[0+:1064];
  1:beat[1104+:944]=f[0+:944];
  2:beat[0+:120]=f[944+:120];
  3:beat[160+:1064]=f[0+:1064];
  4:beat[1264+:784]=f[0+:784];
  5:beat[0+:280]=f[784+:280];
  6:beat[320+:1064]=f[0+:1064];
  7:beat[1424+:624]=f[0+:624];
  8:beat[0+:440]=f[624+:440];
  9:beat[480+:1064]=f[0+:1064];
  10:beat[1584+:464]=f[0+:464];
  11:beat[0+:600]=f[464+:600];
  default:begin end
 endcase end endfunction
 reg packed_v,packed_last;reg [6:0] packed_addr,packed_group;reg [2047:0] packed_data;
 always @(posedge clk_control)begin
  packed_data<=beat(fragment,em[3][8:5]);
  packed_last<=em[3][16];packed_addr<=em[3][15:9];packed_group<={3'b0,em[3][8:5]};
  xw_data<=packed_data;xw_last<=packed_last;xw_addr<=packed_addr;xw_grp<=packed_group;
 end
 always @(posedge clk_control or negedge rst_n)begin
  if(!rst_n)begin
   rv<=0;aq_v<=0;qv<=0;ev<=0;packed_v<=0;xw_en<=0;
   own_fault<=0;epoch<=0;busy<=0;done<=0;retire_fault<=0;
   for(integer b=0;b<8;b=b+1)rq[b*17+16]<=0;
  end else begin
   done<=0;retire_fault<=0;
   for(integer b=0;b<8;b=b+1)rq[b*17+16]<=read_v;
   rv<={rv[6:0],read_v};aq_v<=rv[7];qv<={qv[16:0],aq_v};
   ev<={ev[2:0],emit_v};packed_v<=ev[3];xw_en<=packed_v;
   if(epoch_start)begin
    if(busy||epoch==16'hffff)own_fault<=1;
    busy<=1;epoch<=epoch+1'b1;
   end
   if(read_v && (!busy || control[38:37]!=0 || read_sector[2:0]!=0 || pair_id>=20 || control[17]!=pair_id[0]))own_fault<=1;
   if(emit_v && (!busy || emit_addr>=40 || emit_group>=13 || control[24]!=emit_addr[1]))own_fault<=1;
   for(integer b=0;b<8;b=b+1)if(rr[b*257+256]!=rv[7])own_fault<=1;
   if(aq_vo!={2{qv[17]}} || (qv[17]&&(|aq_fault)))own_fault<=1;
   if(xw_en&&xw_last)begin busy<=0;done<=!fault;retire_fault<=fault;end
  end
 end
endmodule
`default_nettype wire
