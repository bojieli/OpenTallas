#!/usr/bin/env python3
"""Die-owned half-column assignment and exact parent/VM projection.

Every x8 output bit is assigned once. Both parent boundaries meet the same
physical bit; no array reversal or width clamping is allowed.
"""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pin_files import from_tcl
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'physical/s81_die_pins/v18'

def spec(rows):
    return dict(bits=len(rows), uniform=False, per_bit=rows)

def main(request):
    capture = json.loads((OUT/'dsfd_sp_capture_c.json').read_text())
    vm = json.loads((OUT/'dsfd_sp_vm.json').read_text())
    temp = OUT/'capture_clock_request.json'
    from_tcl(request, 'dsfd_sp_capture_c', [1728.,561.6], temp)
    req = json.loads(temp.read_text()); temp.unlink()
    capture['clock_entries'] = req['clock_entries']
    for p in list(capture['ports']):
        if p.startswith('ck'):
            del capture['ports'][p]
    for p,s in req['ports'].items():
        if p.startswith('ck'):
            capture['ports'][p] = s
    ports = {}
    for face, groups in [('S',[('f_w',416),('f_sn',64)]), ('N',[('t_vm',832),('t_st',64)])]:
        n=0
        for p,width in groups:
            rows=[]
            for i in range(width):
                rows.append([face, 'M5' if n%2 == 0 else 'M3', round(5.004+(n//2)*.096,3),.192])
                n+=1
            ports[p]=spec(rows)
    for p,face,x in [('ck','S',55.02),('rst','S',55.212),('t_ho','S',55.404),('ckv','N',55.02),('rsv','N',55.212)]:
        ports[p]=spec([[face,'M5',x,.192]])
    leaf=dict(schema='opentallas.s81.assigned_pins.v1',master='dsfd_capt_x8_dual',case='v18',outline_um=[60.48,270.],
              source='tools/s81/capture_x8_assignment.py; exact parent RTL x8 slice map 733ab4b39',
              rule='die-owned bit order and direct parent/VM peer projection; gate against PG stripes before route',
              clock_entries=dict(stream=['ck[0]'],serial=['ckv[0]']),ports=ports)
    xg=[129.6,302.4,475.2,648.,950.4,1123.2,1296.,1468.8]
    rows=[None]*13376
    for g,x in enumerate(xg):
        for h in range(2):
            lx=x-11.088+h*80.496
            for i,(_,ly,c,d) in enumerate(ports['t_vm']['per_bit']):
                rows[1664*g+832*h+i]=['S',ly,round(lx+c,3),d]
            k=2*g+h
            capture['ports']['ck_x']['per_bit'][k]=['N','M5',round(lx+55.02,3),.192]
            capture['ports']['ckv_x']['per_bit'][k]=['S','M5',round(lx+55.02,3),.192]
    for i,(_,ly,c,d) in enumerate(ports['t_st']['per_bit']):
        rows[13312+i]=['S',ly,round(xg[3]-11.088+c,3),d]
    assert all(rows)
    capture['ports']['t_vm']=spec(rows)
    vm['ports']['f_capture']=spec([['N',ly,x,d] for _,ly,x,d in rows])
    capture['source']='tools/s81/capture_x8_assignment.py;68clock per-child capture; exact x8 output map'
    vm['source']='tools/s81/capture_x8_assignment.py;bitwise facing capture peer'
    assert sum(map(len,capture['clock_entries'].values()))==68
    for record in [leaf,capture,vm]:
        (OUT/(record['master']+'.json')).write_text(json.dumps(record,separators=(',',':'))+'\n')
    print('x8 pins',sum(s['bits'] for s in ports.values()),'capture clocks',68,'capture/VM matched bits',len(rows))

if __name__=='__main__':
    main(sys.argv[1])
