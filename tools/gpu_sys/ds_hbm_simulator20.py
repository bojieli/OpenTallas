"""Persistent actual Verilator CP20/SM20 pins, with preloaded source images.

No ABI3 reinterpretation, native arithmetic emulation, clocks synthesized in
Python, timeout or oracle fallback. Fixed backend topology is two dies, two
SMs/die, two memory partitions/die, each 2M 32-byte sectors.
"""
import hashlib
import json
from pathlib import Path
import subprocess


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):
            h.update(block)
    return h.hexdigest()


class Simulator20:
    def __init__(self, executable, manifest, *, enable=False, log_dir):
        if not enable:
            raise ValueError('explicit actual simulator enable required')
        manifest=Path(manifest).resolve()
        self.source=json.loads(manifest.read_text())
        if self.source.get('schema')!='opentallas.ds_hbm.simulator20_source.v1':
            raise ValueError('source-native simulator manifest required; not ABI3 deployment')
        if self.source['topology']!={'dies':2,'sms_per_die':2,'partitions_per_die':2,'sector_words':2097152}:
            raise ValueError('source image/backend topology mismatch')
        if not 1<=self.source['position_extent']<=1048576:
            raise ValueError('source context extent')
        root=manifest.parent
        required={f'prog_d{d}_s{s}.hex' for d in range(2) for s in range(2)}
        required|={f'mem_d{d}_p{p}.hex' for d in range(2) for p in range(2)}
        if not required<=self.source['artifacts'].keys():
            raise ValueError('complete actual instruction and memory image census required')
        for name,digest in self.source['artifacts'].items():
            if Path(name).name!=name or sha(root/name)!=digest:
                raise ValueError('source image hash mismatch: '+name)
        # Image/preparation source lineage is checked separately from payload hashes.
        origin=root/self.source['origin_manifest']
        if sha(origin)!=self.source['origin_sha256']:
            raise ValueError('source preparation lineage mismatch')
        original=json.loads(origin.read_text())
        for name,digest in original['artifacts'].items():
            if name not in self.source['artifacts'] or self.source['artifacts'][name]!=digest:
                raise ValueError('original instruction/source payload changed: '+name)
        if original['entries']!=self.source['entries']:
            raise ValueError('entry addresses differ from loaded instruction source')
        log_dir=Path(log_dir).resolve();log_dir.mkdir(parents=True,exist_ok=False)
        # The pinned memsys adapter supplies IMAGE_PREFIX=die0/die1 and
        # leaves partition DIE_IDX at -1. A global plusarg would override
        # BOTH dies with one namespace; never supply that override here.
        for die in range(2):
            for part in range(2):
                (log_dir/f'die{die}_p{part}.hex').symlink_to(
                    root/f'mem_d{die}_p{part}.hex')
        self.log=(log_dir/'simulator.log').open('w')
        self.process=subprocess.Popen([str(Path(executable).resolve())],
            cwd=log_dir,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=self.log,text=True,bufsize=1)
        self.closed=False
        self._rpc('RESET')
        for die in range(2):
            for sm in range(2):
                path=root/f'prog_d{die}_s{sm}.hex'
                if any(c.isspace() for c in str(path)):
                    raise ValueError('instruction image path contains whitespace')
                self._rpc(f'LOAD {die} {sm} {path}')
        snap=self.snapshot()
        if not snap['rst_sm_n'] or snap['sys_fault']:
            raise RuntimeError('actual initialized RTL is not ready')
        (log_dir/'owner.json').write_text(json.dumps(dict(pid=self.process.pid,
            source_manifest=str(manifest),source_manifest_sha256=sha(manifest),
            executable=str(Path(executable).resolve()),executable_sha256=sha(executable)),indent=2)+'\n')

    def _rpc(self, message):
        if self.closed:
            raise RuntimeError('simulator owner already closed')
        self.process.stdin.write(message+'\n');self.process.stdin.flush()
        while True:
            line=self.process.stdout.readline()
            if not line:
                raise RuntimeError('actual simulator terminated: rc='+str(self.process.poll()))
            if line.startswith('DS20_REPLY '):
                response=json.loads(line[len('DS20_REPLY '):])
                for die in response.get('dies',[]):
                    die['cpl_data']=die.pop('cpl_lo')|(die.pop('cpl_hi')<<64)
                return response
            self.log.write(line);self.log.flush()
            if '$readmem' in line and ('not found' in line or '%Error' in line):
                raise RuntimeError('actual simulator source load failed: '+line.strip())

    def snapshot(self):return self._rpc('SNAP')
    def tick(self):return self._rpc('TICK')
    def drive_die(self, index, **ports):
        names=('cmd_we','cmd_addr','cmd_wdata','db_v','db_token','db_pos','db_job','db_generation','cpl_rdy')
        if set(ports)!=set(names):
            raise ValueError('complete actual CP20 pin set required')
        if type(index) is not int or not 0<=index<2:
            raise ValueError('actual die index')
        if any(type(ports[n]) is not int or ports[n]<0 for n in names):
            raise ValueError('unsigned integral physical pins required')
        self._rpc('DRIVE '+' '.join(str(v) for v in (index,*(ports[n] for n in names))))
    def close(self):
        snap=self.snapshot()
        if any(s['busy'] for s in snap['sms']) or any(d['cpl_v'] for d in snap['dies']):
            raise RuntimeError('retain live simulator owner; kernel not drained')
        self._rpc('CLOSE');self.closed=True
        self.process.wait();self.log.close()


def factory(args):
    """Factory for the actual DS20 pins backend, not Qwen's unrelated factory."""
    return Simulator20(args.executable,args.source_manifest,
        enable=args.enable,log_dir=args.out)
