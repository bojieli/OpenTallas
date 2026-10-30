from pathlib import Path
import json,shutil,sys
p=Path('/srv/opentallas-scratch2/claude/codex-qc-a0-0336');sys.path.insert(0,str(p/'natural_model/tools'));import core_infra as C
kind,stem=sys.argv[1:];d=p/f'physical/{kind}_pin_clock_install';d.mkdir(exist_ok=True);source=p/f'physical/{kind}_public_edge/public_restored.odb'if kind=='nk'else p/'physical/nl_public_edge_preclock/public_restored.odb';shutil.copy2(source,d/'input.odb')
for src,dst in [('src/install_clock_geometry.tcl','install_clock_geometry.tcl'),('geom_tools/geom_dump.tcl','geom_dump.tcl'),(f'physical/{kind}_widen2/native_pg_binding.tcl','native_pg_binding.tcl'),('natural_model/tools/core_infra.tcl','core_infra_impl.tcl'),('src/core_infra_late_rowcache.tcl','core_infra_late.tcl')]:shutil.copy2(p/src,d/dst)
s=json.load(open(p/'natural_model'/(stem+'_full_qualified.json')));s['core_tree']['late_dpl_max_um']=.054;(d/'master_core_infra_late.tcl').write_text(C.emit_late_tcl(C.compile_slice(s,p/f'physical/{kind}_widen2')))
widths={'BUFx6f_ASAP7_75t_R':540,'BUFx8_ASAP7_75t_R':648,'BUFx12f_ASAP7_75t_R':972,'BUFx16f_ASAP7_75t_R':1188,'BUFx24_ASAP7_75t_R':1620}
with (d/'clock_bodies.tsv').open('w')as f:
 for n in s['core_tree']['nodes']:
  x,y=[round(v*1000)for v in n['body_origin_um']];f.write('\t'.join(map(str,[n['name'],n['master'],x,y,x+widths[n['master']],y+270]))+'\n')
fr=json.load(open(p/f'widen/{kind}_freeze_candidate.json'));rects=[[round(v*1000)for v in r]for c in fr['candidate_clock_corridors']for r in c['clock_islands_um']]
if kind=='nk':
 for line in open(p/'physical/nk_clockfirst_fixed_dpl/clock_bodies.tsv'):rects.append(list(map(int,line.rstrip().split('\t')[2:6])))
(d/'temporary_clock_blockages.tsv').write_text('\n'.join('\t'.join(map(str,r))for r in rects)+'\n')
r=(p/f'physical/{kind}_public_clock_install/run.sh').read_text().replace(f'codex-a0-{kind}clockinstall-0336',f'codex-a0-{kind}-actualpin-install-0336');(d/'run.sh').write_text(r)
(d/'SOURCE.txt').write_text(f'candidate={stem}\ninput={source}\nlate-row-cache=e6a71788c, source-only exact-semantics private copy\nno STA/CTS/GRT/libraries/SDC in this installation\n')
print(d)
