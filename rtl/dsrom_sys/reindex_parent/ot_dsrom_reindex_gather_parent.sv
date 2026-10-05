module ot_dsrom_reindex_gather_parent #(
    parameter integer NPC  = 32,
    parameter integer WB   = 128,
    parameter integer AW   = 28,
    parameter integer HW   = 20,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    parameter integer LBW  = 14,
    parameter integer LMW  = 11,
    parameter integer DF   = 8,
    parameter integer LSW  = 3,          // list slots = 2^LSW (0: the as-built single list)
    localparam integer SLW = (LSW > 0) ? LSW : 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 lw_v,
    input  wire [SLW-1:0]       lw_slot,
    input  wire [LMW-1:0]       lw_addr,
    input  wire [LBW-1:0]       lw_blk,
    input  wire                 cmd_v,
    input  wire [SLW-1:0]       cmd_slot,
    input  wire [HW-1:0]        cmd_base,
    input  wire [9:0]           cmd_skip,
    input  wire [LMW:0]         cmd_n,
    output wire                 busy,
    output wire                 fault,
    output wire [NPC-1:0]       req_v,
    input  wire [NPC-1:0]       req_rdy,
    output wire [NPC*AW-1:0]    req_addr,
    output wire [NPC*LENW-1:0]  req_len,
    output wire [NPC*TAGW-1:0]  req_tag,
    input  wire [NPC-1:0]       rsp_v,
    output wire [NPC-1:0]       rsp_rdy,
    input  wire [NPC*TAGW-1:0]  rsp_tag,
    input  wire [NPC*BEATW-1:0] rsp_beat,
    input  wire [NPC*DW-1:0]    rsp_data,
    output wire                 o_valid,
    input  wire                 o_ready,
    output wire [15:0]          o_kv,
    output wire [16*544-1:0]    o_key,
    output wire [2*LBW-1:0]     o_blk,
    output reg  [47:0]          cnt_keys_streamed,
    output reg  [47:0]          cnt_hbm_beats
);

    initial if(NPC!=32||WB!=128||AW!=28||HW!=20||TAGW!=16||LENW!=4||BEATW!=4||DW!=256||LBW!=14||LMW!=11||LSW!=3||DF!=8)
        $fatal(1,"source-faithful parent geometry required");
    wire cbusy,cfault,mfault,dfault,drain_ready,drain_accept;
    wire [1:0] dr_v;
    wire [6:0] dr_slot;wire [13:0] dr_j;wire [9:0] dr_fc,dr_f0;wire [27:0] dr_blk;
    wire [NPC-1:0] c_req_v,c_req_rdy,qfault;
    wire [NPC*AW-1:0] c_req_addr;wire [NPC*LENW-1:0] c_req_len;wire [NPC*TAGW-1:0] c_req_tag;
    wire command_valid,command_ready,command_in_ready,command_fault;
    wire [47:0] command;
    reg bad_command;
    wire live_fault=dfault||mfault||command_fault||bad_command||(|qfault);
    wire all_fault=live_fault||cfault;
    wire d_valid;wire [15:0] d_kv;wire [16*544-1:0] d_key;wire [27:0] d_blk;
    assign busy=cbusy||d_valid||command_valid||(|req_v)||all_fault;
    assign fault=all_fault;
    assign o_valid=d_valid&&!all_fault;
    assign o_kv=d_kv;assign o_key=d_key;assign o_blk=d_blk;
    ot_dsrom_reindex_request_cut #(.PC(31),.KIND(1)) u_command(
        .clk(clk),.rst_n(rst_n),.in_valid(cmd_v&&!busy),.in_ready(command_in_ready),
        .in_data({3'd0,cmd_slot,cmd_base,cmd_skip,cmd_n}),
        .out_valid(command_valid),.out_ready(command_ready),.out_data(command),.fault(command_fault));
    wire [11:0] command_n=command[11:0];
    wire [9:0] command_skip=command[21:12];
    wire [19:0] command_base=command[41:22];
    wire [2:0] command_slot=command[44:42];
    wire [11:0] list_count;wire writer_pending,read_valid;
    reg [2:0] rd_slot;
    wire [1:0] lr_mask;wire lr_re;wire [9:0] lr_addr;wire [13:0] lr_e,lr_o;
    wire command_bounds=(command[47:45]==0)&&(command_n<=2048)&&(command_skip[2:0]==0)&&command_n<=list_count;
    assign command_ready=!cbusy&&!d_valid&&!(|req_v)&&!all_fault&&!writer_pending&&
                         !(lw_v&&lw_slot==command_slot)&&command_bounds;
    always @(posedge clk)begin
        if(!rst_n)begin rd_slot<=0;bad_command<=0;end
        else begin
            if(command_valid&&!writer_pending&&!(lw_v&&lw_slot==command_slot)&&!command_bounds)bad_command<=1;
            if(command_valid&&command_ready)rd_slot<=command_slot;
        end
    end
    ot_dsrom_reindex_list_macro u_list(
        .clk(clk),.rst_n(rst_n),.w_v(lw_v),.w_slot(lw_slot),.w_addr(lw_addr),.w_block(lw_blk),
        .active(cbusy),.active_slot(cbusy?rd_slot:command_slot),
        .r_re(lr_re),.r_slot(rd_slot),.r_pair(lr_addr),.r_mask(lr_mask),
        .r_even(lr_e),.r_odd(lr_o),.r_valid(read_valid),.corrected(),.fault(mfault),
        .active_count(list_count),.writer_pending(writer_pending));
    ot_dsrom_reindex_kgctl_parent u_c(
        .clk(clk),.rst_n(rst_n),.memory_fault(live_fault),.drain_accept(drain_accept),.lr_mask(lr_mask),
        .lr_re(lr_re),.lr_addr(lr_addr),.lr_e(lr_e),.lr_o(lr_o),
        .cmd_v(command_valid&&command_ready),.cmd_base(command_base),.cmd_skip(command_skip),.cmd_n(command_n),
        .busy(cbusy),.fault(cfault),.req_v(c_req_v),.req_rdy(c_req_rdy),.req_addr(c_req_addr),.req_len(c_req_len),.req_tag(c_req_tag),
        .rsp_v(rsp_v),.rsp_rdy(rsp_rdy),.rsp_tag(rsp_tag),.rsp_beat(rsp_beat),
        .dr_v(dr_v),.dr_slot(dr_slot),.dr_j(dr_j),.dr_fc(dr_fc),.dr_f0(dr_f0),.dr_blk(dr_blk),.dr_ready(drain_ready));
    genvar p;
    generate for(p=0;p<NPC;p=p+1)begin:g_req
        wire [47:0] data;
        ot_dsrom_reindex_request_cut #(.PC(p)) u_q(
            .clk(clk),.rst_n(rst_n),.in_valid(c_req_v[p]),.in_ready(c_req_rdy[p]),
            .in_data({c_req_addr[p*AW+:AW],c_req_len[p*LENW+:LENW],c_req_tag[p*TAGW+:TAGW]}),
            .out_valid(req_v[p]),.out_ready(req_rdy[p]),.out_data(data),.fault(qfault[p]));
        assign {req_addr[p*AW+:AW],req_len[p*LENW+:LENW],req_tag[p*TAGW+:TAGW]}=data;
    end endgenerate
    ot_dsrom_reindex_kgdata_parent u_d(
        .clk(clk),.rst_n(rst_n),.reserve(drain_accept),.fault(dfault),.rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_beat(rsp_beat),.rsp_data(rsp_data),
        .dr_v(dr_v),.dr_slot(dr_slot),.dr_j(dr_j),.dr_fc(dr_fc),.dr_f0(dr_f0),.dr_blk(dr_blk),.dr_ready(drain_ready),
        .o_valid(d_valid),.o_ready(o_ready&&!all_fault),.o_kv(d_kv),.o_key(d_key),.o_blk(d_blk));
    integer ck;reg [4:0] nko;reg [5:0] nbt;
    always @*begin
        nko=0;nbt=0;for(ck=0;ck<16;ck=ck+1)nko=nko+o_kv[ck];for(ck=0;ck<NPC;ck=ck+1)nbt=nbt+rsp_v[ck];
    end
    always @(posedge clk)if(!rst_n)begin cnt_keys_streamed<=0;cnt_hbm_beats<=0;end
    else begin if(o_valid&&o_ready)cnt_keys_streamed<=cnt_keys_streamed+nko;cnt_hbm_beats<=cnt_hbm_beats+nbt;end
endmodule
