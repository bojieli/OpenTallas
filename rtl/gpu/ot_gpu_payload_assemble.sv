`timescale 1ns/1ps
// Opt-in load-time swizzled transport for V4.1 SMs. Each record is exactly
// 128 weight bytes followed by 8 UE8M0 bytes, in golden SM issue order.
// HBM lines contain consecutive records; only the last line is padded.
// Four independently handshaken 32-B sectors may land out of order within
// WINDOW slots. Epoch/index checks reject stale, duplicate and illegal sectors.
// Five sector reads form each 136-B record at one of four 8-B phases. The
// record retires only against its accepted, in-order SM request tag.
// Not adopted: ENABLE defaults to zero pending exact/measured/in-context SSFF.
module ot_gpu_payload_assemble #(
    parameter integer ENABLE=0, WINDOW=16, TAG_DEPTH=16, TAGW=10
)(
    input wire clk, rst_n,
    input wire cfg_valid, output wire cfg_ready,
    input wire [23:0] cfg_payloads, input wire [31:0] cfg_req_base,
    input wire [15:0] cfg_epoch,
    input wire [3:0] sector_valid, output wire [3:0] sector_ready,
    input wire [4*24-1:0] sector_index, input wire [4*16-1:0] sector_epoch,
    input wire [1023:0] sector_data,
    input wire req_valid, output wire req_ready,
    input wire [31:0] req_addr, input wire [TAGW-1:0] req_tag,
    output wire rsp_valid, input wire rsp_ready,
    output wire [TAGW-1:0] rsp_tag, output wire [1087:0] rsp_data,
    output wire idle, output wire fault
);
    generate if (!ENABLE) begin : g_off
        assign cfg_ready=0; assign sector_ready=0; assign req_ready=0;
        assign rsp_valid=0; assign rsp_tag=0; assign rsp_data=0;
        assign idle=1; assign fault=0;
    end else begin : g_on
        localparam integer QW=$clog2(TAG_DEPTH);
        reg active, error;
        reg [23:0] payloads, sectors, received, requested, delivered, head;
        reg [31:0] base;
        reg [15:0] epoch;
        reg [1:0] phase;
        reg [WINDOW-1:0] present;
        reg [255:0] words [0:WINDOW-1];
        reg [TAGW-1:0] tags [0:TAG_DEPTH-1];
        reg [TAG_DEPTH-1:0] live;
        reg [QW-1:0] wp, rp;
        reg [QW:0] qcount;
        reg [3:0] ready;
        reg invalid_sector, duplicate_tag, complete;
        reg [1279:0] gathered;
        integer i,j,idx,delta,slot,advance,landings;
        always @* begin
            ready=0; invalid_sector=0;
            for (i=0;i<4;i=i+1) begin
                idx=sector_index[i*24 +:24];
                delta=idx-head; slot=idx % WINDOW;
                if (active && !error) begin
                    if (sector_epoch[i*16 +:16] == epoch && idx >= head && idx < sectors && delta < WINDOW && !present[slot])
                        ready[i]=1;
                    if (sector_valid[i]) begin
                        if (sector_epoch[i*16 +:16] != epoch || idx < head || idx >= sectors || (delta < WINDOW && present[slot]))
                            invalid_sector=1;
                        // A future sector beyond the finite window is ordinary
                        // backpressure; the sender must hold it until admitted.
                        for (j=0;j<i;j=j+1)
                            if (sector_valid[j] && sector_index[j*24 +:24] == sector_index[i*24 +:24]) invalid_sector=1;
                    end
                end
            end
            duplicate_tag=0;
            for (i=0;i<TAG_DEPTH;i=i+1) if (live[i] && tags[i]==req_tag) duplicate_tag=1;
            complete=1; gathered=0;
            for (i=0;i<5;i=i+1) begin
                if (!present[(head+i)%WINDOW]) complete=0;
                gathered[i*256 +:256]=words[(head+i)%WINDOW];
            end
        end
        assign cfg_ready=!active && !error;
        assign sector_ready=ready & {4{!invalid_sector}};
        assign req_ready=active && !error && requested<payloads && qcount<TAG_DEPTH
            && req_addr==base+requested && !duplicate_tag;
        assign rsp_valid=active && !error && complete && qcount!=0 && delivered<payloads;
        assign rsp_tag=tags[rp];
        assign rsp_data=gathered >> (phase*64);
        assign fault=error;
        assign idle=!active;
        wire push=req_valid && req_ready;
        wire pop=rsp_valid && rsp_ready;
        wire [3:0] land=sector_valid & sector_ready;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                active<=0; error<=0; payloads<=0; sectors<=0; received<=0;
                requested<=0; delivered<=0; head<=0; base<=0; epoch<=0; phase<=0;
                present<=0; live<=0; wp<=0; rp<=0; qcount<=0;
            end else if (cfg_valid && cfg_ready) begin
                if (cfg_payloads==0) error<=1;
                else begin
                    active<=1; payloads<=cfg_payloads;
                    sectors<=((cfg_payloads*136+127)/128)*4;
                    received<=0; requested<=0; delivered<=0; head<=0; phase<=0;
                    base<=cfg_req_base; epoch<=cfg_epoch; present<=0;
                    live<=0; wp<=0; rp<=0; qcount<=0;
                end
            end else if (active && !error) begin
                if (invalid_sector || (req_valid && requested<payloads &&
                    (req_addr!=base+requested || duplicate_tag))) error<=1;
                else begin
                    landings=0;
                    for (i=0;i<4;i=i+1) if (land[i]) begin
                        words[sector_index[i*24 +:24]%WINDOW]<=sector_data[i*256 +:256];
                        present[sector_index[i*24 +:24]%WINDOW]<=1;
                        landings=landings+1;
                    end
                    received<=received+landings;
                    if (push) begin
                        tags[wp]<=req_tag; live[wp]<=1; wp<=wp+1'b1; requested<=requested+1;
                    end
                    qcount<=qcount+(push ? 1:0)-(pop ? 1:0);
                    if (pop) begin
                        live[rp]<=0; rp<=rp+1'b1; delivered<=delivered+1;
                        advance=(phase==3) ? 5:4;
                        for (i=0;i<5;i=i+1) if (i<advance) present[(head+i)%WINDOW]<=0;
                        head<=head+advance; phase<=phase+1'b1;
                    end
                    if (received+landings==sectors && delivered+(pop ? 1:0)==payloads &&
                        requested+(push ? 1:0)==payloads && qcount+(push ? 1:0)-(pop ? 1:0)==0) begin
                        active<=0; present<=0;
                    end
                end
            end
        end
    end endgenerate
endmodule

// Bridge the existing fetch's ordered 128-B line port to four independent
// sector handshakes. Partial acceptance is remembered while the fetch holds
// the line. Metadata is local to a drained descriptor, not a new NoC fabric.
module ot_gpu_payload_line_bridge(
    input wire clk,rst_n,start,
    input wire [15:0] epoch,
    input wire line_valid, output wire line_ready, input wire [1023:0] line_data,
    output wire [3:0] sector_valid, input wire [3:0] sector_ready,
    output wire [95:0] sector_index, output wire [63:0] sector_epoch,
    output wire [1023:0] sector_data
);
    reg [3:0] accepted;
    reg [23:0] ordinal;
    assign sector_valid={4{line_valid}} & ~accepted;
    assign line_ready=&(accepted|sector_ready);
    assign sector_data=line_data;
    genvar g;
    generate for (g=0;g<4;g=g+1) begin : g_meta
        assign sector_index[g*24 +:24]=ordinal*4+g;
        assign sector_epoch[g*16 +:16]=epoch;
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin accepted<=0; ordinal<=0; end
        else if (start) begin accepted<=0; ordinal<=0; end
        else if (line_valid) begin
            if (line_ready) begin accepted<=0; ordinal<=ordinal+1; end
            else accepted<=accepted | sector_ready;
        end
endmodule
