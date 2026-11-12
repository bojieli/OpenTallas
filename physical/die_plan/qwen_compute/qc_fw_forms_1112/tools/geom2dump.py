"""GEOM_TSV OUT_DUMP_JSON SRC -> model_class dump {outline, cells:[[name,x0,y0,x1,y1]], odb} of placed flops"""
import json, sys
tsv, out, src = sys.argv[1:4]
cells, outline = [], None
for line in open(tsv):
    f = line.rstrip("\n").split("\t")
    if f[0] == "D":
        outline = [float(v) for v in f[1:5]]
    elif f[0] == "C" and any(k in f[3] for k in ("DFF", "SDF")):
        cells.append([f[8] if len(f) > 8 else f[1]] + [float(v) for v in f[4:8]])
json.dump(dict(outline=outline, cells=cells, odb=src), open(out, "w"))
print(len(cells), outline)
