import sys
t = open(sys.argv[1]).read(); rl = int(sys.argv[3])
old = "    ot_s81_land #(.W(70),  .D(4)) u (.ck_f(ck_f), .i(i), .ck(ck), .rs(rs), .k(k), .o(o), .fault(fault));"
assert t.count(old) == 1
regs = ""
prev = "rs"
for k in range(rl):
    regs += "    (* keep *) reg rs__ot_rl%d; always @(posedge ck) rs__ot_rl%d <= %s;\n" % (k, k, prev)
    prev = "rs__ot_rl%d" % k
t = t.replace(old, regs + old.replace(".rs(rs)", ".rs(%s)" % prev))
open(sys.argv[2], "w").write(t)
