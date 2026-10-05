`timescale 1ns/1ps
// Existing CP LAUNCH -> actual shared SU lease. No second borrower/GO authority.
// Four protected control/frame/PC rows, within the combined bridge allowance.
module ot_hbm_integrated_su_cp_bind #(parameter integer ENABLE=0,REGISTERED_OUTPUTS=0,REGISTERED_STATUS=0)(
 input wire clk,por_n,input wire [1:0] launch_v,input wire [31:0] launch_pc,
 input wire [31:0] cp_job,input wire [3:0] cp_gen,
 input wire [16:0] launch_token,input wire [19:0] launch_pos,
 output wire [1:0] native_launch,
 output wire lease_v,input wire lease_granted,
 output wire release_v,input wire release_r,
 input wire exec_done,exec_fault,input wire [3:0] retired_original_ops,
 input wire shared_fault,
 output wire owned,pending,quiet,selected,done,fault,
 output wire [31:0] selected_pc,held_job,output wire [3:0] held_gen,
 output wire [16:0] held_token,output wire [19:0] held_pos
);
 generate if(ENABLE==0)begin:off
 assign native_launch=launch_v;assign lease_v=0;assign release_v=0;
 assign owned=0;assign pending=0;assign quiet=1;assign selected=0;
 assign done=0;assign fault=0;assign selected_pc=0;assign held_job=0;
 assign held_gen=0;assign held_token=0;assign held_pos=0;
 end else begin:on
 localparam [3:0] IDLE=0,PENDING=1,ACTIVE=2,RELEASE=3,CLEANUP=4,DONE=5,PREDECODE=6,FAIL=7,QUALIFY=8;
 reg [71:0] control,pc_code,frame_lo,frame_hi;
 wire [65:0] c=ot_gpu_w6_secded_pkg::decode64(control),p=ot_gpu_w6_secded_pkg::decode64(pc_code),lo=ot_gpu_w6_secded_pkg::decode64(frame_lo),hi=ot_gpu_w6_secded_pkg::decode64(frame_hi);
 wire raw_bad=c[65]||p[65]||lo[65]||hi[65];wire [3:0] state=REGISTERED_STATUS?c[3:0]:{1'b0,c[2:0]};
 wire [191:0] decoded_header;wire decode_v,decode_r,decode_bad;
 reg ecc_fault_q,checked_valid_q;
 reg decoder_start_q;
 initial if(REGISTERED_STATUS&&!REGISTERED_OUTPUTS)
  $fatal(1,"registered status requires checked registered header");
 // A dedicated one-bit request cut removes protected control decode/fault
 // fanout from the three header capture banks. Encoded header was captured
 // at the preceding launch edge and remains immutable until completion.
 always @(posedge clk or negedge por_n)begin
  if(!por_n)decoder_start_q<=0;
  else decoder_start_q<=state==IDLE&&launch_v==2'b01&&entry&&!fault;
 end
 wire [127:0] original_frame={hi[63:0],lo[63:0]};
 wire [127:0] frame=REGISTERED_OUTPUTS?decoded_header[191:64]:original_frame;
 wire bad=REGISTERED_OUTPUTS?ecc_fault_q:raw_bad;
 if(REGISTERED_OUTPUTS)begin:registered_header
  ot_hbm_integrated_header_decode decoder(
   .clk(clk),.por_n(por_n),.i_v(REGISTERED_STATUS?decoder_start_q:(state==PREDECODE&&!fault)),.i_r(decode_r),
   .i_code({frame_hi,frame_lo,pc_code}),.o_v(decode_v),.o_r(state==PREDECODE&&decode_v),
   .o_data(decoded_header),.o_bad(decode_bad));
 end else begin:direct_header
  assign decoded_header=0;assign decode_v=0;assign decode_r=0;assign decode_bad=0;
 end
 // ECC errors in immutable source words are recorded before dispatch; during
 // ownership raw output errors also fail the continuously held original CP tuple.
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin ecc_fault_q<=0;checked_valid_q<=0;end
  else begin
   ecc_fault_q<=ecc_fault_q||raw_bad;
   if(state==IDLE)checked_valid_q<=0;
   else if(state==PREDECODE&&decode_v&&!decode_bad)checked_valid_q<=1;
  end
 end
 assign held_job=frame[31:0];assign held_gen=frame[35:32];
 assign held_token=frame[52:36];assign held_pos=frame[72:53];assign selected_pc=REGISTERED_OUTPUTS?decoded_header[31:0]:p[31:0];
 wire entry=launch_pc==32'h80000004||launch_pc==32'hc0000004;
 wire checked_frame_match=cp_job==held_job&&cp_gen==held_gen&&launch_token==held_token&&launch_pos==held_pos&&launch_pc==selected_pc;
 // PREDECODE cannot dispatch. Check the complete captured header at its
 // registered return, avoiding a decoded-source comparator in the recurrence.
 wire source_frame=REGISTERED_OUTPUTS?(state==PREDECODE?1'b1:checked_frame_match):
  (cp_job==held_job&&cp_gen==held_gen&&launch_token==held_token&&launch_pos==held_pos);
 wire checked_shape=decoded_header[63:32]==0&&decoded_header[191:137]==0;
 wire checked_phase=state!=IDLE&&state!=PREDECODE&&state!=QUALIFY;
 wire checked_fault=REGISTERED_OUTPUTS&&checked_phase&&(!checked_valid_q||!checked_frame_match);
 wire qualified_fault,recurrence_fault;
 if(REGISTERED_STATUS)begin:registered_status
 // Owner checks are independently registered before protected-state update.
 // Current exact-match veto is retained at every external handshake: a
 // stale qualified frame can never ACK a changed live CP owner.
 reg [4:0] owner_match_q;reg shape_q,qualification_fault_q,qualification_fault_n;
 wire qualified_sticky=qualification_fault_q||!qualification_fault_n;
 // Dual-rail output status: a single mutable status-bit fault suppresses its
 // positive permit and quarantines the transaction, never creates CP done.
 // [6:0] = selected,done,release,quiet,owned,lease,pending.
 reg [6:0] status_q,status_n;
 wire rails_bad=status_q!=~status_n;
 wire [6:0] checked_status=status_q&~status_n;
 wire live_veto=state!=IDLE&&checked_valid_q&&(!checked_frame_match||!checked_shape);
 wire instant_fault=exec_fault||shared_fault||ecc_fault_q||c[65]||rails_bad||live_veto;
 assign qualified_fault=qualified_sticky||instant_fault;
 assign recurrence_fault=qualified_sticky||exec_fault||shared_fault||ecc_fault_q;
 assign fault=qualified_fault;
 assign native_launch=entry?2'b0:launch_v;
 assign selected=checked_status[6]||(entry&&|launch_v);
 assign pending=checked_status[0]&&!lease_granted&&!fault;
 assign lease_v=checked_status[1]&&checked_valid_q&&!lease_granted&&!fault;
 assign owned=checked_status[2]&&lease_granted&&!fault;
 assign quiet=checked_status[3]&&!lease_granted&&!fault;
 assign release_v=checked_status[4]&&lease_granted&&exec_done&&retired_original_ops==4&&!fault;
 assign done=checked_status[5]&&!lease_granted&&!exec_done&&!fault;
 reg [6:0] next_status;
 always @*begin
  next_status=0;
  next_status[6]=state!=IDLE||(entry&&|launch_v);
  next_status[3]=(state==IDLE||state==PREDECODE||state==QUALIFY||state==PENDING)&&!lease_granted;
  next_status[0]=state==PENDING&&!lease_granted;
  next_status[1]=state==PENDING&&checked_valid_q&&(&owner_match_q)&&shape_q&&!lease_granted;
  next_status[2]=(state==PENDING||state==ACTIVE||state==RELEASE||state==CLEANUP)&&
   lease_granted&&checked_valid_q&&(&owner_match_q)&&shape_q;
  next_status[4]=(state==ACTIVE||state==RELEASE)&&lease_granted&&exec_done&&retired_original_ops==4&&
   checked_valid_q&&(&owner_match_q)&&shape_q;
  // Drop the held release permit on its actual accepted edge, not on an
  // inferred executor completion. Keep the debt alive through cleanup.
  if(release_v&&release_r)next_status[4]=0;
  next_status[5]=state==CLEANUP&&!lease_granted&&!exec_done&&checked_valid_q&&(&owner_match_q)&&shape_q;
  if(qualified_sticky||exec_fault||shared_fault||ecc_fault_q||c[65]||rails_bad)next_status[5:0]=0;
 end
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   owner_match_q<=0;shape_q<=0;qualification_fault_q<=0;qualification_fault_n<=1;
   status_q<=7'b0001000;status_n<=~7'b0001000;
  end else begin
   status_q<=next_status;status_n<=~next_status;
   if(decode_v||checked_valid_q)begin
    owner_match_q<={launch_pc==selected_pc,launch_pos==held_pos,launch_token==held_token,
                    cp_gen==held_gen,cp_job==held_job};
    shape_q<=checked_shape;
   end else begin owner_match_q<=0;shape_q<=0;end
   if(instant_fault||state==FAIL||
      (state==IDLE&&entry&&|launch_v&&launch_v!=2'b01)||
      ((state==QUALIFY||checked_phase)&&(!checked_valid_q||!(&owner_match_q)||!shape_q))||
      (state==PREDECODE&&decode_v&&decode_bad)||
      ((state==ACTIVE||state==RELEASE)&&!lease_granted)||
      (state==ACTIVE&&exec_done&&retired_original_ops!=4)||
      (state!=IDLE&&state!=DONE&&|launch_v))
    begin qualification_fault_q<=1;qualification_fault_n<=0;end
  end
 end
 end else begin:direct_status
 assign qualified_fault=0;assign recurrence_fault=fault;
 assign selected=state!=IDLE||(entry&&|launch_v);
 assign native_launch=entry?2'b0:launch_v;
 assign fault=bad||state==FAIL||exec_fault||shared_fault||checked_fault;
 assign pending=state==PENDING;
 assign lease_v=pending&&!fault;
 // Actual shared grant stays the executor's owned input through its FINISHED.
 assign owned=lease_granted&&!fault;
 assign quiet=(state==IDLE||state==PREDECODE||state==PENDING)&&!lease_granted&&!exec_fault&&!fault;
 assign release_v=state==RELEASE&&exec_done&&retired_original_ops==4&&!fault;
 // One CP done edge follows accepted release and actual executor cleanup.
 assign done=state==DONE&&!fault;
 end
 reg [127:0] captured;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin control<=ot_gpu_w6_secded_pkg::encode64(0);pc_code<=ot_gpu_w6_secded_pkg::encode64(0);frame_lo<=ot_gpu_w6_secded_pkg::encode64(0);frame_hi<=ot_gpu_w6_secded_pkg::encode64(0);end
  else if(recurrence_fault||
    (!REGISTERED_STATUS&&state!=IDLE&&!source_frame)||
    (state!=IDLE&&state!=DONE&&|launch_v))control<=ot_gpu_w6_secded_pkg::encode64(64'(FAIL));
  else case(state)
   IDLE:if(|launch_v&&entry)begin
    if(launch_v!=2'b01)control<=ot_gpu_w6_secded_pkg::encode64(64'(FAIL));
    else begin
     captured={55'b0,launch_pos,launch_token,cp_gen,cp_job};
     frame_lo<=ot_gpu_w6_secded_pkg::encode64(captured[63:0]);frame_hi<=ot_gpu_w6_secded_pkg::encode64(captured[127:64]);
     pc_code<=ot_gpu_w6_secded_pkg::encode64({32'b0,launch_pc});control<=ot_gpu_w6_secded_pkg::encode64(REGISTERED_OUTPUTS?64'(PREDECODE):64'(PENDING));
    end
   end
   PREDECODE:if(decode_v)begin
    if(REGISTERED_STATUS)begin
     if(decode_bad)control<=ot_gpu_w6_secded_pkg::encode64(64'(FAIL));
     else control<=ot_gpu_w6_secded_pkg::encode64(64'(QUALIFY));
    end else if(decode_bad||!checked_shape||!checked_frame_match)control<=ot_gpu_w6_secded_pkg::encode64(64'(FAIL));
    else control<=ot_gpu_w6_secded_pkg::encode64(64'(PENDING));
   end
   QUALIFY:control<=ot_gpu_w6_secded_pkg::encode64(64'(PENDING));
   PENDING:if(lease_granted)control<=ot_gpu_w6_secded_pkg::encode64(64'(ACTIVE));
   ACTIVE:if(!lease_granted)control<=ot_gpu_w6_secded_pkg::encode64(64'(FAIL));
    else if(exec_done)begin
     if(retired_original_ops!=4)control<=ot_gpu_w6_secded_pkg::encode64(64'(FAIL));else control<=ot_gpu_w6_secded_pkg::encode64(64'(RELEASE));
    end
   RELEASE:if(!lease_granted)control<=ot_gpu_w6_secded_pkg::encode64(64'(FAIL));
    else if(release_v&&release_r)control<=ot_gpu_w6_secded_pkg::encode64(64'(CLEANUP));
   CLEANUP:if(!lease_granted&&!exec_done)control<=ot_gpu_w6_secded_pkg::encode64(64'(DONE));
   DONE:control<=ot_gpu_w6_secded_pkg::encode64(64'(IDLE));
   default:control<=ot_gpu_w6_secded_pkg::encode64(64'(FAIL));
  endcase
 end
 end endgenerate
endmodule
