`timescale 1ns/1ps
`default_nettype none
// H-NETLIST/COLL 1045: hard-hierarchy successor of ot_hfd_coll_q{3,2}_static_host_v4 (production V4 + HOST F20).
// The parent is WIRES ONLY: every flop and every gate lives in a hardenable child; the parent carries one clock
// entry port per actual hard-child clock pin (die "entries" ABI, as host_v4). One hardened master per quadrant
// type: q3 (SW, 1x) and q2 (SE/NW/NE, 3x hardened ONCE): physical identity is the static strap `qid` (die
// constant; HOST target = 52+qid), never a parameter. Children:
//   u_fj      ot_hgi_coll_fj_q{3,2}        HOST F20 programme target + aggregate fault/visibility join (leaf)
//   u_issuer  ot_hgi_coll_issuer_m         actual 3-SRAM issuer, uop masked by uop_v INSIDE the leaf
//   u_control ot_hgi_coll_ctl_v5_q{3,2}    protocol leaf: pipelined iteration products + V4 protocol (INJLAT 12)
//   g_qcap    ot_hgi_coll_qslots_capture_pin_v2 x NS  (pin_v2: every check input captured at its pin)
//   g_qout    ot_hgi_coll_qso_q{3,2}_b32 x17 + _b1 x1 (32-bit qslots switch slices)
//   g_link    ot_hgi_coll_link_e x NPT    (TX6/RX2 rail; epoch select inside the capture-control leaf)
//   u_writer  ot_hgi_coll_static_vmwrite_roots_v6_physical (CLOSED hcoll_vmwrite_static_v6_roots_fsw)
//   u_reduce  ot_hgi_coll_reduce_static    (hybrid cluster: 16 state + 16 add lanes)
//   u_ring    ot_hgi_coll_ring_v5          (= pring_captured_static SPLIT_CLOCKS 1; 8 CLOSED state-capture lanes)
//   q3 only:  u_arg ot_hgi_coll_argmax_m (mode gating inside), u_tkm ot_hgi_coll_tkm_m (32 CLOSED tkm tiles)
// V5 ISSUE TIMING: HOST frames are captured at the fj pins (+1: programme-target outputs +1) and the uop stream
// (with exported busy/done) is delayed 2 more edges: issue path +3 vs host_v4; every relative edge is unchanged. Normal data/valid are
// identical to host_v4 shifted by 2 edges (lockstep bench tb_hgi_coll_q_hard_v5). Exceptional fault ABI
// (all sticky; u_fj captures every input at its pin, then registers fault/fault_cause on clk_program). Relative to
// host_v4 shifted by the issue latency (+3: HOST frame capture +1, uop delay +2): every child fault +1 edge, AND
//   qslots capture (pin_v2)        +1 edge (source C -> leaf fault C+1 -> fault C+2)
//   q2 arg capture reservation      -1 edge (q2 has no arg source: checked in u_fj directly, C -> fault C+1)
//   q2 arg sink selection           select_fault instead of unavailable_fault (same edge; class only)
// Containment: no fault changes a reservation, a valid or a payload (static schedule; no kill/stall on die);
// the host isolates a faulted quadrant from host_status t_fault + fault_cause and reprogrammes after rst_n.
// fault_cause bits: 0 programme 1 issuer 2 protocol 3 qslots-capture 4 qslots-select 5 qslots-unavailable
//   6..8 link0..2 epoch abort 9 ring 10 writer 11 reduce 12 arg (q2: illegal arg reservation)
//   13 tkm (q2: illegal tkm reservation) 14..15 zero.

// ---------------------------------------------------------------------------------------------------------------
// Programme target + aggregate fault join (leaf, clk_program). The programme target is the unchanged actual
// ot_hgi_coll_static_program_target #(TARGET 52); the identity strap compares the raw HOST target with 52+qid
// before the target's own input capture, so the captured target equals 52 exactly when the original TARGET
// 52+QID instance would have matched.
module ot_hgi_coll_fj_core #(parameter integer NPT=3,SOLO=1,NS=11,NSL=18)(
 input wire clk,rst_n,
 input wire [1:0] qid,
 input wire cfg_v,
 input wire [7:0] cfg_target,
 input wire [11:0] cfg_addr,
 input wire [255:0] cfg_data,
 input wire desc_v,
 input wire [11:0] desc_base,
 input wire [12:0] desc_limit,
 input wire [15:0] desc_loops,
 input wire launch_v,program_active,
 input wire issuer_busy,issuer_fault,issuer_uop_v,
 input wire [5:0] issuer_uop_pc,
 output wire [36:0] issuer_cfg,
 output wire issuer_start,
 output wire [5:0] issuer_start_pc,
 output wire configured,init_busy,program_fault,
 // child fault faces (each a registered child output)
 input wire protocol_fault,
 input wire [NS-1:0] capture_fault,
 input wire [NSL-1:0] select_fault,unavailable_fault,
 input wire [NPT-1:0] link_abort,
 input wire ring_fault,writer_fault,reduce_fault,
 input wire arg_fault,tkm_fault,                 // q3 engines (SOLO!=0)
 input wire arg_capture_slot,                    // q2: compiled arg capture reservation (no arg source exists)
 input wire tkm_start,                           // q2: compiled tkm start
 input wire [3:0] tkm_del_slot,tkm_dest_v,       // q2: compiled tkm delivery reservation / tkm sinks
 output reg fault,
 output reg [15:0] fault_cause
);
 // Every input is captured at its pin (coordinator native audit of fj_q2 54f035ca0: 71 unregistered inputs, capture
 // 512.9 ps). rst_n: synchronous D-pin flop. HOST frames: +1 edge (target remap after capture, against the static
 // qid strap). Issuer feedback and child faults: +1 edge (exceptional fault ABI +1, like qslots pin_v2).
 reg rst_q;
 always @(posedge clk) rst_q<=rst_n;
 reg cv_q,dv_q,lv_q,act_q,ibusy_q,ifault_q,iuv_q;
 reg [7:0] tgt_q;reg [1:0] qid_q;reg [11:0] addr_q,base_q;reg [255:0] data_q;reg [12:0] limit_q;reg [15:0] loops_q;
 reg [5:0] iupc_q;
 reg prot_q,ring_q,writer_q,reduce_q,arg_q,tkm_q,argcap_q,tkmstart_q;
 reg [NS-1:0] cap_q;reg [NSL-1:0] sel_q,unav_q;reg [NPT-1:0] lk_q;reg [3:0] tdel_q,tdest_q;
 always @(posedge clk)begin
  tgt_q<=cfg_target;qid_q<=qid;addr_q<=cfg_addr;data_q<=cfg_data;base_q<=desc_base;limit_q<=desc_limit;
  loops_q<=desc_loops;iupc_q<=issuer_uop_pc;
 end
 always @(posedge clk or negedge rst_q)
  if(!rst_q)begin
   cv_q<=0;dv_q<=0;lv_q<=0;act_q<=0;ibusy_q<=0;ifault_q<=0;iuv_q<=0;prot_q<=0;ring_q<=0;writer_q<=0;reduce_q<=0;
   arg_q<=0;tkm_q<=0;argcap_q<=0;tkmstart_q<=0;cap_q<=0;sel_q<=0;unav_q<=0;lk_q<=0;tdel_q<=0;tdest_q<=0;
  end else begin
   cv_q<=cfg_v;dv_q<=desc_v;lv_q<=launch_v;act_q<=program_active;ibusy_q<=issuer_busy;ifault_q<=issuer_fault;
   iuv_q<=issuer_uop_v;prot_q<=protocol_fault;ring_q<=ring_fault;writer_q<=writer_fault;reduce_q<=reduce_fault;
   arg_q<=arg_fault;tkm_q<=tkm_fault;argcap_q<=arg_capture_slot;tkmstart_q<=tkm_start;cap_q<=capture_fault;
   sel_q<=select_fault;unav_q<=unavailable_fault;lk_q<=link_abort;tdel_q<=tkm_del_slot;tdest_q<=tkm_dest_v;
  end
 wire [7:0] target_eff=(tgt_q==(8'd52+{6'd0,qid_q}))?8'd52:8'd0;
 ot_hgi_coll_static_program_target #(.TARGET(8'd52)) u_program(
  .clk(clk),.rst_n(rst_q),.cfg_v(cv_q),.cfg_target(target_eff),
  .cfg_addr(addr_q),.cfg_data(data_q),.desc_v(dv_q),.desc_base(base_q),
  .desc_limit(limit_q),.desc_loops(loops_q),.launch_v(lv_q),
  .program_active(act_q),.issuer_busy(ibusy_q),.issuer_fault(ifault_q),
  .issuer_uop_v(iuv_q),.issuer_uop_pc(iupc_q),
  .issuer_cfg(issuer_cfg),.issuer_start(issuer_start),.issuer_start_pc(issuer_start_pc),
  .configured(configured),.init_busy(init_busy),.fault(program_fault));
 wire noengine_arg=(SOLO==0)&&argcap_q;
 wire noengine_tkm=(SOLO==0)&&(tkmstart_q || (|tdest_q) || (|tdel_q));
 wire [2:0] link3;
 for(genvar k=0;k<3;k=k+1)begin:g_l3
  if(k<NPT)begin:p assign link3[k]=lk_q[k]; end else begin:z assign link3[k]=1'b0; end
 end
 wire [15:0] cause_now;
 assign cause_now[0]=program_fault;
 assign cause_now[1]=ifault_q;
 assign cause_now[2]=prot_q;
