import json,sys
P="plan_c.json"; p=json.load(open(P))
W,H=380.16,190.08
pins={f:{q["name"]:(q["x"],q["y"]) for q in json.load(open("pins/"+f))["pins"]} for f in ("kv3_pv_pair_pins_r26c_lc.json","kv3_pv_pair_pins_fMX_r26c_lc.json")}
def tf(o,x,y):
    return {"R0":(x,y),"MX":(x,H-y),"MY":(W-x,y),"R180":(W-x,H-y)}[o]
COMP={"R0":"MX","MX":"R0","MY":"R180","R180":"MY"}
bad=0;n=0;nt=0;apply=len(sys.argv)>1
for tn,t in p["partition_types"].items():
    hc={h["inst"]:h for h in t.get("hard_cores",[]) if h.get("module")=="kv3_pv_pair"}
    if not hc: continue
    taps=(t.get("clock") or {}).get("taps",[])
    for tp in taps:
        i,pn=tp["name"].split(".",1)
        if i not in hc: continue
        h=hc[i]; f=h["pins_file"].split("/")[-1]
        x,y=pins[f][pn]; dx,dy=tf(h["orient"],x,y)
        to=h.get("track_offset_um",[0,0]); e=(round(h["origin_um"][0]+to[0]+dx,3),round(h["origin_um"][1]+to[1]+dy,3))
        if abs(e[0]-tp["xy"][0])>0.01 or abs(e[1]-tp["xy"][1])>0.01:
            bad+=1
            if bad<4: print("MISMATCH",tn,tp["name"],tp["xy"],e,h["orient"],f)
        if apply:
            if "fMX" not in f:
                h["pins_file"]="pins/kv3_pv_pair_pins_fMX_r26c_lc.json"; h["orient"]=COMP[h["orient"]]; n+=1
            x,y=pins["kv3_pv_pair_pins_fMX_r26c_lc.json"]["s1__clk[0]"]; dx,dy=tf(h["orient"],x,y)
            tp["name"]=i+".s1__clk[0]"; tp["xy"]=[round(h["origin_um"][0]+to[0]+dx,3),round(h["origin_um"][1]+to[1]+dy,3)]; nt+=1
print("bad",bad,"slots_changed",n,"taps_renamed",nt)
if apply:
    # all base slots must now be fMX
    left=sum(1 for t in p["partition_types"].values() for h in t.get("hard_cores",[]) if h.get("module")=="kv3_pv_pair" and "fMX" not in h["pins_file"])
    print("base_left",left)
    json.dump(p,open(P,"w"),indent=1); open(P,"a").write("\n")
