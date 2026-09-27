`timescale 1ns/1ps
// Four HBM stacks through the X_IDX pooled adapter, including query loading
// and vector-memory score writes.  Zero is an exact QDQ4 and BF16 test case.
module tb_hdc_v41x_idx_pool_adapt(input wire clk);
    localparam integer G=4, MP=2, W=16, AW=24, NPC=32;
    reg rst_n=0, go=0;
    integer kd=32;
    initial if (!$value$plusargs("KDIM=%d",kd)) kd=32;
    wire ready, idle, ov, fault;
    wire [G*MP-1:0] x_re,o_we;
    wire [G*MP*AW-1:0] x_addr,o_addr;
    wire [G*MP*W-1:0] o_mask;
    wire [G*MP*W*32-1:0] o_data;
    wire [4*NPC-1:0] req_v,req_rdy,rsp_v,rsp_rdy;
    wire [4*NPC*28-1:0] req_addr;
    wire [4*NPC*4-1:0] req_len,rsp_beat;
    wire [4*NPC*16-1:0] req_tag,rsp_tag;
    wire [4*NPC*256-1:0] rsp_data;
    wire [31:0] dbg_ops,dbg_elems;
    wire [47:0] dbg_keys,dbg_beats,dbg_scored,dbg_sums;
    ot_hdc_v41x_idx_pool_adapt #(.NPC(NPC)) dut (
        .clk(clk),.rst_n(rst_n),.go(go),.ready(ready),.idle(idle),
        .cfg_ik_base(24'd0),.i_nout(16'd32),.i_k(16'(kd)),
        .i_wbase(24'd0),.i_xbase(24'd0),.i_xks(24'd1),.i_xjs(24'd32),.i_xcs(24'd256),
        .i_hg(2'd2),.i_round(1'b0),.i_obase(24'd0),.i_mmode(1'b1),
        .i_oen(1'b1),.i_fuse(1'b1),.i_wts(24'd1024),
        .x_re(x_re),.x_addr(x_addr),.x_q('0),
        .ov(ov),.o_we(o_we),.o_addr(o_addr),.o_mask(o_mask),.o_data(o_data),
        .h_req_v(req_v),.h_req_rdy(req_rdy),.h_req_addr(req_addr),.h_req_len(req_len),
        .h_req_tag(req_tag),.h_rsp_v(rsp_v),.h_rsp_rdy(rsp_rdy),.h_rsp_tag(rsp_tag),
        .h_rsp_beat(rsp_beat),.h_rsp_data(rsp_data),.fault(fault),
        .dbg_ops(dbg_ops),.dbg_elems(dbg_elems),.dbg_keys_streamed(dbg_keys),
        .dbg_hbm_beats(dbg_beats),.dbg_keys_scored(dbg_scored),.dbg_headsums_fused(dbg_sums));
    for(genvar s=0;s<4;s=s+1) begin:g_hbm
        ot_hdc_v41x_idx_hbm #(.NPC(NPC),.AW(28),.LENW(4),.MEM_MODE(0),
            .MEM_WORDS(4096),.CLK_PS(1000),.REQ_PS(1000),.RSP_PS(1000)) hm (
            .clk(clk),.rst_n(rst_n),.req_v(req_v[s*NPC +: NPC]),
            .req_rdy(req_rdy[s*NPC +: NPC]),.req_addr(req_addr[s*NPC*28 +: NPC*28]),
            .req_len(req_len[s*NPC*4 +: NPC*4]),.req_tag(req_tag[s*NPC*16 +: NPC*16]),
            .rsp_v(rsp_v[s*NPC +: NPC]),.rsp_rdy(rsp_rdy[s*NPC +: NPC]),
            .rsp_tag(rsp_tag[s*NPC*16 +: NPC*16]),.rsp_beat(rsp_beat[s*NPC*4 +: NPC*4]),
            .rsp_data(rsp_data[s*NPC*256 +: NPC*256]));
        initial begin
            for(integer i=0;i<4096;i=i+1) hm.mem[i]='0;
            for(integer i=0;i<32;i=i+1) hm.mem[128+2*i][3:0]=4'(i);
        end
    end
    integer cyc=0, checked=0, errors=0, merged=0;
    reg [31:0] seen=0;
    always @(posedge clk) begin
        cyc<=cyc+1;
        if(cyc==4) rst_n<=1;
        if(cyc==8) go<=1;
        if(cyc==9) go<=0;
        if(dut.merge_v && dut.merge_r) begin
            merged=merged+1;
            for(integer q=0;q<4;q=q+1)
                for(integer lane=0;lane<16;lane=lane+1)
                    if(lane<8) begin
                        if(!dut.merge_kv[16*q+lane] ||
                           dut.merge_key[544*(16*q+lane) +: 4]!=4'(q*8+lane)) errors=errors+1;
                    end else if(dut.merge_kv[16*q+lane]) errors=errors+1;
        end
        if(ov) begin
            for(integer p=0;p<G*MP;p=p+1)
                for(integer lane=0;lane<W;lane=lane+1)
                    if(o_we[p] && o_mask[p*W+lane]) begin
                        if(o_addr[p*AW +: AW]>1 ||
                           o_data[(p*W+lane)*32 +: 32]!=0 || seen[lane+16*o_addr[p*AW +: AW]])
                            errors=errors+1;
                        if(lane+16*o_addr[p*AW +: AW]<32)
                            seen[lane+16*o_addr[p*AW +: AW]]=1;
                        checked=checked+1;
                    end
        end
        if(cyc>20 && idle) begin
            if(checked!=32 || dbg_elems!=32 || dbg_keys<32 || merged!=1 || fault || seen!=32'hffff_ffff)
                errors=errors+1;
            $display("V41XPOOLADAPT k=%0d checked=%0d errors=%0d keys=%0d beats=%0d cycles=%0d",kd,checked,errors,dbg_keys,dbg_beats,cyc);
            $finish;
        end
        if(cyc>100000) begin $display("V41XPOOLADAPT TIMEOUT checked=%0d",checked);$finish;end
    end
endmodule