`ifdef OT_COLL_V5_MUT_CAUSE_SWAP
 assign cause_now[3]=|sel_q;
 assign cause_now[4]=|cap_q;
`else
 assign cause_now[3]=|cap_q;
 assign cause_now[4]=|sel_q;
`endif
 assign cause_now[5]=|unav_q;
`ifdef OT_COLL_V5_MUT_DROP_LINK
 assign cause_now[8:6]=3'b000;
`else
 assign cause_now[8:6]=link3;
`endif
 assign cause_now[9]=ring_q;
 assign cause_now[10]=writer_q;
 assign cause_now[11]=reduce_q;
 assign cause_now[12]=(SOLO!=0)?arg_q:noengine_arg;
`ifdef OT_COLL_V5_MUT_DROP_TKM
 assign cause_now[13]=(SOLO!=0)?tkm_q:1'b0;
`else
 assign cause_now[13]=(SOLO!=0)?tkm_q:noengine_tkm;
`endif
 assign cause_now[15:14]=2'b00;
 always @(posedge clk or negedge rst_q)
  if(!rst_q)begin fault<=1'b0;fault_cause<=16'd0;end
  else begin fault<=fault | (|cause_now);fault_cause<=fault_cause | cause_now;end
endmodule

module ot_hgi_coll_fj_q3(
 input wire clk,rst_n,input wire [1:0] qid,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,input wire [15:0] desc_loops,
 input wire launch_v,program_active,issuer_busy,issuer_fault,issuer_uop_v,input wire [5:0] issuer_uop_pc,
 output wire [36:0] issuer_cfg,output wire issuer_start,output wire [5:0] issuer_start_pc,
 output wire configured,init_busy,program_fault,
 input wire protocol_fault,input wire [10:0] capture_fault,input wire [17:0] select_fault,unavailable_fault,
 input wire [2:0] link_abort,input wire ring_fault,writer_fault,reduce_fault,arg_fault,tkm_fault,
 output wire fault,output wire [15:0] fault_cause);
 ot_hgi_coll_fj_core #(.NPT(3),.SOLO(1),.NS(11),.NSL(18)) u(.*,
  .arg_capture_slot(1'b0),.tkm_start(1'b0),.tkm_del_slot(4'd0),.tkm_dest_v(4'd0));
endmodule

module ot_hgi_coll_fj_q2(
 input wire clk,rst_n,input wire [1:0] qid,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,input wire [15:0] desc_loops,
 input wire launch_v,program_active,issuer_busy,issuer_fault,issuer_uop_v,input wire [5:0] issuer_uop_pc,
 output wire [36:0] issuer_cfg,output wire issuer_start,output wire [5:0] issuer_start_pc,
 output wire configured,init_busy,program_fault,
 input wire protocol_fault,input wire [8:0] capture_fault,input wire [17:0] select_fault,unavailable_fault,
 input wire [1:0] link_abort,input wire ring_fault,writer_fault,reduce_fault,
 input wire arg_capture_slot,tkm_start,input wire [3:0] tkm_del_slot,tkm_dest_v,
 output wire fault,output wire [15:0] fault_cause);
 ot_hgi_coll_fj_core #(.NPT(2),.SOLO(0),.NS(9),.NSL(18)) u(.*,.arg_fault(1'b0),.tkm_fault(1'b0));
endmodule

// ---------------------------------------------------------------------------------------------------------------
// Issuer leaf: actual issuer (3 x ot_sram_1r1w_64x512_m1_r2c2) with host_v4's `uop_v ? uop : 0` mask inside the
// leaf (bank face flop AND uop_v flop: no input-to-output path).
// COLL-CTL 1045: ONE clock entry. The mask ANDs a bank face flop (issuer clk_mem[b]) with uop_v (clk_control) at the
// same output pin, so separate clk_mem entries would give every uop bit two launch domains (multiple_cts_roots
// refuses a port owned by two roots). The leaf's own CTS tree clocks the control flops, the 3 macro clock pins and
// the 1536 bank face flops: same logical edge as host_v4's related clk_issue[3:0] (lockstep bench unchanged).
module ot_hgi_coll_issuer_m(
 input wire clk_control,input wire rst_n,
 input wire [36:0] cfg,input wire start,input wire [5:0] start_pc,
 output wire busy,done,fault,uop_v,          // raw (programme-target feedback, host_v4 edges)
 output wire [5:0] uop_pc,
 // V5 issue timing: the instruction stream and its control (start/busy/done) leave 2 edges later; the early tap
 // carries iteration and the six step fields at the raw edge for the protocol leaf's pipelined products.
 output reg [1535:0] uop_d2,
 output reg busy_d2,done_d2,start_d2,
 output wire [31:0] tap_iteration,
 output wire [87:0] tap_steps                // {lk8, rgx16, del16, iaddr16, vm16, idx16}
);
 wire [1535:0] raw,uop;wire [31:0] iteration;
 ot_hgi_coll_static_issuer u_issuer(.clk_control(clk_control),.clk_mem({3{clk_control}}),.rst_n(rst_n),
  .cfg(cfg),.start(start),.start_pc(start_pc),.busy(busy),.done(done),.fault(fault),
  .uop_v(uop_v),.uop(raw),.iteration(iteration),.uop_pc(uop_pc));
`ifdef OT_COLL_V5_MUT_NOMASK
 assign uop=raw;
`else
 assign uop=uop_v?raw:1536'd0;
`endif
 assign tap_iteration=iteration;
 assign tap_steps={uop[1407+:8],uop[1318+:16],uop[1350+:16],uop[1366+:16],uop[1302+:16],uop[1334+:16]};
 reg [1535:0] uop_d1;reg busy_d1,done_d1,start_d1;
 always @(posedge clk_control)begin uop_d1<=uop;uop_d2<=uop_d1;end
 always @(posedge clk_control or negedge rst_n)
  if(!rst_n)begin busy_d1<=0;busy_d2<=0;done_d1<=0;done_d2<=0;start_d1<=0;start_d2<=0;end
  else begin busy_d1<=busy;busy_d2<=busy_d1;done_d1<=done;done_d2<=done_d1;start_d1<=start;start_d2<=start_d1;end
endmodule

