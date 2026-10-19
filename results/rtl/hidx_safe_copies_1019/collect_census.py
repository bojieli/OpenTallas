#!/usr/bin/env python3
"""Fleet-only summary of immutable mapped source; nonzero means no gate."""
import argparse,collections,hashlib,json,pathlib,sys
p=argparse.ArgumentParser(description=__doc__);p.add_argument("census");p.add_argument("output");a=p.parse_args()
r=pathlib.Path(a.census);c=json.loads((r/"census.json").read_text());m=json.loads((r/"mapped.json").read_text())["modules"][c["top"]]
ff={n:v for n,v in m["cells"].items() if v["type"].startswith("DFF")}
families={}
for name,fragment in {"rotate":"local_selects.rotate", "pair":"local_selects.pair", "quad":"local_selects.quad", "half":"local_selects.half", "ingress":".safe.slice", "carry":"g_partial_carry.regional", "write":".regional.slice", "emit_enable":"local_emit.enable_copy", "emit_group":"local_emit.group_copy"}.items():
 families[name]=sum(fragment in n for n in ff)
reset=[n for n in c["reset_networks"] if n["fanout"]>32]
bad=c["over32_data_control"]
out={k:c[k] for k in ["top","tool","std_area_um2","source_sha256","macro_counts","unmapped_or_unknown"]}
out.update(source_safety="PASS" if not bad and not reset and not c["unmapped_or_unknown"] else "FAIL",physical_claim=False,ff_count=len(ff),families=families,over32_count=len(bad),reset_over32_count=len(reset),over32=bad,reset_networks=c["reset_networks"],census_sha256=hashlib.sha256((r/"census.json").read_bytes()).hexdigest(),mapped_sha256=hashlib.sha256((r/"mapped.json").read_bytes()).hexdigest())
pathlib.Path(a.output).write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({k:v for k,v in out.items() if k not in ["over32","reset_networks"]},indent=2))
sys.exit(out["source_safety"]!="PASS")
