"""Object-relative byte bounds must be checked before a mapped burst is valid."""

from pathlib import Path
import random
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
def test_operand_byte_mapper(tmp_path):
    rng = random.Random(90222)
    cases = []
    for shift in range(4):
        for _ in range(25):
            wb = rng.randrange(0, 2**32 - 1024)
            bb = rng.randrange(0, 2**64 - 8192)
            delta = rng.randrange(512)
            words = rng.randrange(1, 257)
            offset = bb + (delta << shift)
            end = offset + (words << shift)
            size = end - rng.choice([0, 0, 1])
            cases.append(
                (wb, bb, size, shift, wb + delta, words, int(end > size), offset)
            )
    cases += [
        (0, 2**64 - 1, 2**64 - 1, 3, 1, 1, 1, 0),
        (100, 0, 1000, 0, 99, 1, 1, 0),
        (0, 0, 2**64 - 1, 3, 2**32 - 1, 2, 1, 0),
        (0, 0, 2**64 - 1, 3, 2**32 - 1, 1, 0, (2**32 - 1) * 8),
        (0, 0, 10000, 0, 0, 0, 1, 0),
        (0, 0, 10000, 0, 0, 257, 1, 0),
    ]
    calls = "\n".join(
        f"check_map(32'd{wb},64'd{bb},64'd{size},2'd{shift},32'd{addr},9'd{words},1'b{bad},64'd{expected});"
        for wb, bb, size, shift, addr, words, bad, expected in cases
    )
    bench = tmp_path / "tb.sv"
    bench.write_text(
        """module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0,request_valid=0,burst_ready=0;
reg [31:0] command_generation=7;
reg [95:0] command_objects=0,command_word_bases=0;
reg [191:0] command_byte_bases=0,command_object_bytes=0;
reg [5:0] command_word_shifts=0;
reg [63:0] request_tag=64'h700000009;
reg [1:0] request_plane=0;
reg [31:0] request_address=0;
reg [8:0] request_words=0;
wire command_ready,request_ready,burst_valid,protocol_error;
wire [63:0] burst_tag,burst_offset;
wire [31:0] burst_object;
wire [11:0] burst_bytes;
wire [8:0] burst_words;
wire [1:0] burst_shift;
ot_a3_operand_byte_mapper dut(.*);
integer checks=0;
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
task check_map(input [31:0] wb,input [63:0] bb,size,input [1:0] shift,input [31:0] addr,input [8:0] words,input bad,input [63:0] expected);
begin
 clear=1;tick();clear=0;tick();
 request_plane=2'(checks%3);
 command_word_bases={3{wb}};command_byte_bases={3{bb}};command_object_bytes={3{size}};
 command_word_shifts={3{shift}};command_objects={32'd92,32'd91,32'd90};command_valid=1;
 #1;if(!command_ready)$fatal(1,"command refused");tick();command_valid=0;
 command_word_bases=0;command_byte_bases=0;command_object_bytes=0;command_word_shifts=0;command_objects=0;
 request_address=addr;request_words=words;request_valid=1;
 #1;if(!request_ready)$fatal(1,"request refused");tick();request_valid=0;
 repeat(8)begin tick();if(bad && burst_valid)$fatal(1,"unsafe byte burst published");end
 if(bad)begin if(!protocol_error)$fatal(1,"missing bound fault");end
 else begin
  repeat(5)begin
   if(!burst_valid || protocol_error || burst_offset!=expected || burst_tag!=request_tag || burst_object!=90+32'(request_plane) || burst_words!=words || burst_shift!=shift || burst_bytes!=(12'(words)<<shift))$fatal(1,"wrong held mapping");tick();
  end
  burst_ready=1;tick();burst_ready=0;
  if(burst_valid)$fatal(1,"duplicate mapping");
 end
 checks=checks+1;
end endtask
initial begin tick();rst_n=1;tick();
CALLS
 // Clear in every pipeline stage, including a stalled valid burst, must
 // hide unreset payload and allow a new command with a different mapping.
 for(integer stage=0;stage<8;stage=stage+1)begin
  clear=1;tick();clear=0;command_valid=1;
  command_objects={3{32'd17}};command_word_bases=0;
  command_byte_bases={3{64'd1024}};command_object_bytes={3{64'd4096}};
  command_word_shifts={3{2'd1}};tick();command_valid=0;
  request_plane=0;request_address=16;request_words=2;request_valid=1;tick();request_valid=0;
  repeat(stage)tick();clear=1;#1;
  if(burst_valid || request_ready || command_ready)$fatal(1,"clear did not suppress publication");
  tick();clear=0;repeat(9)begin tick();if(burst_valid)$fatal(1,"stale payload published after clear");end
  check_map(0,64'd2048,64'd4096,2'd2,32'd2,9'd3,0,64'd2056);
 end
 // Stale generation and invalid plane must fault before publication.
 clear=1;tick();clear=0;command_valid=1;tick();command_valid=0;
 request_valid=1;request_tag=64'h800000000;request_words=1;tick();request_valid=0;
 if(!protocol_error || burst_valid)$fatal(1,"stale generation accepted");
 clear=1;tick();clear=0;command_valid=1;tick();command_valid=0;
 request_valid=1;request_tag=64'h700000000;request_plane=3;tick();request_valid=0;
 if(!protocol_error || burst_valid)$fatal(1,"invalid plane accepted");
 clear=1;tick();clear=0;tick();if(burst_valid || protocol_error)$fatal(1,"clear failed");
 $display("PASS operand byte mapper checks=%0d",checks);$finish;
end
initial begin #1000000;$fatal(1,"timeout");end
endmodule
""".replace("CALLS", calls)
    )
    image = tmp_path / "sim"
    subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb",
            "-o",
            str(image),
            str(ROOT / "rtl/abi3/ot_a3_operand_byte_mapper.sv"),
            str(bench),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        ["vvp", str(image)], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS operand byte mapper checks=114" in result.stdout