// ---------------------------------------------------------------------------------------------------------------
// Protocol leaves (V5 issue timing, INJLAT 12; parameters fixed by name for hardening): one leaf = the pipelined
// iteration-product unit (pin capture of the early tap at E+3, registered partials at E+4) + ot_hgi_coll_q_static_ctl_v5
// on the 2-edge-delayed instruction (valid E+4..E+5): only field+partial adders remain in the cycle.
module ot_hgi_coll_ctl_v5_core #(parameter integer NPT=3,SOLO=1,ND=NPT+13)(
 input wire clk_control,rst_n,input wire [1535:0] inst,input wire [31:0] tap_iteration,input wire [87:0] tap_steps,
 input wire hgi_start,hgi_busy,issue_done,tkm_done,tkm_busy,input wire [ND-1:0] dest_v,
 input wire rc_v,input wire [2:0] rc_tag,input wire [2055:0] vm_rr,
 output wire [135:0] vm_req_pin,output wire [1:0] inj_req_pin,output wire [31:0] inj_idx_pin,
 output wire [159:0] inj_addr_pin,delivery_obase_pin,rgx_addr_pin,
 output wire [1:0] inj_source_v,output wire [65:0] inj_source_meta,output wire [131:0] vm_source_meta,
 output wire [2047:0] vm_assembled,output wire [3:0] vm_assembled_v,output wire [NPT*8-1:0] held_epoch,
 output wire [NPT*16-1:0] wr_sequence_pin,rd_sequence_pin,rx_sequence_pin,
 output wire protocol_fault,output wire [31:0] cycles);
 wire [15:0] m_idx,m_vm,m_iaddr_h,m_del_h,m_rgx_h;wire [31:0] m_iaddr_l,m_del_l,m_rgx_l;wire [23:0] m_lk_l,m_lk_h;
 ot_hgi_coll_iter_mul u_mul(.clk(clk_control),.iteration(tap_iteration),.s_idx(tap_steps[0+:16]),
  .s_vm(tap_steps[16+:16]),.s_iaddr(tap_steps[32+:16]),.s_del(tap_steps[48+:16]),.s_rgx(tap_steps[64+:16]),
  .s_lk(tap_steps[80+:8]),.m_idx(m_idx),.m_vm(m_vm),.m_iaddr_l(m_iaddr_l),.m_del_l(m_del_l),.m_rgx_l(m_rgx_l),
  .m_iaddr_h(m_iaddr_h),.m_del_h(m_del_h),.m_rgx_h(m_rgx_h),.m_lk_l(m_lk_l),.m_lk_h(m_lk_h));
 ot_hgi_coll_q_static_ctl_v5 #(.NPT(NPT),.SOLO(SOLO),.INJLAT(12)) u(.clk_control(clk_control),.rst_n(rst_n),
  .inst(inst),.m_idx(m_idx),.m_vm(m_vm),.m_iaddr_l(m_iaddr_l),.m_del_l(m_del_l),.m_rgx_l(m_rgx_l),
  .m_iaddr_h(m_iaddr_h),.m_del_h(m_del_h),.m_rgx_h(m_rgx_h),.m_lk_l(m_lk_l),.m_lk_h(m_lk_h),
  .hgi_start(hgi_start),.hgi_busy(hgi_busy),.issue_done(issue_done),.tkm_done(tkm_done),.tkm_busy(tkm_busy),
  .dest_v(dest_v),.rc_v(rc_v),.rc_tag(rc_tag),.vm_rr(vm_rr),.vm_req_pin(vm_req_pin),.inj_req_pin(inj_req_pin),
  .inj_idx_pin(inj_idx_pin),.inj_addr_pin(inj_addr_pin),.delivery_obase_pin(delivery_obase_pin),
  .rgx_addr_pin(rgx_addr_pin),.inj_source_v(inj_source_v),.inj_source_meta(inj_source_meta),
  .vm_source_meta(vm_source_meta),.vm_assembled(vm_assembled),.vm_assembled_v(vm_assembled_v),
  .held_epoch(held_epoch),.wr_sequence_pin(wr_sequence_pin),.rd_sequence_pin(rd_sequence_pin),
  .rx_sequence_pin(rx_sequence_pin),.protocol_fault(protocol_fault),.cycles(cycles));
endmodule

module ot_hgi_coll_ctl_v5_q3(
 input wire clk_control,rst_n,input wire [1535:0] inst,input wire [31:0] tap_iteration,input wire [87:0] tap_steps,
 input wire hgi_start,hgi_busy,issue_done,tkm_done,tkm_busy,input wire [15:0] dest_v,
 input wire rc_v,input wire [2:0] rc_tag,input wire [2055:0] vm_rr,
 output wire [135:0] vm_req_pin,output wire [1:0] inj_req_pin,output wire [31:0] inj_idx_pin,
 output wire [159:0] inj_addr_pin,delivery_obase_pin,rgx_addr_pin,
 output wire [1:0] inj_source_v,output wire [65:0] inj_source_meta,output wire [131:0] vm_source_meta,
 output wire [2047:0] vm_assembled,output wire [3:0] vm_assembled_v,output wire [23:0] held_epoch,
 output wire [47:0] wr_sequence_pin,rd_sequence_pin,rx_sequence_pin,
 output wire protocol_fault,output wire [31:0] cycles);
 ot_hgi_coll_ctl_v5_core #(.NPT(3),.SOLO(1)) u(.*);
endmodule

module ot_hgi_coll_ctl_v5_q2(
 input wire clk_control,rst_n,input wire [1535:0] inst,input wire [31:0] tap_iteration,input wire [87:0] tap_steps,
 input wire hgi_start,hgi_busy,issue_done,tkm_done,tkm_busy,input wire [14:0] dest_v,
 input wire rc_v,input wire [2:0] rc_tag,input wire [2055:0] vm_rr,
 output wire [135:0] vm_req_pin,output wire [1:0] inj_req_pin,output wire [31:0] inj_idx_pin,
 output wire [159:0] inj_addr_pin,delivery_obase_pin,rgx_addr_pin,
 output wire [1:0] inj_source_v,output wire [65:0] inj_source_meta,output wire [131:0] vm_source_meta,
 output wire [2047:0] vm_assembled,output wire [3:0] vm_assembled_v,output wire [15:0] held_epoch,
 output wire [31:0] wr_sequence_pin,rd_sequence_pin,rx_sequence_pin,
 output wire protocol_fault,output wire [31:0] cycles);
 ot_hgi_coll_ctl_v5_core #(.NPT(2),.SOLO(0)) u(.*);
endmodule

// ---------------------------------------------------------------------------------------------------------------
// qslots switch slices (pin_v2 partition): 17 x 32-bit + 1 x 1-bit per quadrant type. Actual V4 shapes:
// q3 NS 11 (2 inj + 3 rail + 4 VM + reduce + arg), ND 16; q2 NS 9 (no arg source), ND 15. SELW 4.
module ot_hgi_coll_qso_q3_b32(input wire clk,rst_n,input wire [351:0] captured,input wire [10:0] captured_slot,
 input wire [15:0] sink_slot,input wire [63:0] sink_select,output wire [15:0] dst_v,output wire [511:0] dst_d,
 output wire select_fault,unavailable_fault);
 ot_hgi_coll_qslots_output #(.NS(11),.ND(16),.PWT(32),.SELW(4)) u(.*);
endmodule
module ot_hgi_coll_qso_q3_b1(input wire clk,rst_n,input wire [10:0] captured,input wire [10:0] captured_slot,
 input wire [15:0] sink_slot,input wire [63:0] sink_select,output wire [15:0] dst_v,output wire [15:0] dst_d,
 output wire select_fault,unavailable_fault);
 ot_hgi_coll_qslots_output #(.NS(11),.ND(16),.PWT(1),.SELW(4)) u(.*);
endmodule
module ot_hgi_coll_qso_q2_b32(input wire clk,rst_n,input wire [287:0] captured,input wire [8:0] captured_slot,
 input wire [14:0] sink_slot,input wire [59:0] sink_select,output wire [14:0] dst_v,output wire [479:0] dst_d,
 output wire select_fault,unavailable_fault);
 ot_hgi_coll_qslots_output #(.NS(9),.ND(15),.PWT(32),.SELW(4)) u(.*);
endmodule
module ot_hgi_coll_qso_q2_b1(input wire clk,rst_n,input wire [8:0] captured,input wire [8:0] captured_slot,
 input wire [14:0] sink_slot,input wire [59:0] sink_select,output wire [14:0] dst_v,output wire [14:0] dst_d,
 output wire select_fault,unavailable_fault);
 ot_hgi_coll_qslots_output #(.NS(9),.ND(15),.PWT(1),.SELW(4)) u(.*);
