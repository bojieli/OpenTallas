"""Inverse of the actual vm_kshare PC-window address formula (proposal only)."""
import json
from pathlib import Path


def decode(sector):
 if not 0<=sector<1<<30:raise ValueError('K-port address must be stack-local30-bit SECTOR, not byte address')
 pc=((sector>>2)^(sector>>7)^(sector>>12))&31
 j=(((sector>>7)&1)<<3)|((sector>>12)&7)
 return dict(row=sector>>15,col=(sector>>8)&15,pc=pc,slot=j*4+(sector&3),landing_quad='NW'if pc<16 else'NE',landing_bank=pc&7,source_group=(pc>>3)&1)


def encode(row,col,pc,slot):
 if not 0<=row<1<<15 or not 0<=col<16 or not 0<=pc<32 or not 0<=slot<64:raise ValueError('native window field overflow')
 j=slot>>2;bhi=j&7;c=(col<<1)|(j>>3);h=pc^c^(((row&3)<<3)|bhi)
 return(row<<15)|(bhi<<12)|(c<<7)|(h<<2)|(slot&3)


def check():
 count=0
 # All low17 bits include every PC/hash,slot,col and row-low2 combination.
 # Higher row13 bits are passed through without logic; representative high
 # fields check their complete encoded range and the last physical sector.
 for s in range(1<<17):
  d=decode(s);assert encode(d['row'],d['col'],d['pc'],d['slot'])==s;count+=1
 for high in(1,17,8191):
  for low in(0,1,127,128,4095,4096,32767,65535,131071):
   s=(high<<17)|low;d=decode(s);assert encode(d['row'],d['col'],d['pc'],d['slot'])==s;count+=1
 for s in(703124999,):
  d=decode(s);assert encode(d['row'],d['col'],d['pc'],d['slot'])==s;count+=1
 # One complete window covers2048 unique sectors,16PC/1024sectors per
 # landing quadrant. Every bank gets both local source groups and64slots.
 for row,col in((0,0),(2,15),(20736,9)):
  addresses={encode(row,col,p,s)for p in range(32)for s in range(64)};assert len(addresses)==2048
  assert all(decode(v)['row']==row and decode(v)['col']==col for v in addresses)
 return count


if __name__=='__main__':
 result=dict(status='SOURCE_ADDRESS_PROPOSAL_NOT_SELECTED_PROVIDER',inverse_checks=check(),full_window_bytes=2048*32,quadrant_window_bytes=1024*32,source_landing='current stack2:PC0..15→NW,PC16..31→NE; destination independent via load_static dest_q/bank',pre_swizzle_required=False,holds=['current source stack2 only; stack3 candidate unselected','new load_static type/interface + static DQ destination routing needs plan event','fixed fill deadline/epoch/readiness and actual transports still required'])
 path=Path(__file__).with_name('window_map.json');path.write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result))
