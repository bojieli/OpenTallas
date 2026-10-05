#!/usr/bin/env python3
"""Small-process cap verification only, never invokes RTL tools."""
import argparse,json,os,sys
from pathlib import Path
import run_observer_capped_lint as runner

def verify(out):
    out=Path(out);out.mkdir(exist_ok=False)
    probes=[('limits','import os,resource,json; print(json.dumps(dict(affinity=sorted(os.sched_getaffinity(0)),address_space=resource.getrlimit(resource.RLIMIT_AS),core=resource.getrlimit(resource.RLIMIT_CORE))))',2,runner.MEMORY,runner.LOG),
        ('wall_negative','import time; time.sleep(20)',0.15,runner.MEMORY,runner.LOG),
        ('log_negative','import os; os.write(1,b"x"*65536)',2,runner.MEMORY,1024),
        ('memory_negative','a=bytearray(128*1024**2)',2,64*1024**2,runner.LOG)]
    records=[]
    for name,code,seconds,memory,log in probes:
        record=runner.supervise([sys.executable,'-c',code],out,dict(os.environ),out/(name+'.log'),seconds,memory,log)
        records.append(dict(name=name,**record))
    limits=json.loads((out/'limits.log').read_text())
    assert len(limits['affinity'])==2 and limits['address_space']==[runner.MEMORY]*2 and limits['core']==[0,0]
    assert records[1]['cap_reason']=='WALL_CAP' and records[1]['returncode']!=0
    assert records[2]['cap_reason']=='LOG_CAP' and records[2]['log_bytes']<=1024
    assert records[3]['returncode']!=0 and 'MemoryError' in (out/'memory_negative.log').read_text()
    result=dict(status='CAP_VERIFIED_WITH_SMALL_PYTHON_CHILDREN_NO_COMPILER_EXECUTION',probes=records,compiler_execution=False,limits_observed=limits,scope='Direct frontend gets hard address-space4GiB and inherited two-CPU affinity; total gate stdout+stderr capped16MiB, baseline60s/mutant30s enforced by same tested supervisor; no compiler cost measurement')
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();print(verify(a.out)['status'])
