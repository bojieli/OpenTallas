# Synthesis views for the screen only (outside the repository): the ROM loader (initial + $value$plusargs) of
# the spine and the ROM adapter replaced by a write port on new top-level inputs scr_we/scr_wa/scr_wd.
import re
from pathlib import Path
src = Path.home() / "rcl-20261003/src"; dst = Path.home() / "rcl-20261003/jobs/patched"
def patch(rel, init_re, body):
    t = (src / rel).read_text()
    t2, n = re.subn(init_re, body, t, count=1, flags=re.S)
    assert n == 1, rel
    # new ports before the module header's closing ");" (first occurrence after "module")
    m = re.search(r"\n\s*input\s+wire\s+clk,", t2)
    t2 = t2[:m.end()] + "\n    input  wire scr_we,\n    input  wire [15:0] scr_wa,\n    input  wire [63:0] scr_wd," + t2[m.end():]
    p = dst / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(t2); print("wrote", p)
patch("rtl/v41die/ot_v41_spine_w17w10.sv", r"    initial begin\n        for \(ii = 0; ii < \(2 << PHW\).*?\n    end\n",
      "    always @(posedge clk) if (scr_we) begin phrom[scr_wa[PHW:0]] <= scr_wd; strom[scr_wa[SAW-1:0]] <= scr_wd[47:0]; end\n")
patch("rtl/v41die/ot_v41_rom_adapt.sv", r"    initial begin\n        for \(ii = 0; ii < \(1 << PHW\).*?\n    end\n",
      "    always @(posedge clk) if (scr_we) keyrom[scr_wa[PHW-1:0]] <= scr_wd[31:0];\n")
