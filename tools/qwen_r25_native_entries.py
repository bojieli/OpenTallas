#!/usr/bin/env python3
"""Source-assigned CP32 namespace and real native launch-map installer.

These are new CP dispatch addresses, not SM instruction PCs or ROM offsets.
The native CP interception RTL must consume this namespace before adoption.
"""
import argparse,hashlib,json
from pathlib import Path

CP_PREFIX=0x53550000
KERNELS=('prenorm','qknorm','rope','round_q','swiglu','softmax')
CP_ENTRIES={k:CP_PREFIX+i for i,k in enumerate(KERNELS)}

def build(registry):
    if registry.get('schema')!='opentallas.qwen.native_su_registry.v1':raise ValueError('native registry schema')
    resolved={};unresolved=set();operations=[]
    for op in registry['entries']:
        k=op['kernel'];d=op.get('production_entry')
        if not d or k not in CP_ENTRIES:
            unresolved.add(k);continue
        if op['unit']!='SU' or d['unit']!='SU' or d['owner_bits']!=74 or d['dispatch']!='ot_qwen_r25_su_dispatch':
            raise ValueError('native consumer ABI')
        pc,count=d['ROM_PC'],d['ROM_count']
        if type(pc)!=int or type(count)!=int or not 0<=pc<4096 or not 0<count<=4096-pc:
            raise ValueError('native ROM range')
        if not d['dispatch_resolved'] or not d['provider_visibility_required'] or len(d['ROM_metadata'])!=count:
            raise ValueError('native descriptor validity')
        if any(type(x)!=int or not 0<=x<1<<42 or not x>>41 for x in d['ROM_metadata']):
            raise ValueError('native immutable metadata')
        identity={x:d[x] for x in ('ROM_PC','ROM_count','ROM_metadata','ROM_sha256','source_pins')}
        if k in resolved and identity!=resolved[k]:raise ValueError('conflicting family descriptor '+k)
        resolved[k]=identity
        # Actual CP command ABI: LAUNCH opcode1, original16-bit SM completion mask.
        operations.append(dict(id=op['id'],kernel=k,CP_PC=CP_ENTRIES[k],
            command_word=(1<<60)|(0xffff<<44)|CP_ENTRIES[k],
            requires_native_interceptor=True,CP_halves='coalesce matching north/south invocation; complete original masks'))
    if set(resolved)!=set(KERNELS):raise ValueError('all six source-assigned native entries must resolve before installation')
    pins=[dict(map_v=1,map_checked=3,map_slot=i,map_cp_pc=CP_ENTRIES[k],
        map_rom_pc=resolved[k]['ROM_PC'],map_count=resolved[k]['ROM_count']) for i,k in enumerate(KERNELS)]
    return dict(schema='opentallas.qwen.native_cp_map.v1',
        assignment_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        CP_prefix=CP_PREFIX,CP_namespace_mask=0xffff0000,owner_bits=74,
        launcher='ot_qwen_r25_cp_native_launch',map_install_pins=pins,
        descriptors=resolved,operations=operations,resolved_operations=len(operations),
        unresolved_kernel_families=sorted(unresolved),
        actual_interceptor_bound=False,actual_VM_lease_bound=False,
        full_decode_executable=False,adopted=False,
        requirement='Install after cold reset through real map_v/map_rdy; source-assigned CP namespace requires actual two-half interception before SM dispatch. No native ROM PC is passed as an SM instruction PC.')

class MapInstaller:
    """Drives the real map handshake. No inferred ready or synthetic completion."""
    def __init__(self,pins,manifest):
        if manifest.get('schema')!='opentallas.qwen.native_cp_map.v1':raise ValueError('map schema')
        self.pins=pins;self.rows=manifest['map_install_pins'];self.cursor=0
    def step(self):
        snapshot=self.pins.snapshot()
        if snapshot['fault']:raise RuntimeError('actual launcher fault during map install')
        if self.cursor==len(self.rows):
            self.pins.drive(dict(map_v=0));return 'DONE'
        row=dict(self.rows[self.cursor]);self.pins.drive(row)
        accepted=bool(snapshot['map_rdy']);self.pins.tick()
        if accepted:self.cursor+=1
        if self.cursor==len(self.rows):self.pins.drive(dict(map_v=0))
        return 'DONE' if self.cursor==len(self.rows) else 'INSTALL'

def main():
    p=argparse.ArgumentParser();p.add_argument('--registry',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();a.out.write_text(json.dumps(build(json.loads(a.registry.read_text())),indent=2)+'\n')
if __name__=='__main__':main()
