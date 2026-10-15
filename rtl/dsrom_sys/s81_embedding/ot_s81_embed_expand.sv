`timescale 1ns/1ps
// Fixed-calendar embedding leaf. One 320-word ROM stream -> 640 four-copy
// BF16 HIDDEN rows. SRAM holds the native ROM order, never a C++ DUT array.
// Two real 512x128 SRAM macros (81,920 live bits / 131,072 physical bits).
// Eight SRAM reads transpose one 128-element block into 16 output rows.
// Calendar from accepted start edge: ROM samples at +3..+322; header +325;
// each 26-cycle block: read slots 0..7, capture slots 1..8, emit 10..25.
// Outputs have no ready inputs. A fault reports a violated compiled contract;
// it does not delay, replay, or dynamically schedule a single transfer.
module ot_s81_embed_expand #(
    parameter integer MUTANT = 0
)(
    input wire clk, rst_n, start,
    input wire [511:0] header,
    input wire [13:0] vm_base,
    input wire rom_v,
    input wire [8:0] rom_idx,
    input wire [511:0] rom_d,
    output reg busy, done, fault,
    output reg vm_v,
    output reg [13:0] vm_row,
    output reg [511:0] vm_d,
    output reg hop_v, hop_last,
    output reg [511:0] hop_d
);
    localparam IDLE=0, LOAD=1, HEADER=2, BLOCK=3;
    reg [1:0] state;
    reg [8:0] age;
    reg [5:0] block_no;
    reg [4:0] slot;
    reg [13:0] base_q;
    reg [511:0] header_q;
    reg [255:0] transpose [0:7];
    wire write_slot=(state==LOAD && age>=3 && age<=322);
    wire read_slot=(state==BLOCK && slot<8);
    wire [8:0] wa=age-9'd3;
    wire [8:0] ra={block_no,3'b000}+9'(slot);
    wire [255:0] packed_d, ram_d;
    for(genvar l=0;l<16;l=l+1) begin: pack_bf16
        assign packed_d[16*l+:16]=rom_d[32*l+16+:16];
    end
    for(genvar c=0;c<2;c=c+1) begin: storage
        ot_sram_1r1w_512x128_m4_r2c2 u_mem(
            .clk(clk),.r_ce_in(read_slot),.r_addr_in(ra),.rd_out(ram_d[128*c+:128]),
            .w_ce_in(write_slot),.w_addr_in(wa),.wd_in(packed_d[128*c+:128]),
            .w_mask_in({128{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(14'b0));
    end
    wire [3:0] element_lane=4'(slot-10);
    wire [511:0] expanded;
    for(genvar b=0;b<8;b=b+1) begin: expand_element
        for(genvar k=0;k<4;k=k+1) begin: copies
            assign expanded[16*(b*4+k)+:16] =
                (MUTANT==1 && k==3) ? 16'b0 : transpose[b][16*element_lane+:16];
        end
    end
    always @(posedge clk) begin
        if(!rst_n) begin
            state<=IDLE;age<=0;block_no<=0;slot<=0;base_q<=0;header_q<=0;
            busy<=0;done<=0;fault<=0;vm_v<=0;hop_v<=0;hop_last<=0;
            vm_row<=0;vm_d<=0;hop_d<=0;
        end else begin
            done<=0;vm_v<=0;hop_v<=0;hop_last<=0;
            if(start && busy) fault<=1;
            case(state)
            IDLE: if(start) begin
                busy<=1;age<=1;base_q<=vm_base;header_q<=header;state<=LOAD;
                if(vm_base>14'd15744) fault<=1;
            end
            LOAD: begin
                // No data-valid scheduling: write slots come from age alone.
                if(rom_v!=write_slot) fault<=1;
                if(write_slot && rom_idx!=wa) fault<=1;
                if(age==324) state<=HEADER;
                else age<=age+1'b1;
            end
            HEADER: begin
                hop_v<=1;hop_d<=header_q;block_no<=0;slot<=0;state<=BLOCK;
            end
            BLOCK: begin
                if(slot>=1 && slot<=8) transpose[slot-1]<=ram_d;
                if(slot>=10) begin
                    vm_v<=1;vm_row<=base_q+14'(block_no*16)+14'(slot-10);
                    vm_d<=expanded;hop_v<=1;hop_d<=expanded;
                    hop_last<=(block_no==39 && slot==25);
                end
                if(slot==25) begin
                    slot<=0;
                    if(block_no==39) begin state<=IDLE;busy<=0;done<=1;end
                    else block_no<=block_no+1'b1;
                end else slot<=slot+1'b1;
            end
            default: begin state<=IDLE;busy<=0;fault<=1;end
            endcase
        end
    end
endmodule