endmodule

// ---------------------------------------------------------------------------------------------------------------
// Rail: actual link_capture structure (capture-control leaf + 4 native store leaves); the V4 parent's epoch
// select (`epoch_begin ? epoch : held_epoch`) moves inside the capture-control leaf ahead of its pin capture.
module ot_hgi_coll_capture_ctl_e(
 input wire clk,rst_n,epoch_begin,input wire [7:0] epoch_new,held_epoch,
 input wire wr_v,wr_observed_v,input wire [15:0] wr_seq,input wire [544:0] wr_flit,
 input wire rd_v,input wire [15:0] rd_seq,input wire rx_expect_v,input wire [15:0] rx_expect_seq,
 input wire phy_up,output wire tx_pin_v,output wire [611:0] tx_pin_flit,
 input wire rx_pin_v,input wire [611:0] rx_pin_flit,output wire rx_v,output wire [544:0] rx_flit,
 output wire epoch_abort,retry_requested,output wire [10:0] fault_cause,
 output wire bank_we,output wire [5:0] bank_wa,bank_ra,output wire [563:0] bank_data,input wire [563:0] stored);
 ot_hgi_coll_static_capture_ctl u(.clk(clk),.rst_n(rst_n),.epoch_begin(epoch_begin),
  .epoch(epoch_begin?epoch_new:held_epoch),
  .wr_v(wr_v),.wr_observed_v(wr_observed_v),.wr_seq(wr_seq),.wr_flit(wr_flit),
  .rd_v(rd_v),.rd_seq(rd_seq),.rx_expect_v(rx_expect_v),.rx_expect_seq(rx_expect_seq),
  .phy_up(phy_up),.tx_pin_v(tx_pin_v),.tx_pin_flit(tx_pin_flit),
  .rx_pin_v(rx_pin_v),.rx_pin_flit(rx_pin_flit),.rx_v(rx_v),.rx_flit(rx_flit),
  .epoch_abort(epoch_abort),.retry_requested(retry_requested),.fault_cause(fault_cause),
  .bank_we(bank_we),.bank_wa(bank_wa),.bank_ra(bank_ra),.bank_data(bank_data),.stored(stored));
endmodule

module ot_hgi_coll_link_e(
 input wire [4:0] ck,input wire rst_n,epoch_begin,input wire [7:0] epoch_new,held_epoch,
 input wire wr_v,wr_observed_v,input wire [15:0] wr_seq,input wire [544:0] wr_flit,
 input wire rd_v,input wire [15:0] rd_seq,input wire rx_expect_v,input wire [15:0] rx_expect_seq,
 input wire phy_up,output wire tx_pin_v,output wire [611:0] tx_pin_flit,
 input wire rx_pin_v,input wire [611:0] rx_pin_flit,output wire rx_v,output wire [544:0] rx_flit,
 output wire epoch_abort,retry_requested,output wire [10:0] fault_cause);
 wire bank_we;wire [5:0] bank_wa,bank_ra;
 wire [563:0] bank_data,stored;
 for(genvar b=0;b<4;b=b+1)begin:g_bank
  ot_hgi_coll_static_pinreg_store u_store(.clk(ck[b+1]),.we(bank_we),.wa(bank_wa),.ra(bank_ra),
   .din(bank_data[b*141+:141]),.dout(stored[b*141+:141]));
 end
 ot_hgi_coll_capture_ctl_e u_ctl(.clk(ck[0]),.rst_n(rst_n),.epoch_begin(epoch_begin),
  .epoch_new(epoch_new),.held_epoch(held_epoch),
  .wr_v(wr_v),.wr_observed_v(wr_observed_v),.wr_seq(wr_seq),.wr_flit(wr_flit),
  .rd_v(rd_v),.rd_seq(rd_seq),.rx_expect_v(rx_expect_v),.rx_expect_seq(rx_expect_seq),
  .phy_up(phy_up),.tx_pin_v(tx_pin_v),.tx_pin_flit(tx_pin_flit),
  .rx_pin_v(rx_pin_v),.rx_pin_flit(rx_pin_flit),.rx_v(rx_v),.rx_flit(rx_flit),
  .epoch_abort(epoch_abort),.retry_requested(retry_requested),.fault_cause(fault_cause),
  .bank_we(bank_we),.bank_wa(bank_wa),.bank_ra(bank_ra),.bank_data(bank_data),.stored(stored));
endmodule

