`timescale 1ns/1ps
`default_nettype none
// STEWARD-HBM/COLL-LP (10-21): ROWS-256 SAFE fj leaves for the ROWS-256 COLL quadrant landed parents
// ot_hfd_coll_{q3,n1s0,q2}_lp_ars256 (hard issuer ot_hgi_coll_issuer_m256v8, CLOSED hcoll_issuer_r256v8_grid-grid-95a231167).
// The die binds hb_coll_* = ot_hfd_coll_q3_hard_v8x / q2_hard_v8g #(AR_ITER 1, ROWS 256) (RS(144) as one programme = 218 rows
// > 128, TOK-FUNC-HBM-XDIE 10-21 09:26); the 8-bit-pc m256v8 issuer needs an 8-bit-pc programme target, so the ROWS-128 fj
// leaves (ot_hgi_coll_fj_*_r128, PW 7) cannot be bound.  These leaves are the ROWS-256 twins of the SAFE r128 leaves
// (ot_hgi_coll_safe_leaves.sv, unchanged): same capture rung, same RC 32 kept reset copies, same fault join, same edges.
// ot_hgi_coll_static_program_target_s256 = ot_hgi_coll_static_program_target_s128 at ROWS 256 / PW 8 / FW 18, i.e.
// PORT- AND EDGE-IDENTICAL to ot_hgi_coll_static_program_target #(ROWS 256) (the v8g/v8x lockstep reference):
//  * flow store 256 x 18 b in ONE ot_sram_1rw_256x64_m4_r2c2 (the reference's own ROWS-256 macro; the macro read is the
//    scan lookahead), write registered one edge after the accepted segment-6 frame (fw_q/fa_q/fd_q, as s128);
//  * loaded[256] = 16 banks x 16 flops, each bank read through its own kept 4-bit lookup-address copy (cfg_lookup_addr
//    64 b = 16 x cfg_addr[6:3]) and 8 kept scan / write address copies (2 banks each), 4 kept checking copies;
//  * registered decode (tm/seg/ahb = addr[11]/dsp with MSPARE 0x1fc0 / dbad at 256 / ldh with the drain forward);
//  * mode-0 cfg row word carries row[7:6] in cfg[9:8] (the reference's PW 8 encoding), flow word {halt, rep, tgt[7:0], nx[7:0]}
//    with pc MSBs from metadata[55:54] (tgt[7], nx[7]) / [52:51] (tgt[6], nx[6]).
// Schedule: 0 port edges moved -> 0 cycles.  Bench: tb_hfd_coll_<v>_lpf_ars256_eq (parent lockstep vs v8x/v8g #(AR_ITER 1,
// ROWS 256)) + random miter tb_hgi_coll_pt_s256_miter (run_coll_pt_s256_miter.sh) vs program_target #(ROWS 256).  The s256
// mutants have their own defines OT_PT256_MUT_* (the reference #(ROWS 256) also reads OT_PT_MUT_LA_STALE, which would freeze
// both sides): lastale (SRAM flow / loaded lookahead never advance) and ldhnofwd must FAIL the miter.

module ot_hgi_coll_static_program_target_s256 #(
    parameter [7:0] TARGET=8'd52,
    parameter integer MUT_DATA=0,
    parameter integer ASSEMBLY_PIPE=0
)(
    input wire clk,rst_n,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [63:0] cfg_lookup_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,program_active,
    input wire issuer_busy,issuer_fault,issuer_uop_v,
    input wire [7:0] issuer_uop_pc,
    output reg [36:0] issuer_cfg,
    output reg issuer_start,
    output reg [7:0] issuer_start_pc,
    output reg configured,init_busy,fault
);
    localparam integer ROWS=256, PW=8, FW=18;
    localparam [12:0] MSPARE=13'h1fc0;
    // capture rung (as the reference) + the registered decode of the captured values
    reg cv,dv,lv;
    reg [11:0] addr_q,base_q;
    reg [12:0] limit_q;
    reg [255:0] data_q;
    reg tm_q,ahb_q,dsp_q,dbad_q,ldh_q;
    reg [7:0] seg_q;
    reg [1535:0] assembly;
    reg [63:0] metadata;
    reg [6:0] seen;
    reg [PW-1:0] row;
    reg [ROWS-1:0] loaded;
    reg checking,check_bad;
    reg [PW-1:0] check_row;
    reg draining;
    reg [5:0] step;
    reg [PW-1:0] base;
    reg [PW:0] limit;
    reg ld_la;
    reg fw_q;reg [PW-1:0] fa_q;reg [FW-1:0] fd_q;
