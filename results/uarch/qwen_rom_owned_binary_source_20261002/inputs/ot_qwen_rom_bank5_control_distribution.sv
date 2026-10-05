`timescale 1ns/1ps
// Maxwell cdcbe60a model-r3 fixed topology. This is the exact76-cell
// combinational distribution network, not a reset-release producer or clock
// tree. Caller must bind physical FF QN polarity, real metadata sink pins,
// launch timing/reset phase and complete tile context before STA/adoption.
module ot_qwen_rom_bank5_control_distribution (
    input wire [4:0] bank_read_n,       // actual mapped bank-strobe FF QN
    input wire [4:0] bank_hold_term,    // actual five bank NOR outputs
    input wire [11:0] low_address,
    input wire reset_n,
    output wire [84:0] strobe_sink_n,  //17 sinks/bank: one NOR +16 hold feedback
    output wire [79:0] hold_term_sink,//16 mask hold terms/bank
    output wire [119:0] macro_address,//12 bits for each of10 ROMs
    output wire [89:0] metadata_reset_n
);
    genvar bank,leaf,sink,bit_index;
    generate for (bank=0;bank<5;bank=bank+1) begin:g_bank
        wire [2:0] strobe_leaf;
        wire [1:0] term_leaf;
        for(leaf=0;leaf<3;leaf=leaf+1) begin:g_strobe
            (* keep=1, dont_touch=1 *) BUFx4_ASAP7_75t_R u_buf
                (.A(bank_read_n[bank]),.Y(strobe_leaf[leaf]));
        end
        for(leaf=0;leaf<2;leaf=leaf+1) begin:g_term
            (* keep=1, dont_touch=1 *) BUFx4_ASAP7_75t_R u_buf
                (.A(bank_hold_term[bank]),.Y(term_leaf[leaf]));
        end
        for(sink=0;sink<17;sink=sink+1) begin:g_strobe_sink
            assign strobe_sink_n[17*bank+sink]=strobe_leaf[sink/6];
        end
        for(sink=0;sink<16;sink=sink+1) begin:g_term_sink
            assign hold_term_sink[16*bank+sink]=term_leaf[sink/8];
        end
    end endgenerate
    generate for(bit_index=0;bit_index<12;bit_index=bit_index+1) begin:g_address
        wire root;
        wire [1:0] addr_leaf;
        (* keep=1, dont_touch=1 *) BUFx4_ASAP7_75t_R u_root
            (.A(low_address[bit_index]),.Y(root));
        for(leaf=0;leaf<2;leaf=leaf+1) begin:g_leaf
            (* keep=1, dont_touch=1 *) BUFx4_ASAP7_75t_R u_buf
                (.A(root),.Y(addr_leaf[leaf]));
        end
        for(sink=0;sink<10;sink=sink+1) begin:g_sink
            assign macro_address[12*sink+bit_index]=addr_leaf[sink/5];
        end
    end endgenerate
    wire reset_root;
    wire [1:0] reset_mid;
    wire [11:0] reset_leaf;
    (* keep=1, dont_touch=1 *) BUFx4_ASAP7_75t_R u_reset_root
        (.A(reset_n),.Y(reset_root));
    generate for(leaf=0;leaf<2;leaf=leaf+1) begin:g_reset_mid
        (* keep=1, dont_touch=1 *) BUFx4_ASAP7_75t_R u_buf
            (.A(reset_root),.Y(reset_mid[leaf]));
    end
    for(leaf=0;leaf<12;leaf=leaf+1) begin:g_reset_leaf
        (* keep=1, dont_touch=1 *) BUFx4_ASAP7_75t_R u_buf
            (.A(reset_mid[leaf/6]),.Y(reset_leaf[leaf]));
    end
    for(sink=0;sink<90;sink=sink+1) begin:g_reset_sink
        assign metadata_reset_n[sink]=reset_leaf[sink/8];
    end endgenerate
endmodule
