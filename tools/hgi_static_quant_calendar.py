#!/usr/bin/env python3
"""Emit/check fixed native QDQ beat reservations from immutable production vectors.

This is the component calendar. Loading/executing it from the native NW programme
SRAM, adding actual station edges and composing with all clients remain required.
No address/operation is supplied from a golden result; golden files are expected
outputs only. Relocation to SID0 reproduces the historical B2 local bench scope.
"""
import argparse
import hashlib
import json
from pathlib import Path


def calendar(vectors: Path, read_station=0, write_station=0):
    lines = vectors.joinpath('recs.txt').read_text().splitlines()
    rows = [list(map(int, line.split())) for line in lines[1:] if line.strip()]
    assert len(rows) == int(lines[0])
    # Input n -> request output n, bank samples n+1; response at n+7;
    # gather captures n+8, decoder captures n+9; native output n+33;
    # output pin n+34, bank samples n+35, commits n+38.
    commit_delta = 38 + 2*read_station + write_station
    slots, commands, writes, reads, cost = set(), [], {}, {}, 0
    for rec, (op, n, a, o, price, block) in enumerate(rows):
        assert op in (4, 5, 6) and n > 0 and n % 32 == 0
        assert a % 8 == o % 8 == 0
        assert op != 6 or block == 16
        a, o = a % 65536, o % 65536
        cost += price
        for beat in range(n//32):
            cycle = len(commands)
            src, dst = a//8+4*beat, o//8+4*beat
            assert src//8 == (src+3)//8 and dst//8 == (dst+3)//8
            readcycle = cycle+1+read_station
            writecycle = cycle+35+2*read_station+write_station
            for j in range(4):
                rs, ws = src+j, dst+j
                for kind, c, s in [('r', readcycle, rs), ('w', writecycle, ws)]:
                    key = kind, c, s & 7
                    assert key not in slots, ('port collision', key)
                    slots.add(key)
                assert writes.get(rs, -1) < readcycle, ('RAW not committed', rs)
                assert reads.get(ws, -1) < writecycle, ('WAR clobber', ws)
                assert writes.get(ws, -1) < writecycle, ('WAW collision', ws)
                reads[rs] = readcycle
                writes[ws] = cycle+commit_delta
            commands.append(dict(cycle=cycle, record=rec, beat=beat, op=op, block=block,
                src=src, dst=dst, last=int(beat==n//32-1), bank_read_cycle=readcycle,
                bank_write_cycle=writecycle, commit_cycle=cycle+commit_delta))
    source_sha = {str(p.relative_to(vectors)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(vectors.iterdir()) if p.is_file()}
    return dict(schema='opentallas.hbm-quant-component-calendar.v1', commands=commands,
        records=len(rows), beats=len(commands), words=len(commands)*32,
        command_bits=48, source_sha256=source_sha, immutable_price=cost,
        measured_wq3_price_historical=184, local_sid=0, bare_bank_response_edges=6,
        read_station_edges_each_way=read_station, write_station_edges=write_station,
        first_command_to_commit_edges=commit_delta, cycles=len(commands)+commit_delta,
        programme_launch_to_first_engine_command_edges=5,
        programme_launch_cycles=len(commands)+commit_delta+5,
        throughput_gate_cycles=cost*1.1, conflicts=0,
        qualification='COMPONENT ONLY; native CP/programme SRAM and actual NW station+other-client composition OPEN')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--vectors',type=Path,default=Path('tools/hgi_unit_tput/vectors/qdqvec'))
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--program-out',type=Path)
    ap.add_argument('--read-station',type=int,default=0)
    ap.add_argument('--write-station',type=int,default=0)
    a=ap.parse_args()
    result=calendar(a.vectors,a.read_station,a.write_station)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    if a.program_out:
        a.program_out.parent.mkdir(parents=True,exist_ok=True)
        words=[]
        for pc,c in enumerate(result['commands']):
            payload=(c['last']<<47)|(c['dst']<<31)|(c['src']<<15)|(c['block']<<7)|(c['op']<<1)|1
            words.append((0xc7a1<<240)|(pc<<224)|payload)
        a.program_out.write_text(''.join(f'{w:064x}\n' for w in words))
    print(json.dumps({k:result[k] for k in ['records','beats','words','cycles','immutable_price','conflicts']}))


if __name__=='__main__':main()
