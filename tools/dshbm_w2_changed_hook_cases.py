#!/usr/bin/env python3
"""Changed production-hook cases, using ONE retained paired-SM executable.

Copy literal cached payload slices; no new checkpoint, golden or arithmetic.
Ordinary flag-OFF is not a compile-time PACK_W2=0 measurement.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from dshbm_sm_xmap_seq import parse_output


def run(work):
    cache=work/'case'
    receipt=json.loads((cache/'fixture.json').read_text())
    ds=receipt['composite_descriptors']
    lines=(cache/'lines.hex').read_text().splitlines()
    xs=(cache/'x.hex').read_text().splitlines()
    exe=work/'build/Vtb_hbm_accel_sm_w2_pair_seq'
    if not exe.is_file() or (work/'build/build.exit').read_text().strip()!='0':
        raise ValueError('require existing successful actual build; never build here')
    summary={}
    for name,k in [('ordinary_flag_off',0),('illegal_pair_shape',receipt['w2_groups'][0])]:
        p=work/name
        p.mkdir(exist_ok=False)
        d=ds[k].copy()
        line_offset=sum(q[4] for q in ds[:k])
        x_offset=sum((q[7] if q[6] else 0)+(q[13] if q[10] else 0) for q in ds[:k])
        nx=(d[7] if d[6] else 0)+(d[13] if d[10] else 0)
        if d[10]:
            d[11]-=line_offset  # B in copied same 64-line physical payload
            d[1]=7             # ONLY invalid c: production PACK shape needs 8
        elif k!=0 or d[10]:
            raise ValueError('ordinary cached first descriptor required')
        (p/'seq.hex').write_text('\n'.join(f'{v:08x}' for v in d)+'\n')
        (p/'lines.hex').write_text('\n'.join(lines[line_offset:line_offset+d[4]])+'\n')
        (p/'x.hex').write_text('\n'.join(xs[x_offset:x_offset+nx])+'\n')
        cmd=[str(exe),f'+DIR={p}','+NOPS=1','+TRACE']
        with (p/'runtime.log').open('w') as log:
            rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
        (p/'runtime.exit').write_text(str(rc)+'\n')
        got,meta,total=parse_output(p/'out.txt')
        faults=[m['fault'] for m in meta.values()]
        if name=='ordinary_flag_off':
            ref,_,_=parse_output(cache/'reference_out.txt')
            want={key:v for key,v in ref.items() if key[0]==d[14]}
            exact=set(got)==set(want) and all((got[key]&0xffffffff)==(v&0xffffffff) for key,v in want.items())
            ok=rc==0 and exact and len(meta)==1 and faults==[0] and total is not None
        else:
            # Sticky fault must be observed; no output-value or performance
            # qualification of malformed input is claimed.
            ok=rc==0 and ' FAULT' in (p/'runtime.log').read_text() and faults==[1] and total is not None
        summary[name]=dict(pass_check=ok,runtime_returncode=rc,faults=faults,
            outputs=len(got),total_cycles=total,cached_descriptor_index=k,
            copied_line_slice=[line_offset,line_offset+d[4]],copied_x_slice=[x_offset,x_offset+nx],
            stimulus_change='c8->c7 only' if d[10] else None,
            executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
            compiletime_default_off_tested=False,no_build=True,no_golden_generation=True)
        (p/'result.json').write_text(json.dumps(summary[name],indent=2)+'\n')
    (work/'changed_hook_cases.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))
    return 0 if all(x['pass_check'] for x in summary.values()) else 1


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--work',type=Path,required=True)
    raise SystemExit(run(a.parse_args().work.resolve()))
