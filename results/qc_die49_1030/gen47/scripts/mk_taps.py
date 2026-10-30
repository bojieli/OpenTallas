import json,sys
e=json.load(open(sys.argv[1]))["endpoints"]
with open(sys.argv[2],"w") as f:
  for k,v in sorted(e.items()): f.write("%s %s %s %.3f %.3f\n"%(k,v["inst"],v["pin"],v["xy_um"][0],v["xy_um"][1]))
print(len(e))
