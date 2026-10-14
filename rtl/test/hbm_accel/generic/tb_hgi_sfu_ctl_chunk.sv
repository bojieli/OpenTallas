`timescale 1ns/1ps
module tb_hgi_sfu_ctl_chunk;
parameter integer MUT_BOUNDARY=0, PIN_CAPTURE=0, WIDTH=75, STATUS_REG=0;
reg clk=0;always #0.416667 clk=~clk;
reg rst_n=0,v=0;reg [2:0] sfu=0;
reg [WIDTH-1:0] d=0;
wire [WIDTH-1:0] hi,lo,expected,actual;
wire hiv,lov,hic,loc,hib,lob,ev,ec,eb;
wire [6:0] sel={sfu==7,sfu==6,sfu==3,sfu==2,sfu==4||sfu==5,sfu==1,sfu==0};
ot_hdc_v41x_ins #(.W(WIDTH),.K(7),.DEPTHS({16'd158,16'd276,16'd35,16'd77,16'd122,16'd94,16'd0}),.DMAX(276)) oracle
 (.clk(clk),.rst_n(rst_n),.v(v),.sel(sel),.d(d),.vo(ev),.q(expected),.coll(ec),.busy(eb));
ot_hgi_sfu_ctl_chunk #(.W(WIDTH),.OFFSET(138),.PIN_CAPTURE(PIN_CAPTURE),.STATUS_REG(STATUS_REG)) high
 (.clk(clk),.rst_n(rst_n),.v(v),.sfu(sfu),.d(d),.tail_d(WIDTH'(0)),.tail_v(1'b0),.q(hi),.vo(hiv),.coll(hic),.busy(hib));
ot_hgi_sfu_ctl_chunk #(.W(WIDTH),.OFFSET(0),.MUT_BOUNDARY(MUT_BOUNDARY),.PIN_CAPTURE(PIN_CAPTURE),.STATUS_REG(STATUS_REG)) low
 (.clk(clk),.rst_n(rst_n),.v(v),.sfu(sfu),.d(d),.tail_d(hi),.tail_v(hiv),.q(lo),.vo(lov),.coll(loc),.busy(lob));
wire now=v&&sfu==0;
assign actual=now?d:lo;
wire av=now||lov;
wire ac=hic||loc||(now&&lov);
reg expected_status_coll=0,expected_status_busy=0;
always @(posedge clk or negedge rst_n)
 if(!rst_n)begin expected_status_coll<=0;expected_status_busy<=0;end
 else begin expected_status_coll<=|oracle.g_line.cl;expected_status_busy<=eb;end
integer checks=0,valid=0,collisions=0,wraps=0;
reg [31:0] lfsr=32'h12345678;
always @(negedge clk)if(rst_n)begin
 if(av!==ev||(!PIN_CAPTURE&&!STATUS_REG&&(ac!==ec||(hib||lob)!==eb))||(ev&&actual!==expected))
  $fatal(1,"CHUNK_MISMATCH cycle%0d sfu%0d valid%0d/%0d",checks,sfu,av,ev);
 if(STATUS_REG&&!PIN_CAPTURE&&(ac!==(expected_status_coll||(now&&lov))||(hib||lob)!==expected_status_busy))
  $fatal(1,"REGISTERED_STATUS_MISMATCH");
 checks++;if(ev)valid++;if(ec)collisions++;
end
initial begin
 repeat(4)@(negedge clk);rst_n=1;
 for(integer run=0;run<3;run++)begin
 for(integer c=0;c<1500;c++)begin
  @(posedge clk);#0.01;
  lfsr={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
  v=lfsr[4:0]<24;sfu=lfsr[8:6];d={11'(c),lfsr,~lfsr};
 end
 v=0;repeat(280)@(negedge clk);
 rst_n=0;repeat(3)@(negedge clk);rst_n=1;
 end
 if(valid<1000||collisions<100)$fatal(1,"INSUFFICIENT_CHUNK_COVERAGE");
 $display("PASS SFU chronological chunks checks=%0d valid=%0d collisions=%0d warm_resets=3 depths0/35/77/94/122/158/276",checks,valid,collisions);$finish;
end
endmodule
