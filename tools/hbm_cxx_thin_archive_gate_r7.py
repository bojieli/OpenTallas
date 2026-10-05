#!/usr/bin/env python3
"""Cold make + exact thin-archive membership gate; no old object/binary reuse."""
import argparse,json,subprocess,sys
from pathlib import Path
import hbm_ds_frontend_reuse as I
AR=Path('/usr/bin/ar')
def generated_objects(root):
    names=[];group=None
    for line in (root/'Vconnected_classes.mk').read_text().splitlines():
        s=line.strip()
        if s.startswith('VM_') and (' +=' in s or ' =' in s):group=s.split()[0]
        elif group and s.startswith(('Vconnected','verilated')):
            if group in ('VM_CLASSES_FAST','VM_CLASSES_SLOW','VM_SUPPORT_FAST','VM_SUPPORT_SLOW'):
                names.extend(x+'.o' for x in s.rstrip('\\').split())
        else:group=None
    if not names or len(names)!=len(set(names)) or any(Path(n).name!=n for n in names):
        raise ValueError('invalid generated object census')
    return names

def verify_archive(root):
    archive=root/'Vconnected__ALL.a';binary=root/'Vconnected';want=generated_objects(root)
    with archive.open('rb') as f:
        if f.read(8)!=b'!<thin>\n':raise ValueError('GNU thin archive required')
    members=subprocess.check_output([str(AR),'t',str(archive)],text=True).splitlines()
    # GNU ar can display absolute paths when listing an absolute thin archive.
    paths=[Path(n) if Path(n).is_absolute() else archive.parent/Path(n) for n in members]
    if any(p.is_symlink() or p.resolve().parent!=root.resolve() for p in paths):raise ValueError('archive escapes fresh object root')
    got=[p.name for p in paths]
    if len(got)!=len(set(got)) or set(got)!=set(want):raise ValueError('archive membership incomplete or unexpected')
    for name in want:
        p=root/name
        if p.is_symlink() or not p.is_file():raise ValueError('regular cold-built object required')
        with p.open('rb') as f:
            if f.read(4)!=b'\x7fELF':raise ValueError('invalid cold-built object')
    if binary.is_symlink():raise ValueError('regular linked binary required')
    with binary.open('rb') as f:
        if f.read(4)!=b'\x7fELF':raise ValueError('linked ELF binary required')
    return dict(verdict='PASS_COLD_CXX_EXACT_THIN_ARCHIVE_ONLY',generated_objects=len(want),
                archive_members=len(got),archive_bytes=archive.stat().st_size,
                archive_sha256=I.digest(archive),binary_sha256=I.digest(binary),
                membership_sha256=__import__('hashlib').sha256(json.dumps(sorted(got),separators=(',',':')).encode()).hexdigest(),
                arithmetic_or_RTL_substitution=False,compiled_objects_reused=False)

def execute(root,argv):
    # This wrapper only receives the reviewed parent's phase argv in fresh output.
    # -B remains mandatory even if the generated make recipe ignores archive errors.
    if not argv or argv[0]!='/usr/bin/make' or '-B' not in argv or 'AR=/usr/bin/ar --thin' not in argv:
        raise ValueError('reviewed cold make/thin flags required')
    if argv[argv.index('-C')+1]!=str(root):raise ValueError('make object root mismatch')
    rc=subprocess.call(argv)
    if rc:raise RuntimeError('cold make failed: '+str(rc))
    verdict=verify_archive(root)
    with (root.parent/'CXX_archive_receipt.json').open('x') as f:json.dump(verdict,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(verdict,sort_keys=True))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--object-root',type=Path,required=True);p.add_argument('make_argv',nargs=argparse.REMAINDER);a=p.parse_args()
    try:execute(a.object_root,a.make_argv[1:] if a.make_argv[:1]==['--'] else a.make_argv)
    except Exception as exc:raise SystemExit(str(exc))
