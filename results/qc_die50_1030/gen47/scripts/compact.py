"""DIE-QC-50/gen47: Codex-style local FF compaction (3 columns x 3 R0 rows, same stage budget) for both stages of every
interstage edge whose whole-stage all-FF box exceeds 405 um. No RTL/cycle/rule change; windows stay inside each stage's window."""
import json,sys
bud,boxes,out=sys.argv[1:4]
b=json.load(open(bud));e=json.load(open(boxes))["interstage_edges"]
bad={x for ed in e if ed["whole_stage_over405"] for x in (ed["src_stage"],ed["dst_stage"])}
n=0
for s in b["stages"]:
  if s["stage"] in bad:
    x0,y0=s["legacy_ff_rect_um"][:2];w=s["windows_um"][0]
    f=[round(x0,3),round(y0-0.54,3),round(x0+3.24,3),round(y0+0.81,3)]
    assert w[0]<=f[0] and f[2]<=w[2] and w[1]<=f[1] and f[3]<=w[3],s["stage"]
    s["ff_windows_um"]=[f];n+=1
b["local_ff_compaction_reason"]="DIE-QC-50 gen47: %d stages on whole-stage >405 edges get 3col/3row FF windows (Codex wave2_compact form)"%n
json.dump(b,open(out,"w"),separators=(",",":"));print("compacted",n,"stages",sorted(bad)[:8])
