`timescale 1ns/1ps
`default_nettype none
// F20 programme target, COLL gather-issue copy (HNX-UNITS/GQ s4 2026-10-20, kits hnx_gq_issue_s4_1020 / s4b) of the hc_<q>
// copy ot_hnx_prog_target (claude/hnx-hub-safe2-1020 b72f6e65f: bitmap as kept per-row copies, no bitmap reset, 2-stage
// registered scan = +2 INITIALIZATION edges only).  s3 census of ot_static_program_target in the issue leaf: reset_live 293,
// scan_row 136..261, install_open 159, the p_we && p_wa < 16 row-file write decode 1,351 / row enables 134..148, p_sv 88.
// GQ additions (same F20 protocol, faults and outputs; zero schedule edges):
//  * reset_ctrl_copies: 8 KEPT identical synchronizer copies (the kit's OT_RST_COPIES_RE matches u_target.reset_ctrl_copies,
//    ot_rst_copies.py spreads the reset loads over them, <= 32 each); configuration registers without a reset value
//    (program_cfg_addr, stored_*, program_start_*) are in a reset-free block (their load conditions are 0 in reset).
//  * program_row_we[NRW*NWC]: KEPT per-row write strobes, NWC copies per row r < NRW, registered from the SAME next-state as
//    program_cfg_we (we_n) and program_cfg_addr (address), so the caller's row file writes on the same edge as before with
//    <= 28 enables per strobe.  we_n is formed by 4 kept-hierarchy instances (ot_hnx_gq_tgt_wen) so no copy of it drives
//    more than ~30 strobe inputs.
//  * program_start_vc[NSV]: KEPT copies of program_start_v (same next-state).
module ot_hnx_gq_prog_target #(parameter integer PCW=8, parameter integer NRW=16, parameter integer NWC=5,
                              parameter integer NSV=9)(
    input wire clk,rst_n,
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
    output reg configured,fault,
    output wire [NRW*NWC-1:0] program_row_we,
    output wire [NSV-1:0] program_start_vc
);
    localparam integer ROWS=1<<PCW, NR=ROWS/32, RB=PCW-5;
    initial if(PCW<8 || PCW>12)$fatal(1,"programme target PCW must be8..12");
    (* async_reg = "true" *) reg reset_meta;
    (* keep = "true" *) reg [7:0] reset_ctrl_copies;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin reset_meta<=0;reset_ctrl_copies<=8'd0;end
        else begin reset_meta<=1;reset_ctrl_copies<={8{reset_meta}};end
    wire reset_live=reset_ctrl_copies[0];
    reg cv,dv,lv;
    reg [7:0] target;
    reg [7:0] tgt_q; always @(posedge clk) tgt_q<=tgt;
    wire [7:0] tid=tgt_q;
    reg [11:0] address,base;
    reg [PCW-1:0] stored_base;
    reg [255:0] data_q;
    reg [12:0] limit;
    reg [PCW:0] stored_limit;
    reg [15:0] loops,stored_loops;
    reg install_open,armed,scanning,validated,missing,img_v;
    reg sissue;                       // scan rows still being issued
    reg [PCW-1:0] scan_row;
    reg [PCW:0] scan_limit;
    reg [1:0] commit;
    wire launch_ready=armed&&validated&&!scanning&&commit==0&&!program_active&&!fault;
    always @(posedge clk)begin
        target<=cfg_target;address<=cfg_addr;data_q<=cfg_data;
        base<=desc_base;limit<=desc_limit;loops<=desc_loops;
        program_cfg_data<=data_q;
    end
    always @(posedge clk or negedge reset_live)
        if(!reset_live)begin cv<=0;dv<=0;lv<=0;end
        else begin cv<=cfg_v;dv<=desc_v;lv<=launch_v;end
    // ---- next-state of the write strobe and of install_open (exactly the assignments of the control block below)
    wire cfg_hit=cv && target==tid;
    wire dsc_hit=dv && target==tid;
    wire dsc_bad=program_active || scanning || lv || cv || loops==0 || limit<={1'b0,base} || limit>(13'd1<<PCW);
    wire cfg_bad=program_active || scanning || lv || {1'b0,address}>=(13'd1<<PCW) ||
                 data_q[255:240]!=16'hc7a1 || data_q[239:224]!={4'b0,address};
    wire we_n=cfg_hit && !cfg_bad;
    // kept-hierarchy copies of we_n: 0 = program_cfg_we + bitmap strobes, 1..3 = row strobes
    wire [3:0] wen_k;
    for(genvar k=0;k<4;k=k+1)begin:g_wen
        ot_hnx_gq_tgt_wen #(.PCW(PCW)) u_w(.cv(cv),.target(target),.tid(tid),.program_active(program_active),
            .scanning(scanning),.lv(lv),.address(address),.hdr(data_q[255:224]),.we(wen_k[k]));
    end
    initial if(NRW>16 || NRW*NWC>160)$fatal(1,"ot_hnx_gq_prog_target: NRW <= 16, <= 160 strobes");
    (* keep = "true" *) reg [NRW*NWC-1:0] row_we_c;
    for(genvar r=0;r<NRW;r=r+1)begin:g_rw
        wire wk=(r<6)?wen_k[1]:(r<11)?wen_k[2]:wen_k[3];
        for(genvar c=0;c<NWC;c=c+1)begin:g_c
            always @(posedge clk or negedge reset_live)
                if(!reset_live)row_we_c[r*NWC+c]<=1'b0;
                else row_we_c[r*NWC+c]<=wk && address[PCW-1:0]==PCW'(r);
        end
    end
    assign program_row_we=row_we_c;
    // program_start_v next-state and its kept copies
    wire sv_n=lv && armed && launch_ready && !cv && !dv;
    // s4 census r1: the launch / descriptor load enables of the reset-free config registers (33 bits each) drove 41 / 50
    // loads -> 4 kept-hierarchy instances each (<= 9 bits, ~2 loads per enabled bit)
    wire [3:0] sv_k,dk_k;
    for(genvar k=0;k<4;k=k+1)begin:g_svk
        ot_hnx_gq_tgt_and2 u_s(.a(lv && armed),.b(launch_ready && !cv && !dv),.y(sv_k[k]));
        ot_hnx_gq_tgt_and2 u_d(.a(dsc_hit),.b(!dsc_bad),.y(dk_k[k]));
    end
    (* keep = "true" *) reg [NSV-1:0] sv_c;
    always @(posedge clk or negedge reset_live) if(!reset_live)sv_c<='0; else sv_c<={NSV{sv_n}};
    assign program_start_vc=sv_c;
    wire io_n=dsc_hit ? 1'b0 : (program_cfg_we ? 1'b1 : install_open);
    // scan pointer next-state
    wire scan_start=dsc_hit && !dsc_bad && !(validated && base==stored_base && limit==stored_limit);
    wire scan_last={1'b0,scan_row}+1'b1==scan_limit;
    wire [PCW-1:0] srow_n=scan_start ? base[PCW-1:0] : ((sissue && !scan_last) ? scan_row+1'b1 : scan_row);
    // ---- bitmap (no reset) with kept per-row copies
    reg [31:0] colbit_a;              // stage A: row r's bit at the scan column
    for(genvar r=0;r<NR;r=r+1)begin:g_r
        (* keep = "true", dont_touch = "true" *) reg we_c,clr_c,row_c;
        (* keep = "true", dont_touch = "true" *) reg [31:0] col_c;
        (* keep = "true", dont_touch = "true" *) reg [4:0] scol_c;
        reg [31:0] inst;
        always @(posedge clk)begin
            we_c<=wen_k[0]; clr_c<=!io_n; row_c<=address[PCW-1:5]==RB'(r);   // each <= 32 loads (used under we_c)
            col_c<=32'd1<<address[4:0];
            scol_c<=srow_n[4:0];
            if(we_c)inst<=(clr_c?32'd0:inst)|({32{row_c}}&col_c);
        end
        if(r<32)begin:g_a
            always @(posedge clk)colbit_a[r]<=inst[scol_c];
        end
    end
    // stage B: the row group's bit (NR <= 32 rows of 32 for PCW <= 10)
    reg sv_a,sl_a,img_a,sv_b,sl_b,bit_b;
    reg [RB-1:0] srow_a;
    always @(posedge clk)begin
        srow_a<=scan_row[PCW-1:5];img_a<=img_v;
        bit_b<=img_a && colbit_a[srow_a];
    end
    initial if(PCW>10)$fatal(1,"ot_hnx_gq_prog_target: PCW <= 10");
    // configuration registers without a reset value (load conditions are 0 while cv / dv / lv are in reset)
    always @(posedge clk)begin
        if(wen_k[0])program_cfg_addr<=address[PCW-1:0];
        if(dk_k[0])stored_base<=base[PCW-1:0];
        if(dk_k[1])stored_limit<=limit[PCW:0];
        if(dk_k[2])stored_loops[7:0]<=loops[7:0];
        if(dk_k[3])stored_loops[15:8]<=loops[15:8];
        if(sv_k[0])program_start_base<=stored_base;
        if(sv_k[1])program_start_limit<=stored_limit;
        if(sv_k[2])program_start_loops[7:0]<=stored_loops[7:0];
        if(sv_k[3])program_start_loops[15:8]<=stored_loops[15:8];
    end
    always @(posedge clk or negedge reset_live)
        if(!reset_live)begin
            program_cfg_we<=0;program_start_v<=0;configured<=0;fault<=0;
            install_open<=0;armed<=0;scanning<=0;validated<=0;missing<=0;img_v<=0;sissue<=0;
            scan_row<=0;scan_limit<=0;commit<=0;sv_a<=0;sl_a<=0;sv_b<=0;sl_b<=0;
        end else begin
            program_cfg_we<=0;program_start_v<=0;
            configured<=launch_ready&&!lv&&!((cv||dv)&&target==tid);
            commit<={commit[0],program_cfg_we};
            if(program_cfg_we)begin install_open<=1;img_v<=1;end
            if(cfg_hit)begin
                armed<=0;validated<=0;configured<=0;
                if(cfg_bad)fault<=1;
                else program_cfg_we<=1;
            end
            if(dsc_hit)begin
                armed<=0;validated<=0;configured<=0;install_open<=0;
                if(dsc_bad)fault<=1;
                else begin
                    armed<=1;missing<=0;
                    if(validated && base==stored_base && limit==stored_limit)begin
                        validated<=1;scanning<=0;
                    end else begin
                        scanning<=1;sissue<=1;scan_row<=base[PCW-1:0];scan_limit<=limit[PCW:0];
                    end
                end
            end
            // scan pipeline: issue (sissue) -> stage A (sv_a) -> stage B (sv_b: bit_b valid)
            sv_a<=sissue;sl_a<=sissue && scan_last;
            sv_b<=sv_a;sl_b<=sv_a && sl_a;
            if(sv_b)begin
                if(!bit_b)missing<=1;
                if(sl_b)begin
                    scanning<=0;
                    if(missing || !bit_b)fault<=1;
                    else validated<=1;
                end
            end
            if(sissue)begin
                if(scan_last)sissue<=0;
                else scan_row<=scan_row+1'b1;
            end
            if(lv && armed)begin
                armed<=0;configured<=0;
                if(!launch_ready || cv || dv)fault<=1;
                else program_start_v<=1;
            end
        end
endmodule

// a AND b in its own kept hierarchy (one instance per enable group: ABC cannot share the gate)
(* keep_hierarchy = "yes" *)
module ot_hnx_gq_tgt_and2(input wire a,b,output wire y);
    assign y=a&&b;
endmodule

// we_n of the target (cfg_hit && !cfg_bad), one kept-hierarchy instance per strobe group (Yosys / ABC cannot share it)
(* keep_hierarchy = "yes" *)
module ot_hnx_gq_tgt_wen #(parameter integer PCW=8)(
    input wire cv, input wire [7:0] target, tid, input wire program_active, scanning, lv,
    input wire [11:0] address, input wire [31:0] hdr, output wire we);
    assign we=cv && target==tid && !(program_active || scanning || lv || {1'b0,address}>=(13'd1<<PCW) ||
              hdr[31:16]!=16'hc7a1 || hdr[15:0]!={4'b0,address});
endmodule
`default_nettype wire
