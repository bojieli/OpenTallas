module tb_status_copy;
    timeunit 1ps; timeprecision 1fs;
    logic fclk=0, clk=0, t_rst_n=0, r_rst_n=0;
    logic [63:0] data=64'h123456789abcdef1;
    integer phase=0;
    integer checks=0;
    always #416.5 fclk=~fclk;
    initial begin
        void'($value$plusargs("PHASE=%d",phase));
        #(phase);
        forever #416.5 clk=~clk;
    end
    always @(negedge fclk) data <= {data[62:0],data[63]^data[62]^data[60]^data[59]};
    for(genvar g=0;g<2;g++) begin: depth_cases
        localparam integer D=4<<g;
        localparam integer KW=$clog2(D)+4;
        wire [KW-1:0] k=KW'(2);
        wire [63:0] q_gold,q_copy;
        wire [3:0] flags_gold,flags_copy;
        integer clean_gold=0;
        ot_meso_ring_ca #(.W(64),.DEPTH(D),.GUARD_HI(D),.CONTROL_STATUS_COPY(0)) u_gold (
            .tclk(fclk),.t_rst_n(t_rst_n),.t_d(data),.rclk(clk),.r_rst_n(r_rst_n),.k_s(k),
            .r_d(q_gold),.r_v(flags_gold[0]),.r_lap_ok(flags_gold[1]),
            .r_glo_ok(flags_gold[2]),.r_ghi_ok(flags_gold[3]));
        ot_meso_ring_ca #(.W(64),.DEPTH(D),.GUARD_HI(D),.CONTROL_STATUS_COPY(1)) u_copy (
            .tclk(fclk),.t_rst_n(t_rst_n),.t_d(data),.rclk(clk),.r_rst_n(r_rst_n),.k_s(k),
            .r_d(q_copy),.r_v(flags_copy[0]),.r_lap_ok(flags_copy[1]),
            .r_glo_ok(flags_copy[2]),.r_ghi_ok(flags_copy[3]));
        always @(posedge clk) begin
            #1;
            if(r_rst_n && flags_gold==4'hf) clean_gold=clean_gold+1;
            if(r_rst_n && ((q_gold !== q_copy) || (flags_gold !== flags_copy))) begin
                $display("STATUS_COPY_MISMATCH depth=%0d phase=%0d checks=%0d flags=%h/%h q=%h/%h",D,phase,checks,flags_gold,flags_copy,q_gold,q_copy);
                $fatal(1,"status copy lockstep differs");
            end
        end
        final $display("STATUS_COPY_CLEAN depth=%0d phase=%0d words=%0d",D,phase,clean_gold);
    end
    always @(posedge clk) if(r_rst_n) checks<=checks+1;
    initial begin
        for(integer epoch=0;epoch<4;epoch++) begin
            @(negedge fclk);t_rst_n=0;
            @(negedge clk);r_rst_n=0;
            repeat(12) @(negedge fclk);
            t_rst_n=1;
            repeat(1) @(negedge clk);
            r_rst_n=1;
            repeat(512) @(negedge clk);
        end
        $display("STATUS_COPY_PASS phase=%0d checks=%0d depths=4,8 added_cycles=0",phase,checks);
        $finish;
    end
endmodule