// ---------------------------------------------------------------------------------------------------------------
// q3 engines with the V4 parent's arg/tkm mode gating inside the hardened child.
// COLL-CTL 1045: the leaf takes only the delivery bits the engine reads -- per lane the FP32 key + index word
// (flit[63:0], ot_hgi_coll_amerge stage 1) and the 33b meta (flit[544:512], argmax_static source/order checks).
// flit[511:64] has no load in either module (amerge runs with en=1, so its pass-through o_f never reaches out_flit);
// dropping those 1,792 pins changes no edge or value (lockstep bench) and removes a pin-bound 2,180-bit face.
module ot_hgi_coll_argmax_m(
 input wire clk,rst_n,start,mode,input wire [7:0] cfg_g,cfg_gbase,cfg_rank,
 input wire [3:0] in_slot,in_v,input wire [255:0] in_key,input wire [131:0] in_meta,input wire flush_slot,publish_slot,
 output wire out_v,output wire [544:0] out_flit,output wire fault);
 // u_data: live inputs, data/valid edges exact (its check logic has no load and is removed by synthesis).
 // u_chk : the same actual module on pin-captured inputs; only its sticky fault is used (arg fault ABI +1 edge;
 //         the 15-level input-check cone becomes reg->reg).
 wire [2179:0] in_flit;
 for(genvar l=0;l<4;l=l+1)begin:g_lane
  assign in_flit[l*545+:545]={in_meta[l*33+:33],448'd0,in_key[l*64+:64]};
 end
 ot_hgi_coll_argmax_static u_data(.clk(clk),.rst_n(rst_n),.start(start),.cfg_g(cfg_g),.cfg_gbase(cfg_gbase),
  .cfg_rank(cfg_rank),.in_slot(in_slot & {4{mode}}),.in_v(in_v & {4{mode}}),.in_flit(in_flit),
  .flush_slot(flush_slot),.publish_slot(publish_slot),.out_v(out_v),.out_flit(out_flit),.fault());
 reg start_q,flush_q,pub_q;reg [7:0] g_q,gb_q,rk_q;reg [3:0] slot_q,v_q;reg [2179:0] flit_q;
 always @(posedge clk)begin g_q<=cfg_g;gb_q<=cfg_gbase;rk_q<=cfg_rank;flit_q<=in_flit;end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin start_q<=0;flush_q<=0;pub_q<=0;slot_q<=0;v_q<=0;end
  else begin start_q<=start;flush_q<=flush_slot;pub_q<=publish_slot;slot_q<=in_slot & {4{mode}};v_q<=in_v & {4{mode}};end
 ot_hgi_coll_argmax_static u_chk(.clk(clk),.rst_n(rst_n),.start(start_q),.cfg_g(g_q),.cfg_gbase(gb_q),
  .cfg_rank(rk_q),.in_slot(slot_q),.in_v(v_q),.in_flit(flit_q),
  .flush_slot(flush_q),.publish_slot(pub_q),.out_v(),.out_flit(),.fault(fault));
endmodule

module ot_hgi_coll_tkm_m(
 input wire clk,rst_n,start,arg_mode,input wire [31:0] tile_clk,input wire buffer_clk,
 input wire [11:0] cfg_n,input wire [12:0] cfg_k,cfg_nout,input wire [7:0] cfg_g,cfg_gbase,input wire [15:0] cfg_pf,
 input wire [39:0] cfg_obase,cfg_rbase,input wire cfg_has_r,
 input wire [3:0] del_slot,del_valid,input wire [2179:0] del_flit,
 output wire w_v,output wire [39:0] w_addr,output wire [15:0] w_mask,output wire [511:0] w_data,
 output wire busy,done,fault,output wire [31:0] stat_cycles);
 ot_hgi_coll_tkm_static u(.clk(clk),.tile_clk(tile_clk),.buffer_clk(buffer_clk),.rst_n(rst_n),.start(start),
  .cfg_n(cfg_n),.cfg_k(cfg_k),.cfg_nout(cfg_nout),.cfg_g(cfg_g),.cfg_gbase(cfg_gbase),.cfg_pf(cfg_pf),
  .cfg_obase(cfg_obase),.cfg_rbase(cfg_rbase),.cfg_has_r(cfg_has_r),
  .del_slot(del_slot & {4{!arg_mode}}),.del_valid(del_valid & {4{!arg_mode}}),.del_flit(del_flit),
  .w_v(w_v),.w_addr(w_addr),.w_mask(w_mask),.w_data(w_data),
  .busy(busy),.done(done),.fault(fault),.stat_cycles(stat_cycles));
endmodule

module ot_hgi_coll_ring_v5(
 input wire clk,rst_n,input wire [7:0] clk_state,clk_add,input wire [1:0] qid,
 input wire [279:0] cw_i,ccw_i,output wire [279:0] cw_o,ccw_o,
 input wire lp_we,input wire [2:0] lp_tag,input wire [255:0] lp_data,
 input wire state_read_add,state_read_tx,state_read_rr,input wire [2:0] state_add_tag,state_tx_tag,state_rr_tag,
 input wire [1:0] state_add_src,input wire state_add_rhs_acc,state_tx_acc,
 input wire add_v,input wire [2:0] add_tag,input wire [1:0] add_src,input wire add_rhs_acc,
 input wire [1:0] tx_inject,tx_forward,input wire [2:0] tx_tag,input wire [1:0] tx_dst,input wire tx_result,tx_acc,
 input wire [1:0] rx_slot,input wire [3:0] rx_kind,rx_src,input wire [5:0] rx_tag,
 input wire rr_local,input wire [2:0] rr_local_tag,
 output wire rr_v,output wire [2:0] rr_tag,output wire [255:0] rr_d,output wire fault);
 ot_hgi_coll_pring_captured_static #(.SPLIT_CLOCKS(1)) u(.*);
endmodule

// ---------------------------------------------------------------------------------------------------------------
// Wires-only quadrant body. NPT 3 -> q3 children, NPT 2 -> q2 children.
module ot_hfd_coll_q_hard_v5_body #(
 parameter integer NPT=3,SOLO=1,
 parameter integer NS=(SOLO!=0)?NPT+8:NPT+7,ND=NPT+13,NSL=18,NCK=NS+NSL
)(
 input wire rst_n,
 input wire [1:0] qid,
 input wire clk_program,clk_control,
 input wire clk_issue,
 input wire [NCK-1:0] clk_qslots,       // [NS-1:0] capture leaves, [NCK-1:NS] switch slices
 input wire [16:0] clk_ring,
 input wire [32:0] clk_reduce,
 input wire clk_arg,
 input wire [33:0] clk_tkm,
 input wire [15:0] clk_vmwrite,         // v6 writer: rgx_data0..3, rgx_ctrl, tkw, meta, body, bank0..7
 input wire [5*NPT-1:0] clk_link,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,input wire [15:0] desc_loops,
 input wire launch_v,
 output wire program_configured,program_init_busy,program_fault,
 output wire hgi_busy,hgi_done,hgi_fault,
 output wire [1:0] inj_rd,output wire [31:0] inj_idx,output wire [159:0] hgi_inj_addr,input wire [1023:0] inj_d,
 output wire [3:0] del_valid,output wire [2179:0] del_flit,output wire [159:0] hgi_del_obase,
 input wire rc_v,input wire [2:0] rc_tag,input wire [255:0] rc_d,
 output wire rr_v,output wire [2:0] rr_tag,output wire [255:0] rr_d,
 input wire [NPT-1:0] phy_up,output wire [NPT-1:0] tx_pin_v,output wire [NPT*612-1:0] tx_pin_flit,
 input wire [NPT-1:0] rx_pin_v,input wire [NPT*612-1:0] rx_pin_flit,output wire [NPT-1:0] retry_requested,
 input wire [279:0] pr_cw_i,pr_ccw_i,output wire [279:0] pr_cw_o,pr_ccw_o,
 output wire [135:0] vm_rq,input wire [2055:0] vm_rr,output wire [2247:0] vm_kq,
 output wire fault,output wire [15:0] fault_cause,output wire done,output wire [31:0] stat_cycles
);
 localparam integer PWT=545,SELW=4;
 // ---- issuer + programme target + fault join
 wire [36:0] program_cfg;wire hgi_start;wire [5:0] hgi_start_pc;
 wire issue_fault,issue_done,uop_v;wire [1535:0] inst;wire [5:0] uop_pc;
 wire issue_busy_raw,issue_done_raw,start_d2;wire [31:0] tap_iteration;wire [87:0] tap_steps;
 ot_hgi_coll_issuer_m u_issuer(.clk_control(clk_issue),.rst_n(rst_n),
  .cfg(program_cfg),.start(hgi_start),.start_pc(hgi_start_pc),.busy(issue_busy_raw),.done(issue_done_raw),
  .fault(issue_fault),.uop_v(uop_v),.uop_pc(uop_pc),.uop_d2(inst),.busy_d2(hgi_busy),.done_d2(issue_done),
  .start_d2(start_d2),.tap_iteration(tap_iteration),.tap_steps(tap_steps));
 assign hgi_done=issue_done;assign done=issue_done;assign hgi_fault=fault;
 // ---- ISA fields (wires; identical positions to ot_hfd_coll_q_static_v4)
 wire [9:0] p_capture_slot=inst[0+:10];
 wire [15:0] p_sink_slot=inst[10+:16];
 wire [63:0] p_sink_select=inst[26+:64];
 wire [2:0] p_lk_wr_v=inst[350+:3],p_lk_rd_v=inst[371+:3],p_lk_rx_expect=inst[392+:3],p_lk_epoch_begin=inst[413+:3];
 wire [7:0] p_lk_epoch=inst[416+:8];
 wire p_rgx_vm=inst[584];
 wire [4:0] p_vm_ingress_slot=inst[585+:5];
 wire [7:0] p_vm_slot_valid=inst[590+:8];
 wire [31:0] p_vm_slot_owner=inst[598+:32];
 wire [87:0] p_ring=inst[630+:88];
 wire p_tkm_start=inst[718];
 wire [3:0] p_tkm_del_slot=inst[719+:4];
 wire [11:0] p_tkm_cfg_n=inst[723+:12];
 wire [12:0] p_tkm_cfg_k=inst[735+:13],p_tkm_cfg_nout=inst[748+:13];
 wire [7:0] p_tkm_cfg_g=inst[761+:8],p_tkm_cfg_gbase=inst[769+:8];
 wire [15:0] p_tkm_cfg_pf=inst[777+:16];
 wire [39:0] p_tkm_cfg_obase=inst[793+:40],p_tkm_cfg_rbase=inst[833+:40];
 wire p_tkm_cfg_has_r=inst[873];
 wire [30:0] p_ar_low=inst[1505+:31];
 wire [54:0] ar={p_ring[81:58],p_ar_low};
 wire a_load_v=ar[0];wire [3:0] a_load_tag=ar[1+:4];wire a_add_read=ar[5];wire [3:0] a_read_tag=ar[6+:4];
 wire a_add_issue=ar[10];wire a_pub_read=ar[11];wire [3:0] a_pub_tag_a=ar[12+:4],a_pub_tag_b=ar[16+:4];
 wire a_pub_bf16=ar[20],a_pub_release=ar[21],a_pub_issue=ar[22];wire [7:0] a_pub_src=ar[23+:8];
 wire [15:0] a_pub_index=ar[31+:16];wire a_arg_mode=ar[47],a_arg_start=ar[48],a_arg_flush=ar[49],a_arg_publish=ar[50];
 wire [3:0] a_arg_in_slot=ar[51+:4];
 // ---- protocol leaf
 wire [135:0] vm_req_pin;wire [1:0] inj_req_pin,inj_source_v;wire [31:0] inj_idx_pin;
 wire [159:0] inj_addr_pin,delivery_obase_pin,rgx_addr_pin;wire [65:0] inj_source_meta;wire [131:0] vm_source_meta;
 wire [2047:0] vm_assembled;wire [3:0] vm_assembled_v;wire [8*NPT-1:0] held_epoch;
 wire [NPT*16-1:0] wr_sequence_pin,rd_sequence_pin,rx_sequence_pin;wire protocol_fault;
 wire tkm_done,tkm_busy;
 wire [ND-1:0] dest_v;wire [ND*PWT-1:0] dest_d;
 assign hgi_del_obase=delivery_obase_pin;assign inj_rd=inj_req_pin;assign inj_idx=inj_idx_pin;
 assign hgi_inj_addr=inj_addr_pin;assign vm_rq=vm_req_pin;
 // ---- sources
 wire [NS-1:0] source_v;wire [NS*PWT-1:0] source_d;
 for(genvar j=0;j<2;j=j+1)begin:g_inj
  assign source_v[j]=inj_source_v[j];
  assign source_d[j*PWT+:PWT]={inj_source_meta[j*33+:33],inj_d[j*512+:512]};
 end
 for(genvar j=0;j<4;j=j+1)begin:g_vm
  assign source_v[2+NPT+j]=vm_assembled_v[j];
  assign source_d[(2+NPT+j)*PWT+:PWT]={vm_source_meta[j*33+:33],vm_assembled[j*512+:512]};
 end
 wire reduce_out_v,reduce_fault;wire [PWT-1:0] reduce_out_data;wire [7:0] reduce_fault_cause;
 assign source_v[NPT+6]=reduce_out_v;assign source_d[(NPT+6)*PWT+:PWT]=reduce_out_data;
 wire [NS-1:0] capture_calendar;
 assign capture_calendar[NPT+6:0]=p_capture_slot[NPT+6:0];
 wire arg_fault,tkm_fault,ring_fault,writer_fault;
 wire tk_w_v;wire [39:0] tk_w_addr;wire [15:0] tk_w_mask;wire [511:0] tk_w_data;wire [31:0] tk_cycles;
 wire [NPT-1:0] link_rx_v,link_abort;wire [NPT*PWT-1:0] link_rx_data;wire [NPT*11-1:0] link_cause;
 wire [NS-1:0] capture_fault;wire [NSL-1:0] select_fault,unavailable_fault;
 generate if(SOLO!=0)begin:g_q3
  wire arg_out_v;wire [PWT-1:0] arg_out_data;
  assign source_v[NPT+7]=arg_out_v;assign source_d[(NPT+7)*PWT+:PWT]=arg_out_data;
  assign capture_calendar[NPT+7]=p_ring[82];
  ot_hgi_coll_ctl_v5_q3 u_control(.clk_control(clk_control),.rst_n(rst_n),.inst(inst),
   .tap_iteration(tap_iteration),.tap_steps(tap_steps),.hgi_start(start_d2),.hgi_busy(hgi_busy),.issue_done(issue_done),.tkm_done(tkm_done),.tkm_busy(tkm_busy),
   .dest_v(dest_v),.rc_v(rc_v),.rc_tag(rc_tag),.vm_rr(vm_rr),
   .vm_req_pin(vm_req_pin),.inj_req_pin(inj_req_pin),.inj_idx_pin(inj_idx_pin),.inj_addr_pin(inj_addr_pin),
   .delivery_obase_pin(delivery_obase_pin),.rgx_addr_pin(rgx_addr_pin),
   .inj_source_v(inj_source_v),.inj_source_meta(inj_source_meta),.vm_source_meta(vm_source_meta),
   .vm_assembled(vm_assembled),.vm_assembled_v(vm_assembled_v),.held_epoch(held_epoch),
   .wr_sequence_pin(wr_sequence_pin),.rd_sequence_pin(rd_sequence_pin),.rx_sequence_pin(rx_sequence_pin),
   .protocol_fault(protocol_fault),.cycles(stat_cycles));
  ot_hgi_coll_argmax_m u_arg(.clk(clk_arg),.rst_n(rst_n),.start(a_arg_start),.mode(a_arg_mode),
   .cfg_g(p_tkm_cfg_g),.cfg_gbase(p_tkm_cfg_gbase),.cfg_rank(a_pub_src),
   .in_slot(a_arg_in_slot),.in_v(dest_v[NPT+8+:4]),
   .in_key({dest_d[(NPT+11)*PWT+:64],dest_d[(NPT+10)*PWT+:64],dest_d[(NPT+9)*PWT+:64],dest_d[(NPT+8)*PWT+:64]}),
   .in_meta({dest_d[(NPT+11)*PWT+512+:33],dest_d[(NPT+10)*PWT+512+:33],dest_d[(NPT+9)*PWT+512+:33],dest_d[(NPT+8)*PWT+512+:33]}),
   .flush_slot(a_arg_flush),.publish_slot(a_arg_publish),.out_v(arg_out_v),.out_flit(arg_out_data),.fault(arg_fault));
  ot_hgi_coll_tkm_m u_tkm(.clk(clk_tkm[33]),.tile_clk(clk_tkm[31:0]),.buffer_clk(clk_tkm[32]),.rst_n(rst_n),
   .start(p_tkm_start),.arg_mode(a_arg_mode),.cfg_n(p_tkm_cfg_n),.cfg_k(p_tkm_cfg_k),.cfg_nout(p_tkm_cfg_nout),
   .cfg_g(p_tkm_cfg_g),.cfg_gbase(p_tkm_cfg_gbase),.cfg_pf(p_tkm_cfg_pf),.cfg_obase(p_tkm_cfg_obase),
   .cfg_rbase(p_tkm_cfg_rbase),.cfg_has_r(p_tkm_cfg_has_r),
   .del_slot(p_tkm_del_slot),.del_valid(dest_v[NPT+8+:4]),.del_flit(dest_d[(NPT+8)*PWT+:4*PWT]),
   .w_v(tk_w_v),.w_addr(tk_w_addr),.w_mask(tk_w_mask),.w_data(tk_w_data),
   .busy(tkm_busy),.done(tkm_done),.fault(tkm_fault),.stat_cycles(tk_cycles));
  ot_hgi_coll_fj_q3 u_fj(.clk(clk_program),.rst_n(rst_n),.qid(qid),.cfg_v(cfg_v),.cfg_target(cfg_target),
   .cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),
   .desc_loops(desc_loops),.launch_v(launch_v),.program_active(issue_busy_raw),.issuer_busy(issue_busy_raw),
   .issuer_fault(issue_fault),.issuer_uop_v(uop_v),.issuer_uop_pc(uop_pc),
   .issuer_cfg(program_cfg),.issuer_start(hgi_start),.issuer_start_pc(hgi_start_pc),
   .configured(program_configured),.init_busy(program_init_busy),.program_fault(program_fault),
   .protocol_fault(protocol_fault),.capture_fault(capture_fault),.select_fault(select_fault),
   .unavailable_fault(unavailable_fault),.link_abort(link_abort),.ring_fault(ring_fault),
   .writer_fault(writer_fault),.reduce_fault(reduce_fault),.arg_fault(arg_fault),.tkm_fault(tkm_fault),
   .fault(fault),.fault_cause(fault_cause));
 end else begin:g_q2
  // No arg/tkm engine in q2: their tkm sinks are unrouted switch outputs; illegal reservations fault in u_fj.
  assign tk_w_v=1'b0;assign tk_w_addr=40'd0;assign tk_w_mask=16'd0;assign tk_w_data=512'd0;
  assign tkm_done=1'b0;assign tkm_busy=1'b0;assign arg_fault=1'b0;assign tkm_fault=1'b0;assign tk_cycles=32'd0;
  ot_hgi_coll_ctl_v5_q2 u_control(.clk_control(clk_control),.rst_n(rst_n),.inst(inst),
   .tap_iteration(tap_iteration),.tap_steps(tap_steps),.hgi_start(start_d2),.hgi_busy(hgi_busy),.issue_done(issue_done),.tkm_done(tkm_done),.tkm_busy(tkm_busy),
   .dest_v(dest_v),.rc_v(rc_v),.rc_tag(rc_tag),.vm_rr(vm_rr),
   .vm_req_pin(vm_req_pin),.inj_req_pin(inj_req_pin),.inj_idx_pin(inj_idx_pin),.inj_addr_pin(inj_addr_pin),
   .delivery_obase_pin(delivery_obase_pin),.rgx_addr_pin(rgx_addr_pin),
   .inj_source_v(inj_source_v),.inj_source_meta(inj_source_meta),.vm_source_meta(vm_source_meta),
   .vm_assembled(vm_assembled),.vm_assembled_v(vm_assembled_v),.held_epoch(held_epoch),
   .wr_sequence_pin(wr_sequence_pin),.rd_sequence_pin(rd_sequence_pin),.rx_sequence_pin(rx_sequence_pin),
   .protocol_fault(protocol_fault),.cycles(stat_cycles));
  ot_hgi_coll_fj_q2 u_fj(.clk(clk_program),.rst_n(rst_n),.qid(qid),.cfg_v(cfg_v),.cfg_target(cfg_target),
   .cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),
   .desc_loops(desc_loops),.launch_v(launch_v),.program_active(issue_busy_raw),.issuer_busy(issue_busy_raw),
   .issuer_fault(issue_fault),.issuer_uop_v(uop_v),.issuer_uop_pc(uop_pc),
   .issuer_cfg(program_cfg),.issuer_start(hgi_start),.issuer_start_pc(hgi_start_pc),
   .configured(program_configured),.init_busy(program_init_busy),.program_fault(program_fault),
   .protocol_fault(protocol_fault),.capture_fault(capture_fault),.select_fault(select_fault),
   .unavailable_fault(unavailable_fault),.link_abort(link_abort),.ring_fault(ring_fault),
   .writer_fault(writer_fault),.reduce_fault(reduce_fault),
   .arg_capture_slot(p_capture_slot[NPT+7]),.tkm_start(p_tkm_start),.tkm_del_slot(p_tkm_del_slot),
   .tkm_dest_v(dest_v[NPT+8+:4]),.fault(fault),.fault_cause(fault_cause));
 end endgenerate
 // ---- reduction (hybrid cluster)
 ot_hgi_coll_reduce_static u_reduce(
  .clk_control(clk_reduce[0]),.clk_state(clk_reduce[16:1]),.clk_add(clk_reduce[32:17]),
  .rst_n(rst_n),.clear(p_ring[83]),.in_v(dest_v[ND-1]),.in_flit(dest_d[(ND-1)*PWT+:PWT]),
  .load_v(a_load_v),.load_tag(a_load_tag),.add_read(a_add_read),.read_tag(a_read_tag),.add_issue(a_add_issue),
  .pub_read(a_pub_read),.pub_tag_a(a_pub_tag_a),.pub_tag_b(a_pub_tag_b),.pub_bf16(a_pub_bf16),
  .pub_meta({1'b1,8'hff,a_pub_src,a_pub_index}),.pub_release(a_pub_release),.pub_issue(a_pub_issue),
  .out_v(reduce_out_v),.out_flit(reduce_out_data),.fault(reduce_fault),.fault_cause(reduce_fault_cause));
 // ---- qslots (pin_v2 partition, flattened: capture leaves + 32-bit switch slices)
 wire [NS*PWT-1:0] captured;wire [NS-1:0] captured_slot;
 for(genvar s=0;s<NS;s=s+1)begin:g_qcap
  ot_hgi_coll_qslots_capture_pin_v2 u_cap(.clk(clk_qslots[s]),.rst_n(rst_n),.src_v(source_v[s]),
   .capture_slot(capture_calendar[s]),.src_d(source_d[s*PWT+:PWT]),.captured(captured[s*PWT+:PWT]),
   .captured_slot(captured_slot[s]),.fault(capture_fault[s]));
 end
 wire [ND-1:0] slice_v[0:NSL-1];
 for(genvar k=0;k<NSL;k=k+1)begin:g_qout
  localparam integer CW=(k<NSL-1)?32:1;
  wire [NS*CW-1:0] words;wire [ND*CW-1:0] results;
  for(genvar s=0;s<NS;s=s+1)begin:g_in
   assign words[s*CW+:CW]=captured[s*PWT+k*32+:CW];
  end
  if(SOLO!=0)begin:g3
   if(k<NSL-1)begin:w ot_hgi_coll_qso_q3_b32 u_out(.clk(clk_qslots[NS+k]),.rst_n(rst_n),.captured(words),
    .captured_slot(captured_slot),.sink_slot(p_sink_slot[ND-1:0]),.sink_select(p_sink_select[ND*SELW-1:0]),
    .dst_v(slice_v[k]),.dst_d(results),.select_fault(select_fault[k]),.unavailable_fault(unavailable_fault[k])); end
   else begin:n ot_hgi_coll_qso_q3_b1 u_out(.clk(clk_qslots[NS+k]),.rst_n(rst_n),.captured(words),
    .captured_slot(captured_slot),.sink_slot(p_sink_slot[ND-1:0]),.sink_select(p_sink_select[ND*SELW-1:0]),
    .dst_v(slice_v[k]),.dst_d(results),.select_fault(select_fault[k]),.unavailable_fault(unavailable_fault[k])); end
  end else begin:g2
   if(k<NSL-1)begin:w ot_hgi_coll_qso_q2_b32 u_out(.clk(clk_qslots[NS+k]),.rst_n(rst_n),.captured(words),
    .captured_slot(captured_slot),.sink_slot(p_sink_slot[ND-1:0]),.sink_select(p_sink_select[ND*SELW-1:0]),
    .dst_v(slice_v[k]),.dst_d(results),.select_fault(select_fault[k]),.unavailable_fault(unavailable_fault[k])); end
   else begin:n ot_hgi_coll_qso_q2_b1 u_out(.clk(clk_qslots[NS+k]),.rst_n(rst_n),.captured(words),
    .captured_slot(captured_slot),.sink_slot(p_sink_slot[ND-1:0]),.sink_select(p_sink_select[ND*SELW-1:0]),
    .dst_v(slice_v[k]),.dst_d(results),.select_fault(select_fault[k]),.unavailable_fault(unavailable_fault[k])); end
  end
  for(genvar d=0;d<ND;d=d+1)begin:g_res
   assign dest_d[d*PWT+k*32+:CW]=results[d*CW+:CW];
  end
 end
 assign dest_v=slice_v[0];
 // ---- rails
 for(genvar k=0;k<NPT;k=k+1)begin:g_link
  assign source_v[2+k]=link_rx_v[k];
  assign source_d[(2+k)*PWT+:PWT]=link_rx_data[k*PWT+:PWT];
  ot_hgi_coll_link_e u_link(.ck(clk_link[k*5+:5]),.rst_n(rst_n),
   .epoch_begin(p_lk_epoch_begin[k]),.epoch_new(p_lk_epoch),.held_epoch(held_epoch[k*8+:8]),
   .wr_v(p_lk_wr_v[k]),.wr_observed_v(dest_v[k]),.wr_seq(wr_sequence_pin[k*16+:16]),
   .wr_flit(dest_d[k*PWT+:PWT]),.rd_v(p_lk_rd_v[k]),.rd_seq(rd_sequence_pin[k*16+:16]),
   .rx_expect_v(p_lk_rx_expect[k]),.rx_expect_seq(rx_sequence_pin[k*16+:16]),
   .phy_up(phy_up[k]),.tx_pin_v(tx_pin_v[k]),.tx_pin_flit(tx_pin_flit[k*612+:612]),
   .rx_pin_v(rx_pin_v[k]),.rx_pin_flit(rx_pin_flit[k*612+:612]),
   .rx_v(link_rx_v[k]),.rx_flit(link_rx_data[k*PWT+:PWT]),
   .epoch_abort(link_abort[k]),.retry_requested(retry_requested[k]),.fault_cause(link_cause[k*11+:11]));
 end
 // ---- deliveries
 for(genvar j=0;j<4;j=j+1)begin:g_delivery
  assign del_valid[j]=dest_v[NPT+j];
  assign del_flit[j*PWT+:PWT]=dest_d[(NPT+j)*PWT+:PWT];
 end
 // ---- VM writer (CLOSED v6 roots physical view; same vector ABI as ot_hgi_coll_static_vmwrite)
 ot_hgi_coll_static_vmwrite_roots_v6_physical u_writer(
  .clk_rgx_data0(clk_vmwrite[0]),.clk_rgx_data1(clk_vmwrite[1]),.clk_rgx_data2(clk_vmwrite[2]),
  .clk_rgx_data3(clk_vmwrite[3]),.clk_rgx_ctrl(clk_vmwrite[4]),.clk_tkw(clk_vmwrite[5]),
  .clk_meta(clk_vmwrite[6]),.clk_body(clk_vmwrite[7]),
  .clk_bank0(clk_vmwrite[8]),.clk_bank1(clk_vmwrite[9]),.clk_bank2(clk_vmwrite[10]),.clk_bank3(clk_vmwrite[11]),
  .clk_bank4(clk_vmwrite[12]),.clk_bank5(clk_vmwrite[13]),.clk_bank6(clk_vmwrite[14]),.clk_bank7(clk_vmwrite[15]),
  .rst_n(rst_n),.sid(qid),.rgx_v(dest_v[NPT+4+:4]),.rgx_addr(rgx_addr_pin),
  .rgx_data0(dest_d[(NPT+4)*PWT+:512]),.rgx_data1(dest_d[(NPT+5)*PWT+:512]),
  .rgx_data2(dest_d[(NPT+6)*PWT+:512]),.rgx_data3(dest_d[(NPT+7)*PWT+:512]),
  .rgx_vm(p_rgx_vm),.tkw_v(tk_w_v),.tkw_d({tk_w_addr,tk_w_mask,tk_w_data}),
  .ingress_slot(p_vm_ingress_slot),.slot_valid(p_vm_slot_valid),.slot_owner(p_vm_slot_owner),
  .kq0(vm_kq[0*281+:281]),.kq1(vm_kq[1*281+:281]),.kq2(vm_kq[2*281+:281]),.kq3(vm_kq[3*281+:281]),
  .kq4(vm_kq[4*281+:281]),.kq5(vm_kq[5*281+:281]),.kq6(vm_kq[6*281+:281]),.kq7(vm_kq[7*281+:281]),
  .launch_done(),.fault(writer_fault));
 // ---- ring (8 CLOSED state-capture lanes + 8 add lanes)
 ot_hgi_coll_ring_v5 u_ring(.clk(clk_ring[0]),.clk_state(clk_ring[8:1]),.clk_add(clk_ring[16:9]),.rst_n(rst_n),
  .qid(qid),.cw_i(pr_cw_i),.ccw_i(pr_ccw_i),.cw_o(pr_cw_o),.ccw_o(pr_ccw_o),
  .lp_we(p_ring[0]),.lp_tag(p_ring[1+:3]),.lp_data(rc_d),
  .state_read_add(p_ring[4]),.state_add_tag(p_ring[5+:3]),.state_add_src(p_ring[8+:2]),
  .state_add_rhs_acc(p_ring[10]),.state_read_tx(p_ring[11]),.state_tx_tag(p_ring[12+:3]),
  .state_tx_acc(p_ring[15]),.state_read_rr(p_ring[16]),.state_rr_tag(p_ring[17+:3]),
  .add_v(p_ring[20]),.add_tag(p_ring[21+:3]),.add_src(p_ring[24+:2]),.add_rhs_acc(p_ring[26]),
  .tx_inject(p_ring[27+:2]),.tx_forward(p_ring[29+:2]),.tx_tag(p_ring[31+:3]),.tx_dst(p_ring[34+:2]),
  .tx_result(p_ring[36]),.tx_acc(p_ring[37]),.rx_slot(p_ring[38+:2]),.rx_kind(p_ring[40+:4]),
  .rx_src(p_ring[44+:4]),.rx_tag(p_ring[48+:6]),.rr_local(p_ring[54]),.rr_local_tag(p_ring[55+:3]),
  .rr_v(rr_v),.rr_tag(rr_tag),.rr_d(rr_d),.fault(ring_fault));
