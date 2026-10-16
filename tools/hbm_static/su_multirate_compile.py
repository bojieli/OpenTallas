#!/usr/bin/env python3
"""Source-first 900MHz SU / 1.2GHz VM calendar, integer 1/3 stream ticks.

No requests are inferred at runtime. Every event derives from a serial-edge
programme and declared fixed hardware stages; all times are integer quanta.
"""
import argparse, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def ceildiv(a,b): return (a+b-1)//b

def event(n):
    j=ceildiv(4*n+4,3)
    return dict(serial_capture=n,serial_capture_tick=4*n,
        stream_register=j,stream_register_tick=3*j,
        lg_issue=j+1,lg_issue_tick=3*(j+1),
        lg_read_present=j+11,read_capture_stream=j+12,read_capture_tick=3*(j+12),
        serial_read_present=n+12,serial_read_tick=4*(n+12),
        lg_write_done_present=j+8,write_capture_stream=j+9,write_capture_tick=3*(j+9),
        serial_done_present=n+10,serial_done_tick=4*(n+10))

def serial_for_register(j):
    if j<2 or j%4==1: return None
    if j%4==0: return 3*(j//4)-1
    return 3*(j//4)+(j%4-2)

def prove(count=65536):
    req_min=100; ret_min=100; ack_min=100; overwrite_min=100
    last=-1
    for n in range(count):
        e=event(n); following=event(n+4)
        assert serial_for_register(e['stream_register'])==n
        assert e['stream_register']>last;last=e['stream_register']
        assert e['stream_register_tick']-4*n>=3
        assert e['serial_read_tick']-e['read_capture_tick']>=3
        assert e['serial_done_tick']-e['write_capture_tick']>=3
        # All four-slot payloads remain stable beyond capture, including when
        # serial and stream edges coincide. No same-slot cross-clock collision.
        assert 4*(n+4)-e['stream_register_tick']>=3
        assert following['read_capture_tick']-e['serial_read_tick']>=3
        assert following['write_capture_tick']-e['serial_done_tick']>=3
        req_min=min(req_min,e['stream_register_tick']-4*n)
        ret_min=min(ret_min,e['serial_read_tick']-e['read_capture_tick'])
        ack_min=min(ack_min,e['serial_done_tick']-e['write_capture_tick'])
        overwrite_min=min(overwrite_min,4*(n+4)-e['stream_register_tick'],
            following['read_capture_tick']-e['serial_read_tick'],
            following['write_capture_tick']-e['serial_done_tick'])
    return dict(events_proved=count,request_setup_min_ticks=req_min,
        read_return_setup_min_ticks=ret_min,write_done_setup_min_ticks=ack_min,
        slot_overwrite_guard_min_ticks=overwrite_min,slots_per_direction=4)

def compile_image(source,out,expected_writes=None):
    lines=[int(x,16) for x in source.read_text().split()]
    assert lines and all(0<=x<1<<9688 for x in lines)
    serial=[]; stream={}; writes=[]; reads=[]
    for n,line in enumerate(lines):
        ser=dict(serial_edge=n,tick=4*n,read_return_edge=n+12,done_edge=n+10)
        serial.append(ser)
        for q in range(4):
            qw=(line>>(q*2422))&((1<<2422)-1)
            vmr=(qw>>(74+54+312))&((1<<240)-1)
            vmw=(qw>>(74+54))&((1<<312)-1)
            for p in range(8):
                r=(vmr>>(30*p))&((1<<30)-1); w=(vmw>>(39*p))&((1<<39)-1)
                bank=8*q+p
                if r>>29:
                    e=event(n); s=e['lg_issue']; row=stream.setdefault(s,[0,0]); assert not row[0]>>bank&1
                    row[0]|=1<<bank; reads.append(dict(q=q,p=p,command_edge=n,sector=(r>>13)&65535,**e))
                if w>>38:
                    # The serial store/RF drain path presents its registered
                    # request after command+3; bridge captures at command+4.
                    e=event(n+4); s=e['lg_issue']; row=stream.setdefault(s,[0,0]); assert not row[1]>>bank&1
                    row[1]|=1<<bank; writes.append(dict(q=q,p=p,command_edge=n,sector=(w>>8)&65535,**e))
    end=max([ceildiv(4*len(lines),3)+1]+[k+12 for k in stream])
    out.mkdir(parents=True,exist_ok=True)
    (out/'serial_prog.mem').write_bytes(source.read_bytes())
    (out/'stream_cal.mem').write_text(''.join(f'{stream.get(s,[0,0])[1]:08x}{stream.get(s,[0,0])[0]:08x}\n' for s in range(end)))
    (out/'serial_events.json').write_text(json.dumps(serial,separators=(',',':'))+'\n')
    (out/'read_events.json').write_text(json.dumps(reads,separators=(',',':'))+'\n')
    (out/'write_events.json').write_text(json.dumps(writes,separators=(',',':'))+'\n')
    if expected_writes:
        transformed=[]
        for line in expected_writes.read_text().split():
            old_edge=int(line[:8],16)
            transformed.append(f'{event(old_edge)["lg_issue"]:08x}'+line[8:])
        (out/'stream_expw.mem').write_text('\n'.join(transformed)+'\n')
    m=dict(schema='opentallas.hbm.su_multirate.calendar.v1',qualified=False,
      source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),serial_edges=len(lines),stream_edges=end,
      quantum_ps='2500/9',serial_period_ticks=4,stream_period_ticks=3,epoch_ticks=12,
      phase_contract='coincident phase zero; reset released before common epoch; physical phase proof OPEN',
      serial_read_return=12,serial_write_done=10,lg_read_return_stream=10,lg_write_done_stream=7,
      pgslice_serial_drain_capture=4,pgslice_fill_commit_serial=15,
      stream_slots_register_mod4=[0,2,3],stream_slots_lg_issue_mod4=[0,1,3],
      read_slots=len(reads),write_slots=len(writes),proof=prove(),
      payload_register_bits_per_port=4*(17+281+257+1)+(17+281+257+1),
      source_pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
        'tools/hbm_static/su_multirate_compile.py',
        'rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_pgslice.sv',
        'tools/hbm_static/su_top_compile.py']},
      expected_writes_source_sha256=hashlib.sha256(expected_writes.read_bytes()).hexdigest() if expected_writes else None,
      generated_planes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.mem')},
      limitations=['candidate boundary bridge only; top/compiler not integrated',
        'serial plane requires separate SRAM programme sequencer from stream calendar plane',
        'pgslice serial destination FD must be12 while stream leaf READ_RETURN stays10',
        'expected VM write checks must use stream event edges; arithmetic/scalars stay serial',
        'all programme SRAM and clock distribution timing/physical closure OPEN'])
    (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');return m

def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path,nargs='?');p.add_argument('out',type=Path,nargs='?')
    p.add_argument('--expected-writes',type=Path)
    a=p.parse_args();print(json.dumps(compile_image(a.source,a.out,a.expected_writes) if a.source else prove(),indent=2))
if __name__=='__main__':main()
