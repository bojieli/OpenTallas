#!/usr/bin/env python3
"""Compile explicit quadrant transport reservations; no dynamic flow control.

The emitted words drive ot_hgi_coll_qslots. This is a transport-calendar
backend, not the production collective/VM instruction issuer. Source data and
source arithmetic are supplied by independently scheduled real engines.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class Transfer:
    capture: int
    source: int
    sink: int
    identity: str


def compile_calendar(transfers: list[Transfer], npt: int) -> dict:
    if npt not in (2, 3):
        raise ValueError('NPT must be 2 or 3')
    ns, nd = 2+npt+4+1, npt+3*4+1
    sw = (ns-1).bit_length()
    captures: dict[tuple[int,int], str] = {}
    sinks: dict[tuple[int,int], Transfer] = {}
    for t in transfers:
        if t.capture < 0 or not 0 <= t.source < ns or not 0 <= t.sink < nd:
            raise ValueError(f'out of range reservation: {t}')
        ck, dk = (t.capture,t.source), (t.capture+1,t.sink)
        if ck in captures and captures[ck] != t.identity:
            raise ValueError(f'two payloads own capture {ck}')
        if dk in sinks:
            raise ValueError(f'two transfers own sink edge {dk}')
        captures[ck], sinks[dk] = t.identity, t
    count = max((c+1 for c,_ in sinks), default=0)
    words = [0] * count
    for c,s in captures:
        words[c] |= 1 << s
    for (c,d), t in sinks.items():
        words[c] |= 1 << (ns+d)
        words[c] |= t.source << (ns+nd+d*sw)
    return dict(schema='hcoll.quadrant-calendar.v1',npt=npt,sources=ns,sinks=nd,
                source_select_bits=sw,word_bits=ns+nd+nd*sw,
                packed_order_lsb=['capture_slot','sink_slot','sink_select'],
                cycles=count,last_output_edge=count,transport_latency_edges=2,transfers=len(transfers),unique_captures=len(captures),
                words=words,
                scope='transport reservation compilation; production issuer, topology, arithmetic and slot closure pending')


def shape_calendar(g: int, pf: int, npt: int) -> list[Transfer]:
    """Reservation stress for production rank/flit counts, not an op price.

    Each quarter receives each rank's PF/4 flits striped on its real rail
    input lanes. The same captured flit is delivered to SU and RGX. This
    precisely exercises multicast with no consumption counter or credit.
    Actual rail arrival cycles must come from the link schedule compiler.
    """
    if g not in (1,2,4,8,96) or pf <= 0 or pf % 4:
        raise ValueError('unsupported production shape')
    out=[]
    for rank in range(g):
        for flit in range(pf//4):
            c=rank*(pf//4)+flit
            s=2+flit%npt
            for d in (npt+flit%4,npt+4+flit%4):
                out.append(Transfer(c,s,d,f'rank{rank}:flit{flit}'))
    return out


def selftest() -> dict:
    results={}
    for npt in (2,3):
        for g in (8,96):
            r=compile_calendar(shape_calendar(g,384,npt),npt)
            assert r['transfers']==g*192 and r['unique_captures']==g*96
            results[f'npt{npt}_g{g}']={k:v for k,v in r.items() if k!='words'}
    rejected=[]
    cases={
      'sink_collision':[Transfer(0,0,0,'a'),Transfer(0,1,0,'b')],
      'source_conflict':[Transfer(0,0,0,'a'),Transfer(0,0,1,'b')],
      'invalid_source':[Transfer(0,10,0,'a')],
      'invalid_sink':[Transfer(0,0,17,'a')],
      'negative_cycle':[Transfer(-1,0,0,'a')],
    }
    for name,rows in cases.items():
        try: compile_calendar(rows,3)
        except ValueError: rejected.append(name)
        else: raise AssertionError(f'compiler failed to reject {name}')
    results['rejected']=rejected
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--npt',type=int,default=3)
    p.add_argument('--group',type=int,default=96)
    p.add_argument('--pf',type=int,default=384)
    p.add_argument('--out',type=Path)
    p.add_argument('--selftest',action='store_true')
    a=p.parse_args()
    if a.selftest:
        print(json.dumps(selftest(),indent=2)); return
    if not a.out: p.error('--out is required')
    r=compile_calendar(shape_calendar(a.group,a.pf,a.npt),a.npt)
    words=r.pop('words');a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'calendar.json').write_text(json.dumps(r,indent=2)+'\n')
    digits=(r['word_bits']+3)//4
    (a.out/'calendar.mem').write_text(''.join(f'{word:0{digits}x}\n' for word in words))

if __name__=='__main__': main()
