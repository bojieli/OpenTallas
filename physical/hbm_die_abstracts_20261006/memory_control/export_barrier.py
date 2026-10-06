#!/usr/bin/env python3
"""Reuse only barrier K32's retained routed artifact on E2; fresh CPU fit before guard.
No synthesis/route or repeated functional gate. Capacity refusal is terminal,
not an oversubscribed queued RAM-only guard. Run from a pinned remote checkout.
"""
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
PINNED_IMAGE='openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
INPUT_SHA={'odb':'0a876018c8a9cdc8231d7206892b32af6da55db740428ea1e1bc9975400343b2','spef':'f8ced04e846f0bedbf2454a7391e576632cf5bd413b9a900d6a57a160502dc1d','sdc':'dc105653e03b921eb8a6b589c88f8e46c00d0e9759b7b6dd0db6299a68524475'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def capacity():
 def cpu():
  a=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:]));return sum(a[:8]),a[3]+a[4]
 a=cpu();time.sleep(1);b=cpu();nc=os.cpu_count();idle=nc*(b[1]-a[1])/(b[0]-a[0]);load=os.getloadavg()[0]
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
 disk=os.statvfs('/srv/opentallas-scratch2');return {'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'CPU_count':nc,'load1':load,'idle_CPU_equivalents':idle,'MemAvailable_bytes':mem,'NVMe_free_bytes':disk.f_bavail*disk.f_frsize,'CPU_fit':idle>=1 and load+1<=nc}
def main():
 a=argparse.ArgumentParser();a.add_argument('--orfs-dir',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--tool',type=Path,required=True);args=a.parse_args()
 # E2 address is authoritative; do not execute OpenROAD locally or on another host.
 ips=subprocess.check_output(['hostname','-I'],text=True).split()
 if '5.199.165.105' not in ips:raise SystemExit('E2 only: refusing extraction on this host')
 guard=Path('/srv/opentallas-scratch/admit.sh');guard_hash=sha(guard)
 base=args.orfs_dir/'results/asap7/opentallas_ot_gpu_barrier_node_asap7_fmc_barrier_k32/base'
 for suffix,pin in INPUT_SHA.items():
  if sha(base/f'6_final.{suffix}')!=pin:raise SystemExit('retained routed hash mismatch: '+suffix)
 out=args.out;out.mkdir(parents=True,exist_ok=True);attempt=out/'launch_receipt.json'
 if attempt.exists():raise SystemExit('immutable launch receipt exists; choose distinct attempt directory')
 cap=capacity();rec={'schema':'opentallas.barrier-k32-export-admission.v1','capacity':cap,'guard_sha256':guard_hash,'input_sha256':INPUT_SHA,'tool_sha256':sha(args.tool),'image':PINNED_IMAGE,'requested_CPU':1,'reservation_GiB':4,'RAM_basis':'retained attention view export observed2GiB; barrier139standardcells; reserve4GiB without per-process cap','builds_replayed':0,'routes_replayed':0,'status':'CPU_CAPACITY_REFUSED'}
 attempt.write_text(json.dumps(rec,indent=2)+'\n')
 if not cap['CPU_fit'] or cap['MemAvailable_bytes']<104*1024**3 or cap['NVMe_free_bytes']<16*1024**3:raise SystemExit(66)
 # Guard implementation/reserve remains untouched. Its admitted child rechecks
 # CPU immediately, before starting any extraction; RAM acceptance alone is insufficient.
 script=Path(__file__).resolve()
 cmd=[str(guard),'4','--','python3',str(script),'--admitted','--orfs-dir',str(args.orfs_dir),'--out',str(out),'--tool',str(args.tool)]
 rec['status']='FRESH_CPU_FIT_BEFORE_GUARD';rec['command']=cmd;attempt.write_text(json.dumps(rec,indent=2)+'\n')
 p=subprocess.run(cmd);rec['exit']=p.returncode;rec['guard_unchanged']=sha(guard)==guard_hash;attempt.write_text(json.dumps(rec,indent=2)+'\n');raise SystemExit(p.returncode)
def admitted():
 if '5.199.165.105' not in subprocess.check_output(['hostname','-I'],text=True).split():
  raise SystemExit('E2 only: refusing admitted extraction on this host')
 import sys
 sys.argv.remove('--admitted');a=argparse.ArgumentParser();a.add_argument('--orfs-dir',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--tool',type=Path,required=True);args=a.parse_args()
 base=args.orfs_dir/'results/asap7/opentallas_ot_gpu_barrier_node_asap7_fmc_barrier_k32/base'
 for suffix,pin in INPUT_SHA.items():
  if sha(base/f'6_final.{suffix}')!=pin:raise SystemExit('retained hash changed while waiting')
 cap=capacity();(args.out/'post_guard_capacity.json').write_text(json.dumps(cap,indent=2)+'\n')
 if not cap['CPU_fit']:raise SystemExit(66)
 # Existing routed SDC's real IO timing remains in this leaf export. No new parent
 # closure or change to clock frequency/uncertainty is inferred from the views.
 cmd=['python3',str(args.tool),'--orfs-dir',str(args.orfs_dir),'--name','ot_gpu_barrier_node','--out',str(args.out),'--image',PINNED_IMAGE,'--tmp-dir',str(args.out/'tmp')]
 raise SystemExit(subprocess.run(cmd).returncode)
if __name__=='__main__':
 import sys
 if '--admitted' in sys.argv:admitted()
 else:main()
