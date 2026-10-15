"""Repair measured pin-to-pin overreach using die-placed registered channel relays.

Freeze the die tool's current master pin assignment before adding relays, so a
shared master's face cannot move in response to the new neighbouring relay.
Never route through a leaf; failed placement remains an explicit plan defect.
"""
import math


def repair(K, m):
    M = K.masters(m, 1)
    m['assigned_ports'] = {n: {p: list(v) for p, v in mm.ports.items()}
                           for n, mm in M.items() if not n.startswith('qkd_rly')}
    by = {i.name: i for i in m['insts']}
    additions, buses, unresolved = [], [], []
    for bid, cls, bits, eps in m['buses']:
        if len(eps) != 2 or cls in K.ABUT or cls in ('clock_trunk', 'reset', 'constant'):
            buses.append((bid, cls, bits, eps)); continue
        (a, pa), (b, pb) = eps
        ap, bp = K.pin_xy(by[a], M[by[a].master], pa.lstrip('*')), K.pin_xy(by[b], M[by[b].master], pb.lstrip('*'))
        if abs(ap[0]-bp[0]) + abs(ap[1]-bp[1]) <= K.PIN_REACH:
            buses.append((bid, cls, bits, eps)); continue
        width, height = 52.68, 30.24 if bits <= 512 else K.up(bits * .048 + 4, K.GY)
        initial_ap = ap
        chain, staged, previous = [], [], (a,pa)
        # Several registered stages are necessary for a long fault-chain return.
        # Each stage is chosen in free channel space; a trapped chain is rolled back.
        for stage in range(math.ceil((abs(ap[0]-bp[0])+abs(ap[1]-bp[1]))/200)+12):
            cap = 300 if previous[0].startswith('wctl_') and bid.startswith('wencoded_') else K.PIN_REACH
            if abs(ap[0]-bp[0])+abs(ap[1]-bp[1]) <= cap:
                break
            distance = abs(ap[0]-bp[0])+abs(ap[1]-bp[1])
            fraction = min(.5, 350/distance)
            target = (ap[0]+fraction*(bp[0]-ap[0])-width/2,
                      ap[1]+fraction*(bp[1]-ap[1])-height/2)
            grid = K.GRID/2
            candidates = [(K.up(target[0]+x*grid, K.GX), K.up(target[1]+y*grid, K.GY))
                          for x in range(-16,17) for y in range(-16,17)]
            choices = []
            for x,y in candidates:
                if x < 4.32 or y < 4.32 or x+width+4.32 > m['die']['w'] or y+height+4.32 > m['die']['h']:
                    continue
                orient = 'MY' if bp[0] < ap[0] else 'R0'
                inp_x, out_x = (x+width-K.SHAVE,x) if orient=='MY' else (x,x+width-K.SHAVE)
                left = abs(ap[0]-inp_x)+abs(ap[1]-(y+height/2))
                remaining = abs(bp[0]-out_x)+abs(bp[1]-(y+height/2))
                if left > cap or remaining >= distance-1:
                    continue
                if any(min(x+width+4.32,i.x+i.w)-max(x-4.32,i.x) > .001 and
                       min(y+height+4.32,i.y+i.h)-max(y-4.32,i.y) > .001 for i in m['insts']+staged):
                    continue
                choices.append((remaining,x,y,left,out_x,orient))
            if not choices:
                break
            remaining,x,y,left,out_x,orient=min(choices)
            name='rly_pinfix_'+bid.replace('__','_')+'_'+str(stage)
            it=K.F.Inst(name,f'qkd_rly_{bits}',x,y,width-K.SHAVE,height-K.SHAVE,orient,kind='relay',region='relay')
            staged.append(it)
            sbid=bid if not chain else bid+'__pinfix'+str(stage)
            chain.append((sbid,cls,bits,[previous,(name,'a')]))
            previous=(name,'b');ap=(out_x,y+height/2)
        if abs(ap[0]-bp[0])+abs(ap[1]-bp[1]) > K.PIN_REACH:
            unresolved.append(dict(bus=bid,um=abs(initial_ap[0]-bp[0])+abs(initial_ap[1]-bp[1])));
            buses.append((bid,cls,bits,eps)); continue
        if not staged:
            buses.append((bid,cls,bits,eps));continue
        m['insts'].extend(staged)
        by.update({i.name:i for i in staged})
        buses.extend(chain+[(bid+'__pinfix'+str(len(staged)),cls,bits,[previous,(b,pb)])])
        base=bid.split('__r')[0]
        m['relay_stages'][base]=m['relay_stages'].get(base,0)+len(staged)
        for index,it in enumerate(staged):
            additions.append(dict(bus=bid,relay=it.name,clock_source=a,stages_added=1,
                                  before_um=round(abs(initial_ap[0]-bp[0])+abs(initial_ap[1]-bp[1]),3)))
    for row in additions:
        n=row['relay']; source=row['clock_source']
        clock=next((j for j,(_,cl,_,eps) in enumerate(buses) if cl=='clock_trunk' and any(i==source for i,p in eps)),None)
        if clock is None:
            clock=next(j for j,(bid,_,_,_) in enumerate(buses) if bid=='clk_core_c')
        bid,cl,bits,eps=buses[clock];buses[clock]=(bid,cl,bits,list(eps)+[(n,'ck')])
    m['buses']=buses
    m['pin_repair']=dict(added=additions, unresolved=unresolved, method='fixed master pins; registered channel relay; no leaf traversal')
    return m
