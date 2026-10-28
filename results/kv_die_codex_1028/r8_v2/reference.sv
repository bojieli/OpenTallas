module ref_bank #(parameter integer PROFILE=0, TD=0, ED=0)
(input wire clk,input wire[17:0]tok_i,input wire[15:0]epoch_i,output wire[17:0]tok_o,output wire[15:0]epoch_o);
localparam integer TM=(PROFILE==1)?4:9;
localparam integer EM=(PROFILE==1)?0:2;
generate
 if(TM>0)begin:gt
  (* keep=1 *)reg[17:0]pipe[0:TM-1];
  for(genvar j=0;j<TM;j=j+1)begin:r
   if(j==0)always@(posedge clk)pipe[j]<=tok_i;
   else always@(posedge clk)pipe[j]<=pipe[j-1];
  end
  assign tok_o=(TD==0)?tok_i:pipe[TD-1];
 end else assign tok_o=tok_i;
 if(EM>0)begin:ge
  (* keep=1 *)reg[15:0]pipe[0:EM-1];
  for(genvar j=0;j<EM;j=j+1)begin:r
   if(j==0)always@(posedge clk)pipe[j]<=epoch_i;
   else always@(posedge clk)pipe[j]<=pipe[j-1];
  end
  assign epoch_o=(ED==0)?epoch_i:pipe[ED-1];
 end else assign epoch_o=epoch_i;
endgenerate
endmodule
module gold #(parameter integer PROFILE=0,TD=0,ED=0)
(input wire clk,input wire[17:0]tok_i,input wire[15:0]epoch_i,output wire[17:0]tok_o,output wire[15:0]epoch_o);
ref_bank #(.PROFILE(PROFILE),.TD(TD),.ED(ED))u_bank(.*);
endmodule
module gate #(parameter integer PROFILE=0,STACK=0,GROUP=0,MUT=0)
(input wire clk,input wire[17:0]tok_i,input wire[15:0]epoch_i,output wire[17:0]tok_o,output wire[15:0]epoch_o);
kv_pc_r8_position_bank_v2 #(.PROFILE(PROFILE),.MUT(MUT))u_bank(.clk(clk),.stack_id(STACK[1:0]),.group_id(GROUP[2:0]),.tok_i(tok_i),.epoch_i(epoch_i),.tok_o(tok_o),.epoch_o(epoch_o));
endmodule
