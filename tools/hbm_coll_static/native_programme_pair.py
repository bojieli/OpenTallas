#!/usr/bin/env python3
"""Protected native pair compiler/installer ABI. No host write occurs in this tool."""
import argparse
import hashlib
import json
from pathlib import Path

ROWS=1024
W=291
FIELDS={'attention':(0,192),'read_v':(192,1),'read_bank':(193,1),'read_epoch':(194,16),
 'read_row':(210,6),'read_tag':(216,10),'retire_v':(226,1),'retire_bank':(227,1),'retire_epoch':(228,16),
 'pv_open':(244,1),'pv_buffer':(245,1),'pv_epoch':(246,16),'pv_block':(262,1),'pv_write_expect':(263,1),
 'pv_read':(264,1),'pv_read_buffer':(265,1),'pv_read_block':(266,1),'pv_head':(267,2),'pv_half':(269,1),
 'pv_group':(270,3),'pv_retire':(273,1),'pv_retire_buffer':(274,1),'pv_retire_epoch':(275,16)}


def pack_fields(**fields):
 value=0
 for key,item in fields.items():
  lo,width=FIELDS[key]
  if not 0<=item<(1<<width):raise ValueError((key,item,width))
  if key=='attention' and item and item>>184!=0xa2:raise ValueError('attention command requires a2')
  value|=item<<lo
 return value


def encode(value,pc,plane):
 if not 0<=value<(1<<W) or not 0<=pc<ROWS or plane not in (0,1):raise ValueError('pair bounds')
 data=(value>>(215*plane))&((1<<215)-1)
 return (0xc7a1<<240)|(pc<<224)|((0xa0+plane)<<215)|data


def decode(word,pc,plane):
 if word>>240!=0xc7a1 or (word>>224)&1023!=pc or (word>>234)&63 or (word>>223)&1:
  raise ValueError('protected header')
 if (word>>215)&255!=0xa0+plane:raise ValueError('plane role')
 data=word&((1<<215)-1)
 if plane==1 and data>>(W-215):raise ValueError('unused payload bits')
 return data


def decode_pair(word0,word1,pc):
 return decode(word0,pc,0)|(decode(word1,pc,1)<<215)


def profile_word(sm,epoch,pc):
 # Typed payload tests every context field. This profile is an installation/
 # calendar-preservation vehicle, not a ready-to-run SM arithmetic programme.
 att=(0xa2<<184)|(6<<181)|(1<<180)|((pc&3)<<132)|((epoch&0xfff)<<11)|(sm<<3)|(pc&7)
 return pack_fields(attention=att,read_v=pc&1,read_bank=(pc>>1)&1,read_epoch=epoch,
  read_row=pc%64,read_tag=(pc+sm*7)%1024,retire_v=(pc>>2)&1,retire_bank=(pc>>3)&1,retire_epoch=epoch^pc,
  pv_open=(pc>>4)&1,pv_buffer=(pc>>5)&1,pv_epoch=epoch+sm,pv_block=(pc>>6)&1,pv_write_expect=(pc>>7)&1,
  pv_read=(pc>>8)&1,pv_read_buffer=(pc>>9)&1,pv_read_block=pc&1,pv_head=sm%4,pv_half=sm%2,
  pv_group=(pc//2)%8,pv_retire=(pc>>3)&1,pv_retire_buffer=(pc>>2)&1,pv_retire_epoch=epoch^pc^(sm<<11))


def install_ops(sm,epoch,values):
 if len(values)!=ROWS:raise ValueError('full1024 PC image required')
 if not 0<=sm<32 or not 0<epoch<65536:raise ValueError('target/epoch')
 target=128+sm
 yield dict(kind='begin',target=target,epoch=epoch,expect_ack_kind=1)
 for pc,value in enumerate(values):
  for plane in range(2):
   yield dict(kind='write',target=target,epoch=epoch,addr=(plane<<10)|pc,data=f'{encode(value,pc,plane):064x}',
              expect_ack_kind=0,atomic_pair_seal=bool(plane))
 yield dict(kind='commit',target=target,epoch=epoch,expect_ack_kind=2)


def emit(out):
 out.mkdir(parents=True,exist_ok=True)
 files={}
 for epoch in (1,2):
  paths=[out/f'epoch{epoch}_{name}.hex' for name in ('plane0','plane1','logical')]
  with paths[0].open('w') as f0,paths[1].open('w') as f1,paths[2].open('w') as fl:
   for sm in range(32):
    for pc in range(ROWS):
     value=profile_word(sm,epoch,pc);w0=encode(value,pc,0);w1=encode(value,pc,1)
     assert decode_pair(w0,w1,pc)==value
     f0.write(f'{w0:064x}\n');f1.write(f'{w1:064x}\n');fl.write(f'{value:073x}\n')
  files.update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
 # Byte-level compiler negative checks preserve reserved fields and word roles.
 bad=encode(profile_word(0,1,0),0,0)
 for mutant in (bad^(1<<223),bad^(1<<240),bad^(1<<224),bad^(1<<215)):
  try:decode(mutant,0,0)
  except ValueError:pass
  else:raise AssertionError('compiler protected-format mutant survived')
 model=dict(schema='native-programme-pair-v1',format='c7a1[255:240]; PC[233:224]; reserved239:234 and223 zero; role222:215=A0/A1; data214:0',
  raw_protected_payload_bits=446,role_bits=16,usable_logical_bits=430,native_ABI_bits=W,fields=FIELDS,
  targets=[128,159],addr='[11]=0,[10]=plane,[9:0]=PC',
  install='begin epoch -> plane0 then plane1 for everyPC -> commit; each op waits matching actual ACK; plane1 actual write seals pair',
  control_registers='host adapter D4C begin(epoch16,target8), D50 commit, D58 required launch epoch, D20 target8+addr12, D24 eight LE32 chunks/word',
  launch='all participating target readiness/epoch/fault checked before single fixed launch pulse; no ready stalls in execution',
  source_profile_scope='typed byte-preservation programme vehicle; no arithmetic or HBM-service qualification',
  shape=dict(SMs=32,SRAMs_per_SM=2,SRAMs_die=64,additional_SRAMs_die_vs_single=32,SRAM='actual1024x256 model',
   persistent_install_mask_bits_per_SM=3072,install_payload_bytes_per_image=32*1024*2*32,
   host_data_register_writes_per_image=32*1024*2*8,host_begin_commit_ops_per_image=64),
  predicted_edges=dict(cfg_input_to_macro_commit_and_ACK=1,start_input_to_accept=1,start_input_to_first_macro_read=2,
   start_input_to_first_calendar=4,macro_read_to_calendar=2,execution_II=1),
  files_sha256=files,physical_qualification=False,fullSM_qualification=False)
 (out/'manifest.json').write_text(json.dumps(model,indent=2)+'\n')
 return model

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);ap.add_argument('--install-sm',type=int);ap.add_argument('--epoch',type=int,default=1)
 a=ap.parse_args();out=Path(a.out);model=emit(out)
 if a.install_sm is not None:
  with (out/'install.jsonl').open('w') as f:
   for op in install_ops(a.install_sm,a.epoch,[profile_word(a.install_sm,a.epoch,pc) for pc in range(ROWS)]):f.write(json.dumps(op)+'\n')
 print('NATIVE_PAIR_COMPILER PASS profiles=32 rows=1024 epochs=2 usable_bits=430 ABI_bits=291')
