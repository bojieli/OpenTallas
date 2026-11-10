import glob,gzip,re,json
out=set()
for f in glob.glob("/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*.lib*"):
    t=(gzip.open(f,"rt") if f.endswith(".gz") else open(f)).read()
    for cm in re.finditer(r"cell\s*\(\s*\"?([\w]+)\"?\s*\)\s*\{(.*?)(?=\n\s*cell\s*\(|\Z)",t,re.S):
        for pm in re.finditer(r"pin\s*\(\s*\"?(\w+)\"?\s*\)\s*\{[^{}]*?direction\s*:\s*\"?output",cm.group(2),re.S): out.add((cm.group(1),pm.group(1)))
json.dump(sorted(out),open("/w2/libpins.json","w")); print(len(out))
