#!/usr/bin/env python3
"""Minimum actual registry-to-map and installation protocol gate."""
import argparse,copy,json
from pathlib import Path
import qwen_r25_native_entries as E

def gate(registry):
    result=E.build(registry);cases=[]
    assert result['resolved_operations']==253
    assert [(x['map_rom_pc'],x['map_count']) for x in result['map_install_pins']]==[(0,4),(4,6),(10,6),(16,1),(17,2),(19,23)]
    assert len({x['map_cp_pc'] for x in result['map_install_pins']})==6
    assert all(x['map_cp_pc']!=x['map_rom_pc'] for x in result['map_install_pins'])
    assert result['unresolved_kernel_families'] and not result['full_decode_executable']
    cases.append('253 actual graph operations; six distinct CP32 maps and actual42 native ROM slots')
    cases.append('missing ME/service/weights/KV families remain failclosed')
    class Pins:
        def __init__(self):self.t=0;self.accepted=[];self.pending=None
        def snapshot(self):return dict(fault=False,map_rdy=self.t%3==2)
        def drive(self,x):self.pending=dict(x)
        def tick(self):
            if self.pending['map_v'] and self.t%3==2:self.accepted.append(self.pending)
            self.t+=1
    pins=Pins();driver=E.MapInstaller(pins,result)
    for _ in range(18):status=driver.step()
    assert status=='DONE' and pins.accepted==result['map_install_pins'] and pins.pending==dict(map_v=0)
    cases.append('actual map pin protocol holds every descriptor through backpressure and deasserts map_v on final receipt')
    def reject(name,mutation):
        bad=copy.deepcopy(registry);mutation(bad)
        try:E.build(bad)
        except ValueError:cases.append(name);return
        raise AssertionError('accepted mutant '+name)
    first=next(i for i,o in enumerate(registry['entries']) if o.get('production_entry'))
    reject('TOKEN17 descriptor rejected',lambda x:x['entries'][first]['production_entry'].update(owner_bits=73))
    reject('ROM boundary overflow rejected',lambda x:x['entries'][first]['production_entry'].update(ROM_PC=4095,ROM_count=4))
    reject('unchecked immutable metadata rejected',lambda x:x['entries'][first]['production_entry']['ROM_metadata'].__setitem__(0,0))
    reject('native consumer mismatch rejected',lambda x:x['entries'][first]['production_entry'].update(dispatch='SM'))
    reject('conflicting repeated family rejected',lambda x:x['entries'][first]['production_entry'].update(ROM_PC=1))
    return dict(verdict='PASS_INSTALL_PROTOCOL',cases=cases,actual_registry_operations=253,
        actual_RTL_gate='f3fa10397 separate actual launcher control gate',
        actual_CP_interceptor_bound=False,actual_VM_lease_bound=False,full_decode_executable=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--registry',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    r=gate(json.loads(a.registry.read_text()));a.out.write_text(json.dumps(r,indent=2)+'\n');print('PASS',len(r['cases']),'actual registry/map installation protocol cases')
if __name__=='__main__':main()
