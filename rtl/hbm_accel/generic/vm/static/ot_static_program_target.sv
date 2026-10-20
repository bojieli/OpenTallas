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
    wire rl;
    generate if(RLC>1)begin:g_rlc
        (* keep = "true", dont_touch = "true" *) reg [RLC-1:0] rl__ot_rlv;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)rl__ot_rlv<={RLC{1'b0}};
            else rl__ot_rlv<={RLC{reset_meta}};
        assign rl=rl__ot_rlv[0];
    end else begin:g_rl1
        assign rl=reset_live;
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
            scan_row<=0;scan_limit<=0;commit<=0;
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
                else begin program_cfg_we<=1;program_cfg_addr<=address[PCW-1:0];program_cfg_data<=data_q;end
            end
            if(dv && target==tid)begin
                armed<=0;validated<=0;configured<=0;install_open<=0;
                if(program_active || scanning || lv || cv || loops==0 || limit<={1'b0,base} || limit>(13'd1<<PCW))fault<=1;
                else begin
                    stored_base<=base[PCW-1:0];stored_limit<=limit[PCW:0];stored_loops<=loops;
                    armed<=1;missing<=0;
                    if(validated && base==stored_base && limit==stored_limit)begin
                        // Same range in the unchanged resident generation: reuse
                        // the completed row proof, not a stale descriptor arm.
                        validated<=1;scanning<=0;
                    end else begin
                        scanning<=1;scan_row<=base[PCW-1:0];scan_limit<=limit[PCW:0];
                    end
                end
            end
            if(scanning)begin
                if(!row_installed)missing<=1;
                if({1'b0,scan_row}+1'b1==scan_limit)begin
                    scanning<=0;
                    if(missing || !row_installed)fault<=1;
                    else validated<=1;
                end else scan_row<=scan_row+1'b1;
            end
            if(lv && armed)begin
                armed<=0;configured<=0;
                if(!launch_ready || cv || dv)fault<=1;
                else begin
                    program_start_v<=1;program_start_base<=stored_base;
                    program_start_limit<=stored_limit;program_start_loops<=stored_loops;
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
        always @(posedge clk)
            if(cv && target==tid)begin addr_a[0]<=address[PCW-1:0];addr_a[1]<=address[PCW-1:0];addr_a[2]<=address[PCW-1:0];end
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
        always @(posedge clk or negedge rl)
            if(!rl)inst<=0;
            else for(integer k=0;k<32;k=k+1)
                for(integer r=0;r<32;r=r+1)
                    inst[k*32+r]<=(inst[k*32+r]&&!clr_s[k])||(set_s[k]&&lo_s[k]==5'(r));
        // scan-row read copies: 16 x 6-bit low copies (64-row read slices) + the 4-bit slice select
        (* keep = "true", dont_touch = "true" *) reg [5:0] sl_c [0:15];
        reg [3:0] sh_c;
        wire scan_load=dv && target==tid && !(program_active || scanning || lv || cv || loops==0 || limit<={1'b0,base} ||
                       limit>(13'd1<<PCW)) && !(validated && base==stored_base && limit==stored_limit);
        wire scan_step=scanning && !({1'b0,scan_row}+1'b1==scan_limit);
        wire [PCW-1:0] scan_nxt=scan_load?base[PCW-1:0]:scan_step?scan_row+1'b1:scan_row;
        always @(posedge clk or negedge rl)
            if(!rl)begin for(integer k=0;k<16;k=k+1)sl_c[k]<=0;sh_c<=0;end
            else begin for(integer k=0;k<16;k=k+1)sl_c[k]<=scan_nxt[5:0];sh_c<=scan_nxt[9:6];end
        wire [15:0] slice_rd;
        for(genvar k=0;k<16;k=k+1)begin:g_rd
            assign slice_rd[k]=inst[k*64+sl_c[k]];
        end
        wire inst_rd=slice_rd[sh_c];
        // the FAN32 0 bitmap on this edge = inst updated with the pending write
        wire pend_hit=pend_addr==scan_row;
        assign row_installed=(MUT==1)?inst_rd:pend_we?(pend_open?(inst_rd||pend_hit):pend_hit):inst_rd;
    end endgenerate
endmodule
`default_nettype wire
