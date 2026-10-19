`timescale 1ns/1ps
`default_nettype none
// OPT-IN GQ16 source: owner-approved earlyfault for programmeaddr>=16/limit>16.
// Same public widths and two transport rungs; native replicas add zero edges.
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
module ot_hgi_coll_gq_target16 #(parameter [7:0] TARGET=8'd48,parameter integer PCW=8,parameter integer TGT_PIN=0,
                                  parameter integer CAP_CLK=0)(
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
    output wire [255:0] program_cfg_data,
    output reg program_start_v,
    output reg [PCW-1:0] program_start_base,
    output reg [PCW:0] program_start_limit,
    output reg [15:0] program_start_loops,
    output reg configured,fault,
    output wire [12:0] cfg_bank_we,
    output wire [103:0] cfg_bank_addr,
    output wire [3:0] start_bank_v
);
    localparam integer ROWS=16;
`ifdef OT_GQ_T16_MUT_LIMIT
    localparam integer MAX_DESC=32;
`else
    localparam integer MAX_DESC=16;
`endif
    initial if(PCW!=8)$fatal(1,"GQ local16 target requires canonical PCW8 public widths");
    // External reset reaches two synchronizer pins, not the entire valid bitmap.
    wire reset_live,reset_data,reset_launch;
    ot_gq_t16_reset2 u_reset_ctrl(.clk(clk),.rst_n(rst_n),.q(reset_live));
    ot_gq_t16_reset2 u_reset_data(.clk(clk),.rst_n(rst_n),.q(reset_data));
    ot_gq_t16_reset2 u_reset_launch(.clk(clk),.rst_n(rst_n),.q(reset_launch));
    reg cv,dv,lv;
    reg [7:0] target;
    wire clk_in=(CAP_CLK!=0)?clk_cap:clk;
    reg [7:0] tgt_q; always @(posedge clk_in) tgt_q<=tgt;
    wire [7:0] tid=(TGT_PIN!=0)?tgt_q:TARGET;
    reg [11:0] address,base;
`ifdef OT_GQ_T16_MUT_ADDR
    wire [11:0] capacity_address={8'd0,address[3:0]};
`else
    wire [11:0] capacity_address=address;
`endif
    reg [PCW-1:0] stored_base;
    reg [255:0] data_q;
    reg [12:0] limit;
    reg [PCW:0] stored_limit;
    reg [15:0] loops,stored_loops;
    reg [ROWS-1:0] installed;
    reg install_open,armed,scanning,validated,missing;
    reg [3:0] scan_row;
    reg [PCW:0] scan_limit;
    reg [1:0] commit;
    wire launch_ready=armed&&validated&&!scanning&&commit==0&&!program_active&&!fault;
    //46 private capture slots:14address/write slots (13RF+1bitmap),32payloadbytes.
    // Two retained prefix banks bound each scalar to23 local accept gates.
    wire [1:0] cv_copy,match_copy,header_copy,flags_copy;
    wire [13:0] slot_we; wire [55:0] slot_addr;
    generate for(genvar g=0;g<2;g=g+1)begin:g_prefix
        (* keep="true" *) ot_gq_t16_bitff u_cv(.clk(clk_in),.rst_n(reset_live),.d(cfg_v),.q(cv_copy[g]));
        (* keep="true" *) ot_gq_t16_match u_match(.a(target),.b(tid),.q(match_copy[g]));
        (* keep="true" *) ot_gq_t16_header u_header(.data(data_q),.address(address),.q(header_copy[g]));
        (* keep="true" *) ot_gq_t16_flags u_flags(.active(program_active),.scanning(scanning),.lv(lv),.address(address),.q(flags_copy[g]));
    end endgenerate
    generate for(genvar g=0;g<14;g=g+1)begin:g_cfg_addr
        ot_gq_t16_cfg_slot u_slot(.clk(clk),.rst_n(reset_data),.cv(cv_copy[0]),.match_ok(match_copy[0]),
             .header_ok(header_copy[0]),.flags_ok(flags_copy[0]),
`ifdef OT_GQ_T16_MUT_COPY
            .address((g==0)?(address[3:0]+4'd1):address[3:0]),
`else
            .address(address[3:0]),
`endif
            .we(slot_we[g]),.addr(slot_addr[4*g+:4]));
        if(g<13)begin:g_rf
            assign cfg_bank_we[g]=slot_we[g];
            assign cfg_bank_addr[8*g+:8]={4'b0,slot_addr[4*g+:4]};
        end
    end endgenerate
    generate for(genvar g=0;g<32;g=g+1)begin:g_cfg_byte
        localparam integer P=(g<9)?0:1;
        ot_gq_t16_cfg_byte u_byte(.clk(clk),.cv(cv_copy[P]),.match_ok(match_copy[P]),
            .header_ok(header_copy[P]),.flags_ok(flags_copy[P]),.data(data_q[8*g+:8]),.q(program_cfg_data[8*g+:8]));
    end endgenerate
    wire launch_emit=lv&&armed&&launch_ready&&!cv&&!dv;
    generate for(genvar g=0;g<4;g=g+1)begin:g_launch_copy
        ot_gq_t16_bitff u_v(.clk(clk),.rst_n(reset_launch),.d(launch_emit),.q(start_bank_v[g]));
    end endgenerate
    // Same observed write and generation semantics as the public target pins.
    always @(posedge clk or negedge reset_data)
        if(!reset_data)installed<=0;
        else if(slot_we[13])begin
            if(!install_open)installed<=(16'd1<<slot_addr[52+:4]);
            else installed[slot_addr[52+:4]]<=1'b1;
        end
    always @(posedge clk_in)begin
        target<=cfg_target;address<=cfg_addr;data_q<=cfg_data;
        base<=desc_base;limit<=desc_limit;loops<=desc_loops;
    end
    always @(posedge clk_in or negedge reset_live)
        if(!reset_live)begin cv<=0;dv<=0;lv<=0;end
        else begin cv<=cfg_v;dv<=desc_v;lv<=launch_v;end
    always @(posedge clk or negedge reset_live)
        if(!reset_live)begin
            program_cfg_we<=0;program_start_v<=0;configured<=0;fault<=0;
            install_open<=0;armed<=0;scanning<=0;validated<=0;missing<=0;
            scan_row<=0;scan_limit<=0;commit<=0;
        end else begin
            program_cfg_we<=0;program_start_v<=0;
            configured<=launch_ready&&!lv&&!((cv||dv)&&target==tid);
            // Observe the real registered programme-write pins. The neighbour's
            // capture and SRAM write consume two further edges; commit masks both.
            commit<={commit[0],program_cfg_we};
            if(program_cfg_we)install_open<=1;
            if(cv && target==tid)begin
                armed<=0;validated<=0;configured<=0;
                if(program_active || scanning || lv || {1'b0,capacity_address}>=13'd16 ||
                   data_q[255:240]!=16'hc7a1 || data_q[239:224]!={4'b0,address})fault<=1;
                else begin program_cfg_we<=1;program_cfg_addr<=address[PCW-1:0];end
            end
            if(dv && target==tid)begin
                armed<=0;validated<=0;configured<=0;install_open<=0;
                if(program_active || scanning || lv || cv || loops==0 || limit<={1'b0,base} || limit>MAX_DESC)fault<=1;
                else begin
                    stored_base<=base[PCW-1:0];stored_limit<=limit[PCW:0];stored_loops<=loops;
                    armed<=1;missing<=0;
                    if(validated && base==stored_base && limit==stored_limit)begin
                        // Same range in the unchanged resident generation: reuse
                        // the completed row proof, not a stale descriptor arm.
                        validated<=1;scanning<=0;
                    end else begin
                        scanning<=1;scan_row<=base[3:0];scan_limit<=limit[PCW:0];
                    end
                end
            end
            if(scanning)begin
                if(!installed[scan_row])missing<=1;
                if({1'b0,scan_row}+1'b1==scan_limit)begin
                    scanning<=0;
                    if(missing || !installed[scan_row])fault<=1;
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
endmodule
// Retained native leaves: mapped census is binding; wire attributes alone do not qualify.
(* keep_hierarchy="yes" *)
module ot_gq_t16_reset2(input wire clk,rst_n,output wire q);
    (* keep="true",async_reg="true" *) reg m,l;
    always @(posedge clk or negedge rst_n)if(!rst_n)begin m<=0;l<=0;end else begin m<=1;l<=m;end
    assign q=l;
endmodule
(* keep_hierarchy="yes" *)
module ot_gq_t16_bitff(input wire clk,rst_n,d,output wire q);
    (* keep="true" *)reg r;
    always @(posedge clk or negedge rst_n)if(!rst_n)r<=0;else r<=d;
    assign q=r;
endmodule
(* keep_hierarchy="yes" *)
module ot_gq_t16_match(input wire[7:0]a,b,output wire q);assign q=a==b;endmodule
(* keep_hierarchy="yes" *)
module ot_gq_t16_header(input wire[255:0]data,input wire[11:0]address,output wire q);
    assign q=data[255:240]==16'hc7a1 && data[239:224]=={4'b0,address};
endmodule
(* keep_hierarchy="yes" *)
module ot_gq_t16_flags(input wire active,scanning,lv,input wire[11:0]address,output wire q);
`ifdef OT_GQ_T16_MUT_ADDR
    wire[11:0]capacity_address={8'd0,address[3:0]};
`else
    wire[11:0]capacity_address=address;
`endif
    assign q=!active&&!scanning&&!lv&&capacity_address<12'd16;
endmodule
(* keep_hierarchy="yes" *)
module ot_gq_t16_accept(input wire cv,match_ok,header_ok,flags_ok,output wire q);
    assign q=cv&&match_ok&&header_ok&&flags_ok;
endmodule
(* keep_hierarchy="yes" *)
module ot_gq_t16_cfg_slot(input wire clk,rst_n,cv,match_ok,header_ok,flags_ok,input wire[3:0]address,output wire we,output wire[3:0]addr);
    wire accept;
    (* keep="true" *)ot_gq_t16_accept u_accept(.cv(cv),.match_ok(match_ok),.header_ok(header_ok),.flags_ok(flags_ok),.q(accept));
    (* keep="true" *)reg wr;(* keep="true" *)reg[3:0]a;
    always @(posedge clk or negedge rst_n)if(!rst_n)wr<=0;else wr<=accept;
    always @(posedge clk)if(accept)a<=address;
    assign we=wr;assign addr=a;
endmodule
(* keep_hierarchy="yes" *)
module ot_gq_t16_cfg_byte(input wire clk,cv,match_ok,header_ok,flags_ok,input wire[7:0]data,output wire[7:0]q);
    wire accept;
    (* keep="true" *)ot_gq_t16_accept u_accept(.cv(cv),.match_ok(match_ok),.header_ok(header_ok),.flags_ok(flags_ok),.q(accept));
    (* keep="true" *)reg[7:0]r;always @(posedge clk)if(accept)r<=data;assign q=r;
endmodule
`default_nettype wire
