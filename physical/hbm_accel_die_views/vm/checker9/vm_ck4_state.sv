`timescale 1ns/1ps
`default_nettype none
// Bank-local publication seat, return hold and pipelined checker. Reset affects
// presence and verdict bits only; all 1152-bit row storage is load-qualified.
module vm_ck4_state #(parameter integer OWNER_BANK=0)(
 input wire ck,rst_n,accept_i,return_i,capture_i,check_i,load_i,write_i,hold_i,
 input wire [255:0] raw_i,input wire [287:0] returned_i,
 output wire [287:0] seat_code_o,output wire [255:0] seat_data_o,
 output wire seat_bad_o,output wire checker_error_o,checker_valid_o);
 function [71:0] encode64(input [63:0] data);
  begin encode64={^{data[0],data[1],data[2],data[4],data[5],data[7],data[10],data[11],data[12],data[14],data[17],data[18],data[21],data[23],data[24],data[26],data[27],data[29],data[32],data[33],data[36],data[38],data[39],data[41],data[44],data[46],data[47],data[50],data[51],data[53],data[56],data[57],data[58],data[60],data[63]},data[63],data[62],data[61],data[60],data[59],data[58],data[57],^{data[57],data[58],data[59],data[60],data[61],data[62],data[63]},data[56],data[55],data[54],data[53],data[52],data[51],data[50],data[49],data[48],data[47],data[46],data[45],data[44],data[43],data[42],data[41],data[40],data[39],data[38],data[37],data[36],data[35],data[34],data[33],data[32],data[31],data[30],data[29],data[28],data[27],data[26],^{data[26],data[27],data[28],data[29],data[30],data[31],data[32],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[25],data[24],data[23],data[22],data[21],data[20],data[19],data[18],data[17],data[16],data[15],data[14],data[13],data[12],data[11],^{data[11],data[12],data[13],data[14],data[15],data[16],data[17],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[10],data[9],data[8],data[7],data[6],data[5],data[4],^{data[4],data[5],data[6],data[7],data[8],data[9],data[10],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[3],data[2],data[1],^{data[1],data[2],data[3],data[7],data[8],data[9],data[10],data[14],data[15],data[16],data[17],data[22],data[23],data[24],data[25],data[29],data[30],data[31],data[32],data[37],data[38],data[39],data[40],data[45],data[46],data[47],data[48],data[53],data[54],data[55],data[56],data[60],data[61],data[62],data[63]},data[0],^{data[0],data[2],data[3],data[5],data[6],data[9],data[10],data[12],data[13],data[16],data[17],data[20],data[21],data[24],data[25],data[27],data[28],data[31],data[32],data[35],data[36],data[39],data[40],data[43],data[44],data[47],data[48],data[51],data[52],data[55],data[56],data[58],data[59],data[62],data[63]},^{data[0],data[1],data[3],data[4],data[6],data[8],data[10],data[11],data[13],data[15],data[17],data[19],data[21],data[23],data[25],data[26],data[28],data[30],data[32],data[34],data[36],data[38],data[40],data[42],data[44],data[46],data[48],data[50],data[52],data[54],data[56],data[57],data[59],data[61],data[63]}}; end
 endfunction
 function [65:0] decode64(input [71:0] code);
  reg [71:0] c; reg [6:0] s; reg ov,ue,cor;
  begin
   s={^{code[63],code[64],code[65],code[66],code[67],code[68],code[69],code[70]},^{code[31],code[32],code[33],code[34],code[35],code[36],code[37],code[38],code[39],code[40],code[41],code[42],code[43],code[44],code[45],code[46],code[47],code[48],code[49],code[50],code[51],code[52],code[53],code[54],code[55],code[56],code[57],code[58],code[59],code[60],code[61],code[62]},^{code[15],code[16],code[17],code[18],code[19],code[20],code[21],code[22],code[23],code[24],code[25],code[26],code[27],code[28],code[29],code[30],code[47],code[48],code[49],code[50],code[51],code[52],code[53],code[54],code[55],code[56],code[57],code[58],code[59],code[60],code[61],code[62]},^{code[7],code[8],code[9],code[10],code[11],code[12],code[13],code[14],code[23],code[24],code[25],code[26],code[27],code[28],code[29],code[30],code[39],code[40],code[41],code[42],code[43],code[44],code[45],code[46],code[55],code[56],code[57],code[58],code[59],code[60],code[61],code[62]},^{code[3],code[4],code[5],code[6],code[11],code[12],code[13],code[14],code[19],code[20],code[21],code[22],code[27],code[28],code[29],code[30],code[35],code[36],code[37],code[38],code[43],code[44],code[45],code[46],code[51],code[52],code[53],code[54],code[59],code[60],code[61],code[62],code[67],code[68],code[69],code[70]},^{code[1],code[2],code[5],code[6],code[9],code[10],code[13],code[14],code[17],code[18],code[21],code[22],code[25],code[26],code[29],code[30],code[33],code[34],code[37],code[38],code[41],code[42],code[45],code[46],code[49],code[50],code[53],code[54],code[57],code[58],code[61],code[62],code[65],code[66],code[69],code[70]},^{code[0],code[2],code[4],code[6],code[8],code[10],code[12],code[14],code[16],code[18],code[20],code[22],code[24],code[26],code[28],code[30],code[32],code[34],code[36],code[38],code[40],code[42],code[44],code[46],code[48],code[50],code[52],code[54],code[56],code[58],code[60],code[62],code[64],code[66],code[68],code[70]}}; ov=^code; ue=1'b0; cor=1'b0; c=code;
   if(s!=7'd0)begin
    if(ov&&s<=7'd71)begin c=code^(72'd1<<(s-7'd1)); cor=1'b1; end else ue=1'b1;
   end else if(ov)begin c[71]=~c[71]; cor=1'b1; end
   decode64={ue,cor,{c[70],c[69],c[68],c[67],c[66],c[65],c[64],c[62],c[61],c[60],c[59],c[58],c[57],c[56],c[55],c[54],c[53],c[52],c[51],c[50],c[49],c[48],c[47],c[46],c[45],c[44],c[43],c[42],c[41],c[40],c[39],c[38],c[37],c[36],c[35],c[34],c[33],c[32],c[30],c[29],c[28],c[27],c[26],c[25],c[24],c[23],c[22],c[21],c[20],c[19],c[18],c[17],c[16],c[14],c[13],c[12],c[11],c[10],c[9],c[8],c[6],c[5],c[4],c[2]}};
  end
 endfunction

 reg [287:0] seat,returned;
 reg [255:0] seat_data_q;
 wire [287:0] encoded_raw;
 (* keep = "true", dont_touch = "true" *) reg [7:0] held_q,capture_q,check_q,load_pre_q;
 always @(posedge ck)begin
  capture_q<={8{return_i}};check_q<={8{capture_i}};
  load_pre_q<={8{check_i&&!write_i}};
 end
 reg seat_present,seat_ld_q,seat_bad_q;
 wire [287:0] repaired;
 wire [3:0] seat_ue;
 localparam [255:0] OM=OWNER_BANK?(({256{1'b1}}>>64)<<15):256'd0;
 localparam [255:0] PM=OWNER_BANK?{{49{1'b1}},207'd0}:256'd0;
 for(genvar k=0;k<4;k=k+1)begin:words
  assign encoded_raw[k*72+:72]=encode64(raw_i[k*64+:64]);
  wire [65:0] d=decode64(seat[k*72+:72]);
  assign seat_data_o[k*64+:64]=seat_data_q[k*64+:64];
  assign seat_ue[k]=seat_present&&d[65];
 end
 assign seat_code_o=seat; // Unqualified data is not consumed before the local presence bit.
 assign seat_bad_o=seat_present&&seat_bad_q&&!seat_ld_q;
 vm_ck4 #(.LOCAL_REGIONS(1)) u_checker(.ck(ck),.rst_n(rst_n),.capture_i(capture_i),.check_i(check_i),
  .capture_regions_i(capture_q),.check_regions_i(check_q),
  .write_i(write_i),.sample_i(returned),.expected_i(seat_code_o),
  .owner_mask_i(OM),.padding_mask_i(PM),.error_o(checker_error_o),
  .valid_o(checker_valid_o),.repaired_o(repaired));
 always @(posedge ck)begin
  returned<=returned_i; // Always capture the held return bus; return_i qualifies the syndrome stage.
  for(integer h=0;h<8;h=h+1)if(!held_q[h])begin
   seat[h*36+:36]<=encoded_raw[h*36+:36];seat_data_q[h*32+:32]<=raw_i[h*32+:32];
  end
  for(integer h=0;h<8;h=h+1)if(load_pre_q[h]&&load_i)begin
   integer j,d;d=0;
   seat[h*36+:36]<=repaired[h*36+:36];
   // Extract one repaired data half without adding a second ECC decode.
   for(j=1;j<=71;j=j+1)if(j!=1&&j!=2&&j!=4&&j!=8&&j!=16&&j!=32&&j!=64)begin
    if((d/32)==(h%2))seat_data_q[h*32+(d%32)]<=repaired[(h/2)*72+j-1];d=d+1;
   end
  end
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin seat_present<=0;seat_ld_q<=0;seat_bad_q<=0;held_q<=0;end
  else begin
   held_q<={8{hold_i}};
   if(accept_i||load_i)seat_present<=1;
   seat_ld_q<=accept_i||load_i;
   seat_bad_q<=|seat_ue;
  end
 end
endmodule
module vm_ck4_state_data(input wire ck,rst_n,accept_i,return_i,capture_i,check_i,load_i,write_i,hold_i,
 input wire [255:0] raw_i,input wire [287:0] returned_i,
 output wire [287:0] seat_code_o,output wire [255:0] seat_data_o,
 output wire seat_bad_o,checker_error_o,checker_valid_o);
 vm_ck4_state u_bank(.*);
endmodule
module vm_ck4_state_owner(input wire ck,rst_n,accept_i,return_i,capture_i,check_i,load_i,write_i,hold_i,
 input wire [255:0] raw_i,input wire [287:0] returned_i,
 output wire [287:0] seat_code_o,output wire [255:0] seat_data_o,
 output wire seat_bad_o,checker_error_o,checker_valid_o);
 vm_ck4_state #(.OWNER_BANK(1)) u_bank(.*);
endmodule
`default_nettype wire
