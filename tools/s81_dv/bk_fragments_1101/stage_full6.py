from pathlib import Path
import re,json,hashlib,shutil
r=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101');old=r/'bk_transit';out=r/'bk_transit_fragment6_v2';out.mkdir(exist_ok=False)
for name in(old/'files.f').read_text().split():
 source=old/name;dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
for name in('files.f','defines.f','source_record.json','tb_bk_transit.sv'):shutil.copyfile(old/name,out/name)
selected=out/'physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_l20s.sv';body=selected.read_text();pat=r'module dsdv_idx_vmux6\b.*?\nendmodule';before=re.search(pat,body,re.S)[0]
assert before.replace('module dsdv_idx_vmux6','module dsdv_idx_vmux6_legacy',1)+'\n'==(r/'vmux6_legacy.sv').read_text()
candidate=re.search(pat,(r/'candidate_idx_l20s.sv').read_text(),re.S)[0];selected.write_text(body.replace(before,candidate,1))
(out/'candidate_overlay.json').write_text(json.dumps(dict(module='dsdv_idx_vmux6',selected_file=str(selected),baseline_body_sha256=hashlib.sha256(before.encode()).hexdigest(),candidate_body_sha256=hashlib.sha256(candidate.encode()).hexdigest(),added_local_FF=12,added_edges=0,production_adopted=False),indent=1)+'\n')
(out/'.keep').write_text('critical source-only BK integration; preserve\n')
