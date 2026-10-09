`timescale 1ns/1ps
// CAP1 protected adapter over the unchanged full16 masked R2 SRAM provider.
// SRAM protection is retained; this is not ROM ECC. Read bases are aligned.
// A partial writer reads/corrects the old word, merges lanes, writes data and
// checks, then reads/decode/compares the actual SRAM before publishing its ACK.
// The pulse caller reserves a response seat and holds its native clock.
module ot_qwen_checked_vm_bank_direct_readback #(parameter integer DIRECT_READBACK=0, parameter integer TAG_W=227)(
    input wire clk,rst_n,
    input wire rd_v,input wire [14:0] rd_base_word,
    input wire [TAG_W-1:0] rd_owner,
    output wire rd_accept_v,output reg rd_out_v,
    output reg [1:0] rd_out_rot,output reg [2047:0] rd_out_bank_words,
    output reg [TAG_W-1:0] rd_out_owner,output wire rd_fault,
    input wire [3:0] wr_v,input wire [59:0] wr_word_addr,
    input wire [2047:0] wr_word_data,input wire [63:0] wr_lane_mask,
    input wire [4*TAG_W-1:0] wr_owner,
    output wire [3:0] wr_accept_v,output reg [3:0] wr_ack_v,
    output reg [4*TAG_W-1:0] wr_ack_owner,
    output reg [59:0] wr_ack_word_addr,output reg [63:0] wr_ack_lane_mask,
    output wire wr_fault,rw_collision_fault
);
    // package functions are called fully qualified: ORFS yosys rejects a module-body import
    localparam IDLE=0,OLD=1,DEC1=2,DEC2=3,DEC3=4,MERGE=5,
        ENC1=6,ENC2=7,COMMIT=8,ACK=9,POST=10,VERIFY=11,RELEASE=12;
    reg [3:0] state;
    reg sticky_fault;
    reg is_write,postcheck;
    reg [1:0] bank;
    reg [14:0] word_addr;
    reg [15:0] mask;
    reg [511:0] payload,merged;
    reg [63:0] encoded_checks;
    reg [TAG_W-1:0] tag;
    reg [2047:0] sampled,decoded;
    reg [255:0] sampled_checks;
    reg decode_ue;
    reg [TAG_W-1:0] sampled_tag;
    wire [1:0] selected_bank=wr_v[0]?0:wr_v[1]?1:wr_v[2]?2:3;
    wire single_write=(wr_v==1||wr_v==2||wr_v==4||wr_v==8);
    wire [14:0] selected_word=wr_word_addr[selected_bank*15+:15];
    wire read_bad=rd_base_word[1:0]!=0 || rd_base_word>15'd32764;
    wire write_bad=!single_write || selected_word[1:0]!=selected_bank ||
        wr_lane_mask[selected_bank*16+:16]==0;
    wire ready=state==IDLE && rst_n && !sticky_fault;
    assign rd_accept_v=ready && rd_v && !(|wr_v) && !read_bad;
    assign wr_accept_v={4{ready && !rd_v && !write_bad}} & wr_v;
    assign rd_fault=sticky_fault;
    assign wr_fault=sticky_fault;
    assign rw_collision_fault=ready && rd_v && (|wr_v);
    wire read_initial=rd_accept_v || (|wr_accept_v);
    wire raw_read=read_initial || (state==POST && !sticky_fault);
    wire [14:0] raw_base=read_initial ? ((|wr_accept_v)?
        (wr_word_addr[selected_bank*15+:15] & 15'h7ffc):rd_base_word) : (word_addr & 15'h7ffc);
    wire [TAG_W-1:0] raw_tag=read_initial ? ((|wr_accept_v)?
        wr_owner[selected_bank*TAG_W+:TAG_W]:rd_owner):tag;
    wire raw_commit=state==COMMIT && rst_n && !sticky_fault;
    wire raw_accept,raw_valid,raw_rf,raw_wf,raw_cf;
    wire [2047:0] raw_words;
    wire [1:0] raw_rot;
    wire [TAG_W-1:0] raw_owner;
    wire [3:0] raw_wa,raw_ack;
    wire [4*TAG_W-1:0] raw_ack_owner;
    wire [59:0] raw_ack_addr;
    wire [63:0] raw_ack_mask;
    reg [3:0] we;
    reg [59:0] wa;
    reg [2047:0] wd;
    reg [63:0] wm;
    reg [4*TAG_W-1:0] wo;
    always @* begin
        we=0;wa=0;wd=0;wm=0;wo=0;
        if(raw_commit)begin
            we[bank]=1;wa[bank*15+:15]=word_addr;
            wd[bank*512+:512]=merged;wm[bank*16+:16]=16'hffff;
            wo[bank*TAG_W+:TAG_W]=tag;
        end
    end
    ot_qwen_vm_bank4_direct_readback #(
        .DIRECT_READBACK(DIRECT_READBACK),.MASKED_VISIBLE(1),.DEPTH_GROUPS(16),.AW(15),.TAG_W(TAG_W)) u_data(
        .clk(clk),.rst_n(rst_n),.rd_v(raw_read),.rd_base_word(raw_base),.rd_owner(raw_tag),
        .rd_accept_v(raw_accept),.rd_out_v(raw_valid),.rd_out_rot(raw_rot),
        .rd_out_bank_words(raw_words),.rd_out_owner(raw_owner),.rd_fault(raw_rf),
        .wr_v(we),.wr_word_addr(wa),.wr_word_data(wd),.wr_lane_mask(wm),.wr_owner(wo),
        .wr_accept_v(raw_wa),.wr_ack_v(raw_ack),.wr_ack_owner(raw_ack_owner),
        .wr_ack_word_addr(raw_ack_addr),.wr_ack_lane_mask(raw_ack_mask),
        .wr_fault(raw_wf),.rw_collision_fault(raw_cf));
    // Each group has two existing 512x128 macros. One check byte per64 data
    // bits: 4banks*64checkbits/row=256bits;16groups*2macros=32 check macros.
    wire [127:0] checks[0:15][0:1];
    reg [3:0] check_group;
    reg [255:0] check_hold;
    reg [255:0] check_cut;
    genvar g,p;
    generate for(g=0;g<16;g=g+1)begin:g_check
        for(p=0;p<2;p=p+1)begin:g_pair
            wire check_write=raw_commit && word_addr[14:11]==g && bank[1]==p;
            ot_sram_1r1w_512x128_m4_r2c2 u_check(
                .clk(clk),.r_ce_in(raw_read && raw_base[14:11]==g),
                .r_addr_in(raw_base[10:2]),.rd_out(checks[g][p]),
                .w_ce_in(check_write),.w_addr_in(word_addr[10:2]),
                .wd_in(bank[0]?{encoded_checks,64'b0}:{64'b0,encoded_checks}),
                .w_mask_in(bank[0]?{64'hffffffffffffffff,64'b0}:{64'b0,64'hffffffffffffffff}),
                .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(14'b0));
        end
    end endgenerate
    // Sidecar read arrives ahead of the unchanged data service. Hold immutable
    // pair words through raw read return; no second request while CAP1 is owned.
    always @(posedge clk)begin
        if(raw_read)check_group<=raw_base[14:11];
        check_hold<={checks[check_group][1],checks[check_group][0]};
        check_cut<=check_hold;
    end
    function automatic [71:0] join_code(input [63:0] d,input [7:0] parity);
        reg [71:0] c;integer pos,j,k;
        begin
            c=0;j=0;k=0;
            for(pos=1;pos<=71;pos=pos+1)begin
                if((pos&(pos-1))!=0)begin c[pos-1]=d[j];j=j+1;end
                else begin c[pos-1]=parity[k];k=k+1;end
            end
            c[71]=parity[7];join_code=c;
        end
    endfunction
    function automatic [7:0] parity64(input [63:0] d);
        reg [71:0] code;integer k;
        begin
            code=ot_gpu_w6_secded_pkg::encode64(d);
            for(k=0;k<7;k=k+1)parity64[k]=code[(1<<k)-1];
            parity64[7]=code[71];
        end
    endfunction
    reg [65:0] d;
    always @(posedge clk)begin
        if(!rst_n)begin
            state<=IDLE;sticky_fault<=0;rd_out_v<=0;wr_ack_v<=0;
            rd_out_rot<=0;rd_out_bank_words<=0;rd_out_owner<=0;
            wr_ack_owner<=0;wr_ack_word_addr<=0;wr_ack_lane_mask<=0;
            is_write<=0;postcheck<=0;bank<=0;word_addr<=0;mask<=0;payload<=0;
            merged<=0;encoded_checks<=0;tag<=0;sampled<=0;decoded<=0;
            sampled_checks<=0;sampled_tag<=0;decode_ue<=0;
        end else begin
            rd_out_v<=0;wr_ack_v<=0;
            if(raw_rf||raw_wf||raw_cf)sticky_fault<=1;
            if(!sticky_fault)case(state)
                IDLE:begin
                    if(rd_v && (|wr_v) || rd_v && read_bad || (|wr_v) && write_bad)sticky_fault<=1;
                    else if(read_initial)begin
                        is_write<=|wr_accept_v;postcheck<=0;tag<=raw_tag;
                        word_addr<=(|wr_accept_v)?wr_word_addr[selected_bank*15+:15]:rd_base_word;
                        bank<=selected_bank;mask<=wr_lane_mask[selected_bank*16+:16];
                        payload<=wr_word_data[selected_bank*512+:512];state<=OLD;
                    end
                end
                OLD:if(raw_valid)begin
                    if(raw_owner!=tag || raw_rot!=0)sticky_fault<=1;
                    else begin sampled<=raw_words;sampled_checks<=check_cut;sampled_tag<=raw_owner;state<=DEC1;end
                end
                DEC1:begin
                    decode_ue<=0;
                    for(integer i=0;i<32;i=i+1)begin
                        d=ot_gpu_w6_secded_pkg::decode64(join_code(sampled[i*64+:64],sampled_checks[i*8+:8]));
                        decoded[i*64+:64]<=d[63:0];
                        // A full initialization write replaces its entire word;
                        // no uninitialized old data participates in arithmetic.
                        if((!is_write || i/8==bank) && !(is_write && !postcheck && mask==16'hffff) && d[65])decode_ue<=1;
                    end
                    state<=DEC2;
                end
                DEC2:state<=DEC3;
                DEC3:begin
                    if(decode_ue || sampled_tag!=tag)sticky_fault<=1;
                    else if(postcheck)state<=VERIFY;
                    else if(is_write)state<=MERGE;
                    else begin rd_out_v<=1;rd_out_rot<=0;rd_out_bank_words<=decoded;rd_out_owner<=tag;state<=IDLE;end
                end
                MERGE:begin
                    for(integer i=0;i<16;i=i+1)
                        merged[i*32+:32]<=mask[i]?payload[i*32+:32]:decoded[bank*512+i*32+:32];
                    state<=ENC1;
                end
                ENC1:begin
                    for(integer i=0;i<8;i=i+1)encoded_checks[i*8+:8]<=parity64(merged[i*64+:64]);
                    state<=ENC2;
                end
                ENC2:state<=COMMIT;
                COMMIT:begin if(raw_wa!=we || !(|we))sticky_fault<=1;else state<=ACK;end
                ACK:if(|raw_ack)begin
                    if(raw_ack!=(4'b1<<bank) || raw_ack_owner[bank*TAG_W+:TAG_W]!=tag ||
                        raw_ack_addr[bank*15+:15]!=word_addr || raw_ack_mask[bank*16+:16]!=16'hffff)sticky_fault<=1;
                    else state<=POST;
                end
                POST:begin if(!raw_accept)sticky_fault<=1;else begin postcheck<=1;state<=OLD;end end
                VERIFY:begin
                    if(decoded[bank*512+:512]!=merged)sticky_fault<=1;
                    else state<=RELEASE;
                end
                RELEASE:begin
                    wr_ack_v<=4'b1<<bank;wr_ack_owner[bank*TAG_W+:TAG_W]<=tag;
                    wr_ack_word_addr[bank*15+:15]<=word_addr;
                    wr_ack_lane_mask[bank*16+:16]<=mask;state<=IDLE;
                end
                default:sticky_fault<=1;
            endcase
        end
    end
endmodule
