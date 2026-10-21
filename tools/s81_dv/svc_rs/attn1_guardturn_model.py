#!/usr/bin/env python3
"""Source-bound edge model only; the paired actual-RTL guardturn bench must qualify it.

I=old last QK issue; L=new Q head0 load. Counts edge transitions, not data
arithmetic or physical timing. A bank write and multiplier operand capture on the
same edge see the old nonblocking-assignment value and are safe.
"""
import hashlib,json,pathlib
root=pathlib.Path(__file__).resolve().parents[3]
p=root/'rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv'
s=p.read_bytes();assert hashlib.sha256(s).hexdigest()=='b1f0d0def70e01764895016c92556ec03ebc7254d4b469fe532971d947020dc5'
tile_sha=hashlib.sha256((root/'rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv').read_bytes()).hexdigest()
assert tile_sha=='1c6df348f0027a9cd72185fad65c2b767372384a670ab246ec2b4d5f46bef4ce'
# Production S81 params of tb_attn1_nt1, not the SVCQ_ENG_FG3 diagnostic.
fpl,xd,v=4,1,4
skew=lambda j:0 if j==0 else fpl*(j-1)
guard_q=skew(7)+2
rows=[]
for mutant,vx in [(0,v),(3,0)]:
 timer=guard_q+1+xd+vx
 # An issue edge installs timer; timer decrement reaches0 after timer edges;
 # the allocator consumes the new zero on the following edge.
 load=timer+1
 hazards=[]
 for head in range(16):
  write=load+2+head # E load register + per-head R0 copy + stationary bank write
  for virtual in range(v):
   for col in range(32):
    read=6+virtual+skew(col%8) # issue->rd1/rd2/E/subbeat/R0/D1 + skew + operand capture
    if read>write:hazards.append(dict(head=head,virtual=virtual,col=col,read_edge=read,overwrite_edge=write))
 rows.append(dict(NMUT=mutant,VX=vx,GUARD_Q=guard_q,timer=timer,earliest_q_load=load,hazards=hazards))
assert not rows[0]['hazards'] and len(rows[1]['hazards'])==12
print(json.dumps(dict(scope='EDGE_MODEL_ONLY_NOT_RTL_WITNESS',engine_sha256=hashlib.sha256(s).hexdigest(),tile_sha256=tile_sha,rows=rows),indent=2))
