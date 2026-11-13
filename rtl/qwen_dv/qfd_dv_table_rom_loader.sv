`timescale 1ns/1ps
// Opt-in local programme-store mechanism. No existing die instantiates this.
// Four real 4096x266 ROMs, fixed88 reads, no wait/credits. Checkpoint and
// address certificates come from programme_store.py. Native physical closure
// and producer/consumer joins remain separate obligations.
module qfd_dv_table_rom_loader #(
    parameter integer SLICE=0,
    parameter integer MUT=0,
    parameter integer BTAB_COMPACT=0,
    parameter integer LOCAL_CTRL=0, // opt-in kept stage copies per address nibble, edge-identical
    parameter integer CAPTURE_MUT=0, // bench causal: 1 metadata bypass;2 early done
    parameter integer CAPTURE_STAGE=0, // private structural ROM-capture successor (+1 write edge)
    parameter integer WE_COPIES=1,      // QW-F16PROG4: >1 = kept copies of tw_we for the VM-join select (<=32 loads each)
    parameter integer MONITOR_TAIL=0,  // candidate only: two invariant PROG pairs after the88-read prefix (+2 edges)
    parameter integer HEAD_STAGE37=0  // source-event candidate only; shared HEAD BTAB50/CROM32
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
    localparam integer MAX_STAGE = 36 + HEAD_STAGE37;
    localparam integer TAIL_BASE = 106 * MAX_STAGE;
    generate if (HEAD_STAGE37!=0 && (HEAD_STAGE37!=1 || BTAB_COMPACT!=1 ||
                  CAPTURE_STAGE!=0 || LOCAL_CTRL!=0 || WE_COPIES!=34)) begin:g_head_profile_bad
        initial $fatal(1,"HEAD_STAGE37 requires native compact C0/LOCAL0/WE34 profile");
    end endgenerate
    localparam integer LAST_SLOT = (MONITOR_TAIL!=0) ? 89 : 87;
    generate if (MONITOR_TAIL!=0 && (MONITOR_TAIL!=1 || BTAB_COMPACT!=1 ||
                  CAPTURE_STAGE!=0 || LOCAL_CTRL!=0 || WE_COPIES!=34)) begin:g_monitor_profile_bad
        initial $fatal(1,"MONITOR_TAIL requires native compact C0/LOCAL0/WE34 profile");
    end endgenerate
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
    // QC-KITS-W 10-30: stage_base = 106*k is even, so base[0] is constant 0; it is not stored (synthesis removed the FF,
    // LEC kept it as free state under the derived addr_reset and failed rom_addr). Same values every edge.
    reg [11:0] rom_addr;
    reg [11:1] base_hi;
    wire [11:0] base={base_hi,1'b0};
    reg [1:0] owner;
    assign busy=active|cap_v|((CAPTURE_STAGE!=0)&&data_valid);
    function automatic [11:0] row_addr(input [11:0] b,input [1:0] u,input [6:0] k);
        reg [1:0] pu;
        begin
            pu=(MUT==4)?(u+2'd1):u;
            if (MONITOR_TAIL!=0 && k>=88)
                row_addr=12'(TAIL_BASE)+2*pu+(k-7'd88);
            else row_addr=b+((k<6)?(6*pu+k):(24+k-6));
        end
    endfunction
    wire [1063:0] data, rom_data;
    wire [5:0] local_reset;
    // HARD-QC-FORMS-1 11-13: the four metadata capture copies as module-level nets (were hierarchical references
    // g_capture.meta[k].*_q, which yosys rejects: "Identifier bits_q is implicitly declared"); same registers, same values.
    wire [159:0] cm_bits; wire [7:0] cm_owner; wire [3:0] cm_other, cm_valid, cm_last;
    genvar rg;
    generate if(CAPTURE_STAGE!=0)begin:g_capture
        for(rg=0;rg<6;rg=rg+1)begin:rst
            (* keep=1, keep_hierarchy=1 *) qfd_tload_kept_bit #(.ID(100+rg)) ff
                (.ck(ck),.rst_n(rst_n),.clr(1'b0),.d(r2),.q(local_reset[rg]));
        end
        reg [1023:0] payload;
        always @(posedge ck) payload<=rom_data[1023:0];
        for(rg=0;rg<4;rg=rg+1)begin:meta
            (* keep=1, keep_hierarchy=1 *) qfd_tload_metadata_capture #(.ID(rg)) ff
                (.ck(ck),.rst_n(local_reset[rg]),.bits_d(rom_data[1063:1024]),.owner_d(owner),
                 .other_d(p_other),.valid_d(cap_v),.last_d(cap_last),.bits_q(cm_bits[40*rg+:40]),.owner_q(cm_owner[2*rg+:2]),
                 .other_q(cm_other[rg]),.valid_q(cm_valid[rg]),.last_q(cm_last[rg]));
        end
        assign data={(CAPTURE_MUT==1)?rom_data[1063:1024]:cm_bits[39:0],payload};
    end else begin:g_no_capture
        assign local_reset={6{rst_n}};
        assign data=rom_data;
        assign cm_bits=160'd0; assign cm_owner=8'd0; assign cm_other=4'd0; assign cm_valid=4'd0; assign cm_last=4'd0;
    end endgenerate
    wire ctrl_reset=local_reset[5];
    wire addr_reset=local_reset[4];
    wire [1:0] data_owner;
    wire data_valid,data_last,data_other;
    generate if(CAPTURE_STAGE!=0)begin:g_cfields
        assign data_owner=cm_owner[1:0];
        assign data_valid=cm_valid[0];
        assign data_last=cm_last[0];
        assign data_other=cm_other[0];
    end else begin:g_ofields
        assign data_owner=owner;assign data_valid=cap_v;assign data_last=cap_last;assign data_other=p_other;
    end endgenerate
    wire [3:0] we_group;
    generate for(rg=0;rg<4;rg=rg+1)begin:g_validation
        if(CAPTURE_STAGE!=0)begin:g_c
            wire [39:0] b=cm_bits[40*rg+:40];
            wire [1:0] k=b[2:1];
            wire [23:0] a=b[26:3];
            wire bad=(b[39:27]!=0)||(k==0)||((k==3)&&(a>=64))||((k!=3)&&(a>=128))||
                     ((BTAB_COMPACT!=0)&&(k==2)&&(a>=72))||((k==2)&&(a[1:0]!=0));
            assign we_group[rg]=cm_valid[rg]&&b[0]&&!bad;
        end else begin:g_o
            assign we_group[rg]=cap_v&&data[1024]&&!invalid;
        end
    end endgenerate
`ifdef SYNTHESIS
    ot_rom_4096x266_m8 m0   // hard macro (blackbox view has no INSTANCE parameter; masks bound by INSTANCE name)
