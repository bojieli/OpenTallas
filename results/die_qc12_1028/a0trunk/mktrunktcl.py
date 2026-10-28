import json,sys
d=json.load(open(sys.argv[1])); s=d["summary"]
with open(sys.argv[2],"w") as f:
    f.write("set ICG [list %.3f %.3f]\nset TI {}\nset TS {}\n"%tuple(s["icg"]["site"]))
    for i in d["insts"]:
        f.write("lappend TI [list %s %s %.3f %.3f %s %s]\n"%(i["name"],i["cell"],i["p"][0],i["p"][1],i["in_net"],i["out_net"]))
    for k in d["sinks"]:
        f.write("lappend TS [list %s {%s} %s]\n"%(k["kind"],k["name"],k["net"]))
