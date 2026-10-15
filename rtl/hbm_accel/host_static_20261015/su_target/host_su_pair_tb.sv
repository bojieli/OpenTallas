`timescale 1ps/1fs
// Two independently installed real targets; clock-phase simulation only.
// Parent host demux and physical CDC/skew qualification remain separate.
module host_su_pair_tb;
localparam integer SN=@SEDGES@,TN=@TEDGES@,SW=@SWRITES@,TW=@TWRITES@,SM=@SMACROS@,TM=@TMACROS@;
localparam integer SDE[0:37]=@SENTRIES@,SDB[0:37]=@SBANKS@;
localparam integer TDE[0:0]=@TENTRIES@,TDB[0:0]=@TBANKS@;
localparam realtime HALF_Q=1250.0/9.0;
reg serial_clk=0,stream_clk=0,rst_n=0;
integer half_tick=-1,epoch_half=-1,serial_seen=0,stream_seen=0;
initial forever begin #(HALF_Q);half_tick=half_tick+1;serial_clk=(half_tick%8)<4;stream_clk=(half_tick%6)<3;end
reg scfg=0,tcfg=0,svalidate=0,tvalidate=0,slaunch=0,tlaunch=0;
reg[15:0] sbank=0,tbank=0;reg[6:0] srow=0,trow=0;reg[255:0] sdata=0,tdata=0;
wire sready,tready,sbusy,tbusy,svalid,tvalid,sdone,tdone,sfault,tfault,saccept,taccept;
wire[15:0] sedge,tedge;wire[9687:0] scommand;wire[63:0] tcommand;
reg[279:0] sconfig[0:SW-1],tconfig[0:TW-1];reg[9687:0] sexpected[0:SN-1];reg[63:0] texpected[0:TN-1];
string dir;integer epoch_mut;
host_su_target #(.LINE_BITS(9688),.EDGES(SN),.COLS(38),.DICT_ENTRIES(SDE),.DICT_BANKS(SDB),.MACROS(SM)) serial_target(
 .clk(serial_clk),.rst_n(rst_n),.clk_macro({SM{serial_clk}}),.cfg_v(scfg),.cfg_bank(sbank),.cfg_row(srow),.cfg_data(sdata),.cfg_ready(),.cfg_accept(saccept),
 .validate_v(svalidate),.launch_v(slaunch),.length(16'(SN)),.block_ready(sready),.busy(sbusy),.valid(svalid),.done(sdone),.fault(sfault),.edge_index(sedge),.command(scommand));
host_su_target #(.LINE_BITS(64),.EDGES(TN),.COLS(1),.DICT_ENTRIES(TDE),.DICT_BANKS(TDB),.MACROS(TM)) stream_target(
 .clk(stream_clk),.rst_n(rst_n),.clk_macro({TM{stream_clk}}),.cfg_v(tcfg),.cfg_bank(tbank),.cfg_row(trow),.cfg_data(tdata),.cfg_ready(),.cfg_accept(taccept),
 .validate_v(tvalidate),.launch_v(tlaunch),.length(16'(TN)),.block_ready(tready),.busy(tbusy),.valid(tvalid),.done(tdone),.fault(tfault),.edge_index(tedge),.command(tcommand));
task automatic serial_install;
 for(integer i=0;i<SW;i=i+1)begin
  @(negedge serial_clk);scfg=1;sbank=sconfig[i][279:264];srow=sconfig[i][262:256];sdata=sconfig[i][255:0];
  #0.001;if(!saccept)$fatal(1,"HOST_SU_PAIR serial install refusal");@(posedge serial_clk);#0.001;
 end
 @(negedge serial_clk);scfg=0;repeat(2)begin @(posedge serial_clk);#0.001;end
 @(negedge serial_clk);svalidate=1;@(posedge serial_clk);#0.001;@(negedge serial_clk);svalidate=0;
 for(integer i=0;i<SW+2;i=i+1)begin @(posedge serial_clk);#0.001;if(sready||sfault)break;end
 if(!sready||sfault)$fatal(1,"HOST_SU_PAIR serial not ready");
endtask
task automatic stream_install;
 for(integer i=0;i<TW;i=i+1)begin
  @(negedge stream_clk);tcfg=1;tbank=tconfig[i][279:264];trow=tconfig[i][262:256];tdata=tconfig[i][255:0];
  #0.001;if(!taccept)$fatal(1,"HOST_SU_PAIR stream install refusal");@(posedge stream_clk);#0.001;
 end
 @(negedge stream_clk);tcfg=0;repeat(2)begin @(posedge stream_clk);#0.001;end
 @(negedge stream_clk);tvalidate=1;@(posedge stream_clk);#0.001;@(negedge stream_clk);tvalidate=0;
 for(integer i=0;i<TW+2;i=i+1)begin @(posedge stream_clk);#0.001;if(tready||tfault)break;end
 if(!tready||tfault)$fatal(1,"HOST_SU_PAIR stream not ready");
endtask
always @(posedge serial_clk)if(rst_n&&epoch_half>=0&&half_tick>=epoch_half)begin
 integer n;n=(half_tick-epoch_half)/8;
 if((half_tick-epoch_half)%8!=0)$fatal(1,"HOST_SU_PAIR serial phase");
 if(n<SN)begin
  if(!svalid||sedge!=n||scommand!==sexpected[n]||sdone!=(n==SN-1)||sfault)$fatal(1,"HOST_SU_PAIR serial exact/epoch edge=%0d",n);
  serial_seen=serial_seen+1;
 end else if(svalid||sbusy||sfault)$fatal(1,"HOST_SU_PAIR serial tail");
end
always @(posedge stream_clk)if(rst_n&&epoch_half>=0&&half_tick>=epoch_half)begin
 integer n;n=(half_tick-epoch_half)/6;
 if((half_tick-epoch_half)%6!=0)$fatal(1,"HOST_SU_PAIR stream phase");
 if(n<TN)begin
  if(!tvalid||tedge!=n||tcommand!==texpected[n]||tdone!=(n==TN-1)||tfault)$fatal(1,"HOST_SU_PAIR stream exact/epoch edge=%0d",n);
  stream_seen=stream_seen+1;
 end else if(tvalid||tbusy||tfault)$fatal(1,"HOST_SU_PAIR stream tail");
end
initial begin
 if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR required");epoch_mut=$test$plusargs("MUT_EPOCH");
 $readmemh({dir,"/serial/config.mem"},sconfig);$readmemh({dir,"/stream/config.mem"},tconfig);
 $readmemh({dir,"/serial/expected.mem"},sexpected);$readmemh({dir,"/stream/expected.mem"},texpected);
 repeat(4)@(negedge serial_clk);rst_n=1;
 fork serial_install();stream_install();join
 epoch_half=24*((half_tick+95)/24);
 wait(half_tick==epoch_half-33);slaunch=1;wait(half_tick==epoch_half-31);slaunch=0;
 wait(half_tick==epoch_half-25+6*epoch_mut);tlaunch=1;wait(half_tick==epoch_half-23+6*epoch_mut);tlaunch=0;
 wait(half_tick>=epoch_half+8*(SN+4));#0.002;
 if(serial_seen!=SN||stream_seen!=TN)$fatal(1,"HOST_SU_PAIR counts");
 $display("HOST_SU_PAIR_PASS serial_edges=%0d stream_edges=%0d macros=%0d clocks_MHz=900,1200 consumer_epoch=%0d physical_phase_unproven=1",serial_seen,stream_seen,SM+TM,epoch_half);$finish;
end
endmodule
