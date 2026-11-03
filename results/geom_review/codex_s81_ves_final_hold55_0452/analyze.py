from pathlib import Path
import json,importlib.util,tkinter,collections
p=Path('/home/ubuntu/coord/tmp/codex-ves-final-look-0452');s=importlib.util.spec_from_file_location('G','/home/ubuntu/OpenTallas/tools/autopilot/geom_rules.py');G=importlib.util.module_from_spec(s);s.loader.exec_module(G);d=G.Design(p/'geom.tsv',memory_reach=True);pairs=[];r=G.r2r_metrics(d,pairs);clock=G.clock_metrics(d);area=G.area_metrics(d);t=tkinter.Tcl();rows=[list(t.splitlist(x)) for x in (p/'targets.tsv').read_text().splitlines()];targets={x[1]:x for x in rows if x[0]=='CELL'};nets={}
for x in rows:
 if x[0]=='PIN':nets[x[1]+'/'+x[2]]=x[3]
z={'actual_saved_input_sha256':(p/'input.sha256').read_text().split()[0],'source':'Original VEs final routed NOTSIGNED baseline, no native mutation or STA','area':area,'reach':r,'clock':clock,'target_cells':targets,'target_pin_nets':nets,'FF_count':sum(c[0]=='S' for c in d.cells.values())};(p/'baseline.json').write_text(json.dumps(z,indent=2));(p/'worst_reach_pairs.json').write_text(json.dumps(sorted(pairs,key=lambda z:-z['distance_um'])[:25],indent=2));print(json.dumps(z,indent=1))