`ifdef OT_PT256_MUT_LATE_SPC
    localparam integer PCREG=1;
`else
    localparam integer PCREG=(ASSEMBLY_PIPE==0);
`endif
    generate if(PCREG==0)begin:g_start_pc_alias
        assign issuer_start_pc=base;
    end endgenerate
    integer k;
    wire [PW-1:0] c_row=cfg_addr[PW+2:3];
    wire drain_done=draining && step==6'd53;
    wire cfg_loaded;
    wire scan_loaded;
    wire [7:0] scan_next=check_row+1'b1;
    generate if(ASSEMBLY_PIPE!=0)begin:g_loaded_banks
        (* keep = "true" *) reg [3:0] scan_addr[0:7];
        (* keep = "true" *) reg [3:0] write_addr[0:7];
        wire [15:0] cfg_bits,scan_bits;
        (* keep = "true" *) reg [3:0] checking_copy;
        for(genvar cc=0;cc<4;cc=cc+1)begin:g_check_copy
            always @(posedge clk or negedge rst_n)
                if(!rst_n)checking_copy[cc]<=0;
                else begin
                    if(checking && check_row==255)checking_copy[cc]<=0;
                    if(dacc)checking_copy[cc]<=1;
                end
        end
        for(genvar ac=0;ac<8;ac=ac+1)begin:g_addr
            // Loaded write occurs only at drain step53, long after row settled.
            // Unconditional local copies avoid a shared frame-accept hold mux.
            always @(posedge clk)write_addr[ac]<=row[3:0];
            always @(posedge clk or negedge rst_n)
                if(!rst_n)begin scan_addr[ac]<=1;end
                else begin
                    if(checking_copy[ac/2] && check_row!=255)scan_addr[ac]<=check_row[3:0]+4'd2;
                    else scan_addr[ac]<=1;
                end
        end
        for(genvar bk=0;bk<16;bk=bk+1)begin:g_bank
            reg [15:0] loaded_local;
            assign loaded[bk*16+:16]=loaded_local;
            always @(posedge clk or negedge rst_n)
                if(!rst_n)loaded_local<=0;
                else if(drain_done && row[7:4]==4'(bk))loaded_local[write_addr[bk/2]]<=1;
            assign cfg_bits[bk]=loaded[bk*16+cfg_lookup_addr[bk*4+:4]];
            assign scan_bits[bk]=loaded[bk*16+scan_addr[bk/2]];
        end
        assign cfg_loaded=cfg_bits[c_row[7:4]];
        assign scan_loaded=scan_bits[scan_next[7:4]];
    end else begin:g_loaded_binary
        assign cfg_loaded=loaded[c_row];
        assign scan_loaded=loaded[scan_next];
    end endgenerate
    always @(posedge clk)begin
        addr_q<=cfg_addr;data_q<=cfg_data;base_q<=desc_base;limit_q<=desc_limit;
        tm_q<=(cfg_target==TARGET);
        seg_q<=8'b1<<cfg_addr[2:0];
        ahb_q<=(cfg_addr[11]!=1'b0);
        dsp_q<=(cfg_data[255:64]!=0) || ((cfg_data[63:51]&MSPARE)!=0);
        dbad_q<=(desc_base>=ROWS) || (desc_limit>ROWS) || (desc_limit<={1'b0,desc_base}) || (desc_loops!=1);
`ifdef OT_PT256_MUT_LDH_NOFWD
        ldh_q<=cfg_loaded;                                      // mutant: same-edge drain completion not forwarded