`else
    ot_rom_4096x266_m8 #(.INSTANCE($sformatf("table_s%0d_m0",SLICE))) m0
`endif
        (.clk(ck),.ce_in(active),.addr_in(rom_addr),.rd_out(rom_data[265:0]));
`ifdef SYNTHESIS
    ot_rom_4096x266_m8 m1   // hard macro (blackbox view has no INSTANCE parameter; masks bound by INSTANCE name)
`else
    ot_rom_4096x266_m8 #(.INSTANCE($sformatf("table_s%0d_m1",SLICE))) m1
`endif
        (.clk(ck),.ce_in(active),.addr_in(rom_addr),.rd_out(rom_data[531:266]));
`ifdef SYNTHESIS
    ot_rom_4096x266_m8 m2   // hard macro (blackbox view has no INSTANCE parameter; masks bound by INSTANCE name)
`else
    ot_rom_4096x266_m8 #(.INSTANCE($sformatf("table_s%0d_m2",SLICE))) m2
`endif
        (.clk(ck),.ce_in(active),.addr_in(rom_addr),.rd_out(rom_data[797:532]));
`ifdef SYNTHESIS
    ot_rom_4096x266_m8 m3   // hard macro (blackbox view has no INSTANCE parameter; masks bound by INSTANCE name)
`else
    ot_rom_4096x266_m8 #(.INSTANCE($sformatf("table_s%0d_m3",SLICE))) m3
