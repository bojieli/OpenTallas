`timescale 1ns/1ps
// SOURCE control/transport fixtures. Full unchanged R128 capture and actual
// selected VM assignment/accept and C8 context cones; no arithmetic/token claim.
module publication_case #(parameter integer PIPE=1,CASE=0)(
 input wire clk,rst_n,input wire [3:0] jq,jfault,jquarantine,
 output reg finished=0,output reg [31:0] first_commit=0,last_commit=0,retire_cycle=0);
 localparam AW=30,VM_AW=19,ROM_R=128,R=128,G=4,W=16,SW=8,SUN=256;
 localparam S81_CAPTURE=1,X_ROM=1,CAPTURE_PUBLICATION=PIPE,CAPTURE_ENABLE=1;
 localparam CAPTURE_CAPACITY=1,CAPTURE_VM_ALWAYS_ACCEPT=1;
 localparam MIXED=(CASE==2||CASE==3),COLLISION=(CASE>=4&&CASE<=14);
 reg capture_reset_request=0,f_fault=0;
 reg [127:0] r_v=0,r_e=0;reg [2047:0] r_row=0,r_bf16=0;
 reg [383:0] r_pos=0;reg [4095:0] r_fp32=0;
 wire [2431:0] canonical_root_rows;
 // Actual canonical profile: rows256, healthy positions2 => quota4/root;
 // fault fixtures positions1 => quota2/root. No renamed phase namespace.
 ot_dsrom_s81_phase_capture_profile #(.ENABLE(1)) profile(
 .phase_rows(16'd256),.phase_np(CASE<4?3'd1:3'd0),.root_returns(canonical_root_rows));
 wire [2431:0] capture_root_rows=canonical_root_rows;
 wire [46:0] capture_identity,engine_identity;
 wire cap_ready,cap_idle,capture_live,capture_drained,capture_fault;
 wire [127:0] cap_we,capture_vm_accept;wire [3839:0] cap_addr;wire [4095:0] cap_data;
 wire [127:0] rom_we=cap_we;wire [3839:0] rom_waddr=cap_addr;wire [4095:0] rom_wdata=cap_data;
 wire [9:0] held_phase;
 wire [46:0] held_identity;
 reg [127:0] rom_duplicate=0;
 reg [G-1:0] vw_me_we=0;reg [G*W-1:0] vw_me_mask=0;reg [G*AW-1:0] vw_me_addr=0;reg [G*W*32-1:0] vw_me_data=0;
 reg [SW-1:0] vw_su_we=0,vw_rd_we=0;reg [SW*AW-1:0] vw_su_addr=0,vw_rd_addr=0;reg [SW*32-1:0] vw_su_data=0,vw_rd_data=0;
 reg [SUN-1:0] xs_vm_we=0;reg [SUN*AW-1:0] xs_vm_waddr=0;reg [SUN*32-1:0] xs_vm_wdata=0;
 reg [SUN/8-1:0] xs_res_we=0;reg [SUN/8*AW-1:0] xs_res_addr=0;reg [SUN/8*32-1:0] xs_res_data=0;
 reg vw_xe_we=0,ww_q_we=0,ww_x_we=0,xa_we=0;
 reg [AW-1:0] vw_xe_addr=0,ww_q_addr=0,ww_x_addr=0;reg [31:0] vw_xe_data=0;
 reg [31:0] ww_q_mask=0,ww_x_mask=0;reg [1023:0] ww_q_data=0,ww_x_data=0;
 reg [VM_AW-5:0] xa_waddr=0;reg [511:0] xa_wdata=0;reg [3:0] xb_we4=0;
 reg [4*(VM_AW-4)-1:0] xb_waddr4=0;reg [2047:0] xb_wdata4=0;
 reg [31:0] vm[0:(1<<VM_AW)-1];integer q,l,e,cycles=0,commits=0,launches=0,retirements=0;
 wire [3:0] c8_jquiet=jq,c8_jfault=jfault,c8_jquarantine=jquarantine;
 wire c8_write_quiet,c8_write_quarantine,c8_write_fault;
 // External service pins are explicit component stimuli, not evidence of real
 // CKV/HBM/WINDOW drain/prime. Preserve/test every current enclosing guard.
 reg kb_busy=0,c8_own_pending=0,c8_ckv_reuse_ready=1;
 reg win_service_busy=0,window_prime_ready=1,win_blk_v=0;
 reg [127:0] kh_v=0,kh_we=0;reg [3:0] pm_v=0,pm_we=0;
 task guards;begin
  kb_busy=1;#1;if(c8_write_quiet)$fatal(1,"KV busy guard missing");kb_busy=0;
  c8_own_pending=1;#1;if(c8_write_quiet)$fatal(1,"CKV owner guard missing");c8_own_pending=0;
  c8_ckv_reuse_ready=0;#1;if(c8_write_quiet)$fatal(1,"CKV reuse guard missing");c8_ckv_reuse_ready=1;
  win_service_busy=1;#1;if(c8_write_quiet)$fatal(1,"WINDOW busy guard missing");win_service_busy=0;
  window_prime_ready=0;#1;if(c8_write_quiet)$fatal(1,"WINDOW prime guard missing");window_prime_ready=1;
  win_blk_v=1;#1;if(c8_write_quiet)$fatal(1,"WINDOW write guard missing");win_blk_v=0;
  kh_v[127]=1;kh_we[127]=1;#1;if(c8_write_quiet)$fatal(1,"CKV write guard missing");kh_v=0;kh_we=0;
  pm_v[3]=1;pm_we[3]=1;#1;if(c8_write_quiet)$fatal(1,"VM mux write guard missing");pm_v=0;pm_we=0;
 end endtask
wire capture_visibility_quiet=!S81_CAPTURE || (!capture_live && capture_drained && !capture_fault && !(|capture_vm_accept));
assign c8_write_quiet=capture_visibility_quiet && (&c8_jquiet) && !kb_busy && !c8_own_pending && c8_ckv_reuse_ready && !win_service_busy && window_prime_ready && !win_blk_v && !(|(kh_v & kh_we)) && !(|(pm_v & pm_we));
assign c8_write_quarantine=(|c8_jquarantine) || (S81_CAPTURE && capture_fault);assign c8_write_fault=(|c8_jfault) || (S81_CAPTURE && capture_fault);

    // Literal retained last-write-wins VM semantics: credit only surviving rows.
    // This is a behavioral mutable-VM context, NOT a 128-port SRAM fit claim.
    reg [ROM_R-1:0] capture_commit;
    integer cr,cs,cl;
    reg [VM_AW-1:0] ca;
    always @* begin
      capture_commit=0;ca=0;
      for(cr=0;cr<ROM_R;cr=cr+1)begin
        ca=rom_waddr[cr*AW +: VM_AW];
        capture_commit[cr]=S81_CAPTURE && rst_n && !capture_reset_request && X_ROM && rom_we[cr] && (rom_waddr[cr*AW +:AW] < (AW'(1)<<VM_AW));
        // Later ROM ports and all later source-owned writers retain precedence.
        for(cs=cr+1;cs<ROM_R;cs=cs+1)
          if(rom_we[cs] && ca==rom_waddr[cs*AW +:VM_AW])capture_commit[cr]=0;
        for(cs=0;cs<G;cs=cs+1)for(cl=0;cl<W;cl=cl+1)
          if(vw_me_we[cs] && vw_me_mask[cs*W+cl] && ca==VM_AW'({vw_me_addr[cs*AW +:VM_AW-4],4'b0}+cl))capture_commit[cr]=0;
        for(cs=0;cs<SW;cs=cs+1)begin
          if(vw_su_we[cs] && ca==vw_su_addr[cs*AW +:VM_AW])capture_commit[cr]=0;
          if(vw_rd_we[cs] && ca==vw_rd_addr[cs*AW +:VM_AW])capture_commit[cr]=0;
        end
        for(cs=0;cs<SUN;cs=cs+1)
          if(xs_vm_we[cs] && ca==xs_vm_waddr[cs*AW +:VM_AW])capture_commit[cr]=0;
        for(cs=0;cs<SUN/8;cs=cs+1)
          if(xs_res_we[cs] && ca==xs_res_addr[cs*AW +:VM_AW])capture_commit[cr]=0;
        if(vw_xe_we && ca==vw_xe_addr[VM_AW-1:0])capture_commit[cr]=0;
        for(cl=0;cl<32;cl=cl+1)begin
          if(ww_q_we && ww_q_mask[cl] && ca==VM_AW'(ww_q_addr[VM_AW-1:0]+cl))capture_commit[cr]=0;
          if(ww_x_we && ww_x_mask[cl] && ca==VM_AW'(ww_x_addr[VM_AW-1:0]+cl))capture_commit[cr]=0;
        end
        for(cl=0;cl<16;cl=cl+1)begin
          if(xa_we && ca=={xa_waddr,4'(cl)})capture_commit[cr]=0;
          for(cs=0;cs<4;cs=cs+1)
            if(xb_we4[cs] && ca=={xb_waddr4[cs*(VM_AW-4) +:(VM_AW-4)],4'(cl)})capture_commit[cr]=0;
        end
      end
    end
    assign capture_vm_accept=capture_commit;

    wire [R-1:0] pub_r_v, pub_r_e;
    wire [16*R-1:0] pub_r_row, pub_r_bf16;
    wire [3*R-1:0] pub_r_pos;
    wire [32*R-1:0] pub_r_fp32;
    wire pub_f_fault;
    ot_v41_rom_publication_capture #(.ENABLE(CAPTURE_PUBLICATION),.WIDTH(69*R+1)) u_publication (
      .clk(clk),.rst_n(rst_n),
      .publication_in({f_fault,r_v,r_row,r_pos,r_fp32,r_bf16,r_e}),
      .publication_out({pub_f_fault,pub_r_v,pub_r_row,pub_r_pos,pub_r_fp32,pub_r_bf16,pub_r_e}));
    // All-copy quarantine, NOT an ACK or retroactive VM rollback. The existing
    // capture inhibits every VM valid on reset_request, latches sticky fault,
    // and retains accepted records/identity. No faulty-phase consumer/retire.
    wire publication_quarantine = CAPTURE_PUBLICATION != 0 &&
      (pub_f_fault || (|(pub_r_v & pub_r_e)));
    wire publication_quiet = CAPTURE_PUBLICATION == 0 ||
      (!(|r_v) && !(|pub_r_v) && !f_fault && !pub_f_fault);
    initial if (CAPTURE_PUBLICATION != 0 && CAPTURE_ENABLE == 0)
      $fatal(1,"paired publication requires actual finite capture/VM acceptance");

 // Preserve the emitted capture instance's source expressions/ports.
 wire [29:0] i_obase=30'd16,i_ops=30'd256;
 wire [2:0] i_np=CASE<4?3'd1:3'd0;wire [1:0] i_fmt=MIXED?2'd0:2'd1;
 wire [9:0] i_ph=10'd18;wire [63:0] phrom[0:2047];
 assign phrom[36]={1'b0,1'b1,62'b0}; // low rows FP32, high rows BF16
 assign phrom[37]=64'd128;
 wire CAPTURE_S81_PROFILE=1;
 wire [1:0] st=0;localparam S_IDLE=0;
 wire go=engine_start;
    ot_dsrom_rd64_vm_capture #(.ENABLE(CAPTURE_ENABLE),.ROOTS(R),
      .CAPACITY(CAPTURE_CAPACITY),.VM_AW(19),.VM_ALWAYS_ACCEPT(CAPTURE_VM_ALWAYS_ACCEPT)) u_capture (
      .clk(clk),.rst_n(rst_n),.reset_request(capture_reset_request | publication_quarantine),
      .phase_valid(go && st==S_IDLE),.phase_ready(cap_ready),
      .phase_identity(capture_identity),.phase_id(10'(i_ph)),.phase_root_rows(CAPTURE_S81_PROFILE ? canonical_root_rows : capture_root_rows),
      .phase_obase(30'(i_obase)),.phase_ops(30'(i_ops)),.phase_np(i_np),.phase_fmt(i_fmt),
      .phase_rsplit(phrom[{i_ph,1'b1}][15:0]),
      .phase_fp32_low(phrom[{i_ph,1'b0}][62]),.phase_fp32_high(phrom[{i_ph,1'b0}][63]),
      .r_valid(pub_r_v),.r_error(pub_r_e),.r_row(pub_r_row),.r_pos(pub_r_pos),.r_fp32(pub_r_fp32),.r_bf16(pub_r_bf16),
      .vm_valid(cap_we),.vm_accept(capture_vm_accept),.vm_addr(cap_addr),.vm_data(cap_data),
      .vm_row(),.vm_pos(),.held_identity(),.held_phase(),.phase_live(capture_live),
      .phase_idle(cap_idle),.phase_drained(capture_drained),.fault(capture_fault));

 // Literal source VM assignment order, with ROM ACK only for surviving writes.
 always @(posedge clk)if(rst_n)begin
for (q = 0; q < ROM_R; q = q + 1) if (rom_we[q] && (!S81_CAPTURE || capture_vm_accept[q])) vm[rom_waddr[q*AW +: VM_AW]] <= rom_wdata[32*q +: 32];
        for (q = 0; q < G; q = q + 1)
            if (vw_me_we[q])
                for (l = 0; l < W; l = l + 1)
                    if (vw_me_mask[q*W + l]) vm[{vw_me_addr[q*AW +: VM_AW-4], 4'b0} + l] <= vw_me_data[32*(q*W + l) +: 32];
        for (q = 0; q < SW; q = q + 1) if (vw_su_we[q]) vm[vw_su_addr[q*AW +: VM_AW]] <= vw_su_data[32*q +: 32];
        for (q = 0; q < SW; q = q + 1) if (vw_rd_we[q]) vm[vw_rd_addr[q*AW +: VM_AW]] <= vw_rd_data[32*q +: 32];
        for (q = 0; q < SUN; q = q + 1) if (xs_vm_we[q]) vm[xs_vm_waddr[q*AW +: VM_AW]] <= xs_vm_wdata[32*q +: 32];
        for (q = 0; q < SUN/8; q = q + 1) if (xs_res_we[q]) vm[xs_res_addr[q*AW +: VM_AW]] <= xs_res_data[32*q +: 32];
        if (vw_xe_we) vm[vw_xe_addr[VM_AW-1:0]] <= vw_xe_data;
        if (ww_q_we) for (q = 0; q < 32; q = q + 1) if (ww_q_mask[q]) vm[ww_q_addr[VM_AW-1:0] + q] <= ww_q_data[32*q +: 32];
        if (ww_x_we) for (q = 0; q < 32; q = q + 1) if (ww_x_mask[q]) vm[ww_x_addr[VM_AW-1:0] + q] <= ww_x_data[32*q +: 32];
        for (e = 0; e < 16; e = e + 1) begin
            if (xa_we) vm[{xa_waddr, 4'(e)}] <= xa_wdata[32*e +: 32];
            for (integer b = 0; b < 4; b = b + 1)
                if (xb_we4[b])
                    vm[{xb_waddr4[b*(VM_AW-4) +: (VM_AW-4)], 4'(e)}] <=
                        xb_wdata4[b*512 + 32*e +: 32];

        end

 end
 reg offer_v=0;reg [20:0] offer_pos=21'd1048575;
 wire offer_ready,context_v,engine_start,c8_active,c8_quarantine,retire_v;
 wire [46:0] context_identity,retire_identity;
 assign capture_identity=engine_identity;
 reg armed=0,adversarial_done=0;
 always @(posedge clk)begin
  if(rst_n&&go&&cap_ready)armed<=1;
  if(retire_v)armed<=0;
 end
 wire engine_done=(armed&&capture_drained)||adversarial_done;
 ot_dsrom_c8_stage_context context_owner(.clk(clk),.rst_n(rst_n),
 .offer_v(offer_v),.offer_ready(offer_ready),.offer_token(21'd1),.offer_pos(offer_pos),
 .offer_user(10'd3),.offer_epoch(16'd7),.offer_entry(14'd1),
 .context_v(context_v),.context_restored(1'b1),.context_identity(context_identity),.context_token(),.context_entry(),
 .engine_start(engine_start),.engine_token(),.engine_pos(),.engine_user(),.engine_entry(),.engine_identity(engine_identity),
 .engine_done(engine_done),.write_journal_quiet(c8_write_quiet),.write_quarantine(c8_write_quarantine),.write_fault(c8_write_fault),
 .retire_v(retire_v),.retire_identity(retire_identity),.active(c8_active),.quarantine(c8_quarantine));
 always @(posedge clk)if(rst_n)begin
  cycles<=cycles+1;
  if(engine_start)launches<=launches+1;
  if(retire_v)begin retirements<=retirements+1;retire_cycle<=cycles;
   if(capture_fault||!c8_write_quiet)$fatal(1,"faulty phase retired case%0d",CASE);end
  for(integer j=0;j<R;j=j+1)if(capture_vm_accept[j])begin
   if(publication_quarantine||capture_reset_request)$fatal(1,"ACK under publication quarantine case%0d",CASE);
  end
  if(|capture_vm_accept)begin
   if(first_commit==0)first_commit<=cycles;
   last_commit<=cycles;commits<=commits+$countones(capture_vm_accept);
  end
 end
 task tick;begin @(posedge clk);#1;end endtask
 task set_rows(input integer round);begin
  r_v='1;
  for(integer j=0;j<R;j=j+1)begin
   r_row[j*16+:16]=16'(2*j+(round%2));r_pos[j*3+:3]=3'(round/2);
   r_fp32[j*32+:32]=32'h80000000|32'(j*2+(round%2)+256*(round/2));r_bf16[j*16+:16]=16'h3f00|16'(j*2+(round%2)+256*(round/2));
  end
 end endtask
 task collide;begin
  case(CASE-4)
   0:begin r_row[16+:16]=0;end // Later ROM root owns the same address.
   1:begin vw_me_we[0]=1;vw_me_mask[0]=1;vw_me_addr[0+:AW]=1;vw_me_data[0+:32]=32'h12345678;end
   2:begin vw_su_we[0]=1;vw_su_addr[0+:AW]=16;vw_su_data[0+:32]=32'h12345678;end
   3:begin vw_rd_we[0]=1;vw_rd_addr[0+:AW]=16;vw_rd_data[0+:32]=32'h12345678;end
   4:begin xs_vm_we[0]=1;xs_vm_waddr[0+:AW]=16;xs_vm_wdata[0+:32]=32'h12345678;end
   5:begin xs_res_we[0]=1;xs_res_addr[0+:AW]=16;xs_res_data[0+:32]=32'h12345678;end
   6:begin vw_xe_we=1;vw_xe_addr=16;vw_xe_data=32'h12345678;end
   7:begin ww_q_we=1;ww_q_mask[0]=1;ww_q_addr=16;ww_q_data[0+:32]=32'h12345678;end
   8:begin ww_x_we=1;ww_x_mask[0]=1;ww_x_addr=16;ww_x_data[0+:32]=32'h12345678;end
   9:begin xa_we=1;xa_waddr=1;xa_wdata[0+:32]=32'h12345678;end
  10:begin xb_we4[0]=1;xb_waddr4[0+:VM_AW-4]=1;xb_wdata4[0+:32]=32'h12345678;end
  endcase
 end endtask
 initial begin
  wait(rst_n);#1;guards;@(negedge clk);if(!offer_ready||!c8_write_quiet)$fatal(1,"initial actual ownership blocked");offer_v=1;
  tick;@(negedge clk);offer_v=0;wait(engine_start);tick;
  if(!capture_live)$fatal(1,"actual phase descriptor not captured case%0d",CASE);
  if(CASE>=4)begin
   @(negedge clk);offer_pos=21'd1048574;offer_v=1;if(!offer_ready)$fatal(1,"second accepted slot absent");
   tick;@(negedge clk);offer_v=0;
  end
  @(negedge clk);set_rows(0);
  if(CASE==4)collide;
  if(CASE==16)r_e[127]=1;
  tick;
  if(PIPE && {pub_f_fault,pub_r_v,pub_r_row,pub_r_pos,pub_r_fp32,pub_r_bf16,pub_r_e}!==
   {f_fault,r_v,r_row,r_pos,r_fp32,r_bf16,r_e})$fatal(1,"R128 tuple alignment case%0d",CASE);
  if(CASE==18)begin
   @(negedge clk);set_rows(1);tick;
   @(negedge clk);r_v=0;
   wait(capture_drained);@(negedge clk);f_fault=1;#1;
   // Raw source fault appears before the next real consumer/retirement edge.
   // The paired stage must not hide this live copy behind a false quiet.
   if(c8_write_quiet)$fatal(1,"terminal raw fault hidden by paired publication: false quiet before retire");
   tick;adversarial_done=1;repeat(4)tick;
   if(!capture_fault||capture_drained||!capture_live||!c8_quarantine||!c8_active||
      context_v||offer_ready||retirements||launches!=1||context_owner.count!=1||commits!=256||
      u_capture.committed[0]!=2||u_capture.identity!==engine_identity||vm[16]!==32'h80000000)
    $fatal(1,"terminal publication fault consumed/retired or erased prior VM receipts/owner");
   $display("TERMINAL_FAULT commits%0d queuedcontexts%0d retainedidentity no_rollback no_consumer_or_retire",commits,context_owner.count);
  end else if(CASE<4)begin
   for(integer rr=1;rr<4;rr=rr+1)begin @(negedge clk);set_rows(rr);tick;end
   @(negedge clk);r_v=0;repeat(8)tick;
   if(commits!=512||capture_fault||capture_live||!capture_drained||retirements!=1||launches!=1)
    $fatal(1,"healthy receipt/owner totals case%0d commits%0d",CASE,commits);
   for(integer j=0;j<512;j=j+1)
    if(vm[16+j]!==((MIXED&&(j%256)>=128)?{16'(16'h3f00|j),16'b0}:(32'h80000000|32'(j))))
     $fatal(1,"source VM payload/format/row mismatch case%0d row%0d",CASE,j);
   $display("HEALTHY case%0d PIPE%0d commits%0d first%0d last%0d retire%0d",CASE,PIPE,commits,first_commit,last_commit,retire_cycle);
  end else begin
   @(negedge clk);r_v=0;
   if(CASE>=5&&CASE<=14)begin
    tick;@(negedge clk);collide;#1;
    if(capture_vm_accept[0]||!capture_fault)$fatal(1,"overwritten write credited case%0d",CASE);
   end else if(CASE==15)begin
    tick;@(negedge clk);f_fault=1;tick;
    if(|capture_vm_accept)$fatal(1,"field fault left VM valid");
   end else if(CASE==17)begin
    tick;@(negedge clk);capture_reset_request=1;
   end
   tick;adversarial_done=1;repeat(4)tick;
   if(!capture_fault||capture_drained||!capture_live||c8_write_quiet||!c8_write_quarantine||!c8_write_fault||
      !c8_quarantine||!c8_active||context_v||offer_ready||retirements||launches!=1||context_owner.count!=1)
    $fatal(1,"fault allowed consumer/retire/owner release case%0d",CASE);
   if(u_capture.identity!==engine_identity||u_capture.phase!==10'd18||u_capture.expected[0]!==2)
    $fatal(1,"fault discarded descriptor case%0d",CASE);
   if(COLLISION && (u_capture.count[0]!==1||u_capture.received[0]!==1||u_capture.committed[0]!==0))
    $fatal(1,"collision discarded denied debt case%0d",CASE);
   if(CASE>=5&&CASE<=14&&vm[16]!==32'h12345678)$fatal(1,"later writer precedence lost case%0d",CASE);
   if(CASE==15&&(u_capture.count[0]!==0||u_capture.received[0]!==1||u_capture.committed[0]!==1||commits!=128||vm[16]!==32'h80000000))$fatal(1,"field fault lost accepted prior receipt/remaining phase debt or rolled back VM");
   if(CASE==16&&commits!=0)$fatal(1,"paired root error allowed sibling commit");
   $display("QUARANTINE case%0d actualcommits%0d retained0%0d received0%0d committed0%0d queuedcontexts%0d no_consumer_or_retire",CASE,commits,u_capture.count[0],u_capture.received[0],u_capture.committed[0],context_owner.count);
  end
  finished=1;
 end
endmodule

module tb;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 wire [3:0] jq,jfault,jquarantine;
 genvar k;generate for(k=0;k<4;k=k+1)begin:journal
 // No HBM writes are issued by this component fixture. Quiet is the actual
 // native journal output, not a tied grant or backend ACK.
 ot_dsrom_c8_write_journal j(.clk(clk),.rst_n(rst_n),.accepted_write(128'b0),.backend_wr_done(128'b0),
 .accepted_addr(3840'b0),.backend_done_addr(3840'b0),.accepted_tag(2176'b0),.backend_done_tag(2176'b0),
 .accepted_writer(256'b0),.accepted_identity(47'b0),.visible_v(),.visible_identity(),.visible_addr(),.visible_writer(),
 .quiet(jq[k]),.debt(),.quarantine(jquarantine[k]),.fault(jfault[k]));
 end endgenerate
 wire [18:0] finished;wire [31:0] first[0:18],last[0:18],retire[0:18];
 generate for(k=0;k<19;k=k+1)begin:cases
 publication_case #(.PIPE(k==0||k==2?0:1),.CASE(k)) c(.clk(clk),.rst_n(rst_n),.jq(jq),.jfault(jfault),.jquarantine(jquarantine),
 .finished(finished[k]),.first_commit(first[k]),.last_commit(last[k]),.retire_cycle(retire[k]));
 end endgenerate
 initial begin
 repeat(2)@(negedge clk);rst_n=1;
 wait(&finished);#1;
 if(first[1]!=first[0]+1||last[1]!=last[0]+1||retire[1]!=retire[0]+1||
    first[3]!=first[2]+1||last[3]!=last[2]+1||retire[3]!=retire[2]+1)
  $fatal(1,"paired publication edge debit not exactly1");
 $display("PASS ORIGINAL R128 pairedsource 19 cases: 4 healthyformat/default/paired +11writercollisions +fieldfault +rooterror +warmquarantine +terminalrawfault; actualVMACK/retaineddebt/C8consumer+retire, first/last/retire debit1edge");
 $finish;
 end
endmodule
