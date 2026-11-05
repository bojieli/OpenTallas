import json
s=open("inputs/t5_top.sv").read()
four="xc_NW7__done[0:0], xc_NW6__done[0:0], xc_NW5__done[0:0], xc_NW4__done[0:0], "
a="ot_hbm_obs_leaf #(.N(209), .LID(4), .SYNC_MASK(512'h3ffff0000000000000000000000000000)) obs_NW ("
b="ot_hbm_obs_leaf #(.N(182), .LID(3), .SYNC_MASK(512'h7fffe000000000000000000000000000)) obs_NE ("
assert s.count(a)==1 and s.count(b)==1 and s.count(four)==1
i=s.index(a); j=s.index(four); assert j>i and j-i<1000
s=s[:j]+s[j+len(four):]
s=s.replace(a,a.replace(".N(209)",".N(205)"))
k=s.index(b); m=s.index(".obs({",k); assert m-k<400
s=s[:m+6]+four+s[m+6:]
s=s.replace(b,b.replace(".N(182)",".N(186)"))
open("inputs/t11_top.sv","w").write(s)
for src,dst in [("asbuilt_t7_e.json","asbuilt_t11_e.json"),("asbuilt_t10.json","asbuilt_t11.json")]:
    x=json.load(open(src)); assert x["netlist"]==["physical/die_plan/hbm/bind/d44v/inputs/t5_top.sv"]
    x["netlist"]=["physical/die_plan/hbm/bind/d44v/inputs/t11_top.sv"]; x["note"]="HBM-BIND-10 t11 obs re-home xc_NW4..7 -> obs_NE (candidate) | "+x["note"]
    json.dump(x,open(dst,"w"),indent=1)
print("ok")
