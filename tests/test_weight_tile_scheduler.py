"""Scheduler captures a stream and handles independent protocol stalls."""

from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
@pytest.mark.parametrize("tile_size", [1, 32, 512])
def test_weight_scheduler(tmp_path, tile_size):
    bench = tmp_path / "tb.sv"
    bench.write_text(
        """module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,command_valid=0;
reg [31:0] command_generation=7,command_base=100,command_words=1031;
wire command_ready,active,scheduled,command_error;
wire reserve_valid,reserve_bank,fetch_valid,fill_valid,fill_bank,tile_valid,tile_bank;
wire [63:0] reserve_tag,fetch_tag,fill_tag,tile_tag;
wire [9:0] reserve_words,fetch_words,tile_words;
wire [31:0] fetch_address;
wire [127:0] fill_data;
integer ticks=0,reserved=0,fetched=0,filled=0,acquired=0;
integer reserve_tiles=0,acquire_tiles=0;
reg backing=0,inject=0,poison_index=0;
reg [63:0] response_tag=0;reg [9:0] response_index=0,burst_words=0;
wire response_valid=backing && ticks%5!=0;
wire response_ready,response_mismatch;
wire reserve_ready=ticks%7<5;
wire fetch_ready=!backing && ticks%3!=0;
wire fill_ready=ticks%4!=0;
wire tile_ready=ticks%9<5 && acquired+32'(tile_words)<=filled;
ot_a3_weight_tile_scheduler #(.TILE_WORDS(TSIZE)) dut(
.clk(clk),.rst_n(rst_n),.clear(clear),.command_valid(command_valid),.command_ready(command_ready),
.command_generation(command_generation),.command_base(command_base),.command_words(command_words),
.active(active),.scheduled(scheduled),.command_error(command_error),
.reserve_valid(reserve_valid),.reserve_ready(reserve_ready),.reserve_bank(reserve_bank),.reserve_tag(reserve_tag),.reserve_words(reserve_words),
.fetch_valid(fetch_valid),.fetch_ready(fetch_ready),.fetch_tag(fetch_tag),.fetch_address(fetch_address),.fetch_words(fetch_words),
.response_valid(response_valid),.response_ready(response_ready),.response_mismatch(response_mismatch),
.response_tag(inject?response_tag^64'h100000000:response_tag),.response_index(poison_index?response_index+10'd1:response_index),
.response_data(128'(filled)),.fill_valid(fill_valid),.fill_bank(fill_bank),.fill_ready(fill_ready),.fill_tag(fill_tag),.fill_data(fill_data),
.tile_valid(tile_valid),.tile_ready(tile_ready),.tile_bank(tile_bank),.tile_tag(tile_tag),.tile_words(tile_words));
reg held=0;reg [105:0] held_fetch;
always @(posedge clk)begin
 if(rst_n && !clear)begin
  ticks<=ticks+1;
  if(held && (!fetch_valid || {fetch_tag,fetch_address,fetch_words}!==held_fetch))$fatal(1,"stalled burst changed");
  held<=fetch_valid && !fetch_ready;held_fetch<={fetch_tag,fetch_address,fetch_words};
  if(reserve_valid && reserve_ready)begin
   if(reserve_tag!={32'd7,32'(100+reserved)} || reserve_bank!==1'(reserve_tiles%2) || reserve_words!=10'((1031-reserved<TSIZE)?1031-reserved:TSIZE))$fatal(1,"reservation order");
   reserved<=reserved+32'(reserve_words);reserve_tiles<=reserve_tiles+1;
  end
  if(fetch_valid && fetch_ready)begin
   if(fetch_tag!={32'd7,32'(100+fetched)} || fetch_address!=32'(100+fetched) || fetched+32'(fetch_words)>reserved)$fatal(1,"fetch before reserve");
   fetched<=fetched+32'(fetch_words);backing<=1;response_tag<=fetch_tag;response_index<=0;burst_words<=fetch_words;
  end
  if(response_valid && response_ready)begin
   if(!fill_valid || !fill_ready || fill_data!=128'(filled) || fill_tag!=response_tag || fill_bank!==1'((filled/TSIZE)%2))$fatal(1,"fill identity");
   filled<=filled+1;
   if(response_index==burst_words-1'b1)backing<=0;else response_index<=response_index+1'b1;
  end
  if(tile_valid && tile_ready)begin
   if(tile_tag!={32'd7,32'(100+acquired)} || tile_bank!==1'(acquire_tiles%2))$fatal(1,"tile order");
   acquired<=acquired+32'(tile_words);acquire_tiles<=acquire_tiles+1;
  end
 end else held<=0;
end
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
initial begin
 tick();rst_n=1;command_valid=1;tick();command_valid=0;
 command_generation=0;command_base=0;command_words=0;
 wait(backing);@(negedge clk);inject=1;
 repeat(7)begin #1;if(response_valid && (!response_mismatch || response_ready || fill_valid))$fatal(1,"stale response accepted");tick();end
 inject=0;poison_index=1;
 repeat(7)begin #1;if(response_valid && (!response_mismatch || response_ready || fill_valid))$fatal(1,"wrong beat accepted");tick();end
 poison_index=0;
 wait(scheduled);@(negedge clk);
 if(filled!=1031 || acquired!=1031 || fetched!=1031 || active)$fatal(1,"incomplete schedule");
 command_valid=1;command_words=0;tick();command_valid=0;if(!command_error || active)$fatal(1,"zero accepted");
 command_valid=1;command_base=32'hfffffffe;command_words=3;tick();command_valid=0;if(!command_error || active)$fatal(1,"overflow accepted");
 command_valid=1;command_base=100;command_words=3;tick();command_valid=0;clear=1;#1;
 if(reserve_valid || tile_valid || fetch_valid || response_ready)$fatal(1,"clear left credit");tick();clear=0;#1;
 if(active || !command_ready)$fatal(1,"clear left active schedule");
 $display("PASS weight scheduler tile=%0d words=1031",TSIZE);$finish;
end
initial begin #1000000;$fatal(1,"timeout");end
endmodule
""".replace("TSIZE", str(tile_size))
    )
    sim = tmp_path / "sim"
    built = subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb",
            "-o",
            str(sim),
            str(ROOT / "rtl/abi3/ot_a3_weight_tile_scheduler.sv"),
            str(bench),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert built.returncode == 0, built.stderr
    run = subprocess.run(["vvp", str(sim)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "PASS weight scheduler" in run.stdout
