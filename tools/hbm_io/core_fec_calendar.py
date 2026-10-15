"""Fixed finite core16:FEC17 clock reservations; pointers diagnose only."""
from fractions import Fraction

def core_word(base,k):return base+17*k//16

def fifo(direction,phase=0,ppm=0,words=2048):
 cp=Fraction(16);fp=Fraction(17)*(1+Fraction(ppm,1000000));phase=Fraction(phase)
 wc,rc=('core','fec') if direction=='tx' else ('fec','core')
 writes=({core_word(512,k):k for k in range(words)} if wc=='core' else {649+k:k for k in range(words)})
 reads=({488+k:k for k in range(words)} if rc=='fec' else {core_word(697,k):k for k in range(words)})
 end=max(cp*(max(writes if wc=='core' else reads)+2),fp*(max(writes if wc=='fec' else reads)+2)+phase)
 events={}
 for domain,period in [('core',cp),('fec',fp)]:
  n=int(end/period)+4
  for e in range(1,n):events.setdefault((Fraction(e)-Fraction(1,2))*period+(phase if domain=='fec' else 0),[]).append((domain,e))
 wp=rp=wg=rg=0;rg1=rg2=wg1=wg2=0;mem={};faults=[];occ=[];wf=[];rf=[];checked=0
 def gray(x):return x^(x>>1)
 def binary(x):
  b=0
  while x:b^=x;x>>=1
  return b
 for t,edges in sorted(events.items()):
  # Simultaneous clocks observe old pointer state, just like nonblocking RTL.
  oldwp,oldrp,oldwg,oldrg=wp,rp,wg,rg
  oldrg1,oldrg2,oldwg1,oldwg2=rg1,rg2,wg1,wg2
  for d,e in edges:
   if d==wc:
    rg1,rg2=oldrg,oldrg1
    if e in writes:
     k=writes[e];fill=(oldwp-binary(oldrg2))%32;wf.append(fill)
     if fill>=16:faults.append(('write_ownership',k,e,fill))
     mem[oldwp%16]=k;wp=(oldwp+1)%32;wg=gray(wp)
   if d==rc:
    wg1,wg2=oldwg,oldwg1
    if e in reads:
     k=reads[e];fill=(binary(oldwg2)-oldrp)%32;rf.append(fill)
     if fill==0 or fill>16:faults.append(('read_ownership',k,e,fill))
     if mem.get(oldrp%16)!=k:faults.append(('payload',k,e,mem.get(oldrp%16)))
     rp=(oldrp+1)%32;rg=gray(rp);checked+=1
  occ.append((wp-rp)%32)
 return dict(direction=direction,phase_ticks=float(phase),relative_FEC_ppm=ppm,words_checked=checked,
  min_read_observed_fill=min(rf),max_write_observed_fill=max(wf),max_actual_occupancy=max(occ),
  faults=faults[:8],fault_count=len(faults))

def model():
 return dict(core_GHz=1.2,FEC_GHz=1.2*16/17,core_period_ticks=16,FEC_period_ticks=17,
  core_period_ps=833.333333333,FEC_period_ps=885.416666667,tick_ps=52.083333333,
  words=2048,CDC_entries=16,Gray_sync_stages=2,
  complete_frame_capacity=1627,tail_padding_bits=25,tail_frame_must_be_idle=True,
  actual_CDC_payload_register_bits=2*16*487,
  actual_CDC_read_face_register_bits=2*487,
  control_root_register_bits_upper_bound_per_domain=9000,
  clock_groups=["core1.2:TXstorage+RXread","FEC16/17:RXstorage+TXread"],
  TX_word_steps=[511,core_word(511,2047)],TX_CDC_writes=[512,core_word(512,2047)],
  TX_CDC_FEC_reads=[488,2535],FEC_input_edges=[489,2536],FEC_age_edges=151,
  FEC_capture_edges=[640,2687],internal_FEC_CDC_reads=[648,2695],RX_CDC_FEC_writes=[649,2696],
  RX_CDC_core_reads=[697,core_word(697,2047)],RX_gearbox_core_steps=[698,core_word(698,2047)],
  frame_acceptance='511+floor(17*floor(613*j/487)/16)',endpoint_read='A-7',endpoint_write='A-11',
  endpoint_RX_capture='700+floor(17*(ceil(613*(j+1)/487)-1)/16)',
  endpoint_RX_publish='702+floor(17*(ceil(613*(j+1)/487)-1)/16)',
  stop_contract='word_step=0 outside finite2048word reservations; core may continue local decode/store afterwindow; no missingword fault on unreserved edges',
  bandwidth_application_bytes_per_core_cycle=64*(487/613)*(16/17),
  scope='model before new stepgearbox/real CDC RTL; actualclockphase/drift/physical and wholeintegration tests pending')
if __name__=='__main__':
 import json
 safe=[fifo(d,p,ppm) for d in ['tx','rx'] for p in [-8,0,8] for ppm in [-500,0,500]]
 assert all(x['fault_count']==0 for x in safe),[x for x in safe if x['fault_count']]
 bad=[fifo(d,0,ppm) for d in ['tx','rx'] for ppm in [-10000,10000]]
 assert all(x['fault_count'] for x in bad),bad
 print(json.dumps(dict(model=model(),safe=safe,unsafe_drift=bad),indent=2))
