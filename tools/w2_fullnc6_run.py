#!/usr/bin/env python3
"""Enroll actual primary/secondary/codec/corrector with the fullNC6 fixture.
One new output per invocation; preserve every compile/runtime failure.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
from w2_fullnc6_fixture import selected_primary,selected_secondary

ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def cpu_sample():
    rows={}
    for line in Path('/proc/stat').read_text().splitlines():
        fields=line.split()
        if fields and fields[0].startswith('cpu') and fields[0][3:].isdigit():
            ticks=[int(x) for x in fields[1:9]]
            rows[int(fields[0][3:])]=(sum(ticks),ticks[3])
    return rows

def idle_cpu_equivalents(before,after,allowed):
    available=0.0
    for cpu in allowed:
        if cpu not in before or cpu not in after:continue
        total=after[cpu][0]-before[cpu][0];idle=after[cpu][1]-before[cpu][1]
        if total>0:available+=max(0.0,min(1.0,idle/total))
    return available

def choose_jobs(available,requested=None):
    free=math.floor(available)
    if free<1:raise ValueError('NO_LOCAL_CPU_HEADROOM')
    jobs=min(32,free) if requested is None else requested
    if jobs<1 or jobs>free:raise ValueError('REQUESTED_JOBS_EXCEED_MEASURED_CPU_HEADROOM')
    return jobs



class ObservedPayloadHook:
    """One existing payload clock hook with read-only receipt observation."""
    def __init__(self, payload, observer):
        self.payload, self.observer = payload, observer

    def before_edge(self):
        self.payload.before_edge()
        self.observer.before_edge()  # Snapshot AFTER actual payload drives.

    def after_edge(self):
        self.payload.after_edge()
        self.observer.after_edge()


def observe_registered_payload(pins, payload, observer):
    # Current enclosing source intentionally admits ONE payload hook only.
    # Wrap that exact registration; no second owner, boot, edge or grant.
    if pins.edge_open or pins.stopped or pins.hooks != [payload]:
        raise ValueError('connected observer requires the sole actual payload hook')
    pins.hooks[0] = ObservedPayloadHook(payload, observer)


def connected_runtime(binary, bindings, socket_path, out, *, portbook=None):
    """Existing fixture attached to the actual enclosing driver's two pipes.

    No compiler, arithmetic, memory provider, reset or handler is substituted.
    All sixteen handlers come from the source-owner factory. Socket EOF is
    recorded as session closure, never as full-token qualification.
    """
    import importlib
    import sys
    if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
    from tools.gpu_sys.canonical_qwen_ranked_simulator import RankedEnclosingPins as EnclosingPins, build
    scratch_installed=False
    if portbook is not None:
        from tools.gpu_sys.canonical_qwen_installed_services import InstalledServicePins as EnclosingPins
        book = json.loads(portbook.read_text())
        scratch_installed=book['top']=='ot_gpu_qwen_hbm_integrated_scratch'
        if scratch_installed:
            from tools.gpu_sys.canonical_qwen_installed_services import installed_scratch_pins_class
            from tools.gpu_sys.canonical_qwen_scratch_simulator import build
            EnclosingPins=installed_scratch_pins_class()
            if 'manifest_contract' in book:
                from tools.gpu_sys.canonical_qwen_manifest_simulator import ManifestEnclosingPins
                EnclosingPins=ManifestEnclosingPins
        if book['inventory'].get('source_owner_count') != 64:
            raise ValueError('connected installed sourcebook requires actual64 range owners')
        for path, digest in book['source_sha256'].items():
            if sha(ROOT/path) != digest:
                raise ValueError('connected installed source changed: '+path)
    from tools.gpu_sys.canonical_qwen_transport import UnixDeliveryServer
    from w2_fullnc6_fixture import ConnectedReceiptObserver
    module, separator, name = bindings.partition(':')
    if not separator or not module or not name:
        raise ValueError('connected bindings must be actual module:factory')
    factory = getattr(importlib.import_module(module), name)
    if not callable(factory):
        raise ValueError('actual connected factory missing')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip():
        raise ValueError('connected fixture source dirty')
    if not binary.is_file():
        raise ValueError('actual connected binary missing')
    if socket_path.exists():
        raise ValueError('existing connected socket is owned; refuse launch')
    out.mkdir()
    record = dict(status='STARTING_CONNECTED', pid=os.getpid(),
        fixture_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        binary=str(binary),binary_sha256=sha(binary),bindings=bindings,
        socket=str(socket_path),physical_or_fulltoken_admission=False)
    if portbook is not None:
        record.update(portbook=str(portbook),portbook_sha256=sha(portbook))
    def save():
        (out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    process=server=observer=pins=None
    try:
        with (out/'driver.stderr.log').open('w') as error_log:
            process=subprocess.Popen([str(binary)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                stderr=error_log,text=True,bufsize=1)
            record['driver_pid']=process.pid;save()
            pins=EnclosingPins(process.stdout,process.stdin,**({} if portbook is None else {'portbook':portbook}))
            bound=factory(pins)
            options={'enabled':True}
            if scratch_installed:options['matrix_services']=bound['matrix_services']
            runtime=build(pins,bound['authority'],bound['native_handlers'],bound['w2_ports'],**options)
            observer=ConnectedReceiptObserver(pins)
            actual_hook=runtime['payload']
            if scratch_installed:
                from tools.gpu_sys.canonical_qwen_scratch_simulator import SharedEdgeServices
                if len(pins.hooks)!=1 or not isinstance(pins.hooks[0],SharedEdgeServices) or pins.hooks[0].payload is not runtime['payload']:
                    raise ValueError('actual scratch/MATRIX services require the one enrolled shared edge')
                actual_hook=pins.hooks[0]
            observe_registered_payload(pins,actual_hook,observer)
            server=UnixDeliveryServer(socket_path,runtime['handlers'],require_kv=True)
            record['status']='CONNECTED_READY';save()
            print('CONNECTED_READY',process.pid,socket_path,flush=True)
            # Optional owner callback is actual boot/reset/provider enrollment.
            # Absence drives no fence or ready: downstream RTL stays unchanged.
            if 'enroll' in bound:
                if not callable(bound['enroll']):
                    raise ValueError('actual enrollment callback is not callable')
                bound['enroll']()
            server.serve_once()
            if server.session.stopped or pins.stopped:
                raise ValueError('connected source session stopped with retained debt')
            record['status']='CONNECTED_SESSION_CLOSED_NOT_TOKEN_VERDICT'
    except BaseException as error:
        record.update(status='FAIL_CONNECTED',error=repr(error));raise
    finally:
        if observer is not None:
            record.update(backend_accepts=observer.backend_accepts,
                client_terminals=observer.client_terminals,external_receipts=len(observer.receipts),
                reset_orphans=len(observer.orphans))
        if pins is not None:record['actual_edges']=pins.edges
        if server is not None:
            record['delivery_sequence']=server.session.sequence
            record['session_stopped']=server.session.stopped
            server.close()
        if process is not None:
            # Only this runner's pin process: EOF closes its input loop. Never
            # signal another owner's simulator or impose an elapsed deadline.
            process.stdin.close()
            process.stdout.close()
            record['driver_rc']=process.wait()
            if record['driver_rc'] and record['status']!='FAIL_CONNECTED':
                record['status']='FAIL_CONNECTED_DRIVER'
        save()
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--connected-binary',type=Path,help='actual enclosing pin driver, no standalone compile')
    p.add_argument('--connected-bindings',help='actual source owner module:factory(pins)')
    p.add_argument('--connected-portbook',type=Path,help='actual installed allocator/service sourcebook; checks pins before launch')
    p.add_argument('--connected-socket',type=Path,help='new socket for complete canonical client')
    p.add_argument('--primary-root',type=Path,default=Path('/home/ubuntu/w2-pc-exact-completion-model-20261003'))
    p.add_argument('--corrector-root',type=Path,default=Path('/tmp/Hubble-W2-corrector-rescue-20261003'))
    p.add_argument('--corrector-sha256',help='require exact admitted split-helper source hash')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--simulator',choices=['iverilog','verilator'],default='iverilog')
    p.add_argument('--jobs',type=int,help='compile workers; default up to32 from fresh measured idle CPUs')
    p.add_argument('--output-split',type=int,default=10000,help='generated C++ statements per file')
    p.add_argument('--output-split-cfuncs',type=int,default=1000,help='generated model statements per function')
    p.add_argument('--reset-quarantine',action='store_true',help='enroll matching opt-in reset-quarantine successor sources')
    p.add_argument('--reference-negative',choices=['omit','drop','drop_debt','consume'],
                   help='select one expected-FAIL reset receipt mutant in the existing fixture')
    p.add_argument('--fault-matrix',action='store_true')
    p.add_argument('--full-double-pairs',action='store_true')
    a=p.parse_args()
    connected=(a.connected_binary,a.connected_bindings,a.connected_socket)
    if any(connected):
        if not all(connected):p.error('connected binary/bindings/socket all required')
        if a.reference_negative or a.fault_matrix or a.full_double_pairs:
            p.error('connected gate does not launch standalone variants or fault matrix')
        result=connected_runtime(a.connected_binary.resolve(),a.connected_bindings,a.connected_socket,a.out,
                                 portbook=None if a.connected_portbook is None else a.connected_portbook.resolve())
        return int(result['status'].startswith('FAIL'))
    if a.full_double_pairs and not a.fault_matrix:p.error('--full-double-pairs requires --fault-matrix')
    # Run fixed fixture source, not evolving preparation changes.
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip():
        raise SystemExit('fixture tracked source is dirty')
    a.out.mkdir();inputs=a.out/'inputs';inputs.mkdir()
    files=[selected_primary(a.primary_root,a.reset_quarantine),
           selected_secondary(a.primary_root,a.reset_quarantine),
           a.primary_root/'rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv',
           a.corrector_root/'rtl/experimental/w2_nc6_correction_control_split_20261003/ot_w2_nc6_correction_control.sv',
           ROOT/'rtl/test/w2_fullnc6_functional_20261003/tb.sv']
    if a.corrector_sha256 and sha(files[3]) != a.corrector_sha256:
        raise SystemExit('split-helper source pin mismatch; no compile')
    pins={}
    for f in files:
        data=f.read_bytes();(inputs/f.name).write_bytes(data)
        pins[str(f)]=hashlib.sha256(data).hexdigest()
    record=dict(fixture_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_pins=pins,pid=os.getpid(),utc_start=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        capacity=dict(mem_available=next(x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')),
                      disk_free_bytes=shutil.disk_usage(a.out).free,affinity=sorted(os.sched_getaffinity(0)),load=os.getloadavg()),
        fault_matrix_selected=a.fault_matrix,full_double_pairs_selected=a.full_double_pairs,
        physical_or_fulltoken_admission=False,reset_quarantine_selected=a.reset_quarantine,reference_negative=a.reference_negative,
        reference_negative_expected='FAIL_RUNTIME' if a.reference_negative else None,status='COMPILING')
    def save(): (a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
    if a.simulator=='verilator':
        version=subprocess.check_output(['verilator','--version'],text=True).strip()
        if not version.startswith('Verilator 5.050 '):
            raise SystemExit('exact Verilator5.050 required')
        record['simulator_version']=version
        before=cpu_sample();time.sleep(0.25);after=cpu_sample()
        available=idle_cpu_equivalents(before,after,os.sched_getaffinity(0))
        record['capacity']['measured_idle_cpu_equivalents']=available
        record['capacity']['cpu_sample_seconds']=0.25
        try:jobs=choose_jobs(available,a.jobs)
        except ValueError as error:
            record.update(status='REFUSED_BEFORE_COMPILE',reason=str(error));save()
            raise SystemExit(str(error))
        record['compile_workers']=jobs
        cmd=['verilator','--binary','--timing','--top-module','tb_w2_fullnc6',
             '-Wno-fatal','-j',str(jobs),'--output-split',str(a.output_split),
             '--output-split-cfuncs',str(a.output_split_cfuncs),
             '--Mdir',str(a.out/'obj'),'-o',str(a.out/'gate.bin'),
             *[str(inputs/f.name) for f in files]]
    else:
        cmd=['iverilog','-g2012','-s','tb_w2_fullnc6','-o',str(a.out/'gate.bin'),*[str(inputs/f.name) for f in files]]
    record['simulator']=a.simulator
    record['compile_command']=cmd;save();print('COMPILE',os.getpid(),a.out,flush=True)
    t=time.monotonic()
    with (a.out/'compile.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
    record.update(compile_rc=r.returncode,compile_seconds=time.monotonic()-t);save()
    if r.returncode==0:
        record['binary_sha256']=sha(a.out/'gate.bin');record['status']='RUNNING';save()
        cmd=([str(a.out/'gate.bin')] if a.simulator=='verilator' else ['vvp',str(a.out/'gate.bin')])
        if a.fault_matrix:cmd.append('+fault_matrix')
        if a.full_double_pairs:cmd.append('+full_double_pairs')
        if a.reference_negative:cmd.append('+oracle_reset_'+a.reference_negative)
        record['runtime_command']=cmd;print('RUN',flush=True);t=time.monotonic()
        with (a.out/'runtime.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
        text=(a.out/'runtime.log').read_text()
        record.update(runtime_rc=r.returncode,runtime_seconds=time.monotonic()-t,
                      case_pass_lines=[x for x in text.splitlines() if x.startswith('CASE_PASS')],
                      measurement_lines=[x for x in text.splitlines() if x.startswith('MEASURE')])
        record['status']='PASS_FUNCTIONAL' if not a.reference_negative and r.returncode==0 and 'COMPONENT_PASS' in text else 'FAIL_RUNTIME'
        if a.reference_negative:
            expected_message={'omit':'rejected stale return retired reset-orphan debt',
                              'drop':'reset orphan receipt dropped without provider disposal',
                              'drop_debt':'external accepted receipt conservation',
                              'consume':'client terminal consumed quarantined reset orphan'}[a.reference_negative]
            record['reference_negative_expected_message']=expected_message
            record['reference_negative_observed_failure']=r.returncode!=0 and expected_message in text and 'COMPONENT_PASS' not in text
    else:record['status']='FAIL_COMPILE'
    record['source_pins_post']={str(f):sha(f) for f in files};save();print(record['status'],flush=True)
    return 0 if record['status']=='PASS_FUNCTIONAL' else 1

if __name__=='__main__':raise SystemExit(main())
