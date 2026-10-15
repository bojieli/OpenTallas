#!/usr/bin/env python3
"""Real S81 BF16 weight-ROM head producer, replicated minimum-component proof.

Every exported root/logit comes from ot_dsrom_head_bundle and mapped ROM4096
models. Python only packs released weights and the declared xf input, and checks
RTL outputs. No expected root is supplied to the DUT. --xf is mandatory and must
be the native HC output; never silently substitute the reference final norm.
The default covers all four ranks. --groups is explicitly partial diagnostic.
This proves the replicated datapath, not die timing or native VM delivery.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_1m_head as H


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def group_starts(rank):
    # The rank has 32320 rows: overlap the final 64 rather than fabricate rows
    # or consume another rank's coefficients. Duplicates must agree bit exactly.
    base = rank * H.ROWS_RANK
    return [base + s for s in range(0, H.ROWS_RANK - 127, 128)] + [base + H.ROWS_RANK - 128]


def build(work):
    obj = work / 'obj'
    exe = obj / 'Vtb_dsrom_1m_head_bundle'
    sources = [ROOT / H.TB_BUNDLE] + [ROOT / p for p in H.BUNDLE_RTL]
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    key = dict(sources=hashes, CUT=511, SPLIT9=1, IOREG=1, SAFE=1)
    stamp = work / 'build.json'
    if exe.exists():
        if json.loads(stamp.read_text()) != key:
            raise RuntimeError('existing executable source mismatch; use a fresh work directory')
        return exe
    with (work / 'build.log').open('w') as log:
        subprocess.run([str(H.gate.VERILATOR), '--binary', '--timing', '-j', '8',
                        '-Wno-fatal', '-Wno-lint', '-Wno-style', '-O2',
                        '--top-module', 'tb_dsrom_1m_head_bundle', '-Mdir', str(obj),
                        '-GIOREG=1', '-GSAFE=1', '-GCUT=511', '-GSPLIT9=1'] + [str(p) for p in sources],
                       check=True, stdout=log, stderr=subprocess.STDOUT)
    stamp.write_text(json.dumps(key, indent=2) + '\n')
    return exe


def images(ck, xf, start, work, mutant):
    m = H.gate.Mat(ck, 'head', 'bf16', 128, H.K, r0=start)
    u = np.asarray(m.u16, dtype=np.uint64).copy()
    # Real weight-ROM corruption. Expected answers always use original weights.
    if mutant:
        u[0, 0] ^= 0x8000
    for q in range(4):
        H.write_macro(H.skewed_image(u[32*q:32*q+32, :4096].reshape(H.NW,16)), work, f'ha{q}')
    perm = np.array([32*(n % 4)+n//4 for n in range(128)])
    H.write_macro(H.skewed_image(u[perm,4096:].reshape(H.NW,16)), work, 'hb')
    x16 = xf.view(np.uint32) >> 16
    for name, xx, n in [('xa', x16[:4096],256), ('xb', x16[4096:],64)]:
        (work / f'{name}.hex').write_text(''.join(''.join(f'{int(v):04x}' for v in xx[i*16:i*16+16][::-1])+'\n' for i in range(n)))
    return m, perm


def run_group(exe, work, start, perm):
    proc = subprocess.run([str(exe), f'+DIR={work}', f'+OT_ROM_DIR={work}', f'+ROW0={start}'],
                          capture_output=True, text=True, check=True)
    (work / 'sim.log').write_text(proc.stdout + proc.stderr)
    aa, bb, ll, cycles = {q:[] for q in range(4)}, [], {q:[] for q in range(4)}, []
    result = None
    public = {}
    for line in proc.stdout.splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] == 'HEAD': public[int(t[1])] = (int(t[2],16),int(t[3]))
        if t[0] == 'A': aa[int(t[1])].append(int(t[2],16)); cycles.append(int(t[3]))
        if t[0] == 'B': bb.append(int(t[2],16)); cycles.append(int(t[3]))
        if t[0] == 'L': ll[int(t[1])].append(int(t[2],16)); cycles.append(int(t[3]))
        if t[0] == 'RES': result = dict(row=int(t[1]), bits=int(t[2],16), fault=int(t[3]),cycle=int(t[4]))
    if any(len(aa[q]) != 32 or len(ll[q]) != 32 for q in range(4)) or len(bb)!=128 or not result or result['fault']:
        raise RuntimeError(f'incomplete/faulted RTL group {start}: {result}')
    expected_logits = np.asarray(sum(ll.values(),[]),dtype=np.uint32)
    if set(public) != set(range(start,start+128)) or any(public[start+i][0] != int(expected_logits[i]) for i in range(128)):
        raise RuntimeError('physical head logit pins incomplete or differ from actual arithmetic')
    b = np.zeros(128,dtype=np.uint32); b[perm] = bb
    return np.asarray(sum(aa.values(),[]),dtype=np.uint32), b, np.asarray(sum(ll.values(),[]),dtype=np.uint32), result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--xf',type=Path,required=True,help='native HC xf.npy, float32 BF16-exact [5120]')
    p.add_argument('--xf-provenance',type=Path)
    p.add_argument('--component-input',action='store_true',help='declared external fixture boundary only; never native chain qualification')
    p.add_argument('--snapshot',type=Path,default=H.SNAP)
    p.add_argument('--ranks',default='0,1,2,3')
    p.add_argument('--groups',type=int,help='diagnostic only: first N groups of each rank')
    p.add_argument('--mutant',action='store_true',help='flip first weight sign in every tested group')
    a=p.parse_args()
    if a.groups is not None and a.groups < 1: p.error('--groups must be positive')
    a.work=a.work.resolve(); a.work.mkdir(parents=True,exist_ok=True)
    xf=np.load(a.xf)
    if xf.shape!=(5120,) or xf.dtype!=np.float32 or (xf.view(np.uint32)&65535).any() or not np.isfinite(xf).all():
        raise ValueError('native xf must be finite BF16-exact float32 [5120]')
    if not a.component_input and a.xf_provenance is None: p.error('native chaining requires --xf-provenance')
    provenance=(json.loads(a.xf_provenance.read_text()) if a.xf_provenance else {'producer':'declared external component fixture'})
    actual_mem=''.join(f'{int(v):04x}\n' for v in (xf.view(np.uint32)>>16)).encode()
    if not a.component_input and (provenance.get('gate') != 'PASS' or not provenance.get('rtl_sources')
            or provenance.get('actual_output_sha256') != hashlib.sha256(actual_mem).hexdigest()):
        raise ValueError('xf does not match passing native RTL producer provenance')
    H.setup_gate(); H.SK=11  # CUT511 + production SPLIT9 => eleven stages; skew follows
    exe=build(a.work); ck=H.Ckpt(a.snapshot)
    ranks=[int(r) for r in a.ranks.split(',')]
    if len(set(ranks))!=len(ranks) or any(r not in range(4) for r in ranks): raise ValueError('invalid ranks')
    summary=[]; total_bad=0; tmp=a.work/'active_group'; tmp.mkdir(exist_ok=True)
    for rank in ranks:
        roots=np.zeros((H.ROWS_RANK,2),dtype=np.uint32); logits=np.zeros(H.ROWS_RANK,dtype=np.uint32)
        seen=np.zeros(H.ROWS_RANK,dtype=bool)
        starts=group_starts(rank)
        if a.groups is not None: starts=starts[:a.groups]
        for start in starts:
            m,perm=images(ck,xf,start,tmp,a.mutant)
            ra,rb,lg,res=run_group(exe,tmp,start,perm)
            product=H.G.mul(np.asarray(m.wf,dtype=np.float32),xf[None,:])
            ea=H.G.bits(H.G.csum(product[:,:4096])).astype(np.uint32)
            rawb=H.G.csum(product[:,4096:]); eb=H.G.bits(H.G.add(H.G.add(rawb,np.float32(0)),np.float32(0))).astype(np.uint32)
            el=H.G.bits(H.G.csum(product)).astype(np.uint32)
            bad=int(np.count_nonzero(ra!=ea)+np.count_nonzero(rb!=eb)+np.count_nonzero(lg!=el)); total_bad+=bad
            i=start-rank*H.ROWS_RANK
            old=seen[i:i+128]
            if np.any(roots[i:i+128][old]!=np.stack([ra,rb],axis=1)[old]) or np.any(logits[i:i+128][old]!=lg[old]):
                raise RuntimeError('overlap disagrees')
            roots[i:i+128]=np.stack([ra,rb],axis=1); logits[i:i+128]=lg; seen[i:i+128]=True
            summary.append(dict(rank=rank,row0=start,bad=bad,rtl_result=res))
            (a.work/'groups.json').write_text(json.dumps(summary)+'\n')
            print(f'HEAD_FIELD rank={rank} row0={start} exact={bad==0} cycles={res["cycle"]}',flush=True)
        # These are exclusively RTL-produced roots. B has its two +0 levels;
        # the terminal's duplicate +0 padding preserves finite canonical bits.
        if seen.all():
            with (a.work/f'roots_r{rank}.mem').open('w') as f:
                for x,y in roots: f.write(f'{int(x):08x}{int(y):08x}\n')
        np.savez(a.work/f'rtl_rank{rank}.npz',roots=roots,logits=logits,seen=seen)
    if len({r['rtl_result']['cycle'] for r in summary}) != 1:
        raise RuntimeError('replicated groups violated fixed execution latency')
    complete=(set(ranks)==set(range(4)) and a.groups is None)
    record=dict(schema='opentallas.s81.native_head_field.v1',scope='replicated hardware component; VM delivery and die timing unqualified',
                complete_rows=complete,groups=len(summary),bad=total_bad,mutant=a.mutant,
                xf_sha256=sha(a.xf),xf_provenance=provenance,xf_provenance_sha256=sha(a.xf_provenance) if a.xf_provenance else None,
                native_xf_chained=not a.component_input,physical_head_logit_pins_checked=True,
                source=json.loads((a.work/'build.json').read_text()),checkpoint_header_sha256=ck.pins,
                b_root_format='root1024 padded with two RTL +0 stages',static_group_cycles=sorted({r['rtl_result']['cycle'] for r in summary}))
    (a.work/'record.json').write_text(json.dumps(record,indent=2)+'\n')
    return 0 if (total_bad>0)==a.mutant else 1
if __name__=='__main__': sys.exit(main())
