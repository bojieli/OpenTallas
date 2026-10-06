`timescale 1ns/1ps
// Existing CP LAUNCH -> actual shared SU lease. No second borrower/GO authority.
// Original W6 header/control rows; opt-in boundary control uses protected phase rails.
module ot_hbm_integrated_su_cp_bind #(parameter integer ENABLE=0,REGISTERED_OUTPUTS=0,REGISTERED_STATUS=0,REGISTERED_BOUNDARY=0,GROUPED_OWNER_BOUNDARY=0,BALANCED_OWNER_BOUNDARY=0,FOUR_COMBINATIONAL_CUTS=0,FAST_OWNER_FRONTIER=0,PARALLEL_PHASE_VALIDATION=0,CONTROL_TAIL_CUT=0,OWNER_VETO_POLARITY=0)(
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
 output wire [16:0] held_token,output wire [19:0] held_pos,output wire [11:0] owned_frontier_terms
);
 initial if(OWNER_VETO_POLARITY&&!PARALLEL_PHASE_VALIDATION)
  $fatal(1,"negative owner veto requires exact fast parallel-phase boundary");
 initial if(CONTROL_TAIL_CUT&&!PARALLEL_PHASE_VALIDATION)
  $fatal(1,"control tail requires exact parallel phase and fast frontier");
 initial if(PARALLEL_PHASE_VALIDATION&&!FAST_OWNER_FRONTIER)
  $fatal(1,"parallel phase requires measured fast frontier parent");
 if(ENABLE==0||!FAST_OWNER_FRONTIER)assign owned_frontier_terms=0;
 initial if(FAST_OWNER_FRONTIER&&!FOUR_COMBINATIONAL_CUTS)$fatal(1,"fast frontier requires four cuts");
 generate if(ENABLE==0)begin:off
 assign native_launch=launch_v;assign lease_v=0;assign release_v=0;
 assign owned=0;assign pending=0;assign quiet=1;assign selected=0;
 assign done=0;assign fault=0;assign selected_pc=0;assign held_job=0;
 assign held_gen=0;assign held_token=0;assign held_pos=0;
 end else begin:on
 localparam [3:0] IDLE=0,PENDING=1,ACTIVE=2,RELEASE=3,CLEANUP=4,DONE=5,PREDECODE=6,FAIL=7,QUALIFY=8;
 reg [71:0] control,pc_code,frame_lo,frame_hi;
 wire [65:0] c=ot_gpu_w6_secded_pkg::decode64(control),p=ot_gpu_w6_secded_pkg::decode64(pc_code),lo=ot_gpu_w6_secded_pkg::decode64(frame_lo),hi=ot_gpu_w6_secded_pkg::decode64(frame_hi);
 // Restricted transaction control has a protected one-hot successor. The
 // original W6 control encoding remains selected byte-for-byte with flag0.
 reg [8:0] phase_q,phase_n;
 wire phase_rails_bad=phase_q!=~phase_n;
 wire [8:0] phase=phase_q&~phase_n;
 // One-hot validity: short three-bit groups, no wide subtract/popcount.
 wire [2:0] phase_groups={|phase[8:6],|phase[5:3],|phase[2:0]};
 wire phase_shape_bad=!(|phase)||
  (phase[0]&&phase[1])||(phase[0]&&phase[2])||(phase[1]&&phase[2])||
  (phase[3]&&phase[4])||(phase[3]&&phase[5])||(phase[4]&&phase[5])||
  (phase[6]&&phase[7])||(phase[6]&&phase[8])||(phase[7]&&phase[8])||
  (phase_groups[0]&&phase_groups[1])||(phase_groups[0]&&phase_groups[2])||(phase_groups[1]&&phase_groups[2]);
 wire four_phase_valid,four_entry;
 wire [127:0] capture_frame={55'd0,launch_pos,launch_token,cp_gen,cp_job};
 wire [71:0] four_pc_code,four_frame_lo,four_frame_hi;
 if(FOUR_COMBINATIONAL_CUTS)begin:four_combinational_cuts
  initial if(FAST_OWNER_FRONTIER&&!FOUR_COMBINATIONAL_CUTS)$fatal(1,"fast frontier requires exact four cuts");
  initial if(!BALANCED_OWNER_BOUNDARY)$fatal(1,"four cuts require balanced registered boundary");
  if(PARALLEL_PHASE_VALIDATION)begin:parallel_phase
   ot_hbm_cp_parallel_phase phase_check(.q(phase_q),.n(phase_n),.valid(four_phase_valid));
  end else begin:retained_phase
   ot_hbm_cp_four_phase phase_check(.q(phase_q),.n(phase_n),.valid(four_phase_valid));
  end
  if(FAST_OWNER_FRONTIER)begin:fast_entry
   ot_hbm_cp_frontier_entry entry_check(.pc(launch_pc),.entry(four_entry));
  end else begin:prior_entry
   ot_hbm_cp_four_entry entry_check(.pc(launch_pc),.entry(four_entry));
  end
  ot_hbm_cp_four_encode pc_encoder(.data({32'd0,launch_pc}),.code(four_pc_code));
  ot_hbm_cp_four_encode lo_encoder(.data(capture_frame[63:0]),.code(four_frame_lo));
  ot_hbm_cp_four_encode hi_encoder(.data(capture_frame[127:64]),.code(four_frame_hi));
 end else begin:four_cuts_off
  assign four_phase_valid=0;assign four_entry=0;
  assign four_pc_code=0;assign four_frame_lo=0;assign four_frame_hi=0;
 end
 wire phase_bad=FOUR_COMBINATIONAL_CUTS?!four_phase_valid:(phase_rails_bad||phase_shape_bad);
 reg [3:0] boundary_state;
 always @*begin
  boundary_state=FAIL;
  case(phase)
   9'b000000001:boundary_state=IDLE;
   9'b000000010:boundary_state=PENDING;
   9'b000000100:boundary_state=ACTIVE;
   9'b000001000:boundary_state=RELEASE;
   9'b000010000:boundary_state=CLEANUP;
   9'b000100000:boundary_state=DONE;
   9'b001000000:boundary_state=PREDECODE;
   9'b010000000:boundary_state=FAIL;
   9'b100000000:boundary_state=QUALIFY;
   default:boundary_state=FAIL;
  endcase
 end
 wire control_bad=REGISTERED_BOUNDARY?phase_bad:c[65];
 wire raw_bad=control_bad||p[65]||lo[65]||hi[65];
 wire [3:0] state=REGISTERED_BOUNDARY?boundary_state:(REGISTERED_STATUS?c[3:0]:{1'b0,c[2:0]});
 wire is_idle=REGISTERED_BOUNDARY?phase[IDLE]:(state==IDLE);
 wire is_pending=REGISTERED_BOUNDARY?phase[PENDING]:(state==PENDING);
 wire is_active=REGISTERED_BOUNDARY?phase[ACTIVE]:(state==ACTIVE);
 wire is_release=REGISTERED_BOUNDARY?phase[RELEASE]:(state==RELEASE);
 wire is_cleanup=REGISTERED_BOUNDARY?phase[CLEANUP]:(state==CLEANUP);
 wire is_done=REGISTERED_BOUNDARY?phase[DONE]:(state==DONE);
 wire is_predecode=REGISTERED_BOUNDARY?phase[PREDECODE]:(state==PREDECODE);
 wire is_fail=REGISTERED_BOUNDARY?phase[FAIL]:(state==FAIL);
 wire is_qualify=REGISTERED_BOUNDARY?phase[QUALIFY]:(state==QUALIFY);
 wire [191:0] decoded_header;wire decode_v,decode_r,decode_bad;
 reg ecc_fault_q,checked_valid_q;
 reg decoder_start_q;
 initial if(REGISTERED_BOUNDARY&&!REGISTERED_STATUS)
  $fatal(1,"registered boundary requires registered status");
 initial if(BALANCED_OWNER_BOUNDARY&&(!REGISTERED_BOUNDARY||GROUPED_OWNER_BOUNDARY))
  $fatal(1,"balanced owner boundary requires serial registered boundary, not rejected grouped candidate");
 initial if(GROUPED_OWNER_BOUNDARY&&!REGISTERED_BOUNDARY)
  $fatal(1,"grouped owner boundary requires registered boundary");
 initial if(REGISTERED_STATUS&&!REGISTERED_OUTPUTS)
  $fatal(1,"registered status requires checked registered header");
 // A dedicated one-bit request cut removes protected control decode/fault
 // fanout from the three header capture banks. Encoded header was captured
 // at the preceding launch edge and remains immutable until completion.
 always @(posedge clk or negedge por_n)begin
  if(!por_n)decoder_start_q<=0;
  else decoder_start_q<=is_idle&&launch_v==2'b01&&entry&&!fault;
 end
 wire [127:0] original_frame={hi[63:0],lo[63:0]};
 wire [127:0] frame=REGISTERED_OUTPUTS?decoded_header[191:64]:original_frame;
 wire bad=REGISTERED_OUTPUTS?ecc_fault_q:raw_bad;
 if(REGISTERED_OUTPUTS)begin:registered_header
  ot_hbm_integrated_header_decode decoder(
   .clk(clk),.por_n(por_n),.i_v(REGISTERED_STATUS?decoder_start_q:(is_predecode&&!fault)),.i_r(decode_r),
   .i_code({frame_hi,frame_lo,pc_code}),.o_v(decode_v),.o_r(is_predecode&&decode_v),
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
   if(is_idle)checked_valid_q<=0;
   else if(is_predecode&&decode_v&&!decode_bad)checked_valid_q<=1;
  end
 end
 assign held_job=frame[31:0];assign held_gen=frame[35:32];
 assign held_token=frame[52:36];assign held_pos=frame[72:53];assign selected_pc=REGISTERED_OUTPUTS?decoded_header[31:0]:p[31:0];
 wire entry=FOUR_COMBINATIONAL_CUTS?four_entry:(launch_pc==32'h80000004||launch_pc==32'hc0000004);
 wire checked_frame_match=cp_job==held_job&&cp_gen==held_gen&&launch_token==held_token&&launch_pos==held_pos&&launch_pc==selected_pc;
 // PREDECODE cannot dispatch. Check the complete captured header at its
 // registered return, avoiding a decoded-source comparator in the recurrence.
 wire source_frame=REGISTERED_OUTPUTS?(is_predecode?1'b1:checked_frame_match):
  (cp_job==held_job&&cp_gen==held_gen&&launch_token==held_token&&launch_pos==held_pos);
 wire checked_shape=decoded_header[63:32]==0&&decoded_header[191:137]==0;
 wire checked_phase=!is_idle&&!is_predecode&&!is_qualify;
 wire checked_fault=REGISTERED_OUTPUTS&&checked_phase&&(!checked_valid_q||!checked_frame_match);
 wire qualified_fault,recurrence_fault;
 wire balanced_release_accept;
 wire release_accept=BALANCED_OWNER_BOUNDARY?balanced_release_accept:(release_v&&release_r);
 if(!BALANCED_OWNER_BOUNDARY)assign balanced_release_accept=0;
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
 wire [2:0] frontier_equal64;
 if(!FAST_OWNER_FRONTIER)assign frontier_equal64=0;
 wire live_veto=!is_idle&&checked_valid_q&&(FAST_OWNER_FRONTIER?!(&frontier_equal64):(!checked_frame_match||!checked_shape));
 wire instant_fault=exec_fault||shared_fault||ecc_fault_q||control_bad||rails_bad||live_veto;
 assign qualified_fault=qualified_sticky||instant_fault;
 assign recurrence_fault=qualified_sticky||exec_fault||shared_fault||ecc_fault_q;
 assign native_launch=entry?2'b0:launch_v;
 assign selected=checked_status[6]||(entry&&|launch_v);
 // Distributed positive boundary qualification avoids the state-qualified
 // mismatch->instant_fault->sticky/error OR->inversion cone at every output.
 // The current complete owner/PC and padding still deny on THIS SAME edge.
 wire boundary_ok=!qualified_sticky&&!exec_fault&&!shared_fault&&!ecc_fault_q&&!control_bad&&!rails_bad;
 wire current_owner_ok=checked_valid_q&&checked_frame_match&&checked_shape;
 wire permit_ok=REGISTERED_BOUNDARY?(boundary_ok&&current_owner_ok):!fault;
 wire idle_ok=REGISTERED_BOUNDARY?(boundary_ok&&(!checked_valid_q||is_idle||current_owner_ok)):!fault;
 if(BALANCED_OWNER_BOUNDARY)begin:balanced_owner_boundary
  // Complete current PC/frame/padding, not a hash or a registered permission.
  // 192 bits ->48 four-bit bit_match ->12 mismatch groups ->3 equal64 roots.
  // Keep alternating NOR/NAND boundaries to prevent positive permit chaining.
  wire [191:0] live_header={55'd0,launch_pos,launch_token,cp_gen,cp_job,32'd0,launch_pc};
  wire [47:0] match4;
  wire [11:0] mismatch16;
  wire [2:0] equal64;
  wire all_owner_ok;
  if(OWNER_VETO_POLARITY)begin:shared_full_owner_veto
   ot_hbm_cp_frontier_nor3 root(.bits(~equal64),.result(all_owner_ok));
  end else assign all_owner_ok=1'b0;
  if(FAST_OWNER_FRONTIER)begin:fast_owner
   for(genvar k=0;k<3;k=k+1)begin:g
    if(OWNER_VETO_POLARITY)begin:negative_compare
     wire mismatch;
     ot_hbm_cp_owner_veto64 compare(.held_n(~decoded_header[k*64+:64]),.live(live_header[k*64+:64]),.mismatch(mismatch));
     assign equal64[k]=~mismatch;
    end else begin:positive_compare
    ot_hbm_cp_frontier_equal64 compare(.held_n(~decoded_header[k*64+:64]),.live(live_header[k*64+:64]),.equal(equal64[k]));
    end
   end
   assign frontier_equal64=equal64;
  end else begin:prior_owner
  for(genvar k=0;k<48;k=k+1)begin:owner_leaves
   ot_hbm_integrated_cp_match4 leaf(
    .held(decoded_header[k*4+:4]),.live(live_header[k*4+:4]),.equal(match4[k]));
  end
  for(genvar k=0;k<12;k=k+1)begin:owner_middle
   ot_hbm_integrated_cp_nand4 middle(.bits(match4[k*4+:4]),.result(mismatch16[k]));
  end
  for(genvar k=0;k<3;k=k+1)begin:owner_roots
   ot_hbm_integrated_cp_nor4 root(.bits(mismatch16[k*4+:4]),.result(equal64[k]));
  end
  end
  wire [4:0] local_ok;
  assign local_ok[0]=boundary_ok&&checked_valid_q&&checked_status[0]&&!lease_granted;
  assign local_ok[1]=boundary_ok&&checked_valid_q&&checked_status[1]&&!lease_granted;
  assign local_ok[2]=boundary_ok&&checked_valid_q&&checked_status[2]&&lease_granted;
  assign local_ok[3]=boundary_ok&&checked_valid_q&&checked_status[4]&&lease_granted&&exec_done&&retired_original_ops==4;
  assign local_ok[4]=boundary_ok&&checked_valid_q&&checked_status[5]&&!lease_granted&&!exec_done;
  wire live_owner_bad=!(&equal64);
  if(OWNER_VETO_POLARITY)begin:negative_owner_frontiers
   // All current192 identity bits participate on this edge. Local controls
   // settle independently; no output permit feeds the protected next phase.
   wire [2:0] owner_bad=~equal64;
   wire errors_ok=~|{qualified_sticky,exec_fault,shared_fault,ecc_fault_q};
   wire base_ok=four_phase_valid&&errors_ok&&!rails_bad;
   wire valid_ok=base_ok&&checked_valid_q;
   wire pending_ok=valid_ok&&checked_status[0]&&!lease_granted;
   wire lease_ok=valid_ok&&checked_status[1]&&!lease_granted;
   wire owned_ok=valid_ok&&checked_status[2]&&lease_granted;
   wire release_ok=valid_ok&&checked_status[4]&&lease_granted&&exec_done&&retired_original_ops==4;
   wire done_ok=valid_ok&&checked_status[5]&&!lease_granted&&!exec_done;
   assign owned_frontier_terms={3'b111,equal64,four_phase_valid,errors_ok,!rails_bad,checked_valid_q,checked_status[2],lease_granted};
   ot_hbm_cp_veto_nor4 pending_gate(.bad({owner_bad,!pending_ok}),.permit(pending));
   ot_hbm_cp_veto_nor4 lease_gate(.bad({owner_bad,!lease_ok}),.permit(lease_v));
   ot_hbm_cp_veto_nor4 owned_gate(.bad({owner_bad,!owned_ok}),.permit(owned));
   ot_hbm_cp_veto_nor4 release_gate(.bad({owner_bad,!release_ok}),.permit(release_v));
   ot_hbm_cp_veto_nor4 accept_gate(.bad({owner_bad,!(release_ok&&release_r)}),.permit(balanced_release_accept));
   ot_hbm_cp_veto_nor4 done_gate(.bad({owner_bad,!done_ok}),.permit(done));
   ot_hbm_cp_veto_conditional #(.NEGATIVE(0)) quiet_gate(
    .local_ok(base_ok&&checked_status[3]&&!lease_granted),.owner_ok(all_owner_ok),
    .bypass(is_idle||!checked_valid_q),.result(quiet));
  end else if(FOUR_COMBINATIONAL_CUTS)begin:four_output_frontiers
   // Independent positive factors join only at the final balanced boundary.
   // Full current192-bit owner and current mutable phase/status veto remain.
   wire errors_ok=~|{qualified_sticky,exec_fault,shared_fault,ecc_fault_q};
   if(FAST_OWNER_FRONTIER)assign owned_frontier_terms={3'b111,equal64,four_phase_valid,errors_ok,!rails_bad,checked_valid_q,checked_status[2],lease_granted};
   ot_hbm_cp_frontier_and12 #(.FAST(FAST_OWNER_FRONTIER),.RETAINED_TAIL(CONTROL_TAIL_CUT),.OWNER_LSB(6)) pending_gate(.bits({3'b111,equal64,four_phase_valid,errors_ok,!rails_bad,checked_valid_q,checked_status[0],!lease_granted}),.result(pending));
   ot_hbm_cp_frontier_and12 #(.FAST(FAST_OWNER_FRONTIER),.RETAINED_TAIL(CONTROL_TAIL_CUT),.OWNER_LSB(6)) lease_gate(.bits({3'b111,equal64,four_phase_valid,errors_ok,!rails_bad,checked_valid_q,checked_status[1],!lease_granted}),.result(lease_v));
   ot_hbm_cp_frontier_and12 #(.FAST(FAST_OWNER_FRONTIER),.RETAINED_TAIL(CONTROL_TAIL_CUT),.OWNER_LSB(6)) owned_gate(.bits({3'b111,equal64,four_phase_valid,errors_ok,!rails_bad,checked_valid_q,checked_status[2],lease_granted}),.result(owned));
   ot_hbm_cp_frontier_and12 #(.FAST(FAST_OWNER_FRONTIER),.RETAINED_TAIL(CONTROL_TAIL_CUT),.OWNER_LSB(8)) release_gate(.bits({1'b1,equal64,four_phase_valid,errors_ok,!rails_bad,checked_valid_q,checked_status[4],lease_granted,exec_done,retired_original_ops==4}),.result(release_v));
   ot_hbm_cp_frontier_and12 #(.FAST(FAST_OWNER_FRONTIER),.RETAINED_TAIL(CONTROL_TAIL_CUT),.OWNER_LSB(9)) accept_gate(.bits({equal64,four_phase_valid,errors_ok,!rails_bad,checked_valid_q,checked_status[4],lease_granted,exec_done,retired_original_ops==4,release_r}),.result(balanced_release_accept));
   ot_hbm_cp_frontier_and12 #(.FAST(FAST_OWNER_FRONTIER),.RETAINED_TAIL(CONTROL_TAIL_CUT),.OWNER_LSB(7)) done_gate(.bits({2'b11,equal64,four_phase_valid,errors_ok,!rails_bad,checked_valid_q,checked_status[5],!lease_granted,!exec_done}),.result(done));
   wire bypass_owner=is_idle||!checked_valid_q;
   wire [2:0] quiet_owner=equal64|{3{bypass_owner}};
   if(CONTROL_TAIL_CUT==2)begin:late_quiet
    wire early_ok,owner_bad,owner_permit;
    ot_hbm_cp_frontier_and12 #(.FAST(1),.RETAINED_TAIL(1)) early_gate(.bits({7'b1111111,four_phase_valid,errors_ok,!rails_bad,checked_status[3],!lease_granted}),.result(early_ok));
    ot_hbm_cp_frontier_nand3 late_owner(.bits(equal64),.result(owner_bad));
    ot_hbm_cp_phase_nand2 bypass(.bits({owner_bad,!bypass_owner}),.result(owner_permit));
    ot_hbm_cp_control_tail_and2 tail(.bits({early_ok,owner_permit}),.result(quiet));
   end else begin:prior_quiet
   ot_hbm_cp_frontier_and12 #(.FAST(FAST_OWNER_FRONTIER),.RETAINED_TAIL(CONTROL_TAIL_CUT),.OWNER_LSB(5)) quiet_gate(.bits({4'b1111,quiet_owner,four_phase_valid,errors_ok,!rails_bad,checked_status[3],!lease_granted}),.result(quiet));
   end
  end else begin:original_balanced_frontiers
  ot_hbm_integrated_cp_and4 pending_gate(.bits({equal64,local_ok[0]}),.result(pending));
  ot_hbm_integrated_cp_and4 lease_gate(.bits({equal64,local_ok[1]}),.result(lease_v));
  ot_hbm_integrated_cp_and4 owned_gate(.bits({equal64,local_ok[2]}),.result(owned));
  ot_hbm_integrated_cp_and4 release_gate(.bits({equal64,local_ok[3]}),.result(release_v));
  ot_hbm_integrated_cp_and4 done_gate(.bits({equal64,local_ok[4]}),.result(done));
  // Independent acceptance cone includes every release predicate and real r.
  // It never uses the external output gate as next-phase logic input.
  wire accept_local=local_ok[3]&&release_r;
  ot_hbm_integrated_cp_and4 accept_gate(.bits({equal64,accept_local}),.result(balanced_release_accept));
  assign quiet=boundary_ok&&checked_status[3]&&!lease_granted&&
               (is_idle||!checked_valid_q||!live_owner_bad);
  end
  if(OWNER_VETO_POLARITY)begin:negative_fault_tail
   wire local_ok=four_phase_valid&&!rails_bad&&!(qualified_sticky||exec_fault||shared_fault||ecc_fault_q);
   ot_hbm_cp_veto_conditional #(.NEGATIVE(1)) fault_gate(
    .local_ok(local_ok),.owner_ok(all_owner_ok),.bypass(is_idle||!checked_valid_q),.result(fault));
  end else if(CONTROL_TAIL_CUT)begin:retained_fault_tail
   // Same current-owner scope as the original live veto. This reduction
   // creates no permission or held authority and does not gate accepted debt.
   wire [2:0] fault_owner=equal64|{3{is_idle||!checked_valid_q}};
   wire fault_free;
   wire errors_ok=~|{qualified_sticky,exec_fault,shared_fault,ecc_fault_q};
   ot_hbm_cp_frontier_and12 #(.FAST(1),.RETAINED_TAIL(1)) fault_gate(
    .bits({5'b11111,fault_owner,four_phase_valid,!rails_bad,errors_ok,1'b1}),.result(fault_free));
   assign fault=!fault_free;
  end else begin:original_fault_tail
  assign fault=!boundary_ok||(!is_idle&&checked_valid_q&&live_owner_bad);
  end
 end else if(GROUPED_OWNER_BOUNDARY)begin:grouped_owner_boundary
  // Complete PC64/frame128 comparison includes every zero padding bit.
  // Byte groups are independent combinational frontiers, not registered
  // owner permission. A changed live tuple denies on the original edge.
  wire [191:0] live_header={55'd0,launch_pos,launch_token,cp_gen,cp_job,32'd0,launch_pc};
  wire [23:0] owner_mismatch;
  for(genvar byte_index=0;byte_index<24;byte_index=byte_index+1)begin:bytes
   (* keep_hierarchy = "yes" *) ot_hbm_integrated_cp_owner_byte compare_byte(
    .held(decoded_header[byte_index*8+:8]),.live(live_header[byte_index*8+:8]),
    .mismatch(owner_mismatch[byte_index]));
  end
  // Carry the independent veto terms into each final reduction. Do not
  // serialize full-owner equality -> current_owner_ok -> permit_ok -> output.
  wire [5:0] error_veto={qualified_sticky,exec_fault,shared_fault,ecc_fault_q,
                       control_bad,rails_bad};
  assign pending=~(|{owner_mismatch,error_veto,!checked_valid_q,
                     !checked_status[0],lease_granted});
  assign lease_v=~(|{owner_mismatch,error_veto,!checked_valid_q,
                     !checked_status[1],lease_granted});
  assign owned=~(|{owner_mismatch,error_veto,!checked_valid_q,
                   !checked_status[2],!lease_granted});
  assign release_v=~(|{owner_mismatch,error_veto,!checked_valid_q,
                       !checked_status[4],!lease_granted,!exec_done,
                       retired_original_ops!=4});
  assign done=~(|{owner_mismatch,error_veto,!checked_valid_q,
                  !checked_status[5],lease_granted,exec_done});
  wire [23:0] live_fault_mismatch=owner_mismatch &
                                 {24{!is_idle&&checked_valid_q}};
  assign quiet=~(|{live_fault_mismatch,error_veto,!checked_status[3],lease_granted});
  assign fault=|{live_fault_mismatch,error_veto};
 end else begin:serial_owner_boundary
  assign fault=qualified_fault;
  assign pending=checked_status[0]&&!lease_granted&&permit_ok;
  assign lease_v=checked_status[1]&&checked_valid_q&&!lease_granted&&permit_ok;
  assign owned=checked_status[2]&&lease_granted&&permit_ok;
  assign quiet=checked_status[3]&&!lease_granted&&idle_ok;
  assign release_v=checked_status[4]&&lease_granted&&exec_done&&retired_original_ops==4&&permit_ok;
  assign done=checked_status[5]&&!lease_granted&&!exec_done&&permit_ok;
 end
 reg [6:0] next_status;
 always @*begin
  next_status=0;
  next_status[6]=!is_idle||(entry&&|launch_v);
  // A corrupt phase must not erase an already selected held transaction,
  // even if the corrupted rail transiently also asserts the IDLE bit.
  if(REGISTERED_BOUNDARY&&control_bad&&checked_status[6])next_status[6]=1;
  next_status[3]=(is_idle||is_predecode||is_qualify||is_pending)&&!lease_granted;
  next_status[0]=is_pending&&!lease_granted;
  next_status[1]=is_pending&&checked_valid_q&&(&owner_match_q)&&shape_q&&!lease_granted;
  next_status[2]=(is_pending||is_active||is_release||is_cleanup)&&
   lease_granted&&checked_valid_q&&(&owner_match_q)&&shape_q;
  next_status[4]=(is_active||is_release)&&lease_granted&&exec_done&&retired_original_ops==4&&
   checked_valid_q&&(&owner_match_q)&&shape_q;
  // Drop the held release permit on its actual accepted edge, not on an
  // inferred executor completion. Keep the debt alive through cleanup.
  if(release_accept)next_status[4]=0;
  next_status[5]=is_cleanup&&!lease_granted&&!exec_done&&checked_valid_q&&(&owner_match_q)&&shape_q;
  if(qualified_sticky||exec_fault||shared_fault||ecc_fault_q||control_bad||rails_bad)next_status[5:0]=0;
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
   if(instant_fault||is_fail||
      (is_idle&&entry&&|launch_v&&launch_v!=2'b01)||
      ((is_qualify||checked_phase)&&(!checked_valid_q||!(&owner_match_q)||!shape_q))||
      (is_predecode&&decode_v&&decode_bad)||
      ((is_active||is_release)&&!lease_granted)||
      (is_active&&exec_done&&retired_original_ops!=4)||
      (!is_idle&&!is_done&&|launch_v))
    begin qualification_fault_q<=1;qualification_fault_n<=0;end
  end
 end
 end else begin:direct_status
 assign qualified_fault=0;assign recurrence_fault=fault;
 assign selected=!is_idle||(entry&&|launch_v);
 assign native_launch=entry?2'b0:launch_v;
 assign fault=bad||is_fail||exec_fault||shared_fault||checked_fault;
 assign pending=is_pending;
 assign lease_v=pending&&!fault;
 // Actual shared grant stays the executor's owned input through its FINISHED.
 assign owned=lease_granted&&!fault;
 assign quiet=(is_idle||is_predecode||is_pending)&&!lease_granted&&!exec_fault&&!fault;
 assign release_v=is_release&&exec_done&&retired_original_ops==4&&!fault;
 // One CP done edge follows accepted release and actual executor cleanup.
 assign done=is_done&&!fault;
 end
 // The same transaction transitions use direct protected phase rails. No
 // decode64/re-encode64 recurrence or decoded-control launch-enable path.
 if(REGISTERED_BOUNDARY)begin:boundary_control
 reg [8:0] next_phase;
 always @*begin
  next_phase=phase;
  if(BALANCED_OWNER_BOUNDARY)begin
   // Parallel protected one-hot transitions, same priority and accepted edge.
   // No release output -> priority case -> all phase D feedback chain.
   next_phase=0;
   next_phase[IDLE]=(is_idle&&!(|launch_v&&entry))||is_done;
   next_phase[PREDECODE]=(is_idle&&|launch_v&&entry&&launch_v==2'b01)||
                         (is_predecode&&!decode_v);
   next_phase[QUALIFY]=is_predecode&&decode_v&&!decode_bad;
   next_phase[PENDING]=is_qualify||(is_pending&&!lease_granted);
   next_phase[ACTIVE]=(is_pending&&lease_granted)||
                     (is_active&&lease_granted&&!exec_done);
   next_phase[RELEASE]=(is_active&&lease_granted&&exec_done&&retired_original_ops==4)||
                      (is_release&&lease_granted&&!release_accept);
   next_phase[CLEANUP]=(is_release&&release_accept)||
                      (is_cleanup&&(lease_granted||exec_done));
   next_phase[DONE]=is_cleanup&&!lease_granted&&!exec_done;
   next_phase[FAIL]=is_fail||(is_idle&&|launch_v&&entry&&launch_v!=2'b01)||
                    (is_predecode&&decode_v&&decode_bad)||
                    (is_active&&(!lease_granted||(exec_done&&retired_original_ops!=4)))||
                    (is_release&&!lease_granted);
   if(recurrence_fault||phase_bad||(!is_idle&&!is_done&&|launch_v))
    next_phase=9'b010000000;
  end else if(recurrence_fault||phase_bad||(!is_idle&&!is_done&&|launch_v))next_phase=9'b010000000;
  else case(1'b1)
   phase[IDLE]:if(|launch_v&&entry)next_phase=launch_v==2'b01 ? 9'b001000000 : 9'b010000000;
   phase[PREDECODE]:if(decode_v)next_phase=decode_bad ? 9'b010000000 : 9'b100000000;
   phase[QUALIFY]:next_phase=9'b000000010;
   phase[PENDING]:if(lease_granted)next_phase=9'b000000100;
   phase[ACTIVE]:if(!lease_granted)next_phase=9'b010000000;
    else if(exec_done)next_phase=retired_original_ops==4 ? 9'b000001000 : 9'b010000000;
   phase[RELEASE]:if(!lease_granted)next_phase=9'b010000000;
    else if(release_v&&release_r)next_phase=9'b000010000;
   phase[CLEANUP]:if(!lease_granted&&!exec_done)next_phase=9'b000100000;
   phase[DONE]:next_phase=9'b000000001;
   default:next_phase=9'b010000000;
  endcase
 end
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin phase_q<=9'b000000001;phase_n<=~9'b000000001;end
  else begin phase_q<=next_phase;phase_n<=~next_phase;end
 end
 end else begin:legacy_control_encoding
 always @(posedge clk or negedge por_n)begin phase_q<=9'b000000001;phase_n<=~9'b000000001;end
 end
 reg [127:0] captured;
 // Header capture is separated from the W6 control recurrence. In the
 // successor its enable originates from the protected one-hot IDLE phase.
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   pc_code<=ot_gpu_w6_secded_pkg::encode64(0);
   frame_lo<=ot_gpu_w6_secded_pkg::encode64(0);frame_hi<=ot_gpu_w6_secded_pkg::encode64(0);
  end else if(is_idle&&launch_v==2'b01&&entry&&!recurrence_fault&&(!REGISTERED_BOUNDARY||!control_bad))begin
   captured={55'b0,launch_pos,launch_token,cp_gen,cp_job};
   if(FOUR_COMBINATIONAL_CUTS)begin
    frame_lo<=four_frame_lo;frame_hi<=four_frame_hi;pc_code<=four_pc_code;
   end else begin
    frame_lo<=ot_gpu_w6_secded_pkg::encode64(captured[63:0]);frame_hi<=ot_gpu_w6_secded_pkg::encode64(captured[127:64]);
    pc_code<=ot_gpu_w6_secded_pkg::encode64({32'b0,launch_pc});
   end
  end
 end
 always @(posedge clk or negedge por_n)begin
  if(!por_n)control<=ot_gpu_w6_secded_pkg::encode64(0);
  else if(REGISTERED_BOUNDARY)control<=ot_gpu_w6_secded_pkg::encode64(0);
  else if(recurrence_fault||
    (!REGISTERED_STATUS&&!is_idle&&!source_frame)||
    (!is_idle&&!is_done&&|launch_v))control<=ot_gpu_w6_secded_pkg::encode64(64'(FAIL));
  else case(state)
   IDLE:if(|launch_v&&entry)begin
    if(launch_v!=2'b01)control<=ot_gpu_w6_secded_pkg::encode64(64'(FAIL));
    else begin
     control<=ot_gpu_w6_secded_pkg::encode64(REGISTERED_OUTPUTS?64'(PREDECODE):64'(PENDING));
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

// A retained small synthesis boundary keeps the current-owner byte compares
// parallel. No state, clock, inferred permission, or delayed error veto.
(* keep_hierarchy = "yes" *)
module ot_hbm_integrated_cp_owner_byte(
 input wire [7:0] held,live,output wire mismatch
);
 assign mismatch=|(held^live);
endmodule

// Small retained gates form a balanced NOR/NAND owner tree. No storage.
(* keep_hierarchy = "yes" *)
module ot_hbm_integrated_cp_match4(input wire [3:0] held,live,output wire equal);
 assign equal=~|(held^live);
endmodule
(* keep_hierarchy = "yes" *)
module ot_hbm_integrated_cp_nand4(input wire [3:0] bits,output wire result);
 assign result=~&bits;
endmodule
(* keep_hierarchy = "yes" *)
module ot_hbm_integrated_cp_nor4(input wire [3:0] bits,output wire result);
 assign result=~|bits;
endmodule
(* keep_hierarchy = "yes" *)
module ot_hbm_integrated_cp_and4(input wire [3:0] bits,output wire result);
 assign result=&bits;
endmodule

// Additive four-cut namespace: combinational only, no independent owner state.
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_four_and12(input wire [11:0] bits,output wire result);
 wire [2:0] group_ok;
 for(genvar k=0;k<3;k=k+1)begin:g
  ot_hbm_integrated_cp_and4 a(.bits(bits[k*4+:4]),.result(group_ok[k]));
 end
 ot_hbm_integrated_cp_and4 root(.bits({1'b1,group_ok}),.result(result));
endmodule
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_four_phase(input wire [8:0] q,n,output wire valid);
 wire [8:0] legal;
 for(genvar k=0;k<9;k=k+1)begin:word
  localparam [8:0] Q=9'b1<<k;
  wire [17:0] bit_match=~({q,n}^{Q,~Q});
  wire [4:0] leaf;
  for(genvar j=0;j<4;j=j+1)begin:g
   ot_hbm_integrated_cp_and4 a(.bits(bit_match[j*4+:4]),.result(leaf[j]));
  end
  ot_hbm_integrated_cp_and4 tail(.bits({2'b11,bit_match[17:16]}),.result(leaf[4]));
  wire first;
  ot_hbm_integrated_cp_and4 middle(.bits(leaf[3:0]),.result(first));
  ot_hbm_integrated_cp_and4 root(.bits({2'b11,first,leaf[4]}),.result(legal[k]));
 end
 wire [2:0] none;
 ot_hbm_integrated_cp_nor4 g0(.bits(legal[3:0]),.result(none[0]));
 ot_hbm_integrated_cp_nor4 g1(.bits(legal[7:4]),.result(none[1]));
 ot_hbm_integrated_cp_nor4 g2(.bits({3'b0,legal[8]}),.result(none[2]));
 ot_hbm_integrated_cp_nand4 root(.bits({1'b1,none}),.result(valid));
endmodule
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_four_entry(input wire [31:0] pc,output wire entry);
 // Exactly the original two entry PCs; bit30 differs between them. Full live
 // owner equality elsewhere still compares all32 PC bits, without a mask.
 wire [31:0] normalized={pc[31],1'b0,pc[29:0]};
 wire [7:0] leaf;wire [1:0] mismatch;
 for(genvar k=0;k<8;k=k+1)begin:g
  localparam [31:0] EXPECT=32'h80000004;
  ot_hbm_integrated_cp_match4 a(.held(EXPECT[k*4+:4]),.live(normalized[k*4+:4]),.equal(leaf[k]));
 end
 ot_hbm_integrated_cp_nand4 m0(.bits(leaf[3:0]),.result(mismatch[0]));
 ot_hbm_integrated_cp_nand4 m1(.bits(leaf[7:4]),.result(mismatch[1]));
 ot_hbm_integrated_cp_nor4 root(.bits({2'b0,mismatch}),.result(entry));
endmodule
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_four_xor4(input wire [3:0] bits,output wire result);
 assign result=(bits[0]^bits[1])^(bits[2]^bits[3]);
endmodule
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_four_encode(input wire [63:0] data,output wire [71:0] code);
 wire [71:0] original=ot_gpu_w6_secded_pkg::encode64(data);
 assign code[70:0]=original[70:0];
 // XOR of data+seven Hamming parities cancels exactly the data positions
 // with odd code-index popcount. These35 terms retain bit71 byte-exactly.
 wire [35:0] terms={1'b0,data[63],data[60],data[58],data[57],data[56],data[53],data[51],data[50],data[47],data[46],data[44],data[41],data[39],data[38],data[36],data[33],data[32],data[29],data[27],data[26],data[24],data[23],data[21],data[18],data[17],data[14],data[12],data[11],data[10],data[7],data[5],data[4],data[2],data[1],data[0]};
 wire [8:0] leaf;wire [2:0] middle;
 for(genvar k=0;k<9;k=k+1)begin:g
  ot_hbm_cp_four_xor4 a(.bits(terms[k*4+:4]),.result(leaf[k]));
 end
 ot_hbm_cp_four_xor4 m0(.bits(leaf[3:0]),.result(middle[0]));
 ot_hbm_cp_four_xor4 m1(.bits(leaf[7:4]),.result(middle[1]));
 ot_hbm_cp_four_xor4 m2(.bits({3'b0,leaf[8]}),.result(middle[2]));
 ot_hbm_cp_four_xor4 root(.bits({1'b0,middle}),.result(code[71]));
endmodule

// Alternating three-input reductions map to native NAND/NOR boundaries.
// Complement-fed comparison lets the retained negative-Q bank drive a leaf
// without rebuilding positive-Q before the complete current192-bit veto.
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_frontier_nand3(input wire [2:0] bits,output wire result);
 assign result=~&bits;
endmodule
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_frontier_nor3(input wire [2:0] bits,output wire result);
 assign result=~|bits;
endmodule
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_frontier_equal64(input wire [63:0] held_n,live,output wire equal);
 wire [65:0] bit_equal={2'b11,held_n^live};
 wire [23:0] leaf;wire [8:0] middle;wire [2:0] upper;
 assign leaf[23:22]=0;
 for(genvar k=0;k<22;k=k+1)begin:g0
  ot_hbm_cp_frontier_nand3 n(.bits(bit_equal[k*3+:3]),.result(leaf[k]));
 end
 for(genvar k=0;k<8;k=k+1)begin:g1
  ot_hbm_cp_frontier_nor3 n(.bits(leaf[k*3+:3]),.result(middle[k]));
 end
 assign middle[8]=1;
 for(genvar k=0;k<3;k=k+1)begin:g2
  ot_hbm_cp_frontier_nand3 n(.bits(middle[k*3+:3]),.result(upper[k]));
 end
 ot_hbm_cp_frontier_nor3 root(.bits(upper),.result(equal));
endmodule
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_frontier_entry(input wire [31:0] pc,output wire entry);
 wire [31:0] bits=~(pc^32'h80000004)|32'h40000000;
 wire [32:0] bit_equal={1'b1,bits};wire [11:0] leaf;wire [5:0] middle;wire [2:0] upper;
 for(genvar k=0;k<11;k=k+1)begin:g0
  ot_hbm_cp_frontier_nand3 n(.bits(bit_equal[k*3+:3]),.result(leaf[k]));
 end
 assign leaf[11]=0;
 for(genvar k=0;k<4;k=k+1)begin:g1
  ot_hbm_cp_frontier_nor3 n(.bits(leaf[k*3+:3]),.result(middle[k]));
 end
 assign middle[5:4]=2'b11;
 for(genvar k=0;k<2;k=k+1)begin:g2
  ot_hbm_cp_frontier_nand3 n(.bits(middle[k*3+:3]),.result(upper[k]));
 end
 assign upper[2]=0;
 ot_hbm_cp_frontier_nor3 root(.bits(upper),.result(entry));
endmodule
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_frontier_and12 #(parameter integer FAST=0,RETAINED_TAIL=0,OWNER_LSB=6)(input wire [11:0] bits,output wire result);
 if(!FAST)begin:prior
  ot_hbm_cp_four_and12 gate(.bits(bits),.result(result));
 end else if(RETAINED_TAIL==2)begin:late_owner
  wire [11:0] early_bits=bits | (12'h007 << OWNER_LSB);
  wire early_ok;
  ot_hbm_cp_frontier_and12 #(.FAST(1),.RETAINED_TAIL(1)) early_gate(.bits(early_bits),.result(early_ok));
  ot_hbm_integrated_cp_and4 late_gate(.bits({bits[OWNER_LSB+:3],early_ok}),.result(result));
 end else begin:fast
  wire [3:0] no;wire [1:0] yes;
  for(genvar k=0;k<4;k=k+1)begin:g
   ot_hbm_cp_frontier_nand3 n(.bits(bits[k*3+:3]),.result(no[k]));
  end
  if(RETAINED_TAIL)begin:retained_tail
   // Keep each two-input reduction across ABC; the former unretained tail
   // mapped as OR4+INV in the terminal -19ps current-owner output path.
   ot_hbm_cp_phase_nor2 l0(.bits(no[1:0]),.result(yes[0]));
   ot_hbm_cp_phase_nor2 l1(.bits(no[3:2]),.result(yes[1]));
   ot_hbm_cp_control_tail_and2 root(.bits(yes),.result(result));
  end else begin:original_tail
  assign yes[0]=~|no[1:0];assign yes[1]=~|no[3:2];
  assign result=&yes;
  end
 end
endmodule

// All nine legal protected18-bit words, decomposed without a held mirror.
// n drives only its XOR complement check; q drives eight pair exclusions.
// No registers, added cycles, or delayed current-fault qualification.
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_phase_nand2(input wire [1:0] bits,output wire result);
 assign result=~&bits;
endmodule
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_phase_nor2(input wire [1:0] bits,output wire result);
 assign result=~|bits;
endmodule
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_parallel_phase(input wire [8:0] q,n,output wire valid);
 wire [8:0] complementary=q^n;
 wire [2:0] rails_bad,empty;
 wire rails_ok,present;
 for(genvar k=0;k<3;k=k+1)begin:rails
  ot_hbm_cp_frontier_nand3 r(.bits(complementary[k*3+:3]),.result(rails_bad[k]));
  ot_hbm_cp_frontier_nor3 p(.bits(q[k*3+:3]),.result(empty[k]));
 end
 ot_hbm_cp_frontier_nor3 rroot(.bits(rails_bad),.result(rails_ok));
 ot_hbm_cp_frontier_nand3 proot(.bits(empty),.result(present));
 wire [35:0] pair_ok;
 for(genvar a=0;a<8;a=a+1)begin:pair_a
  for(genvar b=a+1;b<9;b=b+1)begin:pair_b
   localparam integer INDEX=a*(17-a)/2+b-a-1;
   ot_hbm_cp_phase_nand2 exclude_pair(.bits({q[a],q[b]}),.result(pair_ok[INDEX]));
  end
 end
 wire [11:0] bad;wire [3:0] good;wire [1:0] upper_bad;
 wire one_or_zero;
 for(genvar k=0;k<12;k=k+1)begin:pair_leaf
  ot_hbm_cp_frontier_nand3 g(.bits(pair_ok[k*3+:3]),.result(bad[k]));
 end
 for(genvar k=0;k<4;k=k+1)begin:pair_middle
  ot_hbm_cp_frontier_nor3 g(.bits(bad[k*3+:3]),.result(good[k]));
 end
 ot_hbm_cp_frontier_nand3 u0(.bits(good[2:0]),.result(upper_bad[0]));
 ot_hbm_cp_frontier_nand3 u1(.bits({2'b11,good[3]}),.result(upper_bad[1]));
 ot_hbm_cp_phase_nor2 root(.bits(upper_bad),.result(one_or_zero));
 assign valid=rails_ok&&present&&one_or_zero;
endmodule

(* keep_hierarchy = "yes" *)
module ot_hbm_cp_control_tail_and2(input wire [1:0] bits,output wire result);
 assign result=&bits;
endmodule

// Additive exact mismatch polarity: no state or shortened identity.
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_owner_veto64(input wire [63:0] held_n,live,output wire mismatch);
 wire [63:0] equal_bits=held_n^live;
 wire [15:0] bad4;wire [3:0] good16;
 for(genvar k=0;k<16;k=k+1)begin:leaf
  ot_hbm_integrated_cp_nand4 n(.bits(equal_bits[k*4+:4]),.result(bad4[k]));
 end
 for(genvar k=0;k<4;k=k+1)begin:middle
  ot_hbm_integrated_cp_nor4 n(.bits(bad4[k*4+:4]),.result(good16[k]));
 end
 ot_hbm_integrated_cp_nand4 root(.bits(good16),.result(mismatch));
endmodule
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_veto_nor4(input wire [3:0] bad,output wire permit);
 assign permit=~|bad;
endmodule
(* keep_hierarchy = "yes" *)
module ot_hbm_cp_veto_conditional #(parameter integer NEGATIVE=0)(
 input wire local_ok,owner_ok,bypass,output wire result
);
 assign result=NEGATIVE?~(local_ok&&(owner_ok||bypass)):(local_ok&&(owner_ok||bypass));
endmodule
