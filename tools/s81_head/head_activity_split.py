import json,sys
R=json.load(open(sys.argv[1]))
for t in ("A","B"):
    with open(f"{sys.argv[2]}/act_{t}.txt","w") as f:
        for k,v in R["types"][t]["rates"].items():
            if " " not in k: f.write(f"{k} {v:.6f}\n")
