`timescale 1ns/1ps
`default_nettype none
// Compact control leaf; payload datapaths live in the nine direct-die banks.
module vm_root_ctl9(
 input wire clk,por_n,wr_v,wr_bank,rd_v,rd_bank,wr_ACK_ready,mem_rd_v,
 input wire [6:0] wr_addr,rd_addr,
 input wire [3:0] tap_ready,tap_ACK_v,
 input wire [191:0] ack0,ack1,ack2,ack3,seat_owner_i,
 input wire [8:0] bank_bad,checker_err,checker_valid,
 output wire wr_ready,rd_ready,wr_ACK_v,native_release,drained,fault,
 output wire [3:0] tap_v,
 output wire mem_cmd_v,mem_cmd_we,mem_cmd_bank,output wire [6:0] mem_cmd_addr,
 output wire accept_o,return_o,capture_o,check_o,load_o,write_o,write_accept_o,hold_o);
 localparam SEATP=1,FREG=1;
 wire [767:0] tap_ACK_owner={ack3,ack2,ack1,ack0};
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
  localparam [3:0] IDLE=0,WRITE=1,VERIFY=2,CAPTURE=3,CHECK=4,WACK=5,READ=6,PUBLISH=7,WAIT_RD=8,LOAD=9,SEAT=10;
  reg [3:0] state,next_state;
  reg bank,next_bank,is_write,next_is_write,sticky,next_sticky;
  reg [6:0] addr,next_addr;
  reg [3:0] sent,next_sent,acked,next_acked;
  reg [71:0] control_code;
  wire [4*72-1:0] validity; // authoritative coded256 valid bits, cold reset only
  wire [255:0] valid_bits;wire [3:0] valid_UE;
  // A decoded validity shadow is ready before WACK drains. The coded words
  // remain authoritative; UE is still captured directly by bad_cv_q.
  reg [255:0] valid_bits_pipe;
  always @(posedge clk)valid_bits_pipe<=valid_bits;
  for(genvar k=0;k<4;k=k+1)begin:validity_decode
   wire [65:0] d=decode64(validity[k*72+:72]);
   assign valid_bits[k*64+:64]=d[63:0];assign valid_UE[k]=d[65];
  end
  wire [63:0] control={42'b0,sticky,is_write,bank,addr,sent,acked,state};
  wire [63:0] next_control={42'b0,next_sticky,next_is_write,next_bank,next_addr,next_sent,next_acked,next_state};
  wire [65:0] control_d=decode64(control_code);
  wire control_bad=control_d[65] || control_d[63:0]!=control;
  reg bad_cv_q;
  wire bad_cv=bad_cv_q;
  wire seat_bad_e=|bank_bad;
  assign fault=sticky||bad_cv||(state!=IDLE&&seat_bad_e);
  assign wr_ready=state==IDLE&&!fault&&!rd_v;
  assign rd_ready=state==IDLE&&!fault&&!wr_v;
  wire wf=wr_v&&wr_ready,rf=rd_v&&rd_ready;
  wire fault_i=sticky||bad_cv;   // = fault in IDLE
  wire ld_w=SEATP?(state==IDLE&&!fault_i&&wr_v&&!rd_v):wf,ld_r=SEATP?(state==IDLE&&!fault_i&&rd_v&&!wr_v):rf;
  wire chk_err_q=(|checker_err)||!(&checker_valid);
  assign wr_ACK_v=state==WACK&&!fault;
  assign drained=state==IDLE&&!fault;
  assign native_release=state==PUBLISH&&(&acked)&&!fault;
  wire [255:0] next_valid=valid_bits_pipe|(256'd1<<{bank,addr});
  for(genvar r=0;r<4;r=r+1)begin:validity_regions
   (* keep = "true", dont_touch = "true" *) reg region_por_n;
   reg [71:0] coded;
   always @(posedge clk or negedge por_n)begin
    if(!por_n)region_por_n<=0;else region_por_n<=1;
   end
   always @(posedge clk or negedge region_por_n)begin
    if(!region_por_n)coded<=0;
    else if(state==LOAD&&!chk_err_q&&is_write)coded<=encode64(next_valid[r*64+:64]);
   end
   assign validity[r*72+:72]=coded;
  end
  // SRAMs in the tiles (column slices): one command per WRITE / VERIFY / READ cycle, the macros' enables
  assign mem_cmd_v=(state==WRITE||state==VERIFY||state==READ)&&!fault;
  assign mem_cmd_we=state==WRITE;assign mem_cmd_bank=bank;assign mem_cmd_addr=addr;
  for(genvar t=0;t<4;t=t+1)begin:taps
   assign tap_v[t]=state==PUBLISH&&!sent[t]&&!fault;
  end
  always @*begin
   next_state=state;next_bank=bank;next_addr=addr;next_is_write=is_write;
   next_sent=sent;next_acked=acked;next_sticky=sticky||bad_cv||(state!=IDLE&&seat_bad_e);
   if((|tap_ACK_v)&&state!=PUBLISH)next_sticky=1;
   if(!fault)case(state)
    IDLE:begin
     next_sent=0;next_acked=0;
     if(wf)begin next_bank=wr_bank;next_addr=wr_addr;next_is_write=1;next_state=WRITE;end
     if(rf)begin
      if(!valid_bits_pipe[{rd_bank,rd_addr}])next_sticky=1;
      else begin next_bank=rd_bank;next_addr=rd_addr;next_is_write=0;next_state=READ;end
     end
    end
    WRITE:next_state=VERIFY;
    VERIFY,READ:next_state=WAIT_RD;
    WAIT_RD:if(mem_rd_v)next_state=CAPTURE;
    CAPTURE:next_state=CHECK;
    LOAD:begin
     if(chk_err_q)next_sticky=1;else if(is_write)next_state=WACK;else next_state=PUBLISH;
    end
    CHECK:next_state=LOAD;
    WACK:if(wr_ACK_ready)next_state=IDLE;
    PUBLISH:begin
     for(integer t=0;t<4;t=t+1)begin
      if(tap_v[t]&&tap_ready[t])next_sent[t]=1;
      if(tap_ACK_v[t])begin
       if(!sent[t]||acked[t]||tap_ACK_owner[t*192+:192]!=seat_owner_i)next_sticky=1;
       else next_acked[t]=1;
      end
     end
     if(&acked)next_state=IDLE;
    end
    default:next_sticky=1;
   endcase
   if(next_sticky)begin next_state=state;next_sent=sent;next_acked=acked;end
  end
  always @(posedge clk or negedge por_n)begin
   if(!por_n)begin
    state<=IDLE;bank<=0;addr<=0;is_write<=0;sticky<=0;sent<=0;acked<=0;
    control_code<=0;bad_cv_q<=0;
   end else begin
    state<=next_state;bank<=next_bank;addr<=next_addr;is_write<=next_is_write;
    sticky<=next_sticky;sent<=next_sent;acked<=next_acked;control_code<=encode64(next_control);
    bad_cv_q<=control_bad||(|valid_UE);
   end
  end
 assign accept_o=(ld_w||ld_r)&&por_n;
 assign write_accept_o=ld_w;
 assign return_o=mem_rd_v&&por_n;
 assign capture_o=state==CAPTURE&&!fault;
 assign check_o=state==CHECK&&!fault;
 assign load_o=state==LOAD&&!chk_err_q&&!is_write;
 assign write_o=is_write;
 assign hold_o=next_state!=IDLE;
endmodule
`default_nettype wire
