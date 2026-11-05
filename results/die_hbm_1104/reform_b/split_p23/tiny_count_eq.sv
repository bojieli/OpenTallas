// HBM-REFORM-B3 part 23: exact check of the h_take / h_take_b rewrite: the arbiter loop of ot_hbm_svc_sm4pc_cdc_rel_id with all its inputs free.
module tiny(input wire [3:0] response_ok,input wire [11:0] ord,input wire [7:0] fifo_wr_ready,input wire [15:0] cur,input wire [7:0] bank,
 input wire [11:0] h_received,input wire [11:0] h_total,output wire ok);
 localparam integer LBANKS=4;
 reg [3:0] response_accepted;reg [7:0] fifo_wr_valid;
 integer o_take,o_b[0:3];integer p,l,offset,rb;
 always @*begin
  fifo_wr_valid=0;response_accepted=0;o_take=0;for(rb=0;rb<LBANKS;rb=rb+1)o_b[rb]=0;
  for(l=0;l<8;l=l+1)begin
   for(offset=0;offset<4;offset=offset+1)begin
    p=(int'(cur[2*l+:2])+offset)&3;
    if(response_ok[p]&&ord[3*p+:3]==l&&!fifo_wr_valid[l]&&fifo_wr_ready[l])begin
     fifo_wr_valid[l]=1;response_accepted[p]=1;o_take=o_take+1;o_b[bank[2*p+:2]]=o_b[bank[2*p+:2]]+1;
    end
   end
  end
 end
 reg [2:0] h_take;reg [2:0] h_take_b[0:3];integer ta,tb;
 always @*begin
  h_take=3'(response_accepted[0])+3'(response_accepted[1])+3'(response_accepted[2])+3'(response_accepted[3]);
  for(tb=0;tb<LBANKS;tb=tb+1)begin
   h_take_b[tb]=0;
   for(ta=0;ta<4;ta=ta+1)if(response_accepted[ta]&&int'(bank[2*ta+:2])==tb)h_take_b[tb]=h_take_b[tb]+3'd1;
  end
 end
 assign ok=(o_take==int'(h_take))&&(o_b[0]==int'(h_take_b[0]))&&(o_b[1]==int'(h_take_b[1]))&&(o_b[2]==int'(h_take_b[2]))&&(o_b[3]==int'(h_take_b[3]))&&
  (12'(h_received+o_take)==12'(h_received+h_take))&&
  ((h_received+o_take==h_total)==(13'(h_received)+13'(h_take)==13'(h_total)));
endmodule
