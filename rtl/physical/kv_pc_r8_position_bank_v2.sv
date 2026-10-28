// Generated from the actual R8 word ledger. OPTIONAL COPY; not a physical release.
// Existing static position IDs only. No software/runtime delay selector or new wrapper pins.
(* keep_hierarchy=1 *)
module kv_pc_r8_position_bank_v2 #(parameter integer PROFILE=0,parameter integer MUT=0)
(input wire clk,input wire[1:0] stack_id,input wire[2:0] group_id,
 input wire[17:0] tok_i,input wire[15:0] epoch_i,output wire[17:0] tok_o,output wire[15:0] epoch_o);
localparam integer TOK_MAX=(PROFILE==1)?4:9;
localparam integer EPOCH_MAX=(PROFILE==1)?0:2;
function automatic integer tok_count(input [1:0] s,input [2:0] g);
begin
 tok_count=0;
 if (PROFILE==0) case ({s,g})
 5'd5: tok_count=1;
 5'd18: tok_count=1;
 5'd26: tok_count=9;
 5'd27: tok_count=9;
 5'd30: tok_count=9;
 default: tok_count=0;
 endcase
 if (PROFILE==1) case ({s,g})
 5'd20: tok_count=1;
 5'd28: tok_count=4;
 default: tok_count=0;
 endcase
 if (MUT==1 && s==2'd0 && g==3'd5) tok_count=0;
end
endfunction
function automatic integer epoch_count(input [1:0] s,input [2:0] g);
begin
 epoch_count=0;
 if (PROFILE==0) case ({s,g})
 5'd17: epoch_count=2;
 5'd19: epoch_count=1;
 default: epoch_count=0;
 endcase
 if (PROFILE==1) case ({s,g})
 default: epoch_count=0;
 endcase
end
endfunction
wire [7:0] tok_tap=tok_count(stack_id,group_id);
wire [7:0] epoch_tap=epoch_count(stack_id,group_id);
generate
 if (TOK_MAX>0) begin:gt
  (* keep=1 *) reg[17:0] pipe[0:TOK_MAX-1];
  for(genvar j=0;j<TOK_MAX;j=j+1) begin:r
   if(j==0) always @(posedge clk) pipe[j]<=tok_i;
   else always @(posedge clk) pipe[j]<=pipe[j-1];
  end
  assign tok_o=(tok_tap==0)?tok_i:pipe[tok_tap-1];
 end else assign tok_o=tok_i;
 if(EPOCH_MAX>0) begin:ge
  (* keep=1 *) reg[15:0] pipe[0:EPOCH_MAX-1];
  for(genvar j=0;j<EPOCH_MAX;j=j+1) begin:r
   if(j==0) always @(posedge clk) pipe[j]<=epoch_i;
   else always @(posedge clk) pipe[j]<=pipe[j-1];
  end
  assign epoch_o=(epoch_tap==0)?epoch_i:pipe[epoch_tap-1];
 end else assign epoch_o=epoch_i;
endgenerate
endmodule
