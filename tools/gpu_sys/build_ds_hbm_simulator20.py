"""Build the persistent real DS20 backend; no inference, run or timer cap."""
import argparse
import json
from pathlib import Path
import subprocess
from tools.gpu_sys import ds_hbm_cluster_sources as S
from tools.gpu_sys.ds_hbm_simulator20 import sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--enable',action='store_true',required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    source=[s for s in S.sources20() if not s.startswith('rtl/test/')]
    source+=['tools/gpu_sys/sim20/ot_ds_hbm_simulator20.sv']
    server=S.ROOT/'tools/gpu_sys/sim20/server.cpp'
    command=[str(S.VERILATOR),'--cc','--exe','--build','--timing','-O2','-j','4',
        '-Wno-fatal','-Wno-lint','-Wno-style','-Wno-WIDTH','--x-assign','0','--x-initial','0',
        '--top-module','ot_ds_hbm_simulator20','-GENABLE=1','--Mdir',str(a.out/'obj'),
        '-CFLAGS','-std=c++17',str(server),*[str(S.ROOT/s) for s in source]]
    with (a.out/'build.log').open('w') as log:
        result=subprocess.run(command,cwd=S.ROOT,stdout=log,stderr=subprocess.STDOUT)
    executable=a.out/'obj/Vot_ds_hbm_simulator20'
    record=dict(compile_rc=result.returncode,source_sha256={s:sha(S.ROOT/s) for s in source},
        server_sha256=sha(server),executable=str(executable),
        executable_sha256=sha(executable) if result.returncode==0 else None,
        topology=dict(dies=2,sms_per_die=2,partitions_per_die=2,sector_words=2097152),
        clock_ps=dict(sm=833,mem=1000,link=900,host=4000),
        numerical_qualified=False,protected_production_backend_qualified=False)
    (a.out/'build.json').write_text(json.dumps(record,indent=2)+'\n')
    return result.returncode


if __name__=='__main__':raise SystemExit(main())
