from pathlib import Path
import json,re,shutil,sys
r=Path('/srv/opentallas-scratch2/claude/codex-qc-a0-0830');t=sys.argv[1];k=r/'kits'/f'qfd_tile_{t}_a0c_a0{t}14icg2r1'
s=next((k/'run/results/asap7').glob('*/base/1_synth.v')).read_text();names={m.replace('\\','') for m in re.findall(r'^\s*\S+\s+(\\\S+)\s+\(',s,re.M)}
ch=json.loads((r/'nk_children_v1l.json').read_text())['children'] if t=='nk' else []
rows=[];missing=[];clipped=[]
for line in (r/'nl_anchors_reset6.tsv').read_text().splitlines():
 n,x,y=line.split('\t');x=float(x);y=float(y)
 if n.replace('\\','') not in names:missing.append(n);continue
 hit=False
 for c in ch:
  a,b=c['at'];ww,hh=c['size_um']
  if a-4.32<=x<=a+ww+4.32 and b-4.32<=y<=b+hh+4.32:hit=True;break
 if hit:clipped.append([n,x,y]);continue
 rows.append(line)
(k/'anchor_targets.tsv').write_text('\n'.join(rows)+'\n');(k/'anchor_projection.json').write_text(json.dumps(dict(kept=len(rows),missing=len(missing),unanchored_macrohalo=len(clipped),clipped=clipped),indent=1))
shutil.copyfile(r/'apply_anchor_targets.tcl',k/'apply_anchor_targets.tcl')
p=k/'face_flops_release.tcl';s=p.read_text();s+='\n# Existing reset6 targets where current native cells and new V1L macro halos permit.\nsource /work/apply_anchor_targets.tcl\n';p.write_text(s)
p=k/'config.mk';p.write_text(p.read_text()+'\n# Stop at the measured min-overflow basin; this changes GPL only.\nexport GLOBAL_PLACEMENT_ARGS = -overflow 0.21\n')
print('ANCHORS',t,len(rows),'MISSING',len(missing),'UNANCHORED_MACROHALO',len(clipped))