`else
        ldh_q<=cfg_loaded || (drain_done && row==c_row);
`endif
    end
    wire [PW-1:0] a_row=addr_q[PW+2:3];
    wire in_range={1'b0,check_row}>=base && {1'b0,check_row}<limit;
    wire [63:0] rd;
    wire [FW-1:0] f=rd[FW-1:0];
    wire ld=ld_la;
    wire [PW-1:0] f_nx=f[PW-1:0],f_tg=f[2*PW-1:PW];wire f_halt=f[FW-1],f_rep=f[FW-2];
    wire row_bad=in_range && (!ld ||
        (!f_halt && (f_nx<base || {1'b0,f_nx}>=limit ||
          (f_rep && (f_tg<base || {1'b0,f_tg}>=limit)))) ||
        ({1'b0,check_row}==limit-1'b1 && !f_halt));
    wire occupied=program_active || issuer_busy || issuer_start;
    // frame / descriptor accept (the reference's fault conditions, on the registered decode)
    wire frame=cv && tm_q;
    wire frame_bad=occupied || lv || draining || checking || fault || dv || ahb_q || seg_q[7] || ldh_q ||
        (seen!=0 && row!=a_row) || ((seen & seg_q[6:0])!=0) || (seg_q[6] && dsp_q);
    wire desc=dv && tm_q;
    wire desc_guard=!(occupied || lv || draining || checking || seen!=0 || fault || cv || dbad_q);
    wire dacc=desc && desc_guard;
    generate if(ASSEMBLY_PIPE!=0)begin:g_descriptor_fields
        // Two copies of the existing descriptor capture edge give each held
        // field its own physical accept cone; no shared 38-load mux enable.
        (* keep = "true" *) reg [1:0] desc_copy;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)desc_copy<=0;
            else desc_copy<={2{desc_v}};
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin base<=0;limit<=0;end
            else begin
                if(desc_copy[0] && tm_q && desc_guard)base<=base_q[PW-1:0];
                if(desc_copy[1] && tm_q && desc_guard)limit<=limit_q[PW:0];
            end
    end endgenerate
    // COLLFJ native census 10-20: six 256-bit write enables had logical fanout 264.
    // Sixteen kept write-enable copies per segment each serve one 16-bit chunk.
    // The SRAM-style write landing is one internal edge later; first assembly read
    // is drain step 1, two edges after the final accepted frame, so output edges stay exact.
    generate if(ASSEMBLY_PIPE!=0)begin:g_assembly_pipe
        (* keep = "true" *) reg [95:0] we_copy;
        reg [255:0] payload;
        always @(posedge clk) payload<=data_q;
        (* keep = "true" *) reg [3:0] meta_we;
        for(genvar mc=0;mc<4;mc=mc+1)begin:g_metadata
            always @(posedge clk or negedge rst_n)
                if(!rst_n)meta_we[mc]<=0;
                else meta_we[mc]<=frame && !frame_bad && seg_q[6];
            always @(posedge clk)
                if(meta_we[mc])metadata[mc*16+:16]<=payload[mc*16+:16];
        end
        for(genvar sg=0;sg<6;sg=sg+1)begin:g_seg
            for(genvar ch=0;ch<16;ch=ch+1)begin:g_chunk
                always @(posedge clk or negedge rst_n)
                    if(!rst_n)we_copy[sg*16+ch]<=0;
                    else we_copy[sg*16+ch]<=frame && !frame_bad && seg_q[sg];
                always @(posedge clk)
                    if(we_copy[sg*16+ch])assembly[sg*256+ch*16+:16]<=payload[ch*16+:16];
            end
        end
    end endgenerate
    wire [31:0] assembly_word;
    generate if(ASSEMBLY_PIPE!=0)begin:g_drain_onehot
        // Kept read selectors are prepared at the previous drain step, avoiding
        // the runtime divide/modulo -> 48:1 word mux control broadcasts.
        (* keep = "true" *) reg [5:0] step_copy[0:1];
        (* keep = "true" *) reg [95:0] rd_select;
        (* keep = "true" *) reg [1:0] drain_copy;
        for(genvar dc=0;dc<2;dc=dc+1)begin:g_drain_copy
            always @(posedge clk or negedge rst_n)
                if(!rst_n)drain_copy[dc]<=0;
                else begin
                    if(draining && step==53)drain_copy[dc]<=0;
                    if(frame && !frame_bad && ((seen|seg_q[6:0])==7'h7f))drain_copy[dc]<=1;
                end
        end
        for(genvar cg=0;cg<2;cg=cg+1)begin:g_counter
            always @(posedge clk or negedge rst_n)
                if(!rst_n)step_copy[cg]<=0;
                else if(frame && !frame_bad && ((seen|seg_q[6:0])==7'h7f))step_copy[cg]<=0;
                else if(draining && step!=53)step_copy[cg]<=step+1'b1;
        end
        for(genvar wd=0;wd<48;wd=wd+1)begin:g_word
            for(genvar half=0;half<2;half=half+1)begin:g_half
                always @(posedge clk or negedge rst_n)
                    if(!rst_n)rd_select[wd*2+half]<=0;
                    else rd_select[wd*2+half]<=drain_copy[wd/24] && step_copy[wd/24]==6'(wd+wd/16);
            end
        end
        reg [31:0] word_or;
        integer rw,rb;
        always @* begin
            word_or=0;
            for(rw=0;rw<48;rw=rw+1)
                for(rb=0;rb<32;rb=rb+1)
                    word_or[rb]=word_or[rb] | (assembly[rw*32+rb] && rd_select[rw*2+rb/16]);
        end
        assign assembly_word=word_or;
    end else begin:g_drain_binary
        assign assembly_word=assembly[(step/17)*512+(step%17-1)*32+:32];
    end endgenerate
    wire fw=frame && !frame_bad && seg_q[6];
    wire [FW-1:0] fwd={data_q[44],|data_q[43:12],data_q[55],data_q[52],data_q[11:6],data_q[54],data_q[51],data_q[5:0]};
`ifdef OT_PT256_MUT_LA_STALE
    wire fr=dacc;                                                  // mutant: lookahead never advances
`else
    wire fr=dacc || (checking && check_row!=PW'(ROWS-1));
`endif
    wire [PW-1:0] fa=dacc ? {PW{1'b0}} : PW'(check_row+1'b1);
    always @(posedge clk)begin fa_q<=a_row;fd_q<=fwd;end
    ot_sram_1rw_256x64_m4_r2c2 u_flow(.clk(clk),.ce_in(fw_q || fr),.we_in(fw_q),.addr_in(fw_q ? fa_q : fa),
        .wd_in(64'(fd_q)),.w_mask_in({64{1'b1}}),.rd_out(rd),
        .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(12'b0));
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            cv<=0;dv<=0;lv<=0;issuer_cfg<=0;issuer_start<=0;
            if(PCREG!=0)issuer_start_pc<=0;configured<=0;init_busy<=0;fault<=0;
            seen<=0;if(ASSEMBLY_PIPE==0)loaded<=0;row<=0;draining<=0;step<=0;
            if(ASSEMBLY_PIPE==0)begin base<=0;limit<=0;end checking<=0;check_bad<=0;check_row<=0;ld_la<=0;fw_q<=0;
        end else begin
            cv<=cfg_v;dv<=desc_v;lv<=launch_v;
            issuer_cfg<=0;issuer_start<=0;fw_q<=fw;
            if(issuer_fault)fault<=1;
            if(checking)begin
                if(row_bad)check_bad<=1;
                if(check_row==PW'(ROWS-1))begin
                    checking<=0;init_busy<=0;
                    if(check_bad || row_bad)fault<=1;
                    else if(!fault)configured<=1;
                end else begin
                    check_row<=check_row+1'b1;
`ifndef OT_PT256_MUT_LA_STALE
                    ld_la<=scan_loaded;
`endif
                end
            end
            if(issuer_uop_v && (!configured || issuer_uop_pc<base || {1'b0,issuer_uop_pc}>=limit))fault<=1;
            if(draining)begin
                if(step<51)begin
                    if(step%17==0)issuer_cfg<={1'b1,4'd0,22'b0,row[PW-1:PW-2],2'(step/17),row[5:0]};
                    else issuer_cfg<={1'b1,4'd1,assembly_word ^ ((MUT_DATA!=0 && step==1)?32'b1:32'b0)};
                end else if(step==51)issuer_cfg<={1'b1,4'd2,metadata[31:0]};
                else if(step==52)issuer_cfg<={1'b1,4'd3,metadata[63:32]};
                // step53 ensures the issuer has sampled its final metadata.
                if(step==53)begin
                    draining<=0;if(ASSEMBLY_PIPE==0)loaded[row]<=1;seen<=0;init_busy<=0;
                end else step<=step+1'b1;
            end
            if(frame)begin
                if(frame_bad)fault<=1;
                else begin
                    row<=a_row;seen<=seen | seg_q[6:0];init_busy<=1;
                    if(ASSEMBLY_PIPE==0 && seg_q[6])metadata<=data_q[63:0];
                    if(ASSEMBLY_PIPE==0)for(k=0;k<6;k=k+1) if(seg_q[k]) assembly[k*256+:256]<=data_q;
                    if((seen | seg_q[6:0])==7'h7f)begin draining<=1;step<=0;end
                end
            end
            if(desc)begin
                if(!dacc)fault<=1;
                else begin
                    if(ASSEMBLY_PIPE==0)begin base<=base_q[PW-1:0];limit<=limit_q[PW:0];end configured<=0;
`ifndef OT_PT256_MUT_LATE_SPC
                    if(PCREG!=0)issuer_start_pc<=base_q[PW-1:0];                     // mutant: start_pc only at launch (v7 start faults)
`endif
                    checking<=1;check_row<=0;check_bad<=0;init_busy<=1;
                    ld_la<=loaded[0];
                end
            end
            if(lv && configured)begin
                if(occupied || draining || checking || seen!=0 || fault || cv || dv)fault<=1;
                else begin issuer_start<=1;if(PCREG!=0)issuer_start_pc<=base;end
            end else if(lv && (seen!=0 || draining || checking))fault<=1;
        end
    end
endmodule

module ot_hgi_coll_fj_core_s256 #(parameter integer NPT=3,SOLO=1,NS=11,NSL=18,RC=20,PW=8)(
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
 input wire [PW-1:0] issuer_uop_pc,
 output wire [36:0] issuer_cfg,
 output wire issuer_start,
 output wire [PW-1:0] issuer_start_pc,
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
 // SAFE item 1/3: rst_n (landed in 2 registered stages at the face by the kit's reset_landing) is sampled by RC KEPT,
 // identical copies (one edge, the same release edge as the reference's single rst_q); every reset load of this leaf hangs
 // off copy 0 in RTL and physical/common_flow/ot_rst_copies.tcl (kit reset_relay_split max_loads 32) re-points them by
 // hierarchical-name region over the RC copies (~300 loads / 12 = ~25 per copy).  Family name suffix __ot_rlv.
 (* keep = "true" *) reg [RC-1:0] rst__ot_rlv;
 always @(posedge clk) rst__ot_rlv<={RC{rst_n}};
 wire rst_q=rst__ot_rlv[0];
 reg cv_q,dv_q,lv_q,act_q,ibusy_q,ifault_q,iuv_q;
 reg [7:0] tgt_q;reg [1:0] qid_q;reg [11:0] addr_q,base_q;reg [255:0] data_q;reg [12:0] limit_q;reg [15:0] loops_q;
 (* keep = "true" *) reg [63:0] cfg_lookup_addr;
 always @(posedge clk)cfg_lookup_addr<={16{cfg_addr[6:3]}};
 reg [PW-1:0] iupc_q;
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
 ot_hgi_coll_static_program_target_s256 #(.TARGET(8'd52),.ASSEMBLY_PIPE(1)) u_program(
  .clk(clk),.rst_n(rst_q),.cfg_v(cv_q),.cfg_target(target_eff),
  .cfg_addr(addr_q),.cfg_lookup_addr(cfg_lookup_addr),.cfg_data(data_q),.desc_v(dv_q),.desc_base(base_q),
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

// ROWS-256 twin of ot_hgi_coll_fj_n2s1_r128 (same NPT / SOLO / NS). RC 40 kept reset copies (r128: 32): the 256-row target adds ~146 reset
// loads (loaded 128 -> 256 bits, 8 scan/write address copies, 4 checking copies): ~673 loads / 40 = <= 17 per copy
// (reset_relay_split max 19); the kit lands rst_n with 2 last-stage copies (OT_RST_LAND_COPIES rst_n=2, 20 loads each).
module ot_hgi_coll_fj_n2s1_r256(
 input wire clk,rst_n,input wire [1:0] qid,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,input wire [15:0] desc_loops,
 input wire launch_v,program_active,issuer_busy,issuer_fault,issuer_uop_v,input wire [7:0] issuer_uop_pc,
 output wire [36:0] issuer_cfg,output wire issuer_start,output wire [7:0] issuer_start_pc,
 output wire configured,init_busy,program_fault,
 input wire protocol_fault,input wire [9:0] capture_fault,input wire [17:0] select_fault,unavailable_fault,
 input wire [1:0] link_abort,input wire ring_fault,writer_fault,reduce_fault,arg_fault,tkm_fault,
 output wire fault,output wire [15:0] fault_cause);
 ot_hgi_coll_fj_core_s256 #(.NPT(2),.SOLO(1),.NS(10),.NSL(18),.RC(40)) u(.clk(clk),.rst_n(rst_n),.qid(qid),.cfg_v(cfg_v),.cfg_target(cfg_target),
  .cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),
  .desc_loops(desc_loops),.launch_v(launch_v),.program_active(program_active),.issuer_busy(issuer_busy),
  .issuer_fault(issuer_fault),.issuer_uop_v(issuer_uop_v),.issuer_uop_pc(issuer_uop_pc),.issuer_cfg(issuer_cfg),
  .issuer_start(issuer_start),.issuer_start_pc(issuer_start_pc),.configured(configured),.init_busy(init_busy),
  .program_fault(program_fault),.protocol_fault(protocol_fault),.capture_fault(capture_fault),
  .select_fault(select_fault),.unavailable_fault(unavailable_fault),.link_abort(link_abort),.ring_fault(ring_fault),
  .writer_fault(writer_fault),.reduce_fault(reduce_fault),.arg_fault(arg_fault),.tkm_fault(tkm_fault),
  .arg_capture_slot(1'b0),.tkm_start(1'b0),.tkm_del_slot(4'd0),.tkm_dest_v(4'd0),
  .fault(fault),.fault_cause(fault_cause));
endmodule

// ROWS-256 twin of ot_hgi_coll_fj_q2_r128 (same NPT / SOLO / NS). RC 40 kept reset copies (r128: 32): the 256-row target adds ~146 reset
// loads (loaded 128 -> 256 bits, 8 scan/write address copies, 4 checking copies): ~673 loads / 40 = <= 17 per copy
// (reset_relay_split max 19); the kit lands rst_n with 2 last-stage copies (OT_RST_LAND_COPIES rst_n=2, 20 loads each).
module ot_hgi_coll_fj_q2_r256(
 input wire clk,rst_n,input wire [1:0] qid,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,input wire [15:0] desc_loops,
 input wire launch_v,program_active,issuer_busy,issuer_fault,issuer_uop_v,input wire [7:0] issuer_uop_pc,
 output wire [36:0] issuer_cfg,output wire issuer_start,output wire [7:0] issuer_start_pc,
 output wire configured,init_busy,program_fault,
 input wire protocol_fault,input wire [8:0] capture_fault,input wire [17:0] select_fault,unavailable_fault,
 input wire [1:0] link_abort,input wire ring_fault,writer_fault,reduce_fault,
 input wire arg_capture_slot,tkm_start,input wire [3:0] tkm_del_slot,tkm_dest_v,
 output wire fault,output wire [15:0] fault_cause);
 ot_hgi_coll_fj_core_s256 #(.NPT(2),.SOLO(0),.NS(9),.NSL(18),.RC(40)) u(.clk(clk),.rst_n(rst_n),.qid(qid),.cfg_v(cfg_v),.cfg_target(cfg_target),
  .cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),
  .desc_loops(desc_loops),.launch_v(launch_v),.program_active(program_active),.issuer_busy(issuer_busy),
  .issuer_fault(issuer_fault),.issuer_uop_v(issuer_uop_v),.issuer_uop_pc(issuer_uop_pc),.issuer_cfg(issuer_cfg),
  .issuer_start(issuer_start),.issuer_start_pc(issuer_start_pc),.configured(configured),.init_busy(init_busy),
  .program_fault(program_fault),.protocol_fault(protocol_fault),.capture_fault(capture_fault),
  .select_fault(select_fault),.unavailable_fault(unavailable_fault),.link_abort(link_abort),.ring_fault(ring_fault),
  .writer_fault(writer_fault),.reduce_fault(reduce_fault),.arg_capture_slot(arg_capture_slot),.tkm_start(tkm_start),
  .tkm_del_slot(tkm_del_slot),.tkm_dest_v(tkm_dest_v),.arg_fault(1'b0),.tkm_fault(1'b0),.fault(fault),.fault_cause(fault_cause));
endmodule

// ROWS-256 twin of ot_hgi_coll_fj_n1s0_r128 (same NPT / SOLO / NS). RC 40 kept reset copies (r128: 32): the 256-row target adds ~146 reset
// loads (loaded 128 -> 256 bits, 8 scan/write address copies, 4 checking copies): ~673 loads / 40 = <= 17 per copy
// (reset_relay_split max 19); the kit lands rst_n with 2 last-stage copies (OT_RST_LAND_COPIES rst_n=2, 20 loads each).
module ot_hgi_coll_fj_n1s0_r256(
 input wire clk,rst_n,input wire [1:0] qid,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,input wire [15:0] desc_loops,
 input wire launch_v,program_active,issuer_busy,issuer_fault,issuer_uop_v,input wire [7:0] issuer_uop_pc,
 output wire [36:0] issuer_cfg,output wire issuer_start,output wire [7:0] issuer_start_pc,
 output wire configured,init_busy,program_fault,
 input wire protocol_fault,input wire [7:0] capture_fault,input wire [17:0] select_fault,unavailable_fault,
 input wire [0:0] link_abort,input wire ring_fault,writer_fault,reduce_fault,
 input wire arg_capture_slot,tkm_start,input wire [3:0] tkm_del_slot,tkm_dest_v,
 output wire fault,output wire [15:0] fault_cause);
 ot_hgi_coll_fj_core_s256 #(.NPT(1),.SOLO(0),.NS(8),.NSL(18),.RC(40)) u(.clk(clk),.rst_n(rst_n),.qid(qid),.cfg_v(cfg_v),.cfg_target(cfg_target),
  .cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),
  .desc_loops(desc_loops),.launch_v(launch_v),.program_active(program_active),.issuer_busy(issuer_busy),
  .issuer_fault(issuer_fault),.issuer_uop_v(issuer_uop_v),.issuer_uop_pc(issuer_uop_pc),.issuer_cfg(issuer_cfg),
  .issuer_start(issuer_start),.issuer_start_pc(issuer_start_pc),.configured(configured),.init_busy(init_busy),
  .program_fault(program_fault),.protocol_fault(protocol_fault),.capture_fault(capture_fault),
  .select_fault(select_fault),.unavailable_fault(unavailable_fault),.link_abort(link_abort),.ring_fault(ring_fault),
  .writer_fault(writer_fault),.reduce_fault(reduce_fault),.arg_capture_slot(arg_capture_slot),.tkm_start(tkm_start),
  .tkm_del_slot(tkm_del_slot),.tkm_dest_v(tkm_dest_v),.arg_fault(1'b0),.tkm_fault(1'b0),.fault(fault),.fault_cause(fault_cause));
endmodule

`default_nettype wire
