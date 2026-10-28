import json,sys
d=json.load(open(sys.argv[1]))
with open(sys.argv[2],"w") as f:
    f.write("set CL {}\n")
    for c in d["clusters"]:
        f.write("lappend CL [list %s %.3f %.3f {%s}]\n"%(c["name"],c["root"][0],c["root"][1]," ".join("{%s}"%r for r in c["regs"])))
