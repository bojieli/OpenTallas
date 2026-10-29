"""Derive state-exposing copies of the ACTUAL writer modules (old ot_pl_land_local_kw, new ot_s81hd_land_local_dw):
adds outputs x_rq/x_wc/x_woh (assigns only, body untouched) so the miter sees every state register."""
import re, sys
from pathlib import Path
old_src, new_src, out = Path(sys.argv[1]).read_text(), Path(sys.argv[2]).read_text(), Path(sys.argv[3])
def grab(src, name, newname):
    m = re.search(r"module %s\b.*?endmodule" % re.escape(name), src, re.S)
    t = m.group(0).replace("module " + name, "module " + newname, 1)
    t = t.replace("output wire [D-1:0] vld\n", "output wire [D-1:0] vld,\n    output wire x_rq, output wire [AW:0] x_wc, output wire [D-1:0] x_woh\n", 1)
    assert "x_woh" in t
    return t.replace("endmodule", "assign x_rq = rq; assign x_wc = wc; assign x_woh = write_oh;\nendmodule")
out.write_text("`default_nettype none\n" + grab(old_src, "ot_pl_land_local_kw", "old_local") + "\n" +
               grab(new_src, "ot_s81hd_land_local_dw", "new_local") + "\n`default_nettype wire\n")
