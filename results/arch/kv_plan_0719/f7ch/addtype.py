import json, glob, sys
for g in glob.glob(sys.argv[1] + "/*/part_*/grt.json"):
    r = json.load(open(g)); r["type"] = g.split("/")[-3]; json.dump(r, open(g, "w"))
