#!/usr/bin/env python3
"""Read-only scalar schedule expectation; NOT RTL measurement or a live-state reconstruction."""
import json, math

def replay(start_cycle, row_overhead=3, edge_overhead=2):
    # Defaults of pinned idx_hbm through hbm3e_phy: CLK_PS is NOT forwarded to K.
    clk=1000; refi=3900000; nb=32; npc=32
    def channel(s): return ((s>>2)^(s>>7)^(s>>12))&31
    def bank(s): return ((((s>>12)^((s>>15)>>2))&7)<<2)|((s^(s>>15))&3)
    states=[]
    for p in range(npc):
        states.append(dict(nref=refi//nb+refi*p//(npc*nb),done=set(),open=[False]*nb,
          row=[0]*nb,actok=[0]*nb,preok=[0]*nb,act=[0]*nb,lastact=-1000000,
          actbg=[-1000000]*4,col=-1000000,colbg=[-1000000]*4,faw=[-1000000]*4))
    cyc=start_cycle; reads=0; refreshes=0; misses=0; gaps=[]
    # First absolute row pos-127, ring slot0 at pos1048575, followed by slots0..127.
    for row in range(128):
        cyc+=row_overhead
        for sec in range(17):
            addr=0x40000+row*17+sec; p=channel(addr); bk=bank(addr); bg=bk&3
            st=states[p]; now=cyc*clk; tmin=now+10000
            # REFPB=3: least queued bank, then most recently activated; head is protected.
            while st['nref']<=max(tmin,st['col']):
                avail=[b for b in range(nb) if b not in st['done']]
                b=min(avail,key=lambda b: (65 if b==bk else 0,-st['act'][b],b))
                st['done'].add(b)
                if len(st['done'])==nb: st['done'].clear()
                tr=st['nref']
                if st['open'][b]: tr=max(tr,st['preok'][b])+16250
                st['open'][b]=False; st['actok'][b]=max(st['actok'][b],tr+200000)
                st['nref']+=refi//nb; refreshes+=1
            if st['open'][bk] and st['row'][bk]==addr>>15:
                tact=st['act'][bk]
            else:
                misses+=1
                tact=max(tmin,st['preok'][bk])+16250 if st['open'][bk] else tmin
                tact=max(tact,st['actok'][bk],st['lastact']+2500,st['actbg'][bg]+3125,st['faw'][0]+15000)
                st['faw']=st['faw'][1:]+[tact];st['lastact']=tact;st['actbg'][bg]=tact
                st['open'][bk]=True;st['row'][bk]=addr>>15;st['act'][bk]=tact
                st['actok'][bk]=tact+28125+16250;st['preok'][bk]=tact+28125
            tcol=max(tmin,now,tact+19375,st['col']+1024,st['colbg'][bg]+2560)
            st['col']=tcol;st['colbg'][bg]=tcol;st['preok'][bk]=max(st['preok'][bk],tcol+5625)
            nxt=math.ceil((tcol+12500+1024+10000)/clk)+edge_overhead
            gaps.append(nxt-cyc);cyc=nxt;reads+=1
    return dict(start_cycle=start_cycle,end_cycle=cyc,elapsed_cycles=cyc-start_cycle,
      reads=reads,activations=misses,refresh_events_all_channels=refreshes,
      min_sector_cycles=min(gaps),max_sector_cycles=max(gaps),row_overhead=row_overhead,edge_overhead=edge_overhead)

if __name__=='__main__':
    cases=[replay(c,3,e) for e in (1,2) for c in range(12200,13401,100)]
    assert all(c['reads']==2176 and c['elapsed_cycles']>=2176*34 for c in cases)
    assert all(c['elapsed_cycles']>100000 for c in cases)
    print(json.dumps({'scope':'CONDITIONAL_SCALAR_EXPECTATION_NOT_RTL_MEASURED',
      'conditions':['empty request and response queues at start','no concurrent RoPE/index/CKV requester',
      'cold initially closed bank state; refresh deadlines reset-origin','functional pinned ready/valid transport','no source faults'],
      'cycle_padding':'one and two cycles per sector sensitivity for registered response/next FR; three per row for SEND/WAIT; estimate only',
      'not_actual_live_state':'Previous write/RoPE bank state is not reconstructed; these starts form sensitivity examples, not a proof of actual start or deadline.',
      'cases':cases},indent=2))
