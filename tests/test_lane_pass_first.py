"""Pass-first lane: independent address/order and exact FP32 result checks."""
from pathlib import Path
import shutil
import struct
import subprocess
import pytest
from tools.rtl_abi3_lane_campaign import RTL_SOURCES

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog unavailable")
@pytest.mark.parametrize("interleave", [1, 2, 3])
@pytest.mark.parametrize("depth", [1, 4, 160])
@pytest.mark.parametrize("pass_first", [0, 1])
def test_lane_pass_first(tmp_path, interleave, depth, pass_first):
    rows, cols = 3, 7
    block = 1 if depth == 1 else 4
    stride = depth // block
    a = [[65536.0, 1.0, -65536.0, 0.00390625][(r+k)%4]
         for r in range(rows) for k in range(depth)]
    b = [[1.0, -2.0, 0.5, 8.0][(c+2*k)%4]
         for c in range(cols) for k in range(depth)]
    scales_a = [127 + (i % 2) for i in range(2 * stride)]
    scales_b = [127 + (i % 2) for i in range(4 * stride)]
    f32 = lambda v: struct.unpack(">I", struct.pack(">f", v))[0]
    expected, addresses = [], []
    order = [(p, r) for p in range(0, cols, interleave) for r in range(rows)]
    if not pass_first:
        order.sort(key=lambda pr: (pr[1], pr[0]))
    for p, r in order:
        for k in range(depth):
            for c in range(p, min(p + interleave, cols)):
                addresses.append((100+r*depth+k, 200+c*depth+k,
                                  10+(r//2)*stride+k//block,
                                  30+(c//2)*stride+k//block))
        for c in range(p, min(p + interleave, cols)):
            total = 0.0
            for k in range(depth):
                product = (a[r*depth+k]*b[c*depth+k] *
                           (1 << (scales_a[(r//2)*stride+k//block]-127)) *
                           (1 << (scales_b[(c//2)*stride+k//block]-127)))
                # Products are exact powers of two; explicitly round each
                # addition, preserving the required sequential association.
                total = struct.unpack(">f", struct.pack(">f", total+product))[0]
            expected.append((50+r*cols+c, f32(total)))
    def image(name, values, width):
        path = tmp_path/name
        path.write_text("".join(f"{v:0{width}x}\n" for v in values))
        return path
    am = image("a.hex", [f32(v)>>16 for v in a], 16)
    bm = image("b.hex", [f32(v)>>16 for v in b], 16)
    sa = image("sa.hex", scales_a, 8); sb = image("sb.hex", scales_b, 8)
    req = image("req.hex", [(aa<<96)|(bb<<64)|(ss<<32)|tt for aa,bb,ss,tt in addresses], 32)
    out = image("out.hex", [(addr<<32)|v for addr,v in expected], 16)
    bench = tmp_path/"tb.sv"
    bench.write_text(f'''module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,start=0;integer ticks=0,issues=0,writes=0;
wire credit=ticks%7<4;
wire operand_issue,done,out_we,a_rd_en,b_rd_en,s_rd_en,t_rd_en;
wire [31:0] operand_a_addr,operand_b_addr,operand_s_addr,operand_t_addr;
wire [31:0] a_rd_addr,b_rd_addr,s_rd_addr,t_rd_addr,out_addr,out_data,out_acc;
wire [7:0] error_code,error_detail;
reg [63:0] a_rd_data,b_rd_data;reg [31:0] s_rd_data,t_rd_data;
reg [63:0] am[0:{len(a)-1}],bm[0:{len(b)-1}];
reg [31:0] sa[0:{len(scales_a)-1}],sb[0:{len(scales_b)-1}];
reg [127:0] req[0:{len(addresses)-1}];reg [63:0] expected[0:{len(expected)-1}];
ot_a3_lane_pipelined #(.ADDER_STAGES({interleave}),.OPERAND_CREDITS(1),.PASS_FIRST({pass_first})) dut(
.clk(clk),.rst_n(rst_n),.start(start),.operand_credit(credit),.operand_issue(operand_issue),
.operand_a_addr(operand_a_addr),.operand_b_addr(operand_b_addr),.operand_s_addr(operand_s_addr),.operand_t_addr(operand_t_addr),
.cfg_rows(16'd{rows}),.cfg_cols(16'd{cols}),.cfg_depth(16'd{depth}),
.cfg_dtype_a(8'h10),.cfg_dtype_b(8'h10),.cfg_group(8'd1),
.cfg_a_base(32'd100),.cfg_b_base(32'd200),.cfg_scale_a(1'b1),.cfg_scale_b(1'b1),
.cfg_block_a(16'd{block}),.cfg_block_b(16'd{block}),.cfg_block_rows_a(16'd2),.cfg_block_rows_b(16'd2),
.cfg_scale_a_base(32'd10),.cfg_scale_b_base(32'd30),.cfg_out_base(32'd50),.cfg_out_fp32(1'b1),
.a_rd_en(a_rd_en),.b_rd_en(b_rd_en),.s_rd_en(s_rd_en),.t_rd_en(t_rd_en),
.a_rd_addr(a_rd_addr),.b_rd_addr(b_rd_addr),.s_rd_addr(s_rd_addr),.t_rd_addr(t_rd_addr),
.a_rd_data(a_rd_data),.b_rd_data(b_rd_data),.s_rd_data(s_rd_data),.t_rd_data(t_rd_data),
.out_we(out_we),.out_addr(out_addr),.out_data(out_data),.out_acc(out_acc),
.done(done),.error_code(error_code),.error_detail(error_detail));
always @(posedge clk)begin
 ticks<=ticks+1;
 if(rst_n)begin
  if(a_rd_en)a_rd_data<=am[a_rd_addr-100];
  if(b_rd_en)b_rd_data<=bm[b_rd_addr-200];
  if(s_rd_en)s_rd_data<=sa[s_rd_addr-10];
  if(t_rd_en)t_rd_data<=sb[t_rd_addr-30];
  if(operand_issue)begin
   if(issues>={len(addresses)} || {{operand_a_addr,operand_b_addr,operand_s_addr,operand_t_addr}}!==req[issues])$fatal(1,"issue order %0d",issues);
   issues<=issues+1;
  end
  if(out_we)begin
   if(writes>={len(expected)} || {{out_addr,out_data}}!==expected[writes] || out_acc!==out_data)$fatal(1,"output %0d addr %0d data %h",writes,out_addr,out_data);
   writes<=writes+1;
  end
 end
end
initial begin
 $readmemh("{am}",am);$readmemh("{bm}",bm);$readmemh("{sa}",sa);$readmemh("{sb}",sb);
 $readmemh("{req}",req);$readmemh("{out}",expected);
 repeat(2)@(negedge clk);rst_n=1;start=1;@(negedge clk);start=0;
 wait(done);@(negedge clk);
 if(error_code || issues!={len(addresses)} || writes!={len(expected)})$fatal(1,"completion %0d %0d %0d/%0d",issues,writes,error_code,error_detail);
 // Reset midway through a new issue stream, then verify complete recovery.
 issues=0;writes=0;start=1;@(negedge clk);start=0;
 wait(issues>4);@(negedge clk);rst_n=0;
 repeat(2)@(negedge clk);issues=0;writes=0;rst_n=1;start=1;
 @(negedge clk);start=0;wait(done);@(negedge clk);
 if(error_code || issues!={len(addresses)} || writes!={len(expected)})$fatal(1,"recovery");
 $display("PASS pass-first lane");$finish;
end
initial begin #2000000;$fatal(1,"timeout");end
endmodule
''')
    sim = tmp_path/"sim"
    compiled = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", str(sim),
                               *[str(ROOT/s) for s in RTL_SOURCES], str(bench)],
                              capture_output=True, text=True, timeout=60)
    assert compiled.returncode == 0, compiled.stderr
    run = subprocess.run(["vvp", str(sim)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "PASS pass-first lane" in run.stdout


def test_reject_unsupported_adder_depth(tmp_path):
    if shutil.which("iverilog") is None:
        pytest.skip("iverilog unavailable")
    bench = tmp_path / "tb.sv"
    bench.write_text('module tb; ot_a3_lane_pipelined #(.ADDER_STAGES(5)) dut(); endmodule')
    sim = tmp_path / "sim"
    subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", str(sim),
                    *[str(ROOT/s) for s in RTL_SOURCES], str(bench)],
                   check=True, capture_output=True, timeout=60)
    run = subprocess.run(["vvp", str(sim)], capture_output=True, text=True, timeout=30)
    assert run.returncode != 0
    assert "lane adder supports one, two or three stages" in run.stdout
