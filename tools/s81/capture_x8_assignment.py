#!/usr/bin/env python3
"""Die-owned half-column assignment and exact parent/VM projection.

Every x8 output bit is assigned once. Both parent boundaries meet the same
physical bit; no array reversal or width clamping is allowed.
"""
import json
from pathlib import Path
import sys
from bisect import bisect_left, insort
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pin_files import from_tcl
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'physical/s81_die_pins/v18'

def spec(rows):
    return dict(bits=len(rows), uniform=False, per_bit=rows)

def reserve_clocks(record):
    """Use free native M5 tracks beside each child entry, preserving all data pins."""
    occupied = {}
    for p,s in record['ports'].items():
        if p.startswith('ck'):
            continue
        for face,ly,c,d in s['per_bit']:
            occupied.setdefault((face,ly),[]).append(c)
    for used in occupied.values():
        used.sort()
    for p,s in record['ports'].items():
        if not p.startswith('ck'):
            continue
        for row in s['per_bit']:
            face,ly,target,depth = row
            assert ly == 'M5', (p,ly)
            limit = record['outline_um'][0 if face in 'NS' else 1]
            tracks = [.012+.048*k for k in range(int(limit/.048))]
            used = occupied.setdefault((face,ly),[])
            for c in sorted(tracks,key=lambda c:abs(c-target)):
                if not .012<=c<=limit-.012:
                    continue
                ix = bisect_left(used,c)
                if all(abs(c-v)>=.048-1e-6 for v in used[max(0,ix-1):ix+1]):
                    row[2] = round(c,3)
                    insort(used,row[2])
                    break
            else:
                raise ValueError((p,'no free clock track'))

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
                x = (8.028+(n//2)*.432) if face == 'S' else (5.004+(n//2)*.24)
                layer = 'M5' if n%2 == 0 else 'M3'
                if layer == 'M3':
                    x = .009+round((x-.009)/.036)*.036
                rows.append([face,layer,round(x,3),.192])
                n+=1
            ports[p]=spec(rows)
    for p,face,x in [('ck','S',114.012),('rst','S',114.204),('t_ho','S',114.396),('ckv','N',114.012),('rsv','N',114.204)]:
        ports[p]=spec([[face,'M5',x,.192]])
    leaf=dict(schema='opentallas.s81.assigned_pins.v1',master='dsfd_capt_x8_dual',case='v18',outline_um=[123.12,136.08],
              source='tools/s81/capture_x8_assignment.py; exact parent RTL x8 slice map 733ab4b39',
              rule='die-owned bit order and direct parent/VM peer projection; gate against PG stripes before route',
              clock_entries=dict(stream=['ck[0]'],serial=['ckv[0]']),ports=ports)
    xg=[129.6,302.4,475.2,648.,950.4,1123.2,1296.,1468.8]
    rows=[None]*13376
    for g,x in enumerate(xg):
        for h in range(2):
            lx=x-2.304
            for i,(_,ly,c,d) in enumerate(ports['t_vm']['per_bit']):
                if h == 0:
                    px=lx+c
                else:
                    # Upper MX leaf outputs descend in the two measured side
                    # channels. A repeated leaf has identical x coordinates;
                    # copying them to the parent would short both 832-bit buses.
                    j=i%416
                    px=lx+(-22.548 if i<416 else 125.148)+(j//2)*.096
                    if ly == 'M3':
                        px=.009+round((px-.009)/.036)*.036
                rows[1664*g+832*h+i]=['S',ly,round(px,3),d]
            k=2*g+h
            capture['ports']['ck_x']['per_bit'][k]=['N','M5',round(lx+114.012,3),.192]
            capture['ports']['ckv_x']['per_bit'][k]=['S','M5',round(lx+114.012,3),.192]
    for i,(_,ly,c,d) in enumerate(ports['t_st']['per_bit']):
        rows[13312+i]=['S',ly,round(xg[3]-2.304+c,3),d]
    assert all(rows)
    capture['ports']['t_vm']=spec(rows)
    capture['child_placements']=[dict(name=f'g{g}/u_x{h}',master='dsfd_capt_x8_dual',
        origin_um=[x-2.304,24.768 if h==0 else 181.44],outline_um=[123.12,136.08],orient='MX')
        for g,x in enumerate(xg) for h in range(2)]
    capture['upper_output_routing']=dict(bits_per_sidechannel=416,
        channels=[dict(column=g,left=[x-27.144,x-2.304],right=[x+120.816,x+145.656],y=[0,337.536])
                  for g,x in enumerate(xg)],
        rule='upper outputs routed through side channels, parent pin order retained; no added data stage')
    capture['data_clock_bits'] = {
        'f_gather': ['ck_g[%d]'%(i//848) if i<6784 else 'ck_c[0]' for i in range(6947)],
        't_vm': ['ckv_x[%d]'%(i//832) if i<13312 else 'ckv_x[6]' for i in range(13376)],
        't_cd': ['ckv_r[0]']*12,
    }
    contract = json.loads((OUT/'contract_trial.json').read_text())
    slots = {s['name']:s for s in contract['slots']}
    delta = slots['sp_vm']['origin']['x'] - slots['sp_capture']['origin']['x']
    vm_rows = [['N',ly,round(x-delta,3),d] for _,ly,x,d in rows]
    assert all(.012 <= x <= vm['outline_um'][0]-.012 for _,_,x,_ in vm_rows)
    assert all(abs(a[2]+slots['sp_capture']['origin']['x']-b[2]-slots['sp_vm']['origin']['x']) < .001
               for a,b in zip(rows,vm_rows))
    vm['ports']['f_capture']=spec(vm_rows)
    vm['peer_origin_delta_um']=round(delta,3)
    capture['source']='tools/s81/capture_x8_assignment.py;68clock per-child capture; exact x8 output map'
    vm['source']='tools/s81/capture_x8_assignment.py;bitwise facing capture peer'
    assert sum(map(len,capture['clock_entries'].values()))==68
    # Reviewed bundle shifts preserve ordering but their centroids are not
    # necessarily native tracks. Put all M5 boundary points on actual tracks
    # and mirror the data assignment to the facing gather, not independently.
    for s in capture['ports'].values():
        for row in s['per_bit']:
            if row[1]=='M5':
                row[2]=round(.012+round((row[2]-.012)/.048)*.048,3)
    reserve_clocks(capture)
    gather=json.loads((OUT/'dsfd_sp_gather_c.json').read_text())
    gather['ports']['t_capture']=spec([['S',ly,c,d] for _,ly,c,d in capture['ports']['f_gather']['per_bit']])
    gather['ports']['f_cd']=spec([['S',ly,c,d] for _,ly,c,d in capture['ports']['t_cd']['per_bit']])
    gather['ports']['rst']=spec([['E','M4',52.332,.192]])
    gather['ports']['rsv']=spec([['E','M4',52.524,.192]])
    for port,s in gather['ports'].items():
        for row in s['per_bit']:
            if port.startswith('ck'):
                row[1]='M5' if row[0] in 'NS' else 'M4'
            if row[1] in ('M4','M5'):
                row[2]=round(.012+round((row[2]-.012)/.048)*.048,3)
    for record in [leaf,capture,vm,gather]:
        (OUT/(record['master']+'.json')).write_text(json.dumps(record,separators=(',',':'))+'\n')
    print('x8 pins',sum(s['bits'] for s in ports.values()),'capture clocks',68,'capture/VM matched bits',len(rows))

if __name__=='__main__':
    main(sys.argv[1])
