import json, sys
d = json.load(open(sys.argv[1])); out = open(sys.argv[2], "w")
W, H = 380.16, 190.08
out.write(f"CORE 0 0 {W} {H}\nPIN ck {d['port_xy'][0]:.3f} {d['port_xy'][1]:.3f}\n")
mck = {s["path"].rsplit("/", 1)[0]: (s["x"], s["y"]) for s in d["sinks"] if s["macro"]}
for s in d["sinks"]:
    if not s["macro"]:
        out.write(f"SINK {s['x']} {s['y']} {s['master']} {s['path'].rsplit('/',1)[0]} CLK\n")
for m in d["macros"]:
    r = m["rect"]; c = mck[m["name"]]
    out.write(f"MACRO {m['name']} sram {r[0]} {r[1]} {r[2]} {r[3]} CK {c[0]} {c[1]}\n")
