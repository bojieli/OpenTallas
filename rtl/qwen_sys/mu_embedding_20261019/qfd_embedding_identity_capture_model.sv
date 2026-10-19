// MODEL ONLY. Preferred physical policy: input1, sole identity output1, reset2.
// No internal epoch register and no output bypass. All identity pins share one
// capture edge. Bank metadata provenance beyond the component remains unbound.
module qfd_embedding_identity_capture_model(
 input wire ck,rst_n,command_start,input wire [1:0] command_user,
 input wire [17:0] command_token,input wire [71:0] bank_tokens,
 input wire [63:0] bank_epochs,input wire [7:0] bank_generations,
 input wire [3:0] bank_roles,
 output reg identity_v,output reg [1:0] identity_user,
 output reg [17:0] identity_token,output reg [15:0] identity_epoch,
 output reg [1:0] identity_generation,output reg identity_role
);
 reg [1:0] reset_q=0;reg start_q;reg [1:0] user_q;reg [17:0] token_q;
 always @(posedge ck)begin
  reset_q<={reset_q[0],rst_n};
  if(!reset_q[1])begin start_q<=0;user_q<=0;token_q<=0;end
  else begin start_q<=command_start;if(command_start)begin user_q<=command_user;token_q<=command_token;end end
  if(!reset_q[1])begin identity_v<=0;identity_user<=0;identity_token<=0;identity_epoch<=0;identity_generation<=0;identity_role<=0;end
  else begin
   identity_v<=start_q;
   if(start_q)begin
    identity_user<=user_q;identity_token<=bank_tokens[18*user_q+:18];
    identity_epoch<=bank_epochs[16*user_q+:16];
    identity_generation<=bank_generations[2*user_q+:2];identity_role<=bank_roles[user_q];
   end
  end
 end
 // token_q is the paid command input capture; the arm checks selected bank token
 // against its independent command snapshot. It may not substitute live TAG.
endmodule

module qfd_embedding_identity_arm2_model(
 input wire ck,rst_n,command_start,input wire [1:0] command_user,
 input wire [17:0] command_token,input wire identity_v,
 input wire [1:0] identity_user,input wire [17:0] identity_token,
 input wire [15:0] identity_epoch,input wire [1:0] identity_generation,
 input wire identity_role,input wire [15:0] row_epoch,
 input wire [1:0] row_generation,input wire row_role,
 input wire native_read,release_slot,
 output wire validation_start,output wire [17:0] validation_token,
 output wire [15:0] validation_epoch,output reg fault
);
 reg [1:0] start_q;reg [1:0] user_q;reg [17:0] token_q;reg validated;
 assign validation_start=start_q[1];assign validation_token=identity_token;
 assign validation_epoch=identity_epoch;
 always @(posedge ck)begin
  if(!rst_n)begin start_q<=0;user_q<=0;token_q<=0;validated<=0;fault<=0;end
  else begin
   start_q<={start_q[0],command_start};
   if(command_start)begin
    if(validated||start_q!=0)fault<=1;
    user_q<=command_user;token_q<=command_token;validated<=0;
   end
   if(validation_start)begin
    if(!identity_v||identity_user!=user_q||identity_token!=token_q||
       identity_epoch!=row_epoch||identity_generation!=row_generation||
       identity_role!=row_role||native_read||release_slot)fault<=1;
    else validated<=1;
   end
   if(native_read&&!validated)fault<=1;
   if(release_slot)validated<=0;
  end
 end
endmodule
