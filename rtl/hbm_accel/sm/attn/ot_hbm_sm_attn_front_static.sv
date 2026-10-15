`timescale 1ns/1ps
`default_nettype none
// Revisioned192bit fixed calendar. KV_DESC is a SEPARATE64bit data input.
// Existing83bit schedule remains at command[82:0]; new fields are documented
// in sm_parent_revision_model.json. Zero word is idle; nonzero needs0xa2magic.
// Real parser/converter/pstore drive real operand ports. Faults never insert
// cycles or wait for a late packet/operand. Normal modes reuse the legacyfront.
module ot_hbm_sm_attn_front_static(
    input wire clk,rst_n,
    input wire [191:0] command,
    input wire [63:0] kv_desc,
    input wire [1098:0] packet,
    input wire xw_en,input wire [6:0] xw_addr,xw_grp,input wire [2047:0] xw_data,
    output wire [42:0] request,
    output wire [3271:0] rl,rr,
    output wire [4137:0] bl,br,
    input wire [183:0] ql,qr,
    output wire rv,output wire [11:0] rrow,output wire [255:0] rdata,
    output wire fault,output reg schedule_fault
);
    wire [2:0] mode=command[183:181];
    wire attention=mode[2];
    wire h128=command[180];
    wire configure=attention && command[179];
    wire consume=attention && command[152];
    wire arithmetic_v=attention && command[25];
    wire pv=mode[1];
    wire [3271:0] normal_l,normal_r;
    wire [42:0] normal_request;
    wire normal_schedule_fault,normal_fault;
    ot_smh_static_front u_normal(.clk(clk),.rst_n(rst_n),
        .command(attention?83'd0:command[82:0]),.packet(attention?1099'd0:packet),
        .expected_request(normal_request),.schedule_fault(normal_schedule_fault),
        .xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
        .rl(normal_l),.rr(normal_r),.bl(bl),.br(br),.ql(ql),.qr(qr),
        .rv(rv),.rrow(rrow),.rdata(rdata),.fault(normal_fault));
    wire request_v;
    wire [31:0] request_addr;
    wire [9:0] request_tag;
    wire descriptor_fault;
    // r2: one contiguous line-run descriptor (canonical packed rows); command[115] = load, command[82] = next line
    ot_hbm_sm_kv_desc_static u_desc(.clk(clk),.rst_n(rst_n),.kv_desc(kv_desc),
        .load(attention&&command[115]),.request_v(attention&&command[82]),
        .request_tag(command[49:40]),.req_v(request_v),.req_addr(request_addr),
        .req_tag(request_tag),.fault(descriptor_fault));
    reg attention_q;
    reg [42:0] expected_q;
    always @(posedge clk)expected_q<=command[82:40];
    always @(posedge clk or negedge rst_n)
        if(!rst_n)attention_q<=0;else attention_q<=attention;
    assign request=attention_q?{request_v,request_addr,request_tag}:normal_request;
    wire converter_ready,b_valid,b_last,b_wend,converter_busy,converter_fault;
    wire [1023:0] b_data;
    wire [2:0] b_slot,b_step;
    ot_hbm_sm_kv_line u_converter(.clk(clk),.rst_n(rst_n),.cfg_v(configure),
        .cfg_qk(!pv),.cfg_kv4(mode[0]),.cfg_n8(command[165:153]),.cfg_h128(h128),.cfg_rows(command[178:166]),
        .s_valid(attention&&packet[1098]),.s_ready(converter_ready),.s_data(packet[1087:0]),
        .m_valid(b_valid),.m_ready(consume),.m_data(b_data),.m_slot(b_slot),.m_step(b_step),
        .m_wend(b_wend),.m_last(b_last),.busy(converter_busy),.fault(converter_fault));
    wire p_v,p_fault;
    wire [127:0] p_data;
    ot_hbm_sm_attn_pstore u_p(.clk(clk),.rst_n(rst_n),.clear_v(attention&&command[145]),
        .xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
        .read_v(attention&&command[144]),.read_addr(command[143:137]),
        .p_v(p_v),.p_data(p_data),.fault(p_fault));
    reg [531:0] metadata;
    always @(*)begin
        metadata=0;metadata[127:0]=p_data;
        metadata[130:128]=mode;metadata[131]=h128;
        metadata[132]=command[136];metadata[133]=command[135];
        metadata[134]=command[134];metadata[136:135]=command[133:132];metadata[137]=consume;
        // r2 in-SM PV stream fold (head dim 128): command[131] fold, [130:128] entry a, [127:125] entry b
        metadata[138]=attention&&command[131];metadata[141:139]=command[130:128];metadata[144:142]=command[127:125];
    end
    wire [15:0] tag={command[22:11],command[10],command[9:7]};
    wire [21:0] control={1'b0,(arithmetic_v || (attention&&(command[134]||command[131]))),command[24],command[23],1'b1,1'b1,tag};
    wire [3271:0] a_rows;
    genvar j;
    generate for(j=0;j<4;j=j+1)begin:g_row
        ot_hbm_sm_attn_row_launch u_row(.clk(clk),.rst_n(rst_n),
            .d({control,b_data[256*j+:256],metadata,arithmetic_v&&!pv,command[6:0]}),
            .q(a_rows[818*j+:818]));
        assign rl[818*j+:818]=attention_q?a_rows[818*j+:818]:normal_l[818*j+:818];
        assign rr[818*j+:818]=attention_q?a_rows[818*j+:818]:normal_r[818*j+:818];
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if(!rst_n)schedule_fault<=0;
        else begin
            if(command!=0 && (command[191:184]!=8'ha2 || |command[124:116] || |command[114:112] || command[111]))schedule_fault<=1;
            if(!attention && mode==3)schedule_fault<=1;
            if(attention_q && (request[42]!=expected_q[42] || (request[42] && request!=expected_q)))schedule_fault<=1;
            if(!attention && command[25] && converter_busy)schedule_fault<=1;
            if(!attention && command[28] && command[27:26]!=mode[1:0])schedule_fault<=1;
            if(attention)begin
                if(packet[1098]!=command[29] || (command[29] && packet[1097:1088]!=command[39:30]))schedule_fault<=1;
                if(packet[1098] && !converter_ready)schedule_fault<=1;
                if(consume!=arithmetic_v || (consume && (!b_valid || b_slot!=command[151:149] || b_step!=command[148:146])))schedule_fault<=1;
                if(consume && pv && !p_v)schedule_fault<=1;
                if(configure && (converter_busy || command[178:166]==0 || (h128 && mode[0])))schedule_fault<=1;
            end
            if(descriptor_fault || converter_fault || p_fault || normal_schedule_fault)schedule_fault<=1;
        end
    assign fault=normal_fault;
endmodule

// Separate modest launch roots preserve the818bit physical transport ABI.
// No old hardtop view or slot is claimed for these new launch leaves.
module ot_hbm_sm_attn_row_launch(
    input wire clk,rst_n,input wire [817:0] d,output wire [817:0] q
);
    reg [817:0] data;
    always @(posedge clk)data<=d;
    reg vb,vf,ce;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin vb<=0;vf<=0;ce<=0;end
        else begin vb<=d[817];vf<=d[816];ce<=d[7];end
    assign q={vb,vf,data[815:8],ce,data[6:0]};
endmodule
`default_nettype wire
