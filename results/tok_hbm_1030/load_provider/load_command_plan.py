"""Address-only proposal: resolved HGI LOAD -> existing static62-bit commands.

No target, dates, window ownership or backend route is installed. Runtime
indexed/dynamic descriptors must first be resolved through the actual source
I-list/CP contract. Commands group only consecutive naturally aligned elements
from one source sector into consecutive lanes of one VM sector; this retains
exact ordered behavior even when source/destination strides are non-unit.
"""
import json
from window_map import decode,encode
SIZES={0:4,1:2,2:1,4:1,5:4,6:1}


def plan(*,source_base,vm_base,n,m=1,source_stride=0,vm_stride=0,source_istride=1,vm_istride=1,fmt=5,buffer_bank,epoch):
 if fmt not in SIZES or n<1 or m<1 or source_istride<1 or vm_istride<1:raise ValueError('unqualified LOAD format/shape')
 if not 0<=buffer_bank<2 or not 0<=epoch<65536:raise ValueError('caller must provide actual buffer/epoch')
 es=SIZES[fmt];pending=None;out=[]
 def finish():
  if pending is None:return
  q=pending;sector=q['source_sector'];d=decode(sector);v=q['vm_word'];destsector=v>>3
  cmd=buffer_bank|(epoch<<1)|(d['source_group']<<17)|(d['slot']<<19)|(q['source_byte']<<25)|(fmt<<30)|(destsector<<33)|((v&7)<<49)|(q['elements']<<52)|((destsector&7)<<57)|(((destsector>>13)&3)<<60)
  out.append(dict(source_stack=q['stack'],source_window=dict(row=d['row'],col=d['col']),landing_quad=d['landing_quad'],landing_bank=d['landing_bank'],command=f'{cmd:016x}',elements=q['elements'],source_first_byte=q['source_first_byte'],vm_first_word=v,release=False,current_stack2_reachable=q['stack']==2))
 for row in range(m):
  for i in range(n):
   address=source_base+row*source_stride+i*source_istride*es;vm=vm_base+row*vm_stride+i*vm_istride
   local=address&((1<<35)-1);stack=address>>35&3
   if address<0 or address>>37 or local+es>22_500_000_000 or address%es or not 0<=vm<262144:raise ValueError('LOAD outside native physical/VM bounds')
   sector=local>>5;byte=local&31
   if byte+es>32:raise ValueError('source element crosses physical sector')
   if pending and pending['stack']==stack and pending['source_sector']==sector and pending['vm_word']//8==vm//8 and pending['source_byte']+pending['elements']*es==byte and pending['vm_word']+pending['elements']==vm and pending['elements']<8:pending['elements']+=1
   else:
    finish();pending=dict(stack=stack,source_sector=sector,source_byte=byte,source_first_byte=address,vm_word=vm,elements=1)
 finish();return out


def reconstructed_elements(item):
 cmd=int(item['command'],16);fmt=cmd>>30&7;es=SIZES[fmt];sector16=cmd>>33&65535;vm=(sector16<<3)+(cmd>>49&7);count=cmd>>52&15
 d=item['source_window'];pc=(0 if item['landing_quad']=='NW'else 16)|(cmd>>17&1)<<3|item['landing_bank'];s=encode(d['row'],d['col'],pc,cmd>>19&63);byte=cmd>>25&31
 assert (cmd>>57&7)==(sector16&7)and(cmd>>60&3)==(sector16>>13&3),'destination router inconsistent with VM packet'
 return [(((item['source_stack']<<35)|(s<<5))+byte+i*es,vm+i,fmt)for i in range(count)]


if __name__=='__main__':
 cases=[];checks=0
 for fmt,es in SIZES.items():
  for n,si,vi in[(65,1,1),(13,2,2)]:
   kwargs=dict(source_base=0x1D11000000,vm_base=65536,n=n,m=2,source_stride=1024,vm_stride=256,source_istride=si,vm_istride=vi,fmt=fmt,buffer_bank=1,epoch=17)
   result=plan(**kwargs);actual=[v for item in result for v in reconstructed_elements(item)];expected=[(kwargs['source_base']+row*1024+i*si*es,65536+row*256+i*vi,fmt)for row in range(2)for i in range(n)];assert actual==expected;checks+=len(actual);cases.append(dict(format=fmt,n=n,m=2,source_stride=si,vm_stride=vi,commands=len(result),source_elements=len(actual)))
 sample=plan(source_base=0x1D11000000,vm_base=0,n=16,fmt=5,buffer_bank=0,epoch=1)
 controls=[]
 for key,value in[('landing_bank',sample[0]['landing_bank']^1)]:
  bad=dict(sample[0]);bad[key]=value
  try:assert reconstructed_elements(bad)==reconstructed_elements(sample[0])
  except AssertionError:controls.append('wrong_PC_lane_caught')
  else:raise AssertionError('wrong PC escaped')
 result=dict(status='ADDRESS_ONLY_PROPOSAL_NO_INSTALL_OR_SELECTED_TARGET',cases=cases,element_address_checks=checks,controls=controls,sample_commands=sample,holds=['stack3 example has no current source provider','actual fixed calendar/PHYwindow/epoch reservation andrelease-onlybroadcast required','no command issue/drain dates orphysicalcycleprice assigned','runtime I-list anddynamicdescriptors notsilentlyresolved'])
 from pathlib import Path
 Path(__file__).with_name('load_command_plan.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(dict(cases=len(cases),element_address_checks=checks,controls=controls,sample_commands=len(sample))))
