#!/usr/bin/env python3
"""DIE-KV-80: r4k in-context stimulus contract for the stream benches. usage: kctx.py mux|link IN OUT
KCONST=1 reads fixed frame fields as literals; inside the core those fields are fixed by the senders
(coordinator codec lanes: [7]=1 [6:3]=0 [10:8]=0 [13:11]=lane [511:179]=0; rank-0 codec local word:
[13:4]=0 [511:159]=0). The tb copy generates only words that meet this contract, so r4k must match exactly."""
import sys
kind, i, o = sys.argv[1:4]; s = open(i).read()
def wrap(name, sig, args, body):
    global s
    a = f"function automatic bit[511:0] {name}({sig}"
    assert s.count(a) == 1, a
    s = s.replace(a, f"function automatic bit[511:0] {name}_raw({sig}")
    s += f"\nfunction automatic bit[511:0] {name}({sig};bit[511:0] w={name}_raw({args});{body}return w;endfunction\n"
if kind == "mux":
    wrap("w_tx", "input int rk,input int idx)", "rk,idx",
         "w[511:179]=0;w[10:8]=0;w[6:3]=0;if(rk==0)begin w[13:11]=0;w[7]=1;end ")
    wrap("w_loc", "input int idx)", "idx", "w[511:159]=0;w[13:4]=0;")
    a = " qkd_host_peer_root_mux_r3\n"; assert s.count(a) == 1; s = s.replace(a, " qkd_host_peer_root_mux_r3 #(.KCONST(1))\n")
else:
    wrap("w_ptx", "input int idx)", "idx", "w[511:179]=0;w[10:8]=0;w[6:3]=0;")
    a = " #(.MUT(MUTP)) dut("; assert s.count(a) == 1; s = s.replace(a, " #(.MUT(MUTP),.KCONST(1)) dut(")
# functions must be inside the module: move the appended wrappers before endmodule
tail = s[s.rindex("endmodule") + len("endmodule"):]
s = s[:s.rindex("endmodule")] + tail + "endmodule\n"
open(o, "w").write(s)