endmodule

// ---------------------------------------------------------------------------------------------------------------
// Die-facing masters. Ports equal host_v4 except: QID parameter -> `qid` strap input; clk_qslots 2 -> NS+18;
// clk_vmwrite 1 -> 16; clk_issue 4 -> 1 (issuer leaf has one CTS root, COLL-CTL 1045); new output fault_cause[15:0].
module ot_hfd_coll_q3_hard_v5(
 input wire rst_n,input wire [1:0] qid,
 input wire clk_program,clk_control,input wire clk_issue,input wire [28:0] clk_qslots,
 input wire [16:0] clk_ring,input wire [32:0] clk_reduce,input wire clk_arg,input wire [33:0] clk_tkm,
 input wire [15:0] clk_vmwrite,input wire [14:0] clk_link,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,input wire [15:0] desc_loops,
 input wire launch_v,
 output wire program_configured,program_init_busy,program_fault,hgi_busy,hgi_done,hgi_fault,
 output wire [1:0] inj_rd,output wire [31:0] inj_idx,output wire [159:0] hgi_inj_addr,input wire [1023:0] inj_d,
 output wire [3:0] del_valid,output wire [2179:0] del_flit,output wire [159:0] hgi_del_obase,
 input wire rc_v,input wire [2:0] rc_tag,input wire [255:0] rc_d,
 output wire rr_v,output wire [2:0] rr_tag,output wire [255:0] rr_d,
 input wire [2:0] phy_up,output wire [2:0] tx_pin_v,output wire [1835:0] tx_pin_flit,
 input wire [2:0] rx_pin_v,input wire [1835:0] rx_pin_flit,output wire [2:0] retry_requested,
 input wire [279:0] pr_cw_i,pr_ccw_i,output wire [279:0] pr_cw_o,pr_ccw_o,
 output wire [135:0] vm_rq,input wire [2055:0] vm_rr,output wire [2247:0] vm_kq,
 output wire fault,output wire [15:0] fault_cause,output wire done,output wire [31:0] stat_cycles
);
 ot_hfd_coll_q_hard_v5_body #(.NPT(3),.SOLO(1)) u_body(.*);
