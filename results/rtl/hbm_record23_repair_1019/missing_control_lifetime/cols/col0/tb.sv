`timescale 1ns/1ps
module tb;
localparam integer B=256, N=53, W=8;
localparam [32*((B+255)/256)-1:0] DB={32'd1};
logic clk=0; always #5 clk=~clk;
logic rst_n=0,cfg_we=0,start=0;
logic [15:0] cfg_bank=0; logic [6:0] cfg_row=0; logic[255:0] cfg_data=0;
wire busy,valid,done,fault; wire[15:0] edge_index; wire[B-1:0] command;
reg[279:0] config_words[0:W-1]; reg[B-1:0] expected_words[0:N-1];
string dir; integer data_mut,addr_mut,phase_mut;
ot_hbm_su_programme #(.LINE_BITS(B),.COLS((B+255)/256),.EDGES(N),.INDEX_PACK(16),.DICT_BANKS(DB),.MACROS(2)) dut(
 .clk(clk),.clk_macro({2{clk}}),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),
 .start(start),.length(16'(N)),.busy(busy),.valid(valid),.done(done),.fault(fault),
 .edge_index(edge_index),.command(command));
task automatic tick; @(posedge clk); #1; endtask
task automatic execute;
 @(negedge clk); start=1; tick(); @(negedge clk); start=0;
 // Three startup edges after start; third presents line zero.
 for(integer k=0;k<2;k=k+1) begin tick(); if(valid) $fatal(1,"SU_PROGRAMME FAIL early"); end
 for(integer e=0;e<N;e=e+1) begin
   tick();
   if(!valid || edge_index!=e || command!==expected_words[(e+phase_mut)%N] || fault || done!=(e==N-1))
     $fatal(1,"SU_PROGRAMME FAIL edge=%0d index=%0d valid=%b done=%b fault=%b",e,edge_index,valid,done,fault);
 end
 tick(); if(valid || busy || done || command!='0) $fatal(1,"SU_PROGRAMME FAIL tail");
endtask
initial begin
 if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR required");
 data_mut=$test$plusargs("MUT_DATA"); addr_mut=$test$plusargs("MUT_ADDR"); phase_mut=$test$plusargs("MUT_PHASE");
 $readmemh({dir,"/config.mem"},config_words); $readmemh({dir,"/expected.mem"},expected_words);
 tick(); @(negedge clk); rst_n=1;
 for(integer i=0;i<W;i=i+1) begin
   cfg_we=1; cfg_bank=config_words[i][279:264]; cfg_row=config_words[i][262:256]; cfg_data=config_words[i][255:0];
   if(data_mut && cfg_bank==1 && cfg_row==0) cfg_data=cfg_data^256'b1;
   if(addr_mut && cfg_bank==0 && cfg_row==0) cfg_data=cfg_data^256'b1;
   tick(); @(negedge clk);
 end
 cfg_we=0; execute(); execute();
 $display("SU_PROGRAMME PASS edges=%0d restart=1",N); $finish;
end
endmodule
