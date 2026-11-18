#!/usr/bin/env python3
"""s81_svc_ref_bind.py -- the svc memory-closure reference of ONE S81 bind, as one command (FABLE-FIX-S81-SVC2 11-17).

Every S81 bind event runs this once after the bind (before its svc kits are released):

  python3 tools/die_plan/s81_svc_ref_bind.py PLAN --out BIND_OUT --asbuilt ASBUILT --src-tree SRC --tag d8d [--work DIR]

It writes the unclosed T7 kit RTL (bind.py kit-rtl --type svc_lo_dsdv_svc_rs__t7, no kit_rtl_post step), reads the stage
digest of its bound and
  * exits 0 "HAVE" when a reference of that digest already exists (s81_svc_memory_closure.cur_ref takes it);
  * else regenerates results/rtl/s81_svc_memory_fit_1103/ref_<tag>_main with s81_svc_ref_regen2.py (its own proofs:
    no reference token in the residual, T7 self-check 12605dc2, ported chain same as preimage) and exits with its code.
OLD sources = results/rtl/s81_svc_memory_fit_1103/ref_old_src (dsdv_svc_att.sv, dsdv_svc_rs.sv of the 61c902f1 bind);
NEW sources = the same two files found under SRC/rtl.  Nothing else is changed; the new directory is committed with the
event.  Why: D7w kit_rtl failed on four svc_lo types ("reference net 673_Y not structurally mapped") because the bind
staged dsdv_svc_att.sv under a new digest and nobody regenerated the reference.
"""
import argparse, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
T7 = 'svc_lo_dsdv_svc_rs__t7'
FILES = ('dsdv_svc_att.sv', 'dsdv_svc_rs.sv')


def have(CL, digest):
    return next((d for d in CL.ref_dirs() if CL.stage_digest(CL.load_ref(d)[0]) == digest), None)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('plan'); ap.add_argument('--out', required=True); ap.add_argument('--asbuilt', required=True)
    ap.add_argument('--src-tree', required=True); ap.add_argument('--tag', required=True, help='bind event name, e.g. d8d')
    ap.add_argument('--work', help='scratch dir (default a temp dir)')
    ap.add_argument('--bound', help='an existing unclosed T7 bound: skip kit-rtl')
    a = ap.parse_args()
    import s81_svc_memory_closure as CL
    work = Path(a.work or tempfile.mkdtemp(prefix='svc_ref_')); work.mkdir(parents=True, exist_ok=True)
    bound = Path(a.bound) if a.bound else work / 't7_rtl' / ('s81p_%s_bound.sv' % T7)
    if not a.bound:
        subprocess.run([sys.executable, str(HERE / 'bind.py'), 'kit-rtl', a.plan, '--out', a.out, '--asbuilt', a.asbuilt,
                        '--type', T7, '--src-tree', a.src_tree, '--kit', str(work / 't7_rtl')], check=True)
    text = bound.read_text()
    if (work / 't7_rtl' / 'memory_closure.json').exists() or not CL.applies(text):
        sys.exit('S81_SVC_REF: %s is not an unclosed native-helper T7 bound' % bound)
    digest = CL.stage_digest(text)
    if not digest: sys.exit('S81_SVC_REF: no structural_full stage digest in ' + str(bound))
    d = have(CL, digest)
    if d:
        print('S81_SVC_REF HAVE', digest, d.name); return
    dest = CL.REF_ROOT / ('ref_%s_main' % a.tag)
    if dest.exists(): sys.exit('S81_SVC_REF: %s exists with another digest; choose another --tag' % dest)
    new = work / 'new'; new.mkdir(exist_ok=True)
    for f in FILES:
        hits = sorted(Path(a.src_tree, 'rtl').rglob(f))
        if len(hits) != 1: sys.exit('S81_SVC_REF: expected one %s under %s/rtl, found %d' % (f, a.src_tree, len(hits)))
        shutil.copy(hits[0], new / f)
    tmp = work / 'ref_out'
    rc = subprocess.run([sys.executable, '-I', str(HERE / 's81_svc_ref_regen2.py'), str(bound), str(tmp),
                         '--old-src', str(CL.REF_ROOT / 'ref_old_src'), '--new-src', str(new)]).returncode
    if rc or not (tmp / 'ref_map.json').exists():
        sys.exit('S81_SVC_REF REFUSED rc=%d (evidence %s): try s81_svc_ref_regen2.py --modes / --drop-loc by hand' % (rc, tmp))
    shutil.copytree(tmp, dest)
    assert have(CL, digest) == dest
    print('S81_SVC_REF WROTE', digest, dest)


if __name__ == '__main__':
    main()
