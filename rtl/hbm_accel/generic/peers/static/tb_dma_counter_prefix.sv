`timescale 1ns/1ps
module tb;
ot_hgi_dma_back_static_vp4_controller dut();

reg [31:0] a,b,c,want,got; integer errors=0,checks=0; integer seed=371749;
task check(input[31:0] x,y,z);begin a=x;b=y;c=z;want=a+b-c;got=dut.add_total_sub_ack(a,b,c);checks=checks+1;if(got!==want)begin errors=errors+1;if(errors<4)$display("BAD a=%h b=%h c=%h got=%h want=%h",a,b,c,got,want);end end endtask
initial begin
for(integer bitnum=0;bitnum<32;bitnum=bitnum+1)begin
check((32'd1<<bitnum)-1,1,0);check(0,32'd1<<bitnum,1);check(32'hffffffff,32'd1<<bitnum,32'hffffffff);check(0,0,32'd1<<bitnum);
end
for(integer i=0;i<32768;i=i+1)check($random(seed),$random(seed),$random(seed));
$display("DMA_PREFIX_EXACT checks=%0d errors=%0d",checks,errors);if(errors)$fatal(1,"prefix arithmetic mismatch");$finish;
end
endmodule
