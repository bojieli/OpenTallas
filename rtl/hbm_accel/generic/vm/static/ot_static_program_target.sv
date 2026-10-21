`timescale 1ns/1ps
`default_nettype none
// F20 programme target. Two registered transport rungs; execution never waits.
// A descriptor arms exactly one launch. Actual programme-pin writes maintain a
// finite installed-row bitmap, not a shadow payload. The first write after a
// descriptor starts a fresh image generation; unwritten old SRAM rows are invalid.
// A descriptor-only rearm may reuse an installed image. Descriptor verification
// scans the exact [base,limit) range before configured can rise; descriptor-only
// reuse of the same resident range reuses its proof. All scanning and
// write-commit latency is initialization; an early launch faults without replay.
// TGT_PIN=1 (H-NETLIST 0600): the target id comes from the identity strap pin tgt (die constant), so one hardened master
// serves every target id; TGT_PIN=0 keeps the TARGET parameter (tgt unused).
// CAP_CLK=1 (H-NETLIST 0600): the F20 input-capture rung (cv/dv/lv, target/address/data/base/limit/loops, tgt) runs on
// clk_cap, a related same-frequency phase-0 root kept short at the face; the body (bitmap, scan, outputs) stays on clk.
module ot_static_program_target #(parameter [7:0] TARGET=8'd48,parameter integer PCW=10,parameter integer TGT_PIN=0,
                                  parameter integer CAP_CLK=0,
                                  // QHUB-S1 10-19 (SAFE-DESIGN item 3): RLC > 1 = the internal reset (reset_live) becomes RLC KEPT
                                  // identical copies (wire *__ot_rlv), which the kit's reset_relay_split pass
                                  // (physical/common_flow/ot_rst_copies.tcl) spreads over the body's ~1,060 reset loads (<= 32 a
                                  // copy).  Same assert / release edges as reset_live.  Default 1 = unchanged.
                                  parameter integer RLC=1,
                                  // HBM-HCBANK6 10-20 (QHUB SAFE 2, native32 census): FAN32 1 = every driver <= 32 loads with the SAME
                                  // externally visible behaviour.  The 1,024-row installed bitmap is written ONE edge later from
                                  // slice-local kept copies (32 slices x 32 rows: clear / set-enable / low-address copies, fed by 2
                                  // first-level copies of program_cfg_we / install_open / address), and the scan reads it through a
                                  // one-entry bypass of that pending write, so the scan sees exactly the bitmap the FAN32 0 form holds
                                  // on every edge (write-after-clear generation semantics included).  The scan row is held in 16 kept
                                  // slice copies (64-row read slices) next to the master counter.  Requires PCW 10.  Default 0 = unchanged.
                                  parameter integer FAN32=0,
                                  parameter integer MUT=0)(   // bench: FAN32 1 + MUT 1 = scan without the pending-write bypass
    input wire clk,rst_n,
    input wire clk_cap,   // used only when CAP_CLK=1
    input wire [7:0] tgt,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    input wire program_active,
    output reg program_cfg_we,
    output reg [PCW-1:0] program_cfg_addr,
    output reg [255:0] program_cfg_data,
    output reg program_start_v,
    output reg [PCW-1:0] program_start_base,
    output reg [PCW:0] program_start_limit,
    output reg [15:0] program_start_loops,
    output reg configured,fault
);
    localparam integer ROWS=1<<PCW;
    initial if(PCW<8 || PCW>12)$fatal(1,"programme target PCW must be8..12");
    // External reset reaches two synchronizer pins, not the entire valid bitmap.
    (* async_reg = "true" *) reg reset_meta,reset_live;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin reset_meta<=0;reset_live<=0;end
        else begin reset_meta<=1;reset_live<=reset_meta;end
    wire rl, rlb;
    generate if(FAN32!=0)begin:g_rlf
        // two reset families (<= 31 copies each: the sync flop drives every copy), rows 0..511 of the bitmap on rlb
        (* async_reg = "true", keep = "true", dont_touch = "true" *) reg rma, rmb;   // one kept synchroniser per family
        always @(posedge clk or negedge rst_n) if(!rst_n)begin rma<=0;rmb<=0;end else begin rma<=1;rmb<=1;end
        // HBM-HC7-QHUB 10-20: family a 28 copies (the split measured 780 loads on 24 -> 33 a copy)
        (* keep = "true", dont_touch = "true" *) reg [27:0] rla__ot_rlv;
        (* keep = "true", dont_touch = "true" *) reg [23:0] rlb__ot_rlv;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin rla__ot_rlv<=0;rlb__ot_rlv<=0;end
            else begin rla__ot_rlv<={28{rma}};rlb__ot_rlv<={24{rmb}};end
        assign rl=rla__ot_rlv[0]; assign rlb=rlb__ot_rlv[0];
    end else if(RLC>1)begin:g_rlc
        (* keep = "true", dont_touch = "true" *) reg [RLC-1:0] rl__ot_rlv;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)rl__ot_rlv<={RLC{1'b0}};
            else rl__ot_rlv<={RLC{reset_meta}};
        assign rl=rl__ot_rlv[0]; assign rlb=rl;
    end else begin:g_rl1
        assign rl=reset_live; assign rlb=rl;
    end endgenerate
    reg cv,dv,lv;
    reg [7:0] target;
    wire clk_in=(CAP_CLK!=0)?clk_cap:clk;
    reg [7:0] tgt_q; always @(posedge clk_in) tgt_q<=tgt;
    wire [7:0] tid=(TGT_PIN!=0)?tgt_q:TARGET;
    reg [11:0] address,base;
    reg [PCW-1:0] stored_base;
    reg [255:0] data_q;
    reg [12:0] limit;
    reg [PCW:0] stored_limit;
    reg [15:0] loops,stored_loops;
    reg [ROWS-1:0] installed;
    reg install_open,armed,scanning,validated,missing;
    reg [PCW-1:0] scan_row;
    reg [PCW:0] scan_limit;
    reg [1:0] commit;
    wire launch_ready=armed&&validated&&!scanning&&commit==0&&!program_active&&!fault;
    // installed-row view seen by the scan (FAN32 0: the bitmap itself; FAN32 1: bitmap + the pending write, see g_f32)
    wire row_installed;
    always @(posedge clk_in)begin
        target<=cfg_target;address<=cfg_addr;data_q<=cfg_data;
        base<=desc_base;limit<=desc_limit;loops<=desc_loops;
    end
    always @(posedge clk_in or negedge rl)
        if(!rl)begin cv<=0;dv<=0;lv<=0;end
        else begin cv<=cfg_v;dv<=desc_v;lv<=launch_v;end
    always @(posedge clk or negedge rl)
        if(!rl)begin
            program_cfg_we<=0;program_start_v<=0;configured<=0;fault<=0;
            if(FAN32==0)installed<=0;
            install_open<=0;armed<=0;scanning<=0;validated<=0;missing<=0;
            if(FAN32==0)begin scan_row<=0;scan_limit<=0;end
            commit<=0;
        end else begin
            program_cfg_we<=0;program_start_v<=0;
            configured<=launch_ready&&!lv&&!((cv||dv)&&target==tid);
            // Observe the real registered programme-write pins. The neighbour's
            // capture and SRAM write consume two further edges; commit masks both.
            commit<={commit[0],program_cfg_we};
            if(program_cfg_we)begin
                if(FAN32==0)begin
                    if(!install_open)installed<=({{(ROWS-1){1'b0}},1'b1}<<program_cfg_addr);
                    else installed[program_cfg_addr]<=1'b1;
                end
                install_open<=1;
            end
            if(cv && target==tid)begin
                armed<=0;validated<=0;configured<=0;
                if(program_active || scanning || lv || {1'b0,address}>=(13'd1<<PCW) ||
                   data_q[255:240]!=16'hc7a1 || data_q[239:224]!={4'b0,address})fault<=1;
                else begin program_cfg_we<=1;if(FAN32==0)begin program_cfg_addr<=address[PCW-1:0];program_cfg_data<=data_q;end end
            end
            if(dv && target==tid)begin
                armed<=0;validated<=0;configured<=0;install_open<=0;
                if(program_active || scanning || lv || cv || loops==0 || limit<={1'b0,base} || limit>(13'd1<<PCW))fault<=1;
                else begin
                    if(FAN32==0)begin stored_base<=base[PCW-1:0];stored_limit<=limit[PCW:0];stored_loops<=loops;end
                    armed<=1;missing<=0;
                    if(validated && base==stored_base && limit==stored_limit)begin
                        // Same range in the unchanged resident generation: reuse
                        // the completed row proof, not a stale descriptor arm.
                        validated<=1;scanning<=0;
                    end else begin
                        scanning<=1;if(FAN32==0)begin scan_row<=base[PCW-1:0];scan_limit<=limit[PCW:0];end
                    end
                end
            end
            if(scanning)begin
                if(!row_installed)missing<=1;
                if({1'b0,scan_row}+1'b1==scan_limit)begin
                    scanning<=0;
                    if(missing || !row_installed)fault<=1;
                    else validated<=1;
                end else if(FAN32==0)scan_row<=scan_row+1'b1;
            end
            if(lv && armed)begin
                armed<=0;configured<=0;
                if(!launch_ready || cv || dv)fault<=1;
                else begin
                    program_start_v<=1;
                    if(FAN32==0)begin program_start_base<=stored_base;program_start_limit<=stored_limit;program_start_loops<=stored_loops;end
                end
            end
        end
    generate if(FAN32==0)begin:g_f0
        assign row_installed=installed[scan_row];
    end else begin:g_f32
        initial if(PCW!=10)$fatal(1,"FAN32 needs PCW 10 (32 x 32 write slices, 16 x 64 read slices)");
        // first-level copies (same D and edge as program_cfg_we / install_open / program_cfg_addr)
        (* keep = "true", dont_touch = "true" *) reg [2:0] we_a,open_a;   // copy 2 feeds the bypass
        (* keep = "true", dont_touch = "true" *) reg [PCW-1:0] addr_a [0:2];
        always @(posedge clk or negedge rl)
            if(!rl)begin we_a<=0;open_a<=0;end
            else begin
                we_a<=3'b000;
                if(cv && target==tid && !(program_active || scanning || lv || {1'b0,address}>=(13'd1<<PCW) ||
                   data_q[255:240]!=16'hc7a1 || data_q[239:224]!={4'b0,address}))we_a<=3'b111;
                if(program_cfg_we)open_a<=3'b111;
                if(dv && target==tid)open_a<=3'b000;
            end
        // (addr_a copies are loaded below, after the accept-select copies)
        // pending write (one edge after program_cfg_we): slice copies + one bypass copy
        (* keep = "true", dont_touch = "true" *) reg [31:0] clr_s,set_s;
        (* keep = "true", dont_touch = "true" *) reg [4:0] lo_s [0:31];
        reg pend_we,pend_open; reg [PCW-1:0] pend_addr;
        always @(posedge clk or negedge rl)
            if(!rl)begin clr_s<=0;set_s<=0;pend_we<=0;pend_open<=0;end
            else begin
                pend_we<=we_a[2];pend_open<=open_a[2];
                for(integer k=0;k<32;k=k+1)begin
                    clr_s[k]<=we_a[k/16]&&!open_a[k/16];
                    set_s[k]<=we_a[k/16]&&(addr_a[k/16][9:5]==5'(k));
                end
            end
        always @(posedge clk)begin
            pend_addr<=addr_a[2];
            for(integer k=0;k<32;k=k+1)lo_s[k]<=addr_a[k/16][4:0];
        end
        reg [ROWS-1:0] inst;
        for(genvar k=0;k<32;k=k+1)begin:g_ir
            wire rk=(k<16)?rlb:rl;
            always @(posedge clk or negedge rk)
                if(!rk)inst[k*32+:32]<=0;
                else for(integer r=0;r<32;r=r+1)
                    inst[k*32+r]<=(inst[k*32+r]&&!clr_s[k])||(set_s[k]&&lo_s[k]==5'(r));
        end
        // ---- copies of the F20 capture-rung valids / target id (same D: their pins) -> per-group accept selects.  Every select
        // that fans out to a register group is a KEPT wire (an ABC boundary), so the shared terms cannot be pushed into each bit.
        (* keep = "true", dont_touch = "true" *) reg [19:0] cv_c;   // 17..19: addr_a copy enables
        (* keep = "true", dont_touch = "true" *) reg cv_l;
        (* keep = "true", dont_touch = "true" *) reg [10:0] dv_c;
        (* keep = "true", dont_touch = "true" *) reg [2:0] lv_c;
        (* keep = "true", dont_touch = "true" *) reg [9:0] sc_c;        // copies of scanning (same D)
        (* keep = "true", dont_touch = "true" *) reg [7:0] tg_c [0:4];  // copies of the captured target id (4: scan load)
        // HBM-HC7-QHUB 10-20: the pointer load values are REGISTERED decodes of the descriptor base pins (were base_a/base_b
        // copies, which synthesis merged with `base` -> base[4] drove 39 loads); same capture edge, so lo_dq == 1 << base[4:0]
        // (predecoded at the pin register: 2 + 3 bit one-hots, so a descriptor pin loads <= ~10 gates)
        reg [3:0] lo_pa, hi_pa; reg [7:0] lo_pb, hi_pb;
        wire [31:0] lo_dq, hi_dq;
        for(genvar i=0;i<32;i=i+1)begin:g_dq
            assign lo_dq[i]=lo_pa[i%4]&lo_pb[i/4]; assign hi_dq[i]=hi_pa[i%4]&hi_pb[i/4];
        end
        always @(posedge clk_in or negedge rl)
            if(!rl)begin cv_c<=0;cv_l<=0;dv_c<=0;lv_c<=0;end
            else begin cv_c<={20{cfg_v}};cv_l<=cfg_v;dv_c<={11{desc_v}};lv_c<={3{launch_v}};end
        always @(posedge clk_in)begin
            for(integer k=0;k<5;k=k+1)tg_c[k]<=cfg_target;
            lo_pa<=4'd1<<desc_base[1:0];lo_pb<=8'd1<<desc_base[4:2];hi_pa<=4'd1<<desc_base[6:5];hi_pb<=8'd1<<desc_base[9:7];
        end
        wire [4:0] tm;
        for(genvar k=0;k<5;k=k+1)begin:g_tm
            assign tm[k]=tg_c[k]==tid;
        end
        // HBM-HC7-QHUB 10-20: one cfg-accept copy per addr_a copy (one shared `cv && target==tid` drove 39 loads); same edge
        for(genvar k=0;k<3;k=k+1)begin:g_aa
            always @(posedge clk) if(cv_c[17+k] && tm[0]) addr_a[k]<=address[PCW-1:0];
        end
        // HBM-HC7-QHUB 10-20: the shared accept terms are KEPT wires (one ABC node each) so their inputs load one cone
        (* keep = "true" *) wire wbad=program_active || scanning || lv || {1'b0,address}>=(13'd1<<PCW) || data_q[255:240]!=16'hc7a1 ||
                  data_q[239:224]!={4'b0,address};
        (* keep = "true" *) wire dbad=program_active || scanning || lv || cv_l || loops==0 || limit<={1'b0,base} || limit>(13'd1<<PCW);
        (* keep = "true" *) wire reuse=validated && base==stored_base && limit==stored_limit;
        // programme write data / address: 17 groups of 16 bits (a hold select is 2 loads a bit)
        for(genvar k=0;k<17;k=k+1)begin:g_wd
            (* keep = "true" *) wire acc=cv_c[k] && tm[k/9] && !wbad;
            always @(posedge clk)
                if(acc)begin
                    if(k<16)program_cfg_data[k*16+:16]<=data_q[k*16+:16];
                    else program_cfg_addr<=address[PCW-1:0];
                end
        end
        // descriptor store: stored_base / stored_limit / stored_loops on 3 accept copies
        (* keep = "true" *) wire da0=dv_c[0] && tm[2] && !dbad;
        (* keep = "true" *) wire da1=dv_c[1] && tm[2] && !dbad;
        (* keep = "true" *) wire da2=dv_c[2] && tm[2] && !dbad;
        always @(posedge clk) if(da0)stored_base<=base[PCW-1:0];
        always @(posedge clk) if(da1)stored_limit<=limit[PCW:0];
        always @(posedge clk) if(da2)stored_loops<=loops;
        // launch: start base / limit / loops on 3 accept copies
        wire lgo=armed && launch_ready && !cv_l && !dv;
        (* keep = "true" *) wire la0=lv_c[0] && lgo;
        (* keep = "true" *) wire la1=lv_c[1] && lgo;
        (* keep = "true" *) wire la2=lv_c[2] && lgo;
        always @(posedge clk) if(la0)program_start_base<=stored_base;
        always @(posedge clk) if(la1)program_start_limit<=stored_limit;
        always @(posedge clk) if(la2)program_start_loops<=stored_loops;
        // scan row / limit (master counter) and the 2D one-hot read pointers (lo: 32 rows of a slice, hi: 32 slices)
        // HBM-HC7-QHUB 10-20 (native32 census: the slast compare drove 41 pointer loads, the half selects 33/34): slast
        // = (scan_row + 1 == scan_limit) is held in 10 KEPT registers loaded from the NEXT scan_row / scan_limit (the same
        // value on every edge as the combinational compare; both reset to 0 -> slast 0), and the one-hot pointers move in
        // 8 groups of 8 bits (lo 0..3, hi 4..7), each with its own load / step select and slast copy.
        (* keep = "true", dont_touch = "true" *) reg [9:0] sl_c;        // 0 sc_n, 1 sstep, 2..9 pointer groups
        (* keep = "true" *) wire sload=dv && tm[4] && !dbad && !reuse;    // scan_row[4:0]
        (* keep = "true" *) wire sloadh=dv && tm[4] && !dbad && !reuse;   // scan_row[9:5]
        (* keep = "true" *) wire sloadl=dv && tm[4] && !dbad && !reuse;   // scan_limit
        wire sc_n=(sc_c[0] && sl_c[0])?1'b0:(dv && tm[4] && !dbad)?!reuse:sc_c[0];
        always @(posedge clk or negedge rl)
            if(!rl)sc_c<=0;
            else sc_c<={10{sc_n}};
        (* keep = "true" *) wire sstep=sc_c[1] && !sl_c[1];
        wire [4:0] row_lo_n=sload?base[4:0]:sstep?scan_row[4:0]+5'd1:scan_row[4:0];
        wire [PCW-6:0] row_hi_n=sloadh?base[PCW-1:5]:sstep?scan_row[PCW-1:5]+((&scan_row[4:0])?1'b1:1'b0):scan_row[PCW-1:5];
        wire [PCW:0] lim_n=sloadl?limit[PCW:0]:scan_limit;
        wire sl_n={1'b0,row_hi_n,row_lo_n}+1'b1==lim_n;
        always @(posedge clk or negedge rl)
            if(!rl)begin scan_row<=0;scan_limit<=0;sl_c<=0;end
            else begin scan_row<={row_hi_n,row_lo_n};scan_limit<=lim_n;sl_c<={10{sl_n}};end
        reg [31:0] lo1h, hi1h;                                      // state
        (* keep = "true", dont_touch = "true" *) reg [31:0] lo_a, lo_b;   // copies: slices 0..15 / 16..31
        // per-group selects (8 bits each), kept wires
        wire [7:0] ld_h, st_h;
        for(genvar h=0;h<8;h=h+1)begin:g_h
            (* keep = "true" *) wire ldw=dv_c[3+h] && tm[3] && !dbad && !reuse;
            (* keep = "true" *) wire stw=sc_c[2+h] && !sl_c[2+h] && ((h<4)?1'b1:lo1h[31]);
            assign ld_h[h]=ldw; assign st_h[h]=stw;
        end
        wire [31:0] lo_rot={lo1h[30:0],lo1h[31]}, hi_rot={hi1h[30:0],hi1h[31]};
        wire [31:0] lo_n, hi_n;
        for(genvar h=0;h<4;h=h+1)begin:g_pn
            assign lo_n[h*8+:8]=ld_h[h]?lo_dq[h*8+:8]:st_h[h]?lo_rot[h*8+:8]:lo1h[h*8+:8];
            assign hi_n[h*8+:8]=ld_h[4+h]?hi_dq[h*8+:8]:st_h[4+h]?hi_rot[h*8+:8]:hi1h[h*8+:8];
        end
        always @(posedge clk or negedge rl)
            if(!rl)begin lo1h<=1;hi1h<=1;lo_a<=1;lo_b<=1;end
            else begin lo1h<=lo_n;hi1h<=hi_n;lo_a<=lo_n;lo_b<=lo_n;end
        reg inst_rd;
        always @*begin
            inst_rd=1'b0;
            for(integer h=0;h<32;h=h+1)begin
                reg sv; sv=1'b0;
                for(integer l=0;l<32;l=l+1)sv=sv|(((h<16)?lo_a[l]:lo_b[l])&inst[h*32+l]);
                inst_rd=inst_rd|(hi1h[h]&sv);
            end
        end
        // the FAN32 0 bitmap on this edge = inst updated with the pending write
        wire pend_hit=pend_addr==scan_row;
        assign row_installed=(MUT==1)?inst_rd:pend_we?(pend_open?(inst_rd||pend_hit):pend_hit):inst_rd;
    end endgenerate
endmodule
`default_nettype wire
