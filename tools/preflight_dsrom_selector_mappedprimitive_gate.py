"""Read-only local tool/headroom preflight. No launch, lease or build."""
import argparse
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import prepare_dsrom_selector_mappedprimitive_gate as P

def verify_package(package):
    pins=json.loads((package/'artifact_manifest.json').read_text())
    expected=json.loads((P.BASE/'package/artifact_manifest.json').read_text())
    if pins!=expected:raise ValueError('reviewed package manifest changed')
    for path,h in pins.items():
        if P.sha((package/path).read_bytes())!=h:raise ValueError('package source changed: '+path)
    return len(pins)

def verify_tools():
    plan=json.loads((P.ROOT/'results/rtl/dsrom_balanced_selector_candidate_prepare_20261002/compile_proposal.json').read_text())
    observed=[]
    for e in plan['tool_observations']:
        p=Path(e['path']);h=P.sha(p.read_bytes())
        if h!=e['sha256']:raise ValueError('reviewed tool hash changed: '+str(p))
        observed.append(dict(path=str(p),sha256=h))
    tool=plan['tool_observations'][0]['path']
    r=subprocess.run([tool,'--version'],capture_output=True,text=True,check=True)
    if not r.stdout.startswith('Verilator 5.050 '):raise ValueError('explicit5.050 version required')
    return dict(version=r.stdout.strip(),binaries=observed,commands=['--version'])

def preflight(package):
    count=verify_package(package)
    tools=verify_tools()
    fsize=resource.getrlimit(resource.RLIMIT_FSIZE)
    if fsize!=(resource.RLIM_INFINITY,resource.RLIM_INFINITY):raise ValueError('unlimited FSIZE required; no configuration changed')
    memory={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        k,v=line.split(':',1)
        if k in ('MemTotal','MemAvailable'):memory[k+'_bytes']=int(v.split()[0])*1024
    disk=shutil.disk_usage(package)
    return dict(status='READ_ONLY_PREFLIGHT_PASS_NOT_GO_OR_LEASE',package_hashes_verified=count,
        tools=tools,host_admission_observations=dict(cpu_affinity=list(sorted(os.sched_getaffinity(0))),
        load_average=list(os.getloadavg()),memory=memory,disk_free_bytes=disk.free,disk_total_bytes=disk.total),
        FSIZE='infinity',memory_or_disk_or_CPU_lease_reserved=False,live_jobs_reused_or_changed=False,
        HDL_frontend_executed=False,compile_GO=False,physical_admitted=False,integrated_parent_admitted=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('fresh preflight receipt required')
    P.write(a.out,preflight(a.package))
