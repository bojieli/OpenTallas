`timescale 1ns/1ps
module tb_loader_service_burst;
parameter BURST=1,NATIVE_ENABLE=1;reg clk=0,rst_n=0;always #5 clk=~clk;
reg [31:0] normal_pending_write=0;
reg [31:0] normal_v=0;
wire [31:0] normal_rdy;
reg [31:0] normal_we=0;
reg [959:0] normal_addr=0;
reg [127:0] normal_len=0;
reg [543:0] normal_tag=0;
reg [8191:0] normal_wdata=0;
reg [1023:0] normal_wstrb=0;
wire [31:0] normal_rsp_v;
reg [31:0] normal_rsp_rdy=0;
wire [543:0] normal_rsp_tag;
wire [127:0] normal_rsp_beat;
wire [8191:0] normal_rsp_data;
reg native_v=0;
wire native_rdy;
reg [4:0] native_pc=0;
reg [29:0] native_addr=0;
reg [15:0] native_tag=0;
reg [3:0] native_len=0;
wire native_rsp_v;
reg native_rsp_rdy=0;
wire [4:0] native_rsp_pc;
wire [15:0] native_rsp_tag;
wire [3:0] native_rsp_beat;
wire [255:0] native_rsp_data;
wire [31:0] k_v;
reg [31:0] k_rdy=0;
wire [31:0] k_we;
wire [959:0] k_addr;
wire [127:0] k_len;
wire [543:0] k_tag;
wire [8191:0] k_wdata;
wire [1023:0] k_wstrb;
reg [31:0] kr_v=0;
wire [31:0] kr_rdy;
reg [543:0] kr_tag=0;
reg [127:0] kr_beat=0;
reg [8191:0] kr_data=0;
reg [31:0] k_wr_done=0;
wire [31:0] native_busy;
wire fault;
ot_hbm_loader_service_boundary #(.ENABLE(NATIVE_ENABLE),.ENABLE_NATIVE_BURST(BURST)) dut(.*);

integer p,n,b,j,mode,received,expected_len,expected_pc,pc_case;
integer cycles=0,first_cycle,last_cycle,start_cycle,end_cycle,commands, sectors;
always @(posedge clk)cycles<=cycles+1;
reg[15:0]expected_tag;reg[255:0]held_data;reg[3:0]held_beat;
function automatic [255:0] pat(input integer pc,beat);pat={8{32'h91234000 ^ (pc<<8) ^ beat}};endfunction
always @(posedge clk) if(rst_n&&native_rsp_v&&native_rsp_rdy)begin
 if(native_rsp_pc!==expected_pc||native_rsp_tag!==expected_tag||native_rsp_beat!==received||native_rsp_data!==pat(expected_pc,received))$fatal(1,"response identity/data mismatch at beat %0d",received);
 if(received>=expected_len)$fatal(1,"duplicate native response");
 if(received==0)first_cycle=cycles;last_cycle=cycles;
 received=received+1;
end
initial begin #200000;$fatal(1,"bounded bench progress exhausted");end
initial begin
 mode=0;j=$value$plusargs("mode=%d",mode);received=0;expected_len=0;expected_pc=0;expected_tag=0;
 repeat(3)@(negedge clk);rst_n=1;k_rdy='1;normal_rsp_rdy='1;
 if(NATIVE_ENABLE==0)begin
 normal_v='1;normal_we='1;normal_addr='1;normal_len='1;normal_tag='1;normal_wdata='1;normal_wstrb='1;
 kr_v='1;kr_tag='1;kr_beat='1;kr_data='1;native_v=1;
 #1;
 if(k_v!==normal_v||normal_rdy!==k_rdy||k_we!==normal_we||k_addr!==normal_addr||k_len!==normal_len||k_tag!==normal_tag||k_wdata!==normal_wdata||k_wstrb!==normal_wstrb||normal_rsp_v!==kr_v||kr_rdy!==normal_rsp_rdy||normal_rsp_tag!==kr_tag||normal_rsp_beat!==kr_beat||normal_rsp_data!==kr_data||native_rdy!==0||native_rsp_v!==0||native_busy!==0||fault!==0)$fatal(1,"disabled passthrough changed");
 $display("PASS disabled native passthrough");$finish;
 end
 // An accepted normal three-beat read must drain before native admission.
 @(negedge clk);normal_v[7]=1;normal_len[7*4+:4]=3;normal_tag[7*17+:17]=17'h123;
 @(negedge clk);normal_v=0;native_v=1;native_pc=7;native_len=BURST?8:0;
 #1;if(native_rdy)$fatal(1,"native stole normal read debt");
 for(b=0;b<3;b=b+1)begin
 kr_v[7]=1;kr_tag[7*17+:17]=17'h123;kr_beat[7*4+:4]=b;
 #1;if(native_rdy||!normal_rsp_v[7]||!kr_rdy[7])$fatal(1,"normal read debt isolation failed");
 @(negedge clk);
 end
 kr_v=0;native_v=0;
 // Actual pending/accepted writes also retain priority.
 normal_pending_write[7]=1;#1;if(native_rdy)$fatal(1,"pending write was bypassed");
 normal_pending_write=0;normal_v[7]=1;normal_we[7]=1;
 @(negedge clk);normal_v=0;normal_we=0;#1;if(native_rdy)$fatal(1,"accepted write debt bypassed");
 k_wr_done[7]=1;@(negedge clk);k_wr_done=0;
 if(BURST)begin
 native_len=0;#1;if(native_rdy)$fatal(1,"zero length accepted");
 native_len=9;#1;if(native_rdy)$fatal(1,"oversize length accepted");
 end
 for(pc_case=0;pc_case<32;pc_case=pc_case+1)
 for(n=1;n<=(BURST?8:1);n=n+1)begin
 @(negedge clk);p=pc_case;native_pc=p;native_len=BURST?n:0;native_addr=30'h123000+n;native_tag=16'h7000+n;native_v=1;
 expected_len=n;expected_pc=p;expected_tag=native_tag;received=0;
 #1;if(!native_rdy)$fatal(1,"valid native request not admitted");
 @(negedge clk);native_v=0;#1;
 if(!k_v[p]||k_we[p]||k_len[p*4+:4]!==n||k_addr[p*30+:30]!==native_addr||k_tag[p*17+:17]!=={1'b1,native_tag})$fatal(1,"native command burst metadata mismatch");
 @(negedge clk);
 for(b=0;b<n;b=b+1)begin
 kr_v[p]=1;kr_tag[p*17+:17]={1'b1,native_tag};kr_beat[p*4+:4]=b;kr_data[p*256+:256]=pat(p,b);
 if(mode==1&&b==0)kr_tag[p*17+:17]=17'h1;
 if(mode==2&&b==0)kr_beat[p*4+:4]=n;
 if(mode==3&&b==1)kr_beat[p*4+:4]=0;
 native_rsp_rdy=0;
 #1;
 if(mode!=0&&(b==0&&mode!=3||b==1&&mode==3))begin
 @(negedge clk);if(!fault||kr_rdy[p]||native_rsp_v)$fatal(1,"malformed beat did not fault closed");
 $display("PASS malformed mode %0d",mode);$finish;
 end
 // First beat fills the single elastic register; hold it under backpressure.
 while(!kr_rdy[p])@(negedge clk);
 @(negedge clk);kr_v=0;
 if(!native_rsp_v)$fatal(1,"missing buffered reply");
 held_data=native_rsp_data;held_beat=native_rsp_beat;
 repeat(2)begin
 normal_v[p]=1;normal_len[p*4+:4]=1;#1;
 if(native_rdy||normal_rdy[p]||!native_busy[p]||native_rsp_data!==held_data||native_rsp_beat!==held_beat)$fatal(1,"lease/backpressure stability failed");
 @(negedge clk);
 end
 normal_v=0;native_rsp_rdy=1;
 @(negedge clk);native_rsp_rdy=0;
 if(b<n-1&&!native_busy[p])$fatal(1,"lease released before final beat");
 end
 if(received!=n||native_busy[p]||fault)$fatal(1,"burst terminal accounting failed");
 end
 if(mode!=0)$fatal(1,"malformed case never exercised");
 // Elastic buffer must block the next offered beat while its consumer stalls.
 if(BURST)begin
 @(negedge clk);native_pc=31;native_len=2;native_tag=16'h8888;native_addr=1;native_v=1;native_rsp_rdy=0;
 expected_len=2;expected_pc=31;expected_tag=native_tag;received=0;
 @(negedge clk);native_v=0;@(negedge clk);
 kr_v[31]=1;kr_tag[31*17+:17]={1'b1,native_tag};kr_beat[31*4+:4]=0;kr_data[31*256+:256]=pat(31,0);
 @(negedge clk);kr_beat[31*4+:4]=1;kr_data[31*256+:256]=pat(31,1);
 repeat(3)begin
 #1;if(kr_rdy[31]||!native_rsp_v||native_rsp_beat!==0||native_rsp_data!==pat(31,0))$fatal(1,"elastic register overwrote stalled response");
 @(negedge clk);
 end
 native_rsp_rdy=1;#1;if(!kr_rdy[31])$fatal(1,"elastic register failed simultaneous pop/push");
 @(negedge clk);kr_v=0;@(negedge clk);
 if(received!=2||native_busy[31]||fault)$fatal(1,"elastic transfer failed");
 end
 // Saturated unthrottled minimum vehicle: exactly 256 sectors.
 sectors=0;commands=0;start_cycle=cycles;
 while(sectors<256)begin
 n=BURST?8:1;
 native_pc=31;native_len=BURST?n:0;native_tag=16'h9000+commands;native_addr=sectors;native_v=1;native_rsp_rdy=1;
 expected_len=n;expected_pc=31;expected_tag=native_tag;received=0;
 #1;if(!native_rdy)$fatal(1,"stream command not ready");
 @(negedge clk);native_v=0;
 @(negedge clk);
 for(b=0;b<n;b=b+1)begin
 kr_v[31]=1;kr_tag[31*17+:17]={1'b1,native_tag};kr_beat[31*4+:4]=b;kr_data[31*256+:256]=pat(31,b);
 #1;if(!kr_rdy[31])$fatal(1,"stream throughput bubble at beat %0d",b);
 @(negedge clk);
 end
 kr_v=0;@(negedge clk);
 if(received!=n||native_busy[31]||fault||last_cycle-first_cycle!=n-1)$fatal(1,"continuous burst throughput/accounting failed received=%0d n=%0d busy=%b fault=%b span=%0d",received,n,native_busy[31],fault,last_cycle-first_cycle);
 sectors=sectors+n;commands=commands+1;
 end
 end_cycle=cycles;
 $display("MEASURE sectors=%0d commands=%0d cycles=%0d bytes=%0d last_burst_beat_span=%0d",sectors,commands,end_cycle-start_cycle,sectors*32,last_cycle-first_cycle);
 $display("PASS native burst=%0d lengths 1..%0d all32 PCs normal read/write debt and stalls",BURST,BURST?8:1);$finish;
end
endmodule
