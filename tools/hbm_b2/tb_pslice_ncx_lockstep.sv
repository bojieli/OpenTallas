`timescale 1ns/1ps
// Minimum L-column vehicle: actual SRAM models, every dictionary bank, cycle-exact NCX, phase control.
module tb_pslice_ncx_lockstep;
  parameter integer PHASE_MUT=0;
  logic clk=0, rst_n=0;
  always #0.4165 clk=~clk;
  logic cfg_we=0,cfg_any=0,start=0;
  logic [4:0] cfg_bank=0;
  logic [6:0] cfg_row=0;
  logic [255:0] cfg_data=0;
  logic [15:0] length=0;
  wire [1:0] busy,valid,done,fault;
  wire [15:0] edge_index[2];
  wire [255:0] command[2];
  integer compared=0,commands=0;
  for(genvar n=0;n<2;n=n+1) begin:g
    ot_hbm_su_programme_pgcol #(.DB(13),.EDGES(32),.CFGR(2),.CPIN(1),.RRLY(1),.FADV(2),
      .NCX(n),.PMUT(n==1?PHASE_MUT:0)) u(
      .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_any(cfg_any),.cfg_bank(cfg_bank),
      .cfg_row(cfg_row),.cfg_data(cfg_data),.start(start),.length(length),
      .busy(busy[n]),.valid(valid[n]),.done(done[n]),.fault(fault[n]),
      .edge_index(edge_index[n]),.command(command[n]));
  end
  task automatic tick;
    @(posedge clk); #0.1;
    if(rst_n) begin
      compared=compared+1;
      if({busy[0],valid[0],done[0],fault[0]} !== {busy[1],valid[1],done[1],fault[1]})
        $fatal(1,"PSLICE_NCX FAIL control cycle=%0d ref=%b%b%b%b candidate=%b%b%b%b",compared,
          busy[0],valid[0],done[0],fault[0],busy[1],valid[1],done[1],fault[1]);
      if(valid[0]) begin
        commands=commands+1;
        if({edge_index[0],command[0]} !== {edge_index[1],command[1]})
          $fatal(1,"PSLICE_NCX FAIL data cycle=%0d edge=%0d",compared,edge_index[0]);
      end
    end
    @(negedge clk);
  endtask
  task automatic load_word(input integer b,input integer r,input logic[255:0] d);
    cfg_bank=5'(b); cfg_row=7'(r); cfg_data=d;
    tick(); tick(); cfg_we=1; cfg_any=1; tick(); cfg_we=0;cfg_any=0;tick();tick();
  endtask
  task automatic run_programme(input integer count);
    length=16'(count);start=1;tick();start=0;
    repeat(80) tick();
  endtask
  logic [255:0] word_value;
  initial begin
    repeat(8) tick();rst_n=1;repeat(8) tick();
    for(integer b=1;b<14;b=b+1)
      for(integer r=0;r<128;r=r+1) begin
        word_value={8{32'(b*1000+r)}};load_word(b,r,word_value);
      end
    for(integer r=0;r<2;r=r+1) begin
      for(integer j=0;j<16;j=j+1) word_value[16*j+:16]=16'(((16*r+j)*53)%(13*128));
      load_word(0,r,word_value);
    end
    run_programme(32);run_programme(1);run_programme(17);
    if(commands!=50) $fatal(1,"PSLICE_NCX FAIL missing commands=%0d",commands);
    run_programme(0);run_programme(33);
    if(fault!==2'b11) $fatal(1,"PSLICE_NCX FAIL bounds fault missing");
    $display("PSLICE_NCX PASS compared=%0d commands=%0d added_cycles=0",compared,commands);$finish;
  end
endmodule
