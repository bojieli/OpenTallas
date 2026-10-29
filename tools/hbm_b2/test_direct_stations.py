import copy
import random
from pathlib import Path
import subprocess
import tempfile
import unittest

from hbm_b2.direct_stations import materialize


SOURCE = """module native (clk, drive, other, result, mirror);
  input wire clk;
  input wire [256:0] drive;
  input wire [256:0] other;
  output wire [513:0] result;
  output wire [256:0] mirror;
  wire [256:0] bank__rr1;
  source_bank bank (
    .clk(clk),
    .drive(drive[256:0]),
    .rr1(bank__rr1[256:0])
  );
  native_sink sink (
    .clk(clk),
    .rr({other[256:0], bank__rr1[256:0]}),
    .result(result[513:0])
  );
  assign mirror = bank__rr1;
endmodule
"""
CHAIN = dict(name="bank_rr1", source_instance="bank", source_port="rr1",
             sink_instance="sink", sink_port="rr", sink_lsb=0, stages=3)
STUBS = """
module source_bank(input clk, input [256:0] drive, output [256:0] rr1);
  assign rr1 = drive;
endmodule
module native_sink(input clk, input [513:0] rr, output [513:0] result);
  assign result = rr;
endmodule
"""
BENCH = """
module tb;
  reg clk=0;
  reg [256:0] drive=0, other=0;
  wire [513:0] result;
  wire [256:0] mirror;
  reg [256:0] history[0:2];
  integer cycle, bitnum, errors=0;
  reg [31:0] state=32'h97071319;
  native dut(clk,drive,other,result,mirror);
  initial begin
    for(cycle=0;cycle<4096;cycle=cycle+1) begin
      for(bitnum=0;bitnum<257;bitnum=bitnum+1) begin
        state={state[30:0],state[31]^state[21]^state[1]^state[0]};
        drive[bitnum]=state[0]; other[bitnum]=state[3];
      end
      #1;
      if(mirror !== drive) errors=errors+1;
      clk=1; #1;
      if(cycle>=2 && result[256:0] !== history[1]) errors=errors+1;
      if(result[513:257] !== other) errors=errors+1;
      history[2]=history[1]; history[1]=history[0]; history[0]=drive;
      clk=0; #1;
    end
    if(errors) $fatal(1,"MISMATCH errors=%0d",errors);
    $display("PASS cycles=4096 width=257 stages=3 untouched=257 mirror=257");
    $finish;
  end
endmodule
"""


