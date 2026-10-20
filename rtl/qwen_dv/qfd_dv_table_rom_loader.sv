`timescale 1ns/1ps
// Opt-in local programme-store mechanism. No existing die instantiates this.
// Four real 4096x266 ROMs, fixed88 reads, no wait/credits. Checkpoint and
// address certificates come from programme_store.py. Native physical closure
// and producer/consumer joins remain separate obligations.
module qfd_dv_table_rom_loader #(
    parameter integer SLICE=0,
    parameter integer MUT=0,
    parameter integer BTAB_COMPACT=0,
    parameter integer WE_COPIES=1       // QW-F16PROG4: >1 = kept copies of tw_we for the VM-join select (<=32 loads each)
) (
    input wire ck, rst_n,
    input wire start,
    input wire [5:0] stage,
    input wire [1:0] user_id,
    input wire other_table_write,
    output reg tw_we,
    output wire [WE_COPIES-1:0] tw_we_k, // = {WE_COPIES{tw_we}} on every edge (kept, unique-ID registers when > 1)
    output reg [1:0] tw_kind,
    output reg [23:0] tw_addr,
    output reg [1023:0] tw_data,
    output wire busy,
    output reg done,
    output reg fault
);
    // Two-stage reset landing; wide payload registers need no reset.
    reg r1,r2;
    always @(posedge ck or negedge rst_n)
        if(!rst_n) begin r1<=0;r2<=0;end
        else begin r1<=1;r2<=r1;end
    reg p_start,p_other; reg [5:0] p_stage; reg [1:0] p_user;
    always @(posedge ck) begin p_stage<=stage;p_user<=user_id;end
    always @(posedge ck or negedge rst_n)
        if(!rst_n)begin p_start<=0;p_other<=0;end
        else begin p_start<=start;p_other<=other_table_write;end
    reg active,cap_v,cap_last;
    reg [6:0] slot;
    reg [11:0] base,rom_addr;
    reg [1:0] owner;
    assign busy=active|cap_v;
    function automatic [11:0] row_addr(input [11:0] b,input [1:0] u,input [6:0] k);
        reg [1:0] pu;
        begin
            pu=(MUT==4)?(u+2'd1):u;
            row_addr=b+((k<6)?(6*pu+k):(24+k-6));
        end
    endfunction
    wire [1063:0] data;
`ifdef SYNTHESIS
    ot_rom_4096x266_m8 m0   // hard macro (blackbox view has no INSTANCE parameter; masks bound by INSTANCE name)
`else
    ot_rom_4096x266_m8 #(.INSTANCE($sformatf("table_s%0d_m0",SLICE))) m0
`endif
        (.clk(ck),.ce_in(active),.addr_in(rom_addr),.rd_out(data[265:0]));
`ifdef SYNTHESIS
    ot_rom_4096x266_m8 m1   // hard macro (blackbox view has no INSTANCE parameter; masks bound by INSTANCE name)
`else
    ot_rom_4096x266_m8 #(.INSTANCE($sformatf("table_s%0d_m1",SLICE))) m1
`endif
        (.clk(ck),.ce_in(active),.addr_in(rom_addr),.rd_out(data[531:266]));
`ifdef SYNTHESIS
    ot_rom_4096x266_m8 m2   // hard macro (blackbox view has no INSTANCE parameter; masks bound by INSTANCE name)
`else
    ot_rom_4096x266_m8 #(.INSTANCE($sformatf("table_s%0d_m2",SLICE))) m2
`endif
        (.clk(ck),.ce_in(active),.addr_in(rom_addr),.rd_out(data[797:532]));
`ifdef SYNTHESIS
    ot_rom_4096x266_m8 m3   // hard macro (blackbox view has no INSTANCE parameter; masks bound by INSTANCE name)
`else
    ot_rom_4096x266_m8 #(.INSTANCE($sformatf("table_s%0d_m3",SLICE))) m3
`endif
        (.clk(ck),.ce_in(active),.addr_in(rom_addr),.rd_out(data[1063:798]));
    wire [1:0] kind=data[1026:1025];
    wire [23:0] local_addr=data[1050:1027];
    wire invalid=data[1063:1051]!=0 || kind==0 ||
        (kind==3 && local_addr>=64) || (kind!=3 && local_addr>=128) ||
        (BTAB_COMPACT!=0 && kind==2 && local_addr>=72) ||
        (kind==2 && local_addr[1:0]!=0);
    reg [8:0] btab_base;
    always @* case(owner)
        0:btab_base=0;1:btab_base=272;2:btab_base=344;default:btab_base=416;
    endcase
    wire [23:0] uaddr=(MUT==2)?local_addr:
        ((BTAB_COMPACT!=0 && kind==2)?(local_addr+{15'd0,btab_base}):
        (local_addr|((kind==3)?({22'd0,owner}<<6):({22'd0,owner}<<7))));
    // No combinational input-to-output path. Output is the macro capture
    // register; a following VM write samples it on the next edge.
    always @(posedge ck)begin
        tw_data<=(MUT==3)?{data[511:0],data[1023:512]}:data[1023:0];
        tw_kind<=kind;tw_addr<=uaddr;
    end
    // tw_we copies: same D, same reset/r2 clear as tw_we (one hierarchy-kept register per copy, so Yosys keeps them).
    wire we_d = cap_v&&data[1024]&&!invalid;
    genvar wc;
    generate if(WE_COPIES<=1)begin:g_we1
        assign tw_we_k = tw_we;
    end else begin:g_wek
        for(wc=0;wc<WE_COPIES;wc=wc+1)begin:cp
            (* keep=1, keep_hierarchy=1 *) qfd_tload_kept_bit #(.ID(wc)) ff(.ck(ck),.rst_n(rst_n),.clr(!r2),.d(we_d),.q(tw_we_k[wc]));
        end
    end endgenerate
    reg [11:0] go_base;
    always @* go_base=106*((MUT==1 && p_stage==36)?34:(p_stage-1));
    always @(posedge ck or negedge rst_n)begin
        if(!rst_n)begin
            active<=0;cap_v<=0;cap_last<=0;slot<=0;base<=0;rom_addr<=0;
            owner<=0;tw_we<=0;done<=0;fault<=0;
        end else if(!r2)begin
            active<=0;cap_v<=0;cap_last<=0;tw_we<=0;done<=0;fault<=0;
        end else begin
            done<=cap_v&&cap_last;
            tw_we<=we_d;
            cap_v<=active;cap_last<=active&&slot==87;
            if(cap_v&&data[1024]&&(invalid||p_other))fault<=1;
            if(active)begin
                if(slot==87)active<=0;
                else begin slot<=slot+1;rom_addr<=row_addr(base,owner,slot+1);end
            end
            if(p_start)begin
                if(busy||p_stage==0||p_stage>36)fault<=1;
                else begin
                    active<=1;slot<=0;base<=go_base;owner<=p_user;
                    rom_addr<=row_addr(go_base,p_user,0);
                end
            end
        end
    end
endmodule

// QW-F16PROG4: one kept copy register (unique ID so no two copies are the same paramod; Yosys keeps all)
(* keep_hierarchy=1 *)
module qfd_tload_kept_bit #(parameter integer ID=0) (input wire ck, rst_n, clr, d, output reg q);
    always @(posedge ck or negedge rst_n)
        if(!rst_n) q<=1'b0;
        else if(clr) q<=1'b0;
        else q<=d;
    wire unused_id = ID[0];
endmodule
