"""Object output mapping, atomic bounds, stalled writes and acknowledgement drain."""
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.skipif(shutil.which('iverilog') is None, reason='iverilog unavailable')
@pytest.mark.parametrize('fp32', [0, 1])
def test_output_object_writer(tmp_path, fp32):
    bench = tmp_path / 'tb.sv'
    bench.write_text(r'''module tb;
parameter bit FP32=0;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0,part_valid=0,write_ready=0,response_valid=0,response_error=0;
wire command_ready,part_ready,write_valid,response_ready,drained,protocol_error;
reg [31:0] command_generation=17,command_object=39,command_element_base=7;
reg [31:0] command_row_stride=41,command_col_stride=2;
reg [15:0] command_rows=2,command_cols=13,command_padded_cols=16;
wire command_fp32=FP32;
reg [63:0] command_object_bytes=4096;
reg [7:0] part_mask=0;
reg [255:0] part_address=0,part_data=0;
wire [31:0] write_generation,write_object;
wire [7:0] write_mask;
wire [511:0] write_offset;
wire [255:0] write_data;
wire write_fp32;
reg [31:0] response_generation=17;
integer requests=0,checks=0;
reg [840:0] held;
ot_a3_output_object_writer #(.OUTSTANDING(1)) dut(.*);
always @(posedge clk)if(write_valid && write_ready)requests<=requests+1;
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
task launch;begin
 clear=1;tick();clear=0;command_valid=1;#1;
 if(!command_ready)$fatal(1,"command blocked");tick();command_valid=0;
end endtask
task beat(input integer row,input integer col);begin
 for(integer i=0;i<8;i=i+1)begin
  part_address[32*i+:32]=command_element_base+row*2+col;
  part_data[32*i+:32]=32'h3f800000+row*100+col*8+i;
 end
 part_mask=col==1?8'h1f:8'hff;
 part_valid=1;#1;if(!part_ready)$fatal(1,"beat blocked");tick();part_valid=0;
end endtask
task check_write(input integer row,input integer col);begin
 wait(write_valid);@(negedge clk);
 if(drained || write_generation!=17 || write_object!=39 || write_mask!=part_mask || write_fp32!=FP32)
  $fatal(1,"write identity/drain");
 for(integer i=0;i<8;i=i+1)if(write_mask[i])begin
  if(write_offset[64*i+:64]!=(7+row*41+(col*8+i)*2)*(FP32?4:2))$fatal(1,"stride/base mapping");
  if(write_data[32*i+:32]!=part_data[32*i+:32])$fatal(1,"data changed");
 end
 held={write_generation,write_object,write_mask,write_offset,write_data,write_fp32};
 repeat(4)begin tick();if(!write_valid || drained || held!={write_generation,write_object,write_mask,write_offset,write_data,write_fp32})$fatal(1,"stalled request changed");end
 write_ready=1;tick();write_ready=0;
 repeat(3)begin tick();if(drained || part_ready || !response_ready || write_valid)$fatal(1,"write retired before ack");end
 response_valid=1;tick();response_valid=0;
 if(!drained || protocol_error)$fatal(1,"ack failed");checks=checks+1;
end endtask
initial begin
 tick();rst_n=1;launch();
 for(integer r=0;r<2;r=r+1)for(integer c=0;c<2;c=c+1)begin beat(r,c);check_write(r,c);end
 // An extra row, malformed lane identity, or padded mask never emits a request.
 beat(2,0);repeat(3)tick();if(!protocol_error || write_valid || requests!=4)$fatal(1,"extra row escaped");checks=checks+1;
 launch();part_valid=1;part_mask=8'hff;part_address=0;tick();part_valid=0;repeat(3)tick();
 if(!protocol_error || write_valid || requests!=4)$fatal(1,"bad identity escaped");checks=checks+1;
 // Bound check is atomic for a whole beat, including a crossing final element.
 command_object_bytes=7*(FP32?4:2)+14*(FP32?4:2)+(FP32?4:2)-1;
 launch();beat(0,0);repeat(3)tick();if(!protocol_error || write_valid || requests!=4)$fatal(1,"partial out-of-bounds write");checks=checks+1;
 // Subtraction underflow must not turn a short object into a large bound.
 command_object_bytes=(FP32?4:2)-1;launch();beat(0,0);repeat(3)tick();
 if(!protocol_error || write_valid || requests!=4)$fatal(1,"short object underflow");checks=checks+1;
 // Exact object end is legal.
 command_object_bytes=7*(FP32?4:2)+14*(FP32?4:2)+(FP32?4:2);
 launch();beat(0,0);check_write(0,0);
 command_object_bytes=4096;launch();beat(0,0);check_write(0,0);
 part_mask=8'hff;for(integer i=0;i<8;i=i+1)part_address[32*i+:32]=8;
 part_valid=1;tick();part_valid=0;repeat(3)tick();if(!protocol_error || write_valid)$fatal(1,"tail mask escaped");checks=checks+1;
 // Wrong-generation ack faults but cannot drain the accepted write.
 launch();beat(0,0);wait(write_valid);@(negedge clk);write_ready=1;tick();write_ready=0;
 response_generation=18;response_valid=1;tick();response_valid=0;
 if(!protocol_error || drained || !response_ready)$fatal(1,"wrong ack drained");
 response_generation=17;response_valid=1;tick();response_valid=0;
 if(!drained)$fatal(1,"matching ack did not drain");checks=checks+1;
 // Bus error retires the acknowledged transaction and faults the operation.
 launch();beat(0,0);wait(write_valid);@(negedge clk);write_ready=1;tick();write_ready=0;
 response_error=1;response_valid=1;tick();response_valid=0;response_error=0;
 if(!protocol_error || !drained)$fatal(1,"write error lost");checks=checks+1;
 // Recovery must replace all captured geometry and identity.
 launch();beat(0,0);check_write(0,0);
 // Maximum unsigned strides exercise the retained upper address bits.
 command_row_stride=32'hffffffff;command_col_stride=32'hffffffff;
 command_object_bytes=64'hffffffffffffffff;launch();beat(0,0);
 wait(write_valid);@(negedge clk);
 for(integer i=0;i<8;i=i+1)
  if(write_offset[64*i+:64]!=(64'd7+64'(i)*64'hffffffff)*(FP32?4:2))$fatal(1,"wide stride truncated");
 write_ready=1;tick();write_ready=0;response_valid=1;tick();response_valid=0;
 if(protocol_error || !drained)$fatal(1,"wide stride ack");checks=checks+1;
 $display("PASS output writer checks=%0d",checks);$finish;
end
initial begin #20000;$fatal(1,"timeout");end
endmodule
''')
    subprocess.run(['iverilog', '-g2012', '-s', 'tb', f'-Ptb.FP32={fp32}',
                    '-o', str(tmp_path/'sim'),
                    str(ROOT/'rtl/abi3/ot_a3_output_object_writer.sv'), str(bench)],
                   check=True, capture_output=True, text=True)
    result = subprocess.run(['vvp', str(tmp_path/'sim')], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PASS output writer checks=15' in result.stdout

@pytest.mark.skipif(shutil.which('iverilog') is None, reason='iverilog unavailable')
@pytest.mark.parametrize('depth', [1, 2, 4, 8])
def test_ordered_write_credits(tmp_path, depth):
    bench = tmp_path / 'credits.sv'
    bench.write_text(r'''module tb;
parameter integer DEPTH=4;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0,part_valid=0,write_ready=1,response_valid=0,response_error=0;
wire command_ready,part_ready,write_valid,response_ready,drained,protocol_error;
wire [31:0] command_generation=19,command_object=3,command_element_base=0;
wire [31:0] command_row_stride=128,command_col_stride=1;
wire [15:0] command_rows=1,command_cols=128,command_padded_cols=128;
wire command_fp32=1;
wire [63:0] command_object_bytes=512;
wire [7:0] part_mask=255;
reg [255:0] part_address=0,part_data=0;
wire [31:0] write_generation,write_object;
wire [7:0] write_mask;wire [511:0] write_offset;wire [255:0] write_data;wire write_fp32;
reg [31:0] response_generation=19;
integer sent=0,acked=0,cycles=0,started,old_sent;
ot_a3_output_object_writer #(.OUTSTANDING(DEPTH)) dut(.*);
always @(posedge clk)begin
 cycles<=cycles+1;
 if(write_valid && write_ready)sent<=sent+1;
 if(response_valid && response_ready && response_generation==19)acked<=acked+1;
end
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
task beat(input integer address);begin
 wait(part_ready);for(integer i=0;i<8;i=i+1)part_address[32*i+:32]=address;
 part_valid=1;tick();part_valid=0;wait(write_valid);tick();
end endtask
initial begin
 tick();rst_n=1;command_valid=1;tick();command_valid=0;
 for(integer i=0;i<DEPTH;i=i+1)beat(i);
 if(sent!=DEPTH || part_ready || drained)$fatal(1,"credit bound");
 repeat(5)begin tick();if(part_ready || drained)$fatal(1,"unacked credit released");end
 // Invalid generation cannot free a slot; valid responses still drain a fault.
 response_generation=20;response_valid=1;tick();response_valid=0;
 if(!protocol_error || drained || dut.pending!=DEPTH)$fatal(1,"wrong ack credit");
 response_generation=19;response_valid=1;
 repeat(DEPTH)tick();response_valid=0;if(!drained)$fatal(1,"fault drain");
 clear=1;tick();clear=0;command_valid=1;tick();command_valid=0;
 // Every new request may be acknowledged on its own acceptance edge.
 response_valid=1;
 for(integer i=0;i<4;i=i+1)beat(i);
 response_valid=0;
 if(!drained || protocol_error || sent!=acked)$fatal(1,"same-edge acknowledgement");
 // A delayed error does not discard any other outstanding writes.
 for(integer i=0;i<DEPTH;i=i+1)beat(i+4);
 response_error=1;response_valid=1;tick();response_error=0;response_valid=0;
 if(!protocol_error || dut.pending!=DEPTH-1)$fatal(1,"error accounting");
 response_valid=1;repeat(DEPTH-1)tick();response_valid=0;
 if(!drained || sent!=acked)$fatal(1,"error drain");
 clear=1;tick();clear=0;command_valid=1;tick();command_valid=0;
 started=cycles;old_sent=sent;response_valid=1;part_valid=1;
 for(integer j=0;j<8;j=j+1)begin
  for(integer k=0;k<8;k=k+1)part_address[32*k+:32]=j;
  #1;while(!part_ready)tick();tick();
 end
 part_valid=0;while(!drained)tick();response_valid=0;
 if(sent-old_sent!=8 || sent!=acked || protocol_error)$fatal(1,"continuous stream lost writes");
 if(DEPTH>1 && cycles-started!=17)$fatal(1,"handoff bubble cycles=%0d",cycles-started);
 $display("stream depth=%0d cycles=%0d",DEPTH,cycles-started);
 if(DEPTH>1)begin
  clear=1;tick();clear=0;command_valid=1;tick();command_valid=0;
  beat(0); // one write waits for its acknowledgement
  for(integer k=0;k<8;k=k+1)part_address[32*k+:32]=1;
  part_valid=1;tick();part_valid=0; // replacement now in CHECK
  old_sent=sent;response_valid=1;response_error=1;tick();response_valid=0;response_error=0;
  if(write_valid || !protocol_error || !drained || sent!=old_sent)$fatal(1,"failed ack published unchecked successor");
 end
 $display("PASS ordered credits depth=%0d",DEPTH);$finish;
end
initial begin #30000;$fatal(1,"timeout");end
endmodule
''')
    subprocess.run(['iverilog', '-g2012', '-s', 'tb', f'-Ptb.DEPTH={depth}',
                    '-o', str(tmp_path/'sim'), str(ROOT/'rtl/abi3/ot_a3_output_object_writer.sv'), str(bench)],
                   check=True, capture_output=True, text=True)
    result = subprocess.run(['vvp', str(tmp_path/'sim')], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PASS ordered credits' in result.stdout
