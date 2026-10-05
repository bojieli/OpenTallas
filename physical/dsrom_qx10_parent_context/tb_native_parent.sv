`timescale 1ns/1ps
// Directed integration smoke, not checkpoint arithmetic or campaign coverage.
// Real functional FOUR-ROM views contain zero weights. Existing engine exact
// evidence remains responsible for nonzero arithmetic and random fault modes.
module tb_native_parent;
    reg clk=0;always #0.416666666667 clk=~clk;
    reg rst_n=0,cfg_go=0,go=0,xs_v=0;
    reg [7:0] xs_p=0;
    reg [2:0] xs_b=0,xs_pos=0;
    wire [1629:0] broadcast_source={cfg_go,6'd0,3'd0,go,1'b0,2'd0,xs_v,xs_p,xs_b,
        2'b11,256'd0,10'd100,256'd0,10'd100,xs_pos,3'd0,1'b0,3'd0,4'd0,32'd0,1024'd0};
    wire [10:0] cfg_rom_a;
    reg [47:0] cfg_rom_q;
    // Same descriptor fields as the retained QX exact fixture: eight valid
    // single-word FP8 classes, distinct bank rows, one partial per tree.
    always_comb begin
        cfg_rom_q=0;
        if (cfg_rom_a<8)
            cfg_rom_q=48'(cfg_rom_a+1) | (48'd1<<16) | (48'd1<<21) | (48'd1<<27) | (48'd1<<28);
        else if (cfg_rom_a<16)
            cfg_rom_q=48'd1 | (48'(32*(cfg_rom_a-8))<<1) | (48'd1<<9)
                | (48'(cfg_rom_a-8)<<16) | (48'(cfg_rom_a-8)<<19);
        else if (cfg_rom_a>=17 && cfg_rom_a<25) cfg_rom_q=48'(cfg_rom_a-17+101);
    end
    wire node_v,node_e,busy,fault;
    wire [31:0] node_t,node_d;
    wire [66:0] captured_root;
    ot_v41_qx10_native_parent #(.QX(10)) dut
        (.clk(clk),.rst_n(rst_n),.broadcast_source(broadcast_source),.cfg_rom_q(cfg_rom_q),
         .root_v(1'b1),.root_e(1'b1),.root_row(16'h1234),.root_bf(16'habcd),
         .root_pos(3'd5),.root_fp32(32'h3f800000),.cfg_rom_a(cfg_rom_a),
         .node_v(node_v),.node_e(node_e),.node_t(node_t),.node_d(node_d),
         .busy(busy),.fault(fault),.captured_root(captured_root),.f_bus());
    integer rows=0,seen0=0,seen1=0,beats=0,cycles=0;
    integer row,mask;
    always @(negedge clk) if (rst_n) begin
        cycles=cycles+1;
        if (dut.u_ld.fault!==1'b0) $fatal(1,"PQ0 descriptor fault semantics differ after reset");
        if (node_v) begin
            row=int'(node_t[28:13]);
            if (node_d!==32'd0 || node_e!==1'b0 || node_t[31:29]!=0 || node_t[4:0]!=1)
                $fatal(1,"zero-ROM return payload/identity mismatch row=%0d tag=%h data=%h err=%b",row,node_t,node_d,node_e);
            if (row>=1 && row<=8) begin
                mask=1<<(row-1);if (seen0&mask) $fatal(1,"duplicate bank0 row");seen0=seen0|mask;
            end else if (row>=101 && row<=108) begin
                mask=1<<(row-101);if (seen1&mask) $fatal(1,"duplicate bank1 row");seen1=seen1|mask;
            end else $fatal(1,"unexpected row identity %0d",row);
            rows=rows+1;
        end
    end
    task automatic tick(input integer n);repeat(n) @(negedge clk);endtask
    initial begin
        tick(4);rst_n=1;tick(12);
        if (fault!==0) $fatal(1,"parent fault nonzero after reset");
        if (captured_root!=={1'b1,1'b1,14'h1234,16'habcd,3'd5,32'h3f800000})
            $fatal(1,"separate actual root capture mismatch");
        cfg_go=1;tick(1);cfg_go=0;tick(40);
        if (!dut.u_ld.act || dut.u_ld.ld_busy) $fatal(1,"descriptor/class-valid admission failed");
        go=1;tick(1);go=0;tick(8);
        while (dut.u_qx.u_e.n_run) begin
            xs_p=dut.u_qx.u_e.n_pair;xs_b=dut.u_qx.u_e.n_b;xs_pos=dut.u_qx.u_e.n_pos;
            xs_v=1;tick(1);xs_v=0;tick(16);beats=beats+1;
            if (beats>16) $fatal(1,"source walker did not accept directed native broadcast beats");
        end
        tick(400);
        if (busy || fault || rows!=16 || seen0!=255 || seen1!=255)
            $fatal(1,"native return/drain failed rows=%0d banks=%h/%h busy=%b fault=%b",rows,seen0,seen1,busy,fault);
        // Check only the new sticky parent's capture/retention/reset path.
        // This injection does not qualify the engine's fault producer modes.
        force dut.q_fault=1'b1;tick(2);release dut.q_fault;tick(2);
        if (fault!==1) $fatal(1,"actual parent fault capture/retention failed");
        rst_n=0;tick(4);rst_n=1;tick(12);
        if (fault!==0) $fatal(1,"parent fault failed to clear at real reset");
        $display("PASS QX10_NATIVE_PARENT ZERO_ROM rows=%0d beats=%0d cycles=%0d root_capture=1 PQ0_reset_hold=1 injected_fault_capture=1",rows,beats,cycles);
        $finish;
    end
endmodule
