"""Real RTL tile protocol: head tails, commit causality and negative controls."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_head_tiles_require_matching_rtl_commits(tmp_path):
    bench = tmp_path/'tb.sv'
    bench.write_text('''
module tb;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,start=0,br=0,tr=0,commit=0,rel=0;
reg [15:0] ce=7; reg [17:0] cb=1000; reg [8:0] cr=256;
wire bv,tv,arr,done,busy,fault; wire [8:0] rows;
wire [17:0] base; wire [11:0] scale; wire [15:0] ep;
ot_gpu_qwen_row_tiles #(.ENABLE_ROW_TILES(1)) d(
.clk(clk),.rst_n(rst_n),.start(start),.rows_total(18'd2374),
.global_base(18'd1000),.weight_base(32'd4096),.weight_lines(24'd75968),
.epoch(16'd7),.bulk_valid(bv),.bulk_ready(br),.bulk_base(),.bulk_lines(),
.tile_valid(tv),.tile_ready(tr),.tile_rows(rows),.tile_global_base(base),
.tile_scale_base(scale),.tile_epoch(ep),.l2_commit(commit),
.commit_epoch(ce),.commit_base(cb),.commit_rows(cr),
.arrive(arr),.release_in(rel),.done(done),.busy(busy),.fault(fault));
task step; begin @(posedge clk); #1; @(negedge clk); end endtask
integer i,j;
initial begin
step; rst_n=1;start=1;step;start=0;
// Descriptor remains valid while the real backend stalls.
for(j=0;j<5;j=j+1) begin if(!bv || tv || arr) $fatal;step;end
br=1;step;br=0;
for(i=0;i<10;i=i+1) begin
wait(tv); #1;
if(base!=1000+256*i || scale!=256*i || ep!=7 || rows!=(i==9?70:256)) $fatal;
tr=1;step;tr=0;
// Wrong epoch is rejected; it cannot finish a tile or release a barrier.
if(i==0) begin ce=8;commit=1;step;commit=0;ce=7;
if(!fault || tv || arr) $fatal; end
for(j=0;j<3;j=j+1) begin if(tv || arr || bv) $fatal;step;end
cb=base;cr=rows;commit=1;step;commit=0;
end
if(!arr || done) $fatal;
for(j=0;j<4;j=j+1) begin step;if(done || !arr) $fatal;end
rel=1;step;
if(!done || busy || arr) $fatal;
$display("PASS head2374 tiles10 tail70 stalecommit rejected backendwait preserved");
$finish;
end
initial begin #20000;$fatal(1,"timeout");end
endmodule
''')
    exe=tmp_path/'sim.vvp'
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(bench),
                    str(ROOT/'rtl/gpu/ot_gpu_qwen_row_tiles.sv')],check=True,
                   capture_output=True,text=True)
    result=subprocess.run(['vvp',str(exe)],check=True,capture_output=True,
                          text=True,timeout=20)
    assert 'PASS head2374' in result.stdout
