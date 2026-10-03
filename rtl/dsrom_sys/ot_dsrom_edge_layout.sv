`timescale 1ns/1ps
// Frozen contiguous layout shared by index writers, compressed-KV writers and
// the edge scan. N is an INSTALLED image extent, not a changing scan counter.
// A new extent must be installed (including relocated old rows) before use.
// Boundaries preserve candidate blocks of eight; shipped N/4 is unchanged.
module ot_dsrom_edge_layout #(parameter integer IW=20) (
    input wire [IW:0] n,
    input wire [IW-1:0] position,
    output wire [4*(IW+1)-1:0] bases,
    output wire [4*(IW+1)-1:0] counts,
    output reg [1:0] stack,
    output reg [IW-1:0] local_row,
    output wire valid
);
    wire [IW+3:0] groups = ({3'b0,n} + 7) >> 3;
    wire [IW+3:0] boundary [0:4];
    genvar s;
    generate for(s=0;s<=4;s=s+1) begin : g_b
        wire [IW+3:0] raw = ((groups * s) >> 2) << 3;
        assign boundary[s] = raw > n ? n : raw;
        if(s<4) begin : g_out
            assign bases[(IW+1)*s +: IW+1] = boundary[s][IW:0];
            assign counts[(IW+1)*s +: IW+1] = boundary[s+1]-boundary[s];
        end
    end endgenerate
    integer k;
    always @* begin
        stack=0; local_row=0;
        for(k=0;k<4;k=k+1)
            if(position>=boundary[k] && position<boundary[k+1]) begin
                stack=k[1:0]; local_row=position-boundary[k];
            end
    end
    assign valid={1'b0,position}<n;
endmodule

// Payload encoding stays in the pinned writer; only its physical coordinates
// change. RING=1 emits global row and region base, which this adapter maps to
// the same native code/scales sectors as the reader. No legacy file changed.
module ot_dsrom_edge_kwr #(
    parameter integer AW=24,NW=16,NL=8,HAW=28,RING_UBLK=17
) (
    input wire clk,rst_n,
    input wire [AW-1:0] cfg_ik_base,
    input wire [HAW-1:0] i_user_base_sec,
    input wire [AW:0] layout_n,
    input wire layout_installed,
    input wire su_go,
    input wire [1:0] i_dst,
    input wire [AW-1:0] i_obase,i_orow,
    input wire [NW-1:0] i_nout,i_kdim,
    input wire [NL-1:0] kv_we,
    input wire [NL*AW-1:0] kv_waddr,
    input wire [NL*32-1:0] kv_wdata,
    output wire w_v,
    input wire w_rdy,
    output wire [3:0] w_stack_mask,
    output wire [HAW-1:0] w_csec,w_ssec,
    output wire [511:0] w_codes,
    output wire [2:0] w_sslot,
    output wire [31:0] w_scales,
    output wire fault,
    output wire [31:0] dbg_keys
);
    reg [AW:0] n_q;
    reg installed_q, pending;
    reg descriptor_fault, record_bad;
    wire hit=su_go && i_dst==3 && (i_obase>>4)>=cfg_ik_base;
    wire accept=hit && !pending;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin n_q<=0; installed_q<=0; pending<=0; descriptor_fault<=0; record_bad<=0; end
        else begin
            descriptor_fault<=hit && pending;
            if(inner_fault) begin record_bad<=1; if(!v) pending<=0; end
            if(v && (w_rdy || !w_v)) pending<=0;
            if(accept) begin n_q<=layout_n; installed_q<=layout_installed; pending<=1; record_bad<=0; end
        end
    end
    wire v,inner_fault,map_valid;
    wire [HAW-1:0] row,region;
    wire [AW-1:0] local_row;
    wire [1:0] stack;
    ot_hdc_v41x_idx_pool_kwr #(.AW(AW),.NW(NW),.NL(NL),.HAW(HAW),.RING(1),.RING_UBLK(RING_UBLK)) u_encode (
        .clk(clk),.rst_n(rst_n),.cfg_ik_base(cfg_ik_base),.i_user_base_sec(i_user_base_sec),
        .su_go(accept),.i_dst(i_dst),.i_obase(i_obase),.i_orow(i_orow),.i_nout(i_nout),.i_kdim(i_kdim),
        .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.w_v(v),.w_rdy(w_rdy || !w_v),
        .w_stack_mask(),.w_csec(row),.w_codes(w_codes),.w_ssec(region),.w_sslot(),.w_scales(w_scales),
        .fault(inner_fault),.dbg_keys(dbg_keys));
    ot_dsrom_edge_layout #(.IW(AW)) u_map (.n(n_q),.position(row[AW-1:0]),.bases(),.counts(),
        .stack(stack),.local_row(local_row),.valid(map_valid));
    wire [HAW:0] code_sec = {1'b0,region} + ((local_row >> 10)*17 + 1 + ((local_row & 1023) >> 6))*128 + 2*(local_row & 63);
    wire [HAW:0] scale_sec = {1'b0,region} + (local_row >> 10)*17*128 + ((local_row & 1023) >> 3);
    wire region_valid = ((local_row >> 10)*17 + 17 <= RING_UBLK) && (row < (1<<AW));
    assign w_v=v && !record_bad && !inner_fault && installed_q && map_valid && region_valid && !code_sec[HAW] && !scale_sec[HAW];
    assign w_stack_mask=4'b1<<stack;
    assign w_csec=code_sec[HAW-1:0];
    assign w_ssec=scale_sec[HAW-1:0];
    assign w_sslot=local_row[2:0];
    assign fault=descriptor_fault || inner_fault || (v && record_bad) || (v && (!installed_q || !map_valid || !region_valid || code_sec[HAW] || scale_sec[HAW]));
endmodule
