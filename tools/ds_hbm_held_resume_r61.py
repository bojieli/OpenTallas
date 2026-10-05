"""Default-off same-PID resource admission; SIGCONT once, never restart/kill.
No actor patch, no affinity/time/memory/file caps. Start ticks, argv and source
pins checked before admission. Exits if another owner already resumed/exited.
"""
import argparse,json,os,signal,time
from pathlib import Path
from ds_hbm_checkpoint_phase_ram_r61 import ROOT,verify_sources


def start_ticks(proc):return int((proc/'stat').read_text().rsplit(')',1)[1].split()[19])

def admission(available,required):
    if type(available)is not int or type(required)is not int or required<=0:raise ValueError('source-sized positive admission required')
    return available>=required


def main():
    p=argparse.ArgumentParser();p.add_argument('--contract',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--resume-same-pid',action='store_true',required=True);a=p.parse_args()
    c=json.loads(a.contract.read_bytes());verify_sources(c['source_sha256'])
    required=c['resume_MemAvailable_required_bytes'];pid=c['PID'];proc=Path('/proc')/str(pid)
    if a.out.exists():raise ValueError('fresh controller receipt required')
    record=dict(status='WAITING_SOURCE_SIZED_RAM_FOR_SAME_PID',controller_PID=os.getpid(),producer_PID=pid,required_bytes=required,signal_sent=False,source_changes=False,process_restart=False)
    def save():a.out.write_text(json.dumps(record,indent=2)+'\n')
    save()
    if not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'):raise ValueError('exact same-process pidfd signaling required')
    if not proc.exists():record['status']='PRODUCER_EXITED_NO_SIGNAL';save();return
    if start_ticks(proc)!=c['start_ticks']:raise ValueError('PID identity differs before pidfd')
    producer_fd=os.pidfd_open(pid)
    while True:
        if not proc.exists():record['status']='PRODUCER_EXITED_NO_SIGNAL';save();return
        if start_ticks(proc)!=c['start_ticks']:raise ValueError('PID reused; no signal')
        argv=[v.decode() for v in (proc/'cmdline').read_bytes().split(b'\0') if v]
        if argv!=c['producer_argv'] or str((proc/'cwd').resolve())!=c['producer_cwd']:raise ValueError('producer identity changed')
        state=next(l.split()[1] for l in (proc/'status').read_text().splitlines() if l.startswith('State:'))
        if state not in ('T','t'):
            record['status']='PRODUCER_NOT_HELD_NO_SIGNAL';save();return
        mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
        record.update(sample_ns=time.time_ns(),MemAvailable_bytes=mem,margin_bytes=mem-required);save()
        if admission(mem,required):
            verify_sources(c['source_sha256'])
            if start_ticks(proc)!=c['start_ticks']:raise ValueError('PID reuse at signal')
            signal.pidfd_send_signal(producer_fd,signal.SIGCONT)
            record.update(status='SAME_PINNED_PRODUCER_RESUMED_SOURCE_RAM_ADMITTED',signal_sent=True,signal='SIGCONT',resumed_ns=time.time_ns());save();return
        time.sleep(5)

if __name__=='__main__':main()
