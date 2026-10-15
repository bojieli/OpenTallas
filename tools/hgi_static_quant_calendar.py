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


def lower_record(record, start_cycle, resident_sid=0):
    """Lower a real decoded HGI record after static VM residency allocation.

    The caller resolves dependencies and assigns start_cycle. No implicit modulo
    relocation, dynamic address/count, predicate, or ready-driven fallback exists.
    Address relocation/prefetch is a separate real compiler operation, never a
    silently changed memory source. All addresses here are VM FP32 word addresses.
    """
    from hgi_sim.records import Rec
    if not isinstance(start_cycle,int) or not 0<=start_cycle<2**32 or resident_sid not in range(4):
        raise ValueError('Quant start cycle/resident SID invalid')
    if not isinstance(record,Rec) or record.unit!='FUSED':
        raise ValueError('native Quant lowering requires decoded FUSED HGI record')
    opcodes={'QDQ_FP8':4,'QDQ_FP4_E8M0':5,'QDQ_FP4_E4M3':6}
    if record.op not in opcodes or record.pred!='ALWAYS' or set(record.desc)!={'A','O'}:
        raise ValueError('unsupported Quant operation/predicate/operand set')
    a,o=record.desc['A'],record.desc['O']
    for d in [a,o]:
        if d.space!='VM' or d.fmt!='FP32' or d.n<=0 or d.n%32 or d.m<=0 or d.base%8:
            raise ValueError('Quant requires static sector-aligned VM FP32 full beats')
        if d.istride not in (0,1) or any([d.dyn_mul,d.n_sel,d.indexed,d.ibcast,d.lstride,d.l1stride]):
            raise ValueError('Quant dynamic/indexed/strided descriptor not lowered')
        end=d.base+(d.m-1)*d.stride+d.n-1
        if d.stride<0 or (d.m>1 and d.stride%8) or d.base>>16!=resident_sid or end>>16!=resident_sid:
            raise ValueError('Quant operands must reside in explicitly allocated local VM SID')
    if a.n!=o.n or a.m!=o.m:
        raise ValueError('Quant input/output shape mismatch')
    aend=a.base+(a.m-1)*a.stride+a.n
    oend=o.base+(o.m-1)*o.stride+o.n
    overlap=a.base<oend and o.base<aend
    if overlap and (a.base,a.n,a.m,a.stride)!=(o.base,o.n,o.m,o.stride):
        raise ValueError('Quant partial overlap requires an explicit static staging allocation')
    block=(record.param&255) if record.op=='QDQ_FP4_E4M3' else 32
    if record.op=='QDQ_FP4_E4M3' and block!=16:
        raise ValueError('unsupported native E4M3 block size')
    commands=[]
    for row in range(a.m):
        for beat in range(a.n//32):
            src=(a.base+row*a.stride)//8+4*beat
            dst=(o.base+row*o.stride)//8+4*beat
            if src//8!=(src+3)//8 or dst//8!=(dst+3)//8:
                raise ValueError('Quant full beat crosses a bank-row; explicit aligned staging required')
            commands.append(dict(cycle=start_cycle+len(commands),op=opcodes[record.op],block=block,
                src=src,dst=dst,last=int(row==a.m-1 and beat==a.n//32-1)))
    return commands


def calendar(vectors: Path, read_station=0, write_station=0):
    lines = vectors.joinpath('recs.txt').read_text().splitlines()
    rows = [list(map(int, line.split())) for line in lines[1:] if line.strip()]
    assert len(rows) == int(lines[0])
    # Input n -> request output n, bank samples n+1; response at n+7;
    # gather captures n+8, decoder captures n+9; native output n+33;
    # output pin n+34, bank samples n+35, commits n+38.
    commit_delta = 38 + 2*read_station + write_station
    from hgi_sim.records import Rec,MDesc,decode_one
    slots, commands, writes, reads, cost = set(), [], {}, {}, 0
    bindings=[]
    for rec, (op, n, a, o, price, block) in enumerate(rows):
        assert op in (4, 5, 6) and n > 0 and n % 32 == 0
        assert a % 8 == o % 8 == 0
        assert op != 6 or block == 16
        original_a,original_o=a,o
        a, o = a % 65536, o % 65536
        native=Rec(unit='FUSED',op={4:'QDQ_FP8',5:'QDQ_FP4_E8M0',6:'QDQ_FP4_E4M3'}[op],param=block,
            desc={'A':MDesc(base=a,n=n),'O':MDesc(base=o,n=n)})
        encoded=native.encode();decoded,end=decode_one(encoded,0);assert end==len(encoded)
        emitted=lower_record(decoded,len(commands),resident_sid=0)
        bindings.append(dict(record=rec,native_record_hex=encoded.hex(),source_A=original_a,source_O=original_o,
                             allocated_A=a,allocated_O=o,allocation='explicit historical B2 SID0 component fixture relocation'))
        cost += price
        for beat,command in enumerate(emitted):
            cycle = command['cycle']
            src, dst = command['src'],command['dst']
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
    if len(commands)>1024:
        raise ValueError('gapless Quant component programme exceeds actual 1024-word macro; compact timestamped record controller required')
    source_sha = {str(p.relative_to(vectors)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(vectors.iterdir()) if p.is_file()}
    return dict(schema='opentallas.hbm-quant-component-calendar.v1', commands=commands,
        records=len(rows), beats=len(commands), words=len(commands)*32,
        command_bits=48, native_record_bindings=bindings, source_sha256=source_sha, immutable_price=cost,
        measured_wq3_price_historical=184, local_sid=0, bare_bank_response_edges=6,
        read_station_edges_each_way=read_station, write_station_edges=write_station,
        first_command_to_commit_edges=commit_delta, cycles=len(commands)+commit_delta,
        programme_launch_to_first_engine_command_edges=5,
        programme_launch_cycles=len(commands)+commit_delta+5,
        throughput_gate_cycles=cost*1.1, conflicts=0,
        qualification='COMPONENT ONLY; native CP/programme SRAM and actual NW station+other-client composition OPEN')


def compact_record_words(records, issue_cycles, resident_sid):
    """Compile source-decoded native records and absolute global issue timestamps.

    The external whole-program scheduler owns issue_cycles and must prove operand
    residency/dependencies. No cost-driven fabricated timestamps or new price.
    """
    if len(records)!=len(issue_cycles) or not records or len(records)>1024:
        raise ValueError('native Quant record count exceeds actual1024-word macro')
    words=[];previous_end=-1;writes={};reads={}
    for pc,(record,cycle) in enumerate(zip(records,issue_cycles)):
        commands=lower_record(record,cycle,resident_sid)
        if len(commands)<4 or len(commands)>65535 or cycle<8 or cycle<=previous_end or cycle+len(commands)>=2**32:
            raise ValueError('native Quant timestamp/beat count overlaps or lacks initial SRAM margin')
        # Row gaps must be represented as separate statically allocated records.
        if any(c['src']!=commands[0]['src']+4*i or c['dst']!=commands[0]['dst']+4*i for i,c in enumerate(commands)):
            raise ValueError('compact Quant requires contiguous row placement or explicit split records')
        for command in commands:
            read_edge=command['cycle']+1
            write_edge=command['cycle']+35
            commit_edge=command['cycle']+38
            for lane in range(4):
                source=command['src']+lane;destination=command['dst']+lane
                if writes.get(source,-1)>=read_edge:
                    raise ValueError('Quant native RAW operand not committed on compiled read cycle')
                if reads.get(destination,-1)>=write_edge or writes.get(destination,-1)>=commit_edge:
                    raise ValueError('Quant native WAR/WAW conflict in compiled memory timeline')
                reads[source]=read_edge;writes[destination]=commit_edge
        c=commands[0]
        payload=(c['block']<<86)|(c['op']<<80)|(c['dst']<<64)|(c['src']<<48)|(len(commands)<<32)|cycle
        words.append((0xc7a1<<240)|(pc<<224)|payload)
        previous_end=cycle+len(commands)-1
    return words


def compact_native_nw_programme(records, issue_cycles, resident_sid, layout):
    """Compile real NW bank slots for timestamped record issue, current zero-station pins.

    Relative to LCP, record tick t is consumed by engine at t+7. NW ordinal k
    reaches bank at k+7; hence read ordinal=t+1, write ordinal=t+35. Actual
    physical stations must extend this source-derived calendar, never be hidden.
    """
    compact_record_words(records,issue_cycles,resident_sid)
    if layout['params']['RG']!=7 or layout['params']['WG']!=3 or layout['bits']!=187:
        raise ValueError('Quant compact NW requires source-matched native RG7/WG3 layout')
    fields={f['name']:f for f in layout['fields']}
    commands=[c for record,tick in zip(records,issue_cycles) for c in lower_record(record,tick,resident_sid)]
    length=max(c['cycle']+35 for c in commands)+5
    if length>1024:
        raise ValueError('Actual NW calendar storage exceeds1024 words; native global VM paging/resident profiles required')
    values=[0]*length
    for c in commands:
        for offset,key,owner,enabled,selected in [(1,'src',4,'rslot_v','rslot'),(35,'dst',2,'wslot_v','wslot')]:
            e,s=fields[enabled],fields[selected]
            for j in range(4):
                bank=(c[key]+j)&7;i=c['cycle']+offset
                if values[i]>>(e['lo']+bank)&1:raise ValueError('compact NW duplicate bank reservation')
                values[i]|=1<<(e['lo']+bank);values[i]|=owner<<(s['lo']+3*bank)
    return [(0xc7a1<<240)|(pc<<224)|word for pc,word in enumerate(values)]


def native_nw_programme(result, layout):
    """Reserve actual native NW bank selectors from the same command schedule.

    Real host baseline: NW word0 output LCP+6/bank captures+7; Quant word0
    output+8/engine captures+9. Read bank input+10 => NW ordinal3. Write bank
    input+44 => ordinal37. Actual stations must extend both calendars together.
    """
    assert layout['params']['RG']==7 and layout['params']['WG']==3 and layout['bits']==187
    fields={f['name']:f for f in layout['fields']}
    nr=3+result['read_station_edges_each_way']
    nw=37+2*result['read_station_edges_each_way']+result['write_station_edges']
    length=max(c['cycle']+nw for c in result['commands'])+5
    if length>1024:raise ValueError('native NW calendar exceeds actual programme macro')
    values=[0]*length
    for c in result['commands']:
        for offset,key,owner,enabled,selected in [(nr,'src',4,'rslot_v','rslot'),(nw,'dst',2,'wslot_v','wslot')]:
            e,s=fields[enabled],fields[selected]
            for j in range(4):
                bank=(c[key]+j)&7
                i=c['cycle']+offset
                if values[i]>>(e['lo']+bank)&1:raise ValueError('native NW duplicate port reservation')
                values[i]|=1<<(e['lo']+bank)
                values[i]|=owner<<(s['lo']+3*bank)
    return [(0xc7a1<<240)|(pc<<224)|word for pc,word in enumerate(values)]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--vectors',type=Path,default=Path('tools/hgi_unit_tput/vectors/qdqvec'))
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--program-out',type=Path)
    ap.add_argument('--nw-out',type=Path)
    ap.add_argument('--compact-records',type=Path,help='source-pinned actual records with explicit compiled issue cycles and resident_sid')
    ap.add_argument('--compact-out',type=Path)
    ap.add_argument('--nw-layout',type=Path,default=Path('results/hbm_static_quant_1015/nw_layout.json'))
    ap.add_argument('--read-station',type=int,default=0)
    ap.add_argument('--write-station',type=int,default=0)
    a=ap.parse_args()
    if a.compact_records:
        if not a.compact_out:ap.error('--compact-records requires --compact-out')
        from hgi_sim.records import decode_one
        native=json.loads(a.compact_records.read_text())
        records=[];cycles=[]
        for item in native['records']:
            raw=bytes.fromhex(item['record_hex']);record,end=decode_one(raw,0)
            if end!=len(raw):raise ValueError('native Quant source contains trailing/unbound record bytes')
            records.append(record);cycles.append(item['issue_cycle'])
        words=compact_record_words(records,cycles,native['resident_sid'])
        a.compact_out.parent.mkdir(parents=True,exist_ok=True)
        a.compact_out.write_text(''.join(f'{w:064x}\n' for w in words))
        if a.nw_out:
            nw_words=compact_native_nw_programme(records,cycles,native['resident_sid'],json.loads(a.nw_layout.read_text()))
            a.nw_out.parent.mkdir(parents=True,exist_ok=True)
            a.nw_out.write_text(''.join(f'{w:064x}\n' for w in nw_words))
        a.out.write_text(json.dumps(dict(schema='opentallas.hbm-quant-compact-source-binding.v1',
            source=str(a.compact_records),source_sha256=hashlib.sha256(a.compact_records.read_bytes()).hexdigest(),
            record_count=len(records),issue_cycles=cycles,resident_sid=native['resident_sid'],
            hardware_programme_words=len(words),whole_token_qualified=False),indent=2)+'\n')
        return
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
    if a.nw_out:
        words=native_nw_programme(result,json.loads(a.nw_layout.read_text()))
        a.nw_out.write_text(''.join(f'{w:064x}\n' for w in words))
    print(json.dumps({k:result[k] for k in ['records','beats','words','cycles','immutable_price','conflicts']}))


if __name__=='__main__':main()
