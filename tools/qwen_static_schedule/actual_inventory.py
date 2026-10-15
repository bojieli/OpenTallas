#!/usr/bin/env python3
"""Expose every actual emitted PC needing a native fixed-latency microcalendar."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_qwen_fullshape_isa_w12 as ISA
from qwen_static_schedule.calendar import inventory, sha


def requirements(programs):
    out=[]
    for record in inventory(programs):
        f=ISA.decode_instruction(int(record['word'],16))
        unit=f['unit']
        need=['native instruction issue', 'exact native completion']
        shape={}
        if unit==1:
            shape={k:f[k] for k in ('me_wsrc','me_xbase','me_xks','me_xcs','me_xjs','me_k','me_nout','me_split','me_d_k','me_d_nout','me_obase')}
            need += ['native attention service/calendar' if f['me_wsrc'] else 'ROM macro read/scale/matvec/reduction calendar', 'actual operand delivery', 'actual result commits']
        elif unit==2:
            shape={k:f[k] for k in ('su_nin','su_nout','su_d_nin','dst','d_base','d_si','d_so','d_d','a_base','a_si','a_so','b_base','b_si','b_so','c_base','c_si','c_so')}
            need += ['three actual SU descriptor/VM read ports', 'native arithmetic operation latency/II', 'actual SU write masks and commits']
        elif unit==0:
            need += ['native segment END/collective handoff calendar']
        else:
            need += ['explicit unsupported-unit native implementation']
        out.append(dict(record,unit=unit,shape=shape,required_contracts=need,status='NATIVE_MICROCALENDAR_REQUIRED'))
    return dict(schema='opentallas.qwen-static-program-requirements.v1',
        status='NOT_SCHEDULED',program_sha256=[sha(p) for p in programs],instructions=out,
        source_sha256={str(Path(ISA.__file__).resolve()):sha(ISA.__file__)},
        claim='Actual encoded PC inventory only; no guessed latencies, runtime traces or modeled memory scheduling.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--program',type=Path,action='append',required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(requirements(a.program),indent=2)+'\n')

if __name__=='__main__':main()
