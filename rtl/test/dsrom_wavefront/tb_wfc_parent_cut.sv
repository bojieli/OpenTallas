`timescale 1ns/1ps
// Minimum real router/controller boundary: one source-held stage completion.
module tb_wfc_parent_cut;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0,rcfg_we=0,done=0,quiet=0;
    reg [7:0] rcfg_dest=0;
    reg [2:0] rcfg_mask=0;
    integer ip=0,writes=0,starts=0,sends=0,cycles=0;
    wire ready,start,we,valid,last,busy,fault,overflow;
    wire [511:0] data;
    wire [14:0] raddr,waddr;
    wire re;
    reg [511:0] rq=0;
    wire in_valid=rst_n && !rcfg_we && cycles>10 && ip<42;
    wire [511:0] in_data=ip==0 ? (512'd1<<16)|(512'd41<<24) : 512'(ip);
    wire out_ready=cycles%7!=0;
    ot_dsrom_wfc_parent_cut #(.MAXU(1),.SOURCE(0),.DECODED_READ(1)) dut (
      .clk(clk),.rst_n(rst_n),.cfg_users(8'd1),
      .cfg_prompt_len(21'd3),.cfg_gen_len(21'd3),
      .in_valid(in_valid),.in_ready(ready),.in_data(in_data),.in_last(ip==41),
      .out_valid(valid),.out_ready(out_ready),.out_data(data),.out_last(last),
      .core_start(start),.core_done(done),.core_next_token(21'd17),.core_next_val(32'h3f800000),
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
        writes<=writes+1;
      end
      if(start)starts<=starts+1;
      if(re)rq<=512'(raddr+1000);
      if(valid&&out_ready)begin
        if(sends==0) begin
          if(data[19:16]!=1||data[31:24]!=46||last)$fatal(1,"wrong routed HIDDEN header");
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
      quiet=1;
      wait(sends==47);repeat(10)@(negedge clk);
      if(fault||overflow||starts!=1||writes!=41||busy)$fatal(1,"context transfer failed");
      $display("PARENT_CUT PASS 41 writes, one start, held completion blocked by actual quiet gate, 47 routed flits exact under stalls");
      $finish;
    end
    initial begin
      repeat(1000)@(negedge clk);$fatal(1,"minimum protocol case did not finish");
    end
endmodule
