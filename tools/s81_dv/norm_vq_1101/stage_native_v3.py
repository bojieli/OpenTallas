from pathlib import Path
import shutil,json,hashlib
r=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101');old=r/'native_leaf_ece_v2';out=r/'native_leaf_ece_v3';out.mkdir(exist_ok=False)
for name in('source','source.f','defines.f','entry.memh','stage.json','tb_current_native_leaf.sv','run_current_native_leaf.sh'):
 p=old/name;q=out/name
 if p.is_dir():shutil.copytree(p,q)
 else:shutil.copyfile(p,q)
src=Path('/srv/opentallas-scratch2/claude/wt/codex-s81b-1101');added={}
for name in('rtl/common/ot_meso_fifo.sv','rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv'):
 p=src/name;q=out/'source'/p.name;shutil.copyfile(p,q)
 with(out/'source.f').open('a')as f:f.write(str(q.relative_to(out))+'\n')
 added[name]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'closure_retry.json').write_text(json.dumps(dict(reason='actual Verilator found conditional/helper instances omitted by lightweight closure parser',additional_sources=added,original_failure='native_leaf_ece_v2/build.log',RTL_modified=False),indent=1)+'\n')
(out/'.keep').write_text('critical current native source probe; preserve\n')
