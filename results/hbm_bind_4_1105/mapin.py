import json,re
R="/srv/opentallas-scratch2/claude/hbm-bind-4/"
Y=json.load(open(R+"e2/dce/asbuilt.json"))["modules"]; top=Y["hbm_current_native_top"]
m=json.load(open(R+"tip/physical/die_plan/hbm/bind/d44v/inputs/map_recovered.json"))
parts=m["parts"]
MEM=('$memwr_v2','$memrd','$memrd_v2','$meminit_v2','$mem_v2','$memwr')
n=0
def walk(mod,path):
    global n
    for c,x in Y[mod].get("cells",{}).items():
        if x["type"] in MEM:
            o=path
            ex=[k for k in parts if k.startswith(o+".$")]
            assert ex,o
            part,rel=parts[ex[0]][:2]; pre=rel.split(".$",1)[0]
            parts[o+"."+c]=[part,pre+"."+c]; n+=1
        elif x["type"] in Y and Y[x["type"]].get("cells"):
            walk(x["type"],path+"."+c if path else c)
walk("hbm_current_native_top","")
print("homes",n)
json.dump(m,open(R+"e2/map_in.json","w"))