`endif
        (.clk(ck),.ce_in(active),.addr_in(rom_addr),.rd_out(rom_data[1063:798]));
    // The base stays fixed through the capture/output tail; no new request may enter while busy.
    wire shared_head = (HEAD_STAGE37!=0) && base==12'd3816;
    wire [1:0] kind=data[1026:1025];
    wire [23:0] local_addr=data[1050:1027];
    wire invalid=data[1063:1051]!=0 || kind==0 ||
        (kind==3 && local_addr>=64) || (kind!=3 && local_addr>=128 && !(shared_head && kind==2)) ||
        (BTAB_COMPACT!=0 && kind==2 && (shared_head ? (local_addr<72 || local_addr>=272) : local_addr>=72)) ||
        (kind==2 && local_addr[1:0]!=0);
    reg [8:0] btab_base;
    always @* case(data_owner)
        0:btab_base=0;1:btab_base=272;2:btab_base=344;default:btab_base=416;
    endcase
    wire [23:0] uaddr=(MUT==2)?local_addr:
        ((BTAB_COMPACT!=0 && kind==2)?(shared_head ? local_addr : (local_addr+{15'd0,btab_base})):
        (local_addr|((kind==3)?({22'd0,data_owner}<<6):({22'd0,data_owner}<<7))));
    // No combinational input-to-output path. Output is the macro capture
    // register; a following VM write samples it on the next edge.
    always @(posedge ck)begin
        tw_data<=(MUT==3)?{data[511:0],data[1023:512]}:data[1023:0];
        tw_kind<=kind;tw_addr<=uaddr;
    end
    // tw_we copies: same D, same reset/r2 clear as tw_we (one hierarchy-kept register per copy, so Yosys keeps them).
    wire we_d = we_group[0];
    genvar wc;
    generate if(WE_COPIES<=1)begin:g_we1
        assign tw_we_k = tw_we;
    end else begin:g_wek
        for(wc=0;wc<WE_COPIES;wc=wc+1)begin:cp
            (* keep=1, keep_hierarchy=1 *) qfd_tload_kept_bit #(.ID(wc)) ff(.ck(ck),.rst_n(local_reset[(CAPTURE_STAGE!=0)?(wc%4):0]),.clr((CAPTURE_STAGE!=0)?1'b0:!r2),.d(we_group[wc%4]),.q(tw_we_k[wc]));
        end
    end endgenerate
    wire [11:0] go_base;
    function automatic [11:0] stage_base(input [5:0] s);
        stage_base=106*((MUT==1 && s==36)?34:(s-1));
    endfunction
    generate if(LOCAL_CTRL)begin:g_stage_local
        for(genvar sg=0;sg<4;sg=sg+1)begin:g_nibble
            wire [5:0] stage_q;
            wire [11:0] value;
            (* keep=1, keep_hierarchy=1 *) qfd_tload_stage_copy #(.ID(sg)) ff
                (.ck(ck),.d(stage),.q(stage_q));
            assign value=stage_base(stage_q);
            assign go_base[3*sg+:3]=value[3*sg+:3];
        end
    end else begin:g_stage_legacy
        assign go_base=stage_base(p_stage);
    end endgenerate
    always @(posedge ck or negedge ctrl_reset)begin
        if(!ctrl_reset)begin
            active<=0;cap_v<=0;cap_last<=0;slot<=0;tw_we<=0;done<=0;fault<=0;
        end else if(!r2)begin
            active<=0;cap_v<=0;cap_last<=0;tw_we<=0;done<=0;fault<=0;
        end else begin
            done<=(CAPTURE_MUT==2)?(cap_v&&cap_last):(data_valid&&data_last);
            tw_we<=we_d;
            cap_v<=active;cap_last<=active&&slot==LAST_SLOT;
            if(data_valid&&data[1024]&&(invalid||data_other))fault<=1;
            if(active)begin
                if(slot==LAST_SLOT)active<=0;
                else slot<=slot+1;
            end
            if(p_start)begin
                if(busy||p_stage==0||p_stage>MAX_STAGE)fault<=1;
                else begin
                    active<=1;slot<=0;
                end
            end
        end
    end
    always @(posedge ck or negedge addr_reset)begin
        if(!addr_reset)begin base_hi<=0;rom_addr<=0;owner<=0;end
        else if(r2)begin
            if(active&&slot!=LAST_SLOT)rom_addr<=row_addr(base,owner,slot+1);
            if(p_start&&!busy&&p_stage!=0&&p_stage<=MAX_STAGE)begin
                base_hi<=go_base[11:1];owner<=p_user;rom_addr<=row_addr(go_base,p_user,0);
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

// Distinct capture/validation regions retain their metadata registers through synthesis.
(* keep_hierarchy=1 *)
module qfd_tload_metadata_capture #(parameter integer ID=0)(
    input wire ck,rst_n,input wire [39:0] bits_d,input wire [1:0] owner_d,
    input wire other_d,valid_d,last_d,
    output reg [39:0] bits_q,output reg [1:0] owner_q,output reg other_q,valid_q,last_q);
    always @(posedge ck)begin bits_q<=bits_d;owner_q<=owner_d;other_q<=other_d;end
    always @(posedge ck or negedge rst_n)
        if(!rst_n)begin valid_q<=0;last_q<=0;end
        else begin valid_q<=valid_d;last_q<=last_d;end
    wire unused_id=ID[0];
endmodule

// Each address nibble uses its own producer register bank; no new edge.
(* keep_hierarchy=1 *)
module qfd_tload_stage_copy #(parameter integer ID=0)(input wire ck,input wire[5:0]d,output reg[5:0]q);
    (* keep=1 *) wire[5:0] source_word=d;
    always @(posedge ck) q<=source_word;
    wire unused_id=ID[0];
endmodule