class DirectStationTest(unittest.TestCase):
    def test_disabled_identity_and_direct_mapping_refusals(self):
        self.assertEqual(materialize(SOURCE, [CHAIN])[0], SOURCE)
        for key, value, error in (("sink_lsb", 1, "exact direct"),
                                  ("stages", 0, "positive"),
                                  ("sink_lsb", 258, "outside")):
            bad = dict(CHAIN, **{key: value})
            with self.assertRaisesRegex(ValueError, error):
                materialize(SOURCE, [bad], enabled=True)
        different_clock = SOURCE.replace(".clk(clk),\n    .rr(", ".clk(other[0:0]),\n    .rr(")
        with self.assertRaisesRegex(ValueError, "share.*clock"):
            materialize(different_clock, [CHAIN], enabled=True)
        candidate, receipt = materialize(SOURCE, [CHAIN], enabled=True)
        self.assertEqual(receipt["chains"][0]["register_bits"], 771)
        self.assertIn(".rr1(bank__rr1[256:0])", candidate)
        self.assertIn("assign mirror = bank__rr1;", candidate)
        self.assertIn(".rr({other[256:0], __ot_station_bank_rr1_out[256:0]})", candidate)
        with self.assertRaisesRegex(ValueError, "already present"):
            materialize(candidate, [CHAIN], enabled=True)
        for change, error in ((dict(transport="serial_k2"), "serialization"),
                              (dict(runtime_adopt=True), "incomplete parent"),
                              (dict(control_mask=1), "explicit caller")):
            with self.assertRaisesRegex(ValueError, error):
                materialize(SOURCE, [dict(CHAIN, **change)], enabled=True)
        partial, record = materialize(SOURCE, [dict(CHAIN, source_lsb=4,
                                                   source_width=17, sink_lsb=4)], enabled=True)
        self.assertEqual(record["chains"][0]["source_segments"], [("n", "bank__rr1", 4, 20)])
        self.assertIn("{other[256:0], bank__rr1[256:21], __ot_station_bank_rr1_out[16:0], bank__rr1[3:0]}", partial)
        for change in (dict(source_lsb=256, source_width=2), dict(source_width=0)):
            with self.assertRaisesRegex(ValueError, "source slice outside"):
                materialize(SOURCE, [dict(CHAIN, **change)], enabled=True)

    def test_lockstep_exact_delay_and_mutants(self):
        candidate, _ = materialize(SOURCE, [CHAIN], enabled=True)
        variants = dict(positive=candidate,
                        wrong_stage=candidate.replace("assign __ot_station_bank_rr1_out = __ot_station_bank_rr1_s2;",
                                                      "assign __ot_station_bank_rr1_out = __ot_station_bank_rr1_s1;"),
                        wrong_bit=candidate.replace("assign __ot_station_bank_rr1_out = __ot_station_bank_rr1_s2;",
                                                    "assign __ot_station_bank_rr1_out = __ot_station_bank_rr1_s2 ^ 257'b1;"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, design in variants.items():
                sv, exe = root / f"{name}.sv", root / name
                sv.write_text(design + STUBS + BENCH)
                subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", str(exe), str(sv)], check=True,
                               capture_output=True, text=True)
                result = subprocess.run(["vvp", str(exe)], capture_output=True, text=True)
                if name == "positive":
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("PASS cycles=4096", result.stdout)
                else:
                    self.assertNotEqual(result.returncode, 0, name)
                    self.assertIn("MISMATCH", result.stdout)

    def test_six_actual_widths_control_only_reset_and_mutants(self):
        cases = [(257, 3, 1 << 256), (276, 6, 1 << 275),
                 (266, 6, 1 << 265), (18, 6, (1 << 18)-1),
                 (1, 6, 1), (1, 6, 1)]
        rng = random.Random(106290822)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (width, depth, mask) in enumerate(cases):
                source = SOURCE.replace("513", str(2*width-1)).replace("256", str(width-1))
                source = source.replace("module native (clk,", "module native (rst_n, clk,")
                source = source.replace("  input wire clk;", "  input wire clk;\n  input wire rst_n;")
                source = source.replace("source_bank bank (", "source_bank bank (\n    .rst_n(rst_n),")
                chain = dict(CHAIN, stages=depth, control_mask=mask,
                             reset_kind="caller_sync_active_low", source_reset_port="rst_n")
                candidate, receipt = materialize(source, [chain], enabled=True)
                self.assertFalse(receipt["chains"][0]["data_reset"])
                self.assertFalse(receipt["chains"][0]["reset_delivery_qualified"])
                history = [0] * depth
                trace = []
                for cycle in range(128):
                    reset = cycle not in (0, 1, 2, 17, 32, 33, 34, 35, 80)
                    drive, other = rng.getrandbits(width), rng.getrandbits(width)
                    history = [drive] + history[:-1]
                    if not reset:
                        history = [v & ~mask for v in history]
                    trace += [f"rst_n=1'b{int(reset)}; drive={width}'h{drive:x}; other={width}'h{other:x};",
                              "#1; clk=1; #1;",
                              f"if(mirror !== drive || result[{2*width-1}:{width}] !== other) errors=errors+1;"]
                    if cycle >= depth:
                        trace += [f"if(result[{width-1}:0] !== {width}'h{history[-1]:x}) errors=errors+1;"]
                    if not reset:
                        trace += [f"if((result[{width-1}:0] & {width}'h{mask:x}) !== {width}'h0) errors=errors+1;"]
                    trace += ["clk=0; #1;"]
                bench = f"""
module tb;
reg clk=0,rst_n=0; reg [{width-1}:0] drive=0,other=0;
wire [{2*width-1}:0] result; wire [{width-1}:0] mirror;
integer errors=0;
native dut(rst_n,clk,drive,other,result,mirror);
initial begin
{chr(10).join(trace)}
if(errors) $fatal(1,"MISMATCH errors=%0d",errors);
$display("PASS"); $finish;
end
endmodule
"""
                stubs = STUBS.replace("513", str(2*width-1)).replace("256", str(width-1))
                stubs = stubs.replace("source_bank(input clk,", "source_bank(input rst_n,input clk,")
                variants = dict(positive=candidate,
                                wrong_stage=candidate.replace(f"_out = __ot_station_bank_rr1_s{depth-1};",
                                                              f"_out = __ot_station_bank_rr1_s{depth-2};"),
                                wrong_bit=candidate.replace(f"_out = __ot_station_bank_rr1_s{depth-1};",
                                                            f"_out = __ot_station_bank_rr1_s{depth-1} ^ {width}'b1;"),
                                missing_reset=candidate.replace("if (!rst_n)", "if (1'b0)"))
                for variant, design in variants.items():
                    sv, exe = root / "test.sv", root / "test"
                    sv.write_text(design + stubs + bench)
                    subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", str(exe), str(sv)],
                                   check=True, capture_output=True, text=True)
                    result = subprocess.run(["vvp", str(exe)], capture_output=True, text=True)
                    self.assertEqual(result.returncode == 0, variant == "positive",
                                     (index, variant, result.stdout, result.stderr))


if __name__ == "__main__":
    unittest.main()
