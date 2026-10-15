#!/usr/bin/env python3
"""Full production-stage shapes, synthetic external source values; not chip qualification."""
from pathlib import Path
import argparse,hashlib,json
from controller_image import FIELDS,ABI,LATENCIES,L16_LATENCIES,L16_W1_LATENCIES,emit
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--read-pipe',type=int,choices=[0,4],default=0);p.add_argument('--wscatter-pipe',type=int,choices=[0,1],default=0);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[2]
if a.wscatter_pipe and a.read_pipe!=4: p.error("WSCATTER1 requires READ4/CAP2 candidate")
latency=L16_W1_LATENCIES if a.wscatter_pipe else L16_LATENCIES if a.read_pipe==4 else LATENCIES
read_flight=latency['vm_request_to_issue_edges']
N=2153 if a.wscatter_pipe else 2141
cycles=[dict(edge=e,cmd_valid=0,cmd84=0,consumer='none',transport_tag=0,done_valid=0,done_tag=0,controls=dict.fromkeys([n for n,w in FIELDS],0)) for e in range(N)]
reads=[]
def command(e,n,gather,tag,desc,consumer):
 cycles[e].update(cmd_valid=1,cmd84=(1<<83)|(((gather<<16)|n)<<7)|desc,transport_tag=tag,consumer=consumer)
def read(e,row,consumer):
 cycles[e]['controls'].update(read_slot=1,read_row=row);reads.append(dict(edge=e,row=row,consumer=consumer))
def record(j,first,n,tag,kind):
 issue=first+16*(j//3)+4*(j%3);commit=issue+11
 read(issue-read_flight,(64 if kind==0 else 1024)+j,'tp4')
 cycles[issue]['controls'].update(issue_slot=1,tag=tag,seq=j,last=int(j==n-1),rankmask=15)
 if kind==0:
  rows=tuple((4096+20*r+j if j<20 else 4224+8*r+j-20 if j<28 else 4816+8*r+j-28 if j<36 else 4848+8*r+j-36) for r in range(4))
 else:rows=(6000+j,0,0,0)
 cycles[commit]['controls'].update(commit_slot=1,commit_tag=tag,commit_seq=j,commit_last=int(j==n-1),commit_rankmask=15,commit_rows=sum(v<<(15*r) for r,v in enumerate(rows)),commit_gather=int(kind==0))
 if kind:
  inp=commit+1;wr=inp+18
  cycles[inp]['controls']['hc_reduce_slot']=1
  cycles[wr]['controls'].update(hc_write_slot=1,hc_assemble_slot=1,hc_word_index=j%16,hc_expect_seq=j,hc_expect_last=int(j==n-1))
  if j%16==15:cycles[wr+1]['controls'].update(hc_emit_slot=1,hc_emit_tag=tag)
command(0,44,1,0x123,5,'gather_vm')
command(320,320,0,0x456,6,'reduce_vm_hc')
for j in range(44):record(j,64,44,0x123,0)
for j in range(320):record(j,400,320,0x456,1)
cycles[317 if a.wscatter_pipe else 307].update(done_valid=1,done_tag=133)
cycles[2143 if a.wscatter_pipe else 2133].update(done_valid=1,done_tag=134)
# Global peer PHY calendar. All beats, including idle beats, are explicit.
for e,c in enumerate(cycles):
 x=c['controls'];tp=((e-3)//4)%4;rp=((e-4)//4)%4
 x.update(tx_beat_slot=int(e>=3 and e%4==3),tx_phase=tp,
          rx_beat_slot=int(e>=4 and e%4==0),rx_phase=rp)
 for first,n in [(64,44),(400,320)]:
  tj=3*((e-first-3)//16)+tp;rj=3*((e-first-4)//16)+rp-1
  if x['tx_beat_slot'] and e>=first+3 and tp!=3 and 0<=tj<n:x['tx_frame_slot']=1
  if x['rx_beat_slot'] and e>=first+4 and rp!=0 and 0<=rj<n:x['rx_frame_slot']=1
# Three independent real channel clients: raw VM, WFC, host. Channels3/4 idle.
read(344-read_flight,8000,'raw_payload');read(345-read_flight,8001,'raw_meta')
cycles[344]['controls']['raw_capture_payload_slot']=1
cycles[345]['controls']['raw_capture_meta_slot']=1
cycles[346]['controls'].update(channel_tx_slot=7,channel_tx_kind=(1<<2)|(2<<4),channel_tx_last=7)
cycles[347]['controls']['channel_tx_seq']=7|(8<<10)|(9<<20)
cycles[355]['controls'].update(channel_rx_seq=7|(8<<10)|(9<<20),channel_rx_last=7)
cycles[357]['controls'].update(channel_rx_slot=7,channel_rx_kind=(1<<2)|(2<<4))
cycles[358]['controls'].update(raw_rx_write_slot=1,raw_rx_payload_row=7000,raw_rx_meta_row=7001,raw_rx_tag=0x27)
for k in range(4):
 cycles[349+4*k]['controls'].update(channel_tx_beat_slot=7,channel_tx_phase=sum(k<<(2*j) for j in range(3)),channel_tx_frame_slot=7 if k==0 else 0)
 cycles[350+4*k]['controls'].update(channel_rx_beat_slot=7,channel_rx_phase=sum(k<<(2*j) for j in range(3)),channel_rx_frame_slot=7 if k==1 else 0)
request=dict(abi=ABI,command_abi='opentallas.s81.cmd84.v1',latencies=latency,
 evidence=[dict(path='rtl/dsrom_sys/s81_static_collective/s81_static_collective_slab.sv',sha256=hashlib.sha256((root/'rtl/dsrom_sys/s81_static_collective/s81_static_collective_slab.sv').read_bytes()).hexdigest())],
 native_source_binding='COMPONENT: external source fixtures, rank0 actual128SRAM VM; not production FIELD',
 vm_reservations='COMPONENT: source64..107/1024..1343/8000..8001; actual target rows in controls; all sources44..47',
 physical_phase_binding='COMPONENT: common epoch, zero declared external PHY flight; not die phase proof',
 timing_price_binding='UNQUALIFIED: immutable model not altered; full production stage shapes only',
 read_reservations=reads,cycles=cycles,integration_ready=False)
if a.read_pipe==4:
 request['vm_profile']=dict(READ_PIPE=4,CAP_PIPE=2,WSCATTER_PIPE=a.wscatter_pipe,source_sha256=hashlib.sha256((root/'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm_static.sv').read_bytes()).hexdigest())
result=emit(request,root,a.out/'calendar.mem')
(a.out/'request.json').write_text(json.dumps(request,indent=2)+'\n')
(a.out/'image_receipt.json').write_text(json.dumps(result,indent=2)+'\n')
# Exact controls provide ideal external peer programs, never payload/results inside the DUT.
(a.out/'controls.mem').write_text(''.join(f'{sum(c["controls"][n]<<sum(w for _,w in FIELDS[:i]) for i,(n,width) in enumerate(FIELDS)):0{(sum(w for _,w in FIELDS)+3)//4}x}\n' for c in cycles))
print(json.dumps(result))
