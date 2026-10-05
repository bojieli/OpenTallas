#!/usr/bin/env python3
"""Build only existing native TOPK merge leaf, never a self-driving fixture.

Explicit source-pinned geometry and prospective finite port/capture costs.
No numerical stimulus, host select, benchmark or hardware timing admission.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
RTL=ROOT/'rtl/chip/ot_coll_topk_merge.sv'
PARAMETERS=dict(N=4,NMAX=512,LW=16,LDW=4,P=64,PF=64,DIG=8)


def model(nmax=512):
    if nmax==2048:
        m=model(512)
        m.update(parameters=dict(PARAMETERS,NMAX=2048),
            producer="L20.I50 native2048/rank IDs + L20.I51 native gather -> L20.I52 COLL_TOPK",
            stride=32768,input_bytes=65536,output_bytes_per_rank=8192,
            native_candidate_RAM_bits=524288,native_load_edges=256,
            native_unstalled_select_cycles_source_formula=677,
            source_vm_reads_per_rank=4096,software_prefetch_bytes=65536,
            reserved_nonbackpressurable_output_bits=65536,software_output_hold_one_copy_bytes=8192,
            min_VM_scalar_prefetch_shared_edges=4096,prospective_chain_min_cycles=4096+256+677)
        m.update(existing_native_measurement=dict(path='results/rtl/w15_topk_merge_l20.json',
            case='l20_candidate_blocks',cycles=675,scope='historical standalone go-to-done, not this provider runtime'),
            historical_transport_732=dict(path='results/rtl/w15_collectives_topk_ss.json',
                configuration='v41ss_lm_w32_topk',bytes_committed_per_die=4096,
                cycles=732,applicable_to_I52_8192_byte_commit=False),
            native_clocked_load_bytes_per_cycle=256,peak_native_output_bytes_per_cycle=256,
            source_VM_read_bytes_per_shared_cycle=16,
            topology='one existing native merge leaf, four existing rank VMs; output replicated by four actual publishers',
            prospective_chain_min_ns=(4096+256+677)*0.833,
            area_composition='existing NMAX2048 W15 leaf reused once, not four copies; native RAM 524288 bits; no new engine RTL or slot enlargement',
            publication_and_reverse_stall_bound='actual same-VM leases/ACKs required; no zero-latency or finite deadline claim')
        return m
    if nmax!=512: raise ValueError("unsupported native geometry")
    return dict(source='rtl/chip/ot_coll_topk_merge.sv',parameters=PARAMETERS,
        MACs_per_cycle=0,arithmetic='native radix ordered binary32 key TOPK; no host comparison',
        producer='L20.I45 native512/rank ID +L20.I46 native score gather ->L20.I47 COLL_TOPK',
        stride=262144,input_bytes=16384,output_bytes_per_rank=2048,
        input_bits_per_native_load_edge=2048,output_bits_per_native_edge=2048,
        native_candidate_RAM_bits=2*4*512*32,native_load_edges=64,
        native_unstalled_select_cycles_source_formula=4*(2048//64+7)+2048//64+9,
        source_vm_reads_per_rank=1024,software_prefetch_bytes=16384,
        reserved_nonbackpressurable_output_bits=512*32,
        max_output_words_per_edge=4,real_destination_receivers=4,
        software_output_hold_one_copy_bytes=2048,per_rank_publication_positions=4,
        fixed_new_hardware_FF_claim=0,
        min_VM_scalar_prefetch_shared_edges=1024,
        positive_VM_visibility_required_before_completion=True,
        capture_to_VM_ACK_latency='existing same-VM real accepted/ACK path; held-ready stalls included by caller',
        prospective_chain_min_cycles=1024+64+197,
        shared_functional_clock_ps=833,clock_SS_FF_qualified=False,
        track_demand_signal_bits=4096,channel_track_capacity=None,
        area_and_slot='Reuse original W15 native TOPK geometry; no new RTL/physical adoption',
        area_mm2=None,added_routing_and_fanout=None,replica_count=1,
        whole_token_latency_ns=None,hardware_admission=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--source-commit',required=True)
    p.add_argument('--rtl-sha256',required=True)
    p.add_argument('--verilator',required=True)
    p.add_argument('--jobs',type=int,default=2)
    p.add_argument('--nmax',type=int,choices=(512,2048),default=512)
    a=p.parse_args()
    parameters=dict(PARAMETERS,NMAX=a.nmax)
    actual=hashlib.sha256(RTL.read_bytes()).hexdigest()
    if actual!=a.rtl_sha256:raise ValueError('selected native source changed')
    if not 1<=a.jobs<=os.cpu_count():raise ValueError('worker count exceeds host capacity')
    mem={k:int(v.split()[0])*1024 for k,v in (l.split(':',1) for l in Path('/proc/meminfo').read_text().splitlines())}
    disk=os.statvfs(a.out.parent)
    if mem['MemAvailable']<4*1024**3 or disk.f_bavail*disk.f_frsize<4*1024**3:
        raise RuntimeError('no measured4GiB memory/disk headroom')
    if os.getloadavg()[0]+a.jobs>os.cpu_count():raise RuntimeError('no shared CPU headroom')
    a.out.mkdir(parents=True,exist_ok=False)
    data=dict(source_commit=a.source_commit,rtl_sha256=actual,geometry=parameters,
              headroom=dict(available_bytes=mem['MemAvailable'],load=os.getloadavg(),cpus=os.cpu_count()),
              source_model=model(a.nmax))
    (a.out/'inputs.json').write_text(json.dumps(data,indent=2)+'\n')
    argv=[a.verilator,'--cc','--build','--top-module','ot_coll_topk_merge',
          '--prefix',f'VDsromTop{a.nmax}','--Mdir',str(a.out/'obj'),'-j',str(a.jobs),
          '-CFLAGS','-fPIC','-Wno-fatal']+[f'-G{k}={v}' for k,v in parameters.items()]+[str(RTL)]
    started=time.time()
    with (a.out/'compile.log').open('w') as log:
        r=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT)
    result=dict(returncode=r.returncode,elapsed_s=time.time()-started,argv=argv,
                status='NATIVE_LEAF_COMPILE_ONLY' if r.returncode==0 else 'FAIL_COMPILE',
                runtime_qualified=False,physical_qualified=False)
    (a.out/'terminal.json').write_text(json.dumps(result,indent=2)+'\n')
    raise SystemExit(r.returncode)


if __name__=='__main__':main()
