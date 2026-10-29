import json,sys,glob,collections
R=sys.argv[1]
rows={}
for v in ("base","h0","h1"):
    for l in (0,2,14):
        r=json.load(open(f"{R}/emit/{v}/ds_l{l}/replay.json"))
        ev=[e for e in r["events"] if e["k"]!="M"]
        last={d:max([e["cyc"] for e in ev if e["dom"]==d] or [0]) for d in ("stream","serial","hbm")}
        chk=sum(e["k"]=="C" for e in ev)
        rows[(v,l)]=(last["serial"],last["stream"],last["hbm"],chk,len(ev),r.get("priced_layer_cycles"))
for l in (0,2,14):
    b=rows[("base",l)][0]
    for v in ("base","h0","h1"):
        s=rows[(v,l)]
        print(f"ds_l{l:<3} {v:5} serial_end={s[0]:6d} ({(s[0]-b)/b*100:+.3f}% vs base, {s[0]-b:+d}) stream_end={s[1]} hbm_end={s[2]} checks={s[3]} events={s[4]} priced={s[5]}")