endmodule

module ot_hfd_coll_q2_hard_v5(
 input wire rst_n,input wire [1:0] qid,
 input wire clk_program,clk_control,input wire clk_issue,input wire [26:0] clk_qslots,
 input wire [16:0] clk_ring,input wire [32:0] clk_reduce,
 input wire [15:0] clk_vmwrite,input wire [9:0] clk_link,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,input wire [15:0] desc_loops,
 input wire launch_v,
 output wire program_configured,program_init_busy,program_fault,hgi_busy,hgi_done,hgi_fault,
 output wire [1:0] inj_rd,output wire [31:0] inj_idx,output wire [159:0] hgi_inj_addr,input wire [1023:0] inj_d,
 output wire [3:0] del_valid,output wire [2179:0] del_flit,output wire [159:0] hgi_del_obase,
 input wire rc_v,input wire [2:0] rc_tag,input wire [255:0] rc_d,
 output wire rr_v,output wire [2:0] rr_tag,output wire [255:0] rr_d,
 input wire [1:0] phy_up,output wire [1:0] tx_pin_v,output wire [1223:0] tx_pin_flit,
 input wire [1:0] rx_pin_v,input wire [1223:0] rx_pin_flit,output wire [1:0] retry_requested,
 input wire [279:0] pr_cw_i,pr_ccw_i,output wire [279:0] pr_cw_o,pr_ccw_o,
 output wire [135:0] vm_rq,input wire [2055:0] vm_rr,output wire [2247:0] vm_kq,
 output wire fault,output wire [15:0] fault_cause,output wire done,output wire [31:0] stat_cycles
);
 ot_hfd_coll_q_hard_v5_body #(.NPT(2),.SOLO(0)) u_body(.*,.clk_arg(1'b0),.clk_tkm(34'd0));
endmodule
`default_nettype wire
