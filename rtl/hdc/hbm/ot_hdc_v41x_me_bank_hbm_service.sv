`timescale 1ns/1ps
// HBM source for the adopted V4.1 ME bank boundary. Chain position c reads
// one 256-bit sector containing MG=8 FP32 bank words q=8*u+c (u=0..7).
// Each chain has its own bounded tagged ring because the ME skews addresses
// by three cycles per chain. Descriptor bank_sector_base[c] selects a separate
// HBM region. The caller issues its fixed-latency ME op only after ready;
// an underflow during the op fails closed. Memory read latency is two cycles.
module ot_hdc_v41x_me_bank_hbm_service #(
    parameter integer AW=18,
    parameter integer HAW=28,
    parameter integer MG=8,
    parameter integer WINDOW=64,
    parameter integer LEAD=32,
    parameter integer LGW=$clog2(WINDOW)
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  start,
    input  wire                  release_window,
    input  wire [AW-1:0]         rom_base,
    input  wire [AW:0]           nwords,
    input  wire [8*HAW-1:0]      bank_sector_base,
    output reg                   ready,
    output reg                   fault,
    output reg  [3:0]            fault_why,
    output wire [7:0]            hq_v,
    input  wire [7:0]            hq_rdy,
    output wire [8*HAW-1:0]      hq_addr,
    output wire [8*AW-1:0]       hq_tag,
    input  wire [7:0]            hr_v,
    output wire [7:0]            hr_rdy,
    input  wire [8*AW-1:0]       hr_tag,
    input  wire [8*256-1:0]      hr_data,
    input  wire [7:0]            mb_re,
    input  wire [8*AW-1:0]       mb_addr,
    output wire [8*MG*32-1:0]    mb_q,
    output wire [8*(AW+1)-1:0]   issued_words,
    output wire [8*(AW+1)-1:0]   consumed_words,
    output reg  [31:0]           response_sectors
);
    reg active;
    reg [AW-1:0] rom_base_r;
    reg [AW:0] count_r;
    reg [HAW-1:0] sector_base [0:7];
    reg [AW:0] issued [0:7];
    reg [AW:0] consumed [0:7];
    reg [WINDOW-1:0] valid [0:7];
    reg [AW-1:0] tags [0:8*WINDOW-1];
    reg [255:0] data [0:8*WINDOW-1];
    reg [255:0] read0 [0:7];
    reg [255:0] read1 [0:7];
    reg all_lead;
    wire [3:0] response_count = 4'(hr_v[0]) + 4'(hr_v[1]) +
                                4'(hr_v[2]) + 4'(hr_v[3]) +
                                4'(hr_v[4]) + 4'(hr_v[5]) +
                                4'(hr_v[6]) + 4'(hr_v[7]);
    integer c,s,b,u;
    wire [AW:0] rom_end = {1'b0,rom_base} + nwords;
    generate for (genvar g=0;g<8;g=g+1) begin : g_bank
        assign hq_v[g] = active && !fault && issued[g] < count_r &&
                         issued[g] - consumed[g] < (AW+1)'(WINDOW);
        assign hq_addr[g*HAW +: HAW] = sector_base[g] + HAW'(issued[g]);
        assign hq_tag[g*AW +: AW] = issued[g][AW-1:0];
        assign hr_rdy[g] = active && !fault;
        assign issued_words[g*(AW+1) +: AW+1] = issued[g];
        assign consumed_words[g*(AW+1) +: AW+1] = consumed[g];
        for (genvar l=0;l<MG;l=l+1) begin : g_lane
            assign mb_q[(8*l+g)*32 +: 32] = read1[g][l*32 +: 32];
        end
    end endgenerate
    always @* begin
        all_lead = active && !fault;
        for (integer k=0;k<8;k=k+1)
            for (integer j=0;j<LEAD;j=j+1)
                if (j < count_r && (!valid[k][j % WINDOW] ||
                    tags[k*WINDOW+(j % WINDOW)] != AW'(j))) all_lead=1'b0;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; ready <= 1'b0; fault <= 1'b0;
            fault_why <= 0; response_sectors <= 0;
            rom_base_r <= 0; count_r <= 0;
            for (c=0;c<8;c=c+1) begin
                sector_base[c] <= 0; issued[c] <= 0; consumed[c] <= 0;
                valid[c] <= 0; read0[c] <= 0; read1[c] <= 0;
            end
        end else begin
            for (c=0;c<8;c=c+1) read1[c] <= read0[c];
            if (start) begin
                if (active || nwords==0 || nwords>({1'b1,{AW{1'b0}}}) ||
                    rom_end[AW] || MG != 8 || WINDOW < 2 ||
                    (WINDOW & (WINDOW-1)) != 0 || LEAD < 1 || LEAD > WINDOW) begin
                    fault <= 1'b1; fault_why[0] <= 1'b1;
                end else begin
                    active <= 1'b1; ready <= 1'b0;
                    rom_base_r <= rom_base; count_r <= nwords;
                    response_sectors <= 0;
                    for (c=0;c<8;c=c+1) begin
                        sector_base[c] <= bank_sector_base[c*HAW +: HAW];
                        issued[c] <= 0; consumed[c] <= 0; valid[c] <= 0;
                        if (({1'b0,bank_sector_base[c*HAW +: HAW]}+
                            (HAW+1)'(nwords)) > {1'b1,{HAW{1'b0}}}) begin
                            fault <= 1'b1; fault_why[0] <= 1'b1;
                        end
                    end
                end
            end else if (release_window) begin
                active <= 1'b0; ready <= 1'b0;
                for (c=0;c<8;c=c+1)
                    if (consumed[c] != count_r) begin
                        fault <= 1'b1; fault_why[0] <= 1'b1;
                    end
            end else begin
                if (all_lead) ready <= 1'b1;
                if (response_count != 0)
                    response_sectors <= response_sectors+32'(response_count);
                for (c=0;c<8;c=c+1) begin
                    if (hq_v[c] && hq_rdy[c]) issued[c] <= issued[c]+1'b1;
                    if (hr_v[c] && hr_rdy[c]) begin
                        if ({1'b0,hr_tag[c*AW +: AW]} >= issued[c] ||
                            {1'b0,hr_tag[c*AW +: AW]} < consumed[c] ||
                            {1'b0,hr_tag[c*AW +: AW]} >= count_r ||
                            valid[c][hr_tag[c*AW +: LGW]]) begin
                            fault <= 1'b1; fault_why[1] <= 1'b1;
                        end else begin
                            valid[c][hr_tag[c*AW +: LGW]] <= 1'b1;
                            tags[c*WINDOW+int'(hr_tag[c*AW +: LGW])] <= hr_tag[c*AW +: AW];
                            data[c*WINDOW+int'(hr_tag[c*AW +: LGW])] <= hr_data[c*256 +: 256];
                        end
                    end
                    if (mb_re[c]) begin
                        if (!ready || {1'b0,mb_addr[c*AW +: AW]} !=
                            ({1'b0,rom_base_r}+consumed[c]) ||
                            consumed[c] >= count_r) begin
                            fault <= 1'b1; fault_why[2] <= 1'b1;
                        end else if (!valid[c][consumed[c][LGW-1:0]] ||
                                 tags[c*WINDOW+int'(consumed[c][LGW-1:0])] != consumed[c][AW-1:0]) begin
                            fault <= 1'b1; fault_why[3] <= 1'b1;
                        end else begin
                            read0[c] <= data[c*WINDOW+int'(consumed[c][LGW-1:0])];
                            valid[c][consumed[c][LGW-1:0]] <= 1'b0;
                            consumed[c] <= consumed[c]+1'b1;
                        end
                    end
                end
            end
        end
    end
endmodule
