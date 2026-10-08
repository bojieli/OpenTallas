`timescale 1ns/1ps
// Minimum real router/controller boundary: one source-held stage completion.
module wfc_structural_warm_full_case #(parameter integer PIPE=0)(output reg finished=0);
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0,rcfg_we=0,done=0,quiet=0;
    reg [7:0] rcfg_dest=0;
    reg [2:0] rcfg_mask=0;
    integer ip=0,writes=0,starts=0,sends=0,cycles=0;
    integer last_write_edge=-1,start_edge=-1,quiet_edge=-1,take_edge=-1;
    integer root_release_edge=-1,rx_release_edge=-1;
    always @(negedge clk)begin
      if(dut.u_ctrl.rst_q && root_release_edge<0)root_release_edge=cycles;
      if(dut.u_ctrl.rx_enable && rx_release_edge<0)rx_release_edge=cycles;
      if(PIPE && start && dut.u_ctrl.job_done)$fatal(1,"completion consumed on delayed launch edge");
    end
    reg [20:0] next_token=17; reg [31:0] next_val=32'h3f800000;
    wire ready,start,we,valid,last,busy,fault,overflow;
    wire [511:0] data;
    wire [14:0] raddr,waddr;
    wire re;
    reg [511:0] rq=0;
    wire in_valid=rst_n && !rcfg_we && cycles>10 && ip<42;
    wire [511:0] in_data=ip==0 ? (512'd1<<16)|(512'd41<<24)|(512'd97<<32)|(512'd3<<151) : 512'(ip);
    wire out_ready=cycles%7!=0;
    ot_dsrom_wfc_parent_cut #(.MAXU(866),.SOURCE(0),.DECODED_READ(1),.CONTROL_PIPE(PIPE),.QUEUE_SHIFT(PIPE),.HEADER_LOCAL(PIPE),.PREFIX_INC(PIPE)) dut (
      .clk(clk),.rst_n(rst_n),.cfg_users(10'd866),
      .cfg_prompt_len(21'd3),.cfg_gen_len(21'd3),
      .in_valid(in_valid),.in_ready(ready),.in_data(in_data),.in_last(ip==41),
      .out_valid(valid),.out_ready(out_ready),.out_data(data),.out_last(last),
      .core_start(start),.core_done(done),.core_next_token(next_token),.core_next_val(next_val),
      .vm_we(we),.vm_waddr(waddr),.vm_re(re),.vm_raddr(raddr),.vm_rq(rq),
      .pr_q(21'd0),.pr_qk(1'b0),.core_busy(busy),.proto_fault(fault),
      .c8_write_quiet(quiet),.c8_write_quarantine(1'b0),.c8_write_fault(1'b0),.coll_busy(1'b0),
      .bl_rx_valid(1'b0),.bl_rx_last(1'b0),.bl_rx_data(512'd0),.bl_tx_ready(1'b1),
      .rcfg_we(rcfg_we),.rcfg_dest(rcfg_dest),.rcfg_mask(rcfg_mask),.rtr_overflow(overflow));
    always @(posedge clk) begin
      cycles<=cycles+1;
      if(in_valid&&ready)ip<=ip+1;
      if(we) begin
        if(waddr!=writes)$fatal(1,"wrong VM write address");
        writes<=writes+1; if(writes==40)last_write_edge=cycles;
      end
      if(start)begin starts<=starts+1;start_edge=cycles;end
      if(dut.u_ctrl.job_done)take_edge=cycles;
      if(re)rq<=512'(raddr+1000);
      if(valid&&out_ready)begin
        if(sends==0) begin
          if(data[19:16]!=1||data[31:24]!=46||data[39:32]!=97||data[152:151]!=3||last||data[61 +:21]!=17||data[82 +:32]!=32'h3f800000)$fatal(1,"wrong routed HIDDEN header");
        end else if(data!==512'(sends-1+1000)||last!=(sends==46))
          $fatal(1,"wrong routed VM payload sends=%0d data=%h last=%b",sends,data,last);
        sends<=sends+1;
      end
    end
    initial begin
      repeat(5)@(negedge clk);rst_n=1;
      repeat(5)@(negedge clk);
      rcfg_we=1;rcfg_dest=0;rcfg_mask=1;
      @(negedge clk);rcfg_dest=1;rcfg_mask=2;
      @(negedge clk);rcfg_we=0;
      wait(starts==1);@(negedge clk);done=1;
      repeat(12)@(negedge clk);
      if(!busy||sends!=0||writes!=41)$fatal(1,"actual quiet gate failed");
      quiet=1;quiet_edge=cycles;
      if(PIPE)begin
        wait(dut.u_ctrl.g_control_completion.v===1'b1);
        // Drop live producer valid and change payload after the capture edge.
        // The reserved owner must send the captured result exactly once.
        @(negedge clk);done=0;next_token=99;next_val=32'h40000000;
      end
      wait(sends==47);repeat(10)@(negedge clk);
      if(fault||overflow||starts!=1||writes!=41||busy)$fatal(1,"context transfer failed");
      if(rx_release_edge-root_release_edge!=PIPE)$fatal(1,"local RX release calendar mismatch");
      if(start_edge-last_write_edge!=2*PIPE)$fatal(1,"launch calendar mismatch pipe=%0d write=%0d start=%0d",PIPE,last_write_edge,start_edge);
      if(take_edge-quiet_edge!=PIPE)$fatal(1,"completion calendar mismatch pipe=%0d quiet=%0d take=%0d",PIPE,quiet_edge,take_edge);
      $display("CONTROL_PIPE PASS mode=%0d writes=41 starts=1 flits=47 received_launch_delta=%0d completion_delta=%0d reset_release_delta=%0d",PIPE,start_edge-last_write_edge,take_edge-quiet_edge,rx_release_edge-root_release_edge);
      // A warm reset with a captured but unconsumed completion must discard it.
      if(PIPE)begin
        @(negedge clk);rst_n=0;rcfg_we=1;quiet=0;done=0;
        ip=0;writes=0;starts=0;sends=0;next_token=17;next_val=32'h3f800000;
        repeat(3)@(negedge clk);rst_n=1;
        repeat(5)@(negedge clk);rcfg_dest=0;rcfg_mask=1;
        @(negedge clk);rcfg_dest=1;rcfg_mask=2;
        @(negedge clk);rcfg_we=0;
        wait(starts==1);@(negedge clk);done=1;quiet=1;
        wait(dut.u_ctrl.g_control_completion.v===1'b1);
        // Clear while the capture is pending, before its consume edge.
        @(negedge clk);rst_n=0;ip=42;done=0;quiet=0;
        repeat(3)@(negedge clk);rst_n=1;
        repeat(8)@(negedge clk);
        if(dut.u_ctrl.job_done||start||busy||valid||sends!=0)$fatal(1,"warm reset retained pending control debt");
        $display("CONTROL_PIPE_PENDING_RESET PASS captured owner/result cancelled before consume, no publication");
      end
      finished=1;
    end
    initial begin
      repeat(1000)@(negedge clk);$fatal(1,"minimum protocol case did not finish");
    end
endmodule

module tb_wfc_structural_warm_full;
 wire a,b;
 wfc_structural_warm_full_case #(.PIPE(0)) original(a);
 wfc_structural_warm_full_case #(.PIPE(1)) piped(b);
 initial begin wait(a&&b);$display("STRUCTURAL_WARM_FULL MAXU866 user865 PASS both modes exact payload/one-shot/quiet/backpressure/warm reset");$finish;end
endmodule
