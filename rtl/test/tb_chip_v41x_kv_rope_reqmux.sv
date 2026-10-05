`timescale 1ns/1ps
module tb_chip_v41x_kv_rope_reqmux;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0;
    reg [3:0] w_v=0,c_v=0,p_v=0,m_rdy=4'hf,s_v=0;
    wire [3:0] w_rdy,c_rdy,p_rdy,w_sv,c_sv,p_sv,m_v,s_rdy;
    reg [63:0] w_tag=0,c_tag=0,p_tag=0,s_tag=0;
    wire [63:0] m_tag,w_stag,c_stag,p_stag;
    reg [1023:0] s_data=0;
    wire [1023:0] w_sdata,c_sdata,p_sdata;
    wire [31:0] rope_grants,rope_wait_cycles;
    wire fault;
    integer grants=0;
    reg [1:0] owners [0:2];

    ot_chip_v41x_kv_rope_reqmux dut (
        .clk(clk),.rst_n(rst_n),
        .w_v(w_v),.w_rdy(w_rdy),.w_addr(120'(101)),.w_len(16'(1)),.w_tag(w_tag),
        .w_we(4'b0),.w_wdata('0),.w_wstrb('0),.w_wr_done(),
        .w_sv(w_sv),.w_srdy(4'hf),.w_stag(w_stag),.w_sbeat(),.w_sdata(w_sdata),
        .c_v(c_v),.c_rdy(c_rdy),.c_addr(120'(202)),.c_len(16'(1)),.c_tag(c_tag),
        .c_we(4'b0),.c_wdata('0),.c_wstrb('0),.c_wr_done(),
        .c_sv(c_sv),.c_srdy(4'hf),.c_stag(c_stag),.c_sbeat(),.c_sdata(c_sdata),
        .p_v(p_v),.p_rdy(p_rdy),.p_addr(120'(303)),.p_len(16'(1)),.p_tag(p_tag),
        .p_we(4'b0),.p_wdata('0),.p_wstrb('0),.p_wr_done(),
        .p_sv(p_sv),.p_srdy(4'hf),.p_stag(p_stag),.p_sbeat(),.p_sdata(p_sdata),
        .m_v(m_v),.m_rdy(m_rdy),.m_addr(),.m_len(),.m_tag(m_tag),
        .m_we(),.m_wdata(),.m_wstrb(),.m_wr_done(4'b0),
        .s_v(s_v),.s_rdy(s_rdy),.s_tag(s_tag),.s_beat(16'b0),.s_data(s_data),
        .fault(fault),.rope_grants(rope_grants),.rope_wait_cycles(rope_wait_cycles));

    always @(posedge clk) if(rst_n && m_v[0] && m_rdy[0]) begin
        if(grants>2) $fatal(1,"too many grants");
        owners[grants] <= m_tag[15:14];
        grants <= grants+1;
        if(w_rdy[0]) w_v[0]<=0;
        if(c_rdy[0]) c_v[0]<=0;
        if(p_rdy[0]) p_v[0]<=0;
    end
    initial begin
        repeat(3) @(negedge clk); rst_n=1;
        w_v=1;c_v=1;p_v=1; w_tag=16'd0;c_tag=16'd1;p_tag=16'd2;
        wait(grants==3);
        @(negedge clk);
        if(owners[0]!=0 || owners[1]!=2 || owners[2]!=1 || rope_grants!=1 || rope_wait_cycles==0)
            $fatal(1,"arbitration/order: %0d %0d %0d g=%0d wait=%0d",
                   owners[0],owners[1],owners[2],rope_grants,rope_wait_cycles);
        s_v=1;s_tag=16'h8002;s_data=1024'(256'habc);
        #1; if(!p_sv[0] || w_sv[0] || c_sv[0] || p_stag[15:0]!=16'd2 || p_sdata[255:0]!=256'habc)
            $fatal(1,"RoPE response misrouted");
        @(negedge clk);s_tag=16'h4001;s_data=1024'(256'hdef);
        #1; if(!c_sv[0] || w_sv[0] || p_sv[0] || c_stag[15:0]!=16'd1 || c_sdata[255:0]!=256'hdef)
            $fatal(1,"CKV response misrouted");
        @(negedge clk);s_tag=16'h0000;s_data=1024'(256'h123);
        #1; if(!w_sv[0] || c_sv[0] || p_sv[0] || w_stag[15:0]!=0 || w_sdata[255:0]!=256'h123)
            $fatal(1,"window response misrouted");
        @(negedge clk);s_v=0;p_v=1;p_tag=16'h4000;
        #1; if(m_v[0] || p_rdy[0]) $fatal(1,"invalid child tag not blocked");
        @(posedge clk);#1;if(!fault) $fatal(1,"invalid child tag did not fault");
        $display("KV_ROPE_MUX_PASS grants=%0d rope_grants=%0d wait=%0d",grants,rope_grants,rope_wait_cycles);
        $finish;
    end
    initial begin #5000;$fatal(1,"KV/RoPE mux timeout");end
endmodule
