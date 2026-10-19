#!/usr/bin/env python3
"""Source-first 900MHz SU / 1.2GHz VM calendar, integer 1/3 stream ticks.

No requests are inferred at runtime. Every event derives from a serial-edge
programme and declared fixed hardware stages; all times are integer quanta.
"""
import argparse, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def ceildiv(a,b): return (a+b-1)//b

# HBM-BANKLAT-SU 2026-10-19: stream LG round trip READ_RETURN/WRITE_RETURN (pgslice/bridge parameters; 10/7 = zero-lane
# non-pin bank). The serial presentation edges follow ot_hbm_su_multirate_bridge: SRD=ceil((3RR+18)/4) (12 at 10),
# SWD=ceil((3WR+18)/4) (10 at 7). Set once per die binding with set_round_trip() or --read-return/--write-return.
LG_RR, LG_WR = 10, 7
def srd(rr): return ceildiv(3*rr+18,4)
def set_round_trip(rr,wr):
    global LG_RR,LG_WR
    assert 10<=rr and 7<=wr<=rr, (rr,wr)
    LG_RR,LG_WR=rr,wr

def event(n):
    j=ceildiv(4*n+4,3); rr,wr=LG_RR,LG_WR; sr,sw=srd(rr),srd(wr)
    return dict(serial_capture=n,serial_capture_tick=4*n,
        stream_register=j,stream_register_tick=3*j,
        lg_issue=j+1,lg_issue_tick=3*(j+1),
        lg_read_present=j+1+rr,read_capture_stream=j+2+rr,read_capture_tick=3*(j+2+rr),
        serial_read_present=n+sr,serial_read_tick=4*(n+sr),
        lg_write_done_present=j+1+wr,write_capture_stream=j+2+wr,write_capture_tick=3*(j+2+wr),
        serial_done_present=n+sw,serial_done_tick=4*(n+sw))

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
        ser=dict(serial_edge=n,tick=4*n,read_return_edge=n+srd(LG_RR),done_edge=n+srd(LG_WR))
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
    end=max([ceildiv(4*len(lines),3)+1]+[k+LG_RR+2 for k in stream])
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
      serial_read_return=srd(LG_RR),serial_write_done=srd(LG_WR),lg_read_return_stream=LG_RR,lg_write_done_stream=LG_WR,
      pgslice_serial_drain_capture=4,pgslice_fill_commit_serial=srd(LG_RR)+3,
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
        f'pgslice serial destination FD must be{srd(LG_RR)} while stream leaf READ_RETURN is{LG_RR}',
        'expected VM write checks must use stream event edges; arithmetic/scalars stay serial',
        'all programme SRAM and clock distribution timing/physical closure OPEN'])
    (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');return m

def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path,nargs='?');p.add_argument('out',type=Path,nargs='?')
    p.add_argument('--expected-writes',type=Path)
    p.add_argument('--read-return',type=int,default=10,help='stream LG read round trip (pgslice READ_RETURN)')
    p.add_argument('--write-return',type=int,default=7,help='stream LG write round trip (pgslice WRITE_RETURN)')
    a=p.parse_args();set_round_trip(a.read_return,a.write_return);print(json.dumps(compile_image(a.source,a.out,a.expected_writes) if a.source else prove(),indent=2))
if __name__=='__main__':main()
