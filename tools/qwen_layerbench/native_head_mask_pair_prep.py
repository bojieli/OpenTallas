#!/usr/bin/env python3
"""Decode the two existing selected tile0/bank4 masks against genuine HEAD bytes."""
import argparse,hashlib,json
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('receipt','excerpt','mask-dir','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();r=json.loads(a.receipt.read_text());ex=json.loads(a.excerpt.read_text());pair=r['pair']
 assert pair['tile']==0 and pair['bank']==4 and pair['resident_base']==16384
 assert r['head']['resident_base']==18432 and r['head']['words']==1600
 assert r['head']['sha256']==ex['code_sha256']
 columns=[];sha_by_file={}
 for col,c in enumerate(pair['columns']):
  f=a.mask_dir/c['file'];assert sha(f)==c['sha256'];sha_by_file[c['file']]=sha(f)
  rows=[int(x,16)for x in f.read_text().split()];assert len(rows)==512 and all(x>>2048==0 for x in rows)
  words=[]
  for local in range(1600):
   adr=2048+local
   value=sum(((rows[adr//8]>>(8*b+adr%8))&1)<<b for b in range(256))
   assert value==(int(ex['code_words'][local],16)>>(256*col))&((1<<256)-1),(col,local)
   words.append(value)
  columns.append(dict(column=col,groups=[2*col,2*col+1],instance=c['instance'],mask_sha256=sha(f),head_row_range=[2048,3648],checked_words=len(words),checked_code_bytes=32*len(words)))
 result=dict(status='PASS_DATA_ONLY_SELECTED_NATIVE_MASK_DECODE',rank=0,tile=0,bank=4,macro_count=2,logical_code_bytes=102400,columns=columns,physical_mapping='bitline=8*logical_bit+(word%8), maskrow=word//8; unused high80physicalbitlines zero',readset={str(a.receipt):sha(a.receipt),str(a.excerpt):sha(a.excerpt),**sha_by_file},scope='Genuine code address/payload mapping only; no numeric engine, clocks, Xfill, scales or AMAX execution')
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
if __name__=='__main__':main()
