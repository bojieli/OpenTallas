`timescale 1ns/1ps
module tb_hgi_sfu_ctl_chunk;
parameter integer MUT_BOUNDARY=0, PIN_CAPTURE=0, WIDTH=75, STATUS_REG=0, MUT_STALE_STATUS=0;
// c6: C6=1 = low chunk RDK 3 + TAIL_CAPTURE, high chunk RDK 4, both RST_RELAY; the oracle and the depth-0 bypass see the
// same relayed reset (the SFU quarter releases every part on one edge, 3 edges after its port).
parameter integer C6=0, MUT_TAIL_LATE=0;   // MUT_TAIL_LATE: high chunk RDK 3 (not early) under the low chunk's tail pin capture
reg clk=0;always #0.416667 clk=~clk;
reg rst_n=0,v=0;reg [2:0] sfu=0;
reg [WIDTH-1:0] d=0;
wire rr_tb;
generate if(C6)begin:g_rr wire [0:0] o; ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u(.clk(clk),.rst_n_in(rst_n),.rst_n(o)); assign rr_tb=o[0]; end
else begin:g_nrr assign rr_tb=rst_n; end endgenerate
wire [WIDTH-1:0] hi,lo,expected,actual;
wire hiv,lov,hic,loc,hib,lob,ev,ec,eb;
wire [6:0] sel={sfu==7,sfu==6,sfu==3,sfu==2,sfu==4||sfu==5,sfu==1,sfu==0};
ot_hdc_v41x_ins #(.W(WIDTH),.K(7),.DEPTHS({16'd158,16'd276,16'd35,16'd77,16'd122,16'd94,16'd0}),.DMAX(276)) oracle
 (.clk(clk),.rst_n(rr_tb),.v(v),.sel(sel),.d(d),.vo(ev),.q(expected),.coll(ec),.busy(eb));
ot_hgi_sfu_ctl_chunk #(.W(WIDTH),.OFFSET(138),.PIN_CAPTURE(PIN_CAPTURE),.STATUS_REG(STATUS_REG),.MUT_STALE_STATUS(MUT_STALE_STATUS),.RDK(C6?(MUT_TAIL_LATE?3:4):1),.RST_RELAY(C6)) high
 (.clk(clk),.rst_n(rst_n),.v(v),.sfu(sfu),.d(d),.tail_d(WIDTH'(0)),.tail_v(1'b0),.q(hi),.vo(hiv),.coll(hic),.busy(hib));
ot_hgi_sfu_ctl_chunk #(.W(WIDTH),.OFFSET(0),.MUT_BOUNDARY(MUT_BOUNDARY),.PIN_CAPTURE(PIN_CAPTURE),.STATUS_REG(STATUS_REG),.MUT_STALE_STATUS(MUT_STALE_STATUS),.RDK(C6?3:1),.TAIL_CAPTURE(C6),.RST_RELAY(C6)) low
 (.clk(clk),.rst_n(rst_n),.v(v),.sfu(sfu),.d(d),.tail_d(hi),.tail_v(hiv),.q(lo),.vo(lov),.coll(loc),.busy(lob));
wire now=v&&sfu==0&&rr_tb;
assign actual=now?d:lo;
wire av=now||lov;
wire ac=hic||loc||(now&&lov);
reg [3:0] expected_coll=0,expected_busy=0;
always @(posedge clk or negedge rr_tb)
 if(!rr_tb)begin expected_coll<=0;expected_busy<=0;end
 else begin expected_coll<={expected_coll[2:0],|oracle.g_line.cl};expected_busy<={expected_busy[2:0],eb};end
integer checks=0,valid=0,collisions=0,wraps=0;
reg [31:0] lfsr=32'h12345678;
always @(negedge clk)if(rr_tb)begin
 if(av!==ev||(!PIN_CAPTURE&&!STATUS_REG&&(ac!==ec||(hib||lob)!==eb))||(ev&&actual!==expected))
  $fatal(1,"CHUNK_MISMATCH cycle%0d sfu%0d valid%0d/%0d",checks,sfu,av,ev);
 if((STATUS_REG||PIN_CAPTURE)&&(ac!==((STATUS_REG+PIN_CAPTURE ? expected_coll[STATUS_REG+PIN_CAPTURE-1] : (|oracle.g_line.cl))||(now&&lov))||(hib||lob)!==(STATUS_REG ? expected_busy[STATUS_REG-1] : eb)))
  $fatal(1,"REGISTERED_STATUS_MISMATCH cycle%0d coll%0d/%0d busy%0d/%0d",checks,ac,(expected_coll[STATUS_REG+PIN_CAPTURE-1]||(now&&lov)),hib||lob,expected_busy[STATUS_REG-1]);
 checks++;if(ev)valid++;if(ec)collisions++;
end
initial begin
 repeat(4)@(negedge clk);rst_n=1;
 for(integer run=0;run<3;run++)begin
 for(integer c=0;c<1500;c++)begin
  @(posedge clk);#0.01;
  lfsr={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
  v=lfsr[4:0]<24;sfu=lfsr[8:6];d={11'(c),lfsr,~lfsr};
  if(run==2&&c==750)begin #0.1;v=0;rst_n=0;#0.001;rst_n=1;end
 end
 v=0;repeat(280)@(negedge clk);
 rst_n=0;repeat(3)@(negedge clk);rst_n=1;
 end
 if(valid<1000||collisions<100)$fatal(1,"INSUFFICIENT_CHUNK_COVERAGE");
 $display("PASS SFU chronological chunks C6=%0d",C6);$display("PASS SFU chronological chunks checks=%0d valid=%0d collisions=%0d warm_resets=3 active_narrow_async_reset=1 depths0/35/77/94/122/158/276",checks,valid,collisions);$finish;
end
endmodule
