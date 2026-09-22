"""Future address walk compared with direct tensor/scale indexing under stalls."""

from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
@pytest.mark.parametrize("interleave", [1, 3, 5])
@pytest.mark.parametrize("scale_group,scale_base", [(0, 300), (1, 300), (4, 300), (4, 0xFFFFFFFC)])
def test_future_cursor(tmp_path, interleave, scale_group, scale_base):
    rows, cols, depth = 5, 7, 12
    scale_stride = depth // scale_group if scale_group else 0
    expected = []
    for row in range(rows):
        for base_col in range(0, cols, interleave):
            for k in range(depth):
                for col in range(base_col, min(base_col + interleave, cols)):
                    expected.append(
                        (
                            100 + row * depth + k,
                            200 + (row // 2) * 4 + k // 3,
                            (scale_base + col * scale_stride + (k // scale_group if scale_group else 0)) & 0xFFFFFFFF,
                            400 + len(expected),
                        )
                    )
    image = tmp_path / "expected.hex"
    image.write_text(
        "".join(f"{a:08x}{s:08x}{ws:08x}{w:08x}\n" for a, s, ws, w in expected)
    )
    bench = tmp_path / "tb.sv"
    bench.write_text(f'''
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,start=0;
integer ticks=0,seen=0;
wire request_valid,active,invalid_geometry,last;
wire request_ready=ticks%7<4;
wire [31:0] generation,a_address,s_address,ws_address,w_address;
reg [127:0] expected[0:{len(expected) - 1}];
reg held=0;reg [127:0] held_address;
reg [31:0] cfg_a_base=100;
ot_a3_lq8_operand_cursor #(.INTERLEAVE({interleave})) dut(
.clk(clk),.rst_n(rst_n),.clear(clear),.start(start),.cfg_generation(32'd9),
.cfg_rows(16'd5),.cfg_local_cols(16'd7),.cfg_depth_words(16'd12),
.cfg_rows_per_scale_a(16'd2),.cfg_scale_stride_a(16'd4),.cfg_scale_stride_b(16'd{scale_stride}),
.cfg_groups_per_scale_a(16'd3),.cfg_groups_per_scale_b(16'd{scale_group}),
.cfg_a_base(cfg_a_base),.cfg_s_base(32'd200),.cfg_ws_base(32'd{scale_base}),.cfg_w_base(32'd400),
.request_valid(request_valid),.request_ready(request_ready),.generation(generation),
.a_address(a_address),.s_address(s_address),.ws_address(ws_address),.w_address(w_address),
.last(last),.active(active),.invalid_geometry(invalid_geometry));
always @(posedge clk)begin
 if(rst_n && !clear)begin
  ticks<=ticks+1;
  if(held && (!request_valid || {{a_address,s_address,ws_address,w_address}}!==held_address))$fatal(1,"stalled cursor changed");
  held<=request_valid && !request_ready;held_address<={{a_address,s_address,ws_address,w_address}};
  if(request_valid && request_ready)begin
   if(generation!=9 || {{a_address,s_address,ws_address,w_address}}!==expected[seen] || last!==(seen=={len(expected) - 1}))$fatal(1,"address index %0d",seen);
   seen<=seen+1;
  end
 end else held<=0;
end
initial begin
 $readmemh("{image}",expected);
 @(negedge clk);rst_n=1;start=1;
 @(negedge clk);start=0;cfg_a_base=999;
 wait(seen=={len(expected)});@(negedge clk);
 if(active || invalid_geometry)$fatal(1,"cursor did not finish");
 cfg_a_base=100;seen=0;start=1;@(negedge clk);start=0;
 wait(seen>4);@(negedge clk);clear=1;@(negedge clk);
 if(active || request_valid)$fatal(1,"clear did not abort");
 $display("PASS cursor interleave={interleave} words={len(expected)}");$finish;
end
initial begin #100000;$fatal(1,"timeout");end
endmodule
''')
    sim = tmp_path / "sim"
    built = subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-s",
            "tb",
            "-o",
            str(sim),
            str(ROOT / "rtl/abi3/ot_a3_lq8_operand_cursor.sv"),
            str(bench),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert built.returncode == 0, built.stderr
    run = subprocess.run(["vvp", str(sim)], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "PASS cursor" in run.stdout
