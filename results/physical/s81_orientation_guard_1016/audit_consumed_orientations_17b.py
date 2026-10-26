#!/usr/bin/env python3
import argparse,collections,gzip,hashlib,json,re
from pathlib import Path
BOUND_ORIENTS=('R0','MY','MX','R180')
def bound_view_orientation_contract(view, master=None):
    """Declared transforms of this hash-verified LEF, within placer support.

    No SYMMETRY declares R0 only. A placer accepting MY/MX is not evidence that
    an individual hard macro permits those transforms. This does not add any
    physical symmetry or qualify mirrored clock/PG/native timing invariants.
    """
    lines = view['text'].splitlines()
    macros = [(j, z.group(1)) for j, line in enumerate(lines)
              if (z := re.fullmatch(r'\s*MACRO\s+(\S+)\s*', line))]
    errors, symmetry = [], []
    targets = [(j, name) for j, name in macros if master is None or name == master]
    if len(targets) != 1:
        errors.append(f'expected exactly one verified MACRO {master!r}, found {len(targets)}')
    else:
        start, name = targets[0]
        next_macro = next((j for j, _ in macros if j > start), len(lines))
        end = next((j for j in range(start + 1, next_macro)
                    if lines[j].strip() == f'END {name}'), None)
        if end is None:
            errors.append(f'MACRO {name} has no matching END')
        else:
            declarations = []
            for line in lines[start + 1:end]:
                line = line.strip()
                if re.match(r'^(PIN|OBS)\b', line):
                    break
                if re.match(r'^SYMMETRY\b', line):
                    declarations.append(line)
            if len(declarations) > 1:
                errors.append('duplicate MACRO-header SYMMETRY declarations')
            elif declarations:
                match = re.fullmatch(r'SYMMETRY\s+([^;]+)\s*;\s*', declarations[0])
                if match is None:
                    errors.append('malformed MACRO-header SYMMETRY declaration')
                else:
                    symmetry = match.group(1).split()
                    if not symmetry or set(symmetry) - {'X', 'Y', 'R90'} or len(symmetry) != len(set(symmetry)):
                        errors.append(f'unknown or duplicate SYMMETRY tokens {symmetry}')
    legal = {'R0'}
    if 'X' in symmetry:
        legal.add('MX')
    if 'Y' in symmetry:
        legal.add('MY')
    if 'X' in symmetry and 'Y' in symmetry:
        legal.add('R180')
    if 'R90' in symmetry:
        legal.update(('R90', 'R180', 'R270'))
        if 'X' in symmetry or 'Y' in symmetry:
            legal.update(('MX', 'MY', 'MXR90', 'MYR90'))
    return dict(symmetry=symmetry, declared=sorted(legal) if not errors else [],
                supported=[o for o in BOUND_ORIENTS if o in legal] if not errors else [],
                errors=errors)

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);args=p.parse_args()
raw=(args.root/'results/arch/s81_native_20261013/view_binding_closed_0030b.json').read_bytes();table=json.loads(raw)['bound'];views={}
for master,entry in table.items():
 file=entry['files']['lef'];blob=(args.root/file['path']).read_bytes();digest=hashlib.sha256(blob).hexdigest();assert digest==file['sha256'],(master,digest)
 c=bound_view_orientation_contract({'text':blob.decode()},master);assert not c['errors'],(master,c)
 views[master]=dict(path=file['path'],sha256=digest,contract=c)
plan=json.load(gzip.open(args.plan,'rt'));bad=[];missing=collections.Counter()
for it in plan['insts']:
 view=views.get(it['master'])
 if view is None:missing[it['master']]+=1;continue
 if it['orient']not in view['contract']['supported']:bad.append(dict(instance=it['name'],master=it['master'],orientation=it['orient'],view_sha256=view['sha256']))
print(json.dumps(dict(source_commit=(args.root/'SOURCE_SHA').read_text().strip(),scope=plan['scope'],audit_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),table_sha256=hashlib.sha256(raw).hexdigest(),views=views,unsupported_instances=bad,summary=dict(verified_LEFs=len(views),unsupported_initial_instances=len(bad),unsupported_initial_families=len({x['master']for x in bad})),missing_initial_table_master_counts=dict(missing),warning='Pre-finalize only; later native aliases/placement/view skips must be reconciled with final GEN.'),indent=1))
