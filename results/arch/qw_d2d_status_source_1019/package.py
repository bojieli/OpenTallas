"""Copy small immutable receipts, preserving predecessor failures separately."""
from pathlib import Path
import gzip
import hashlib
import json
import shutil

R = Path.cwd()
A = R/'results/arch/qw_d2d_status_source_1019'
dest = A/'receipts'
dest.mkdir(exist_ok=True)
for name in ('functional','functional_private40_evidence','functional_initial_import_FAIL',
             'pair_wrong_plan_FAIL','pair_initial_fixture_FAIL'):
    src = R/name
    if src.exists():
        for p in sorted(src.rglob('*')):
            if p.is_file() and 'obj' not in p.parts and p.suffix not in ('.o','.a'):
                out = dest/name/p.relative_to(src)
                out.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(p,out)
for name in ('native','native_private40_FAIL','native_paramod_keep_FAIL','native_initial_import_FAIL'):
    src=R/name
    for basename in ('native_synth.log','census.log','all_roots_full.tsv','pickup_all_roots.tsv','cells.tsv','source_mapped.v'):
        p=src/basename
        if not p.exists():
            continue
        out=dest/name/basename
        out.parent.mkdir(parents=True,exist_ok=True)
        if p.suffix in ('.v','.tsv') or p.stat().st_size > 500_000:
            out=out.with_name(out.name+'.gz')
            with out.open('wb') as file:
                file.write(gzip.compress(p.read_bytes(),mtime=0))
        else:
            shutil.copyfile(p,out)
manifest={str(p.relative_to(A)):hashlib.sha256(p.read_bytes()).hexdigest()
          for p in sorted(dest.rglob('*')) if p.is_file()}
(A/'receipts_sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PACKAGED',len(manifest),'files')
