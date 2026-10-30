import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from load_command_plan import plan,SIZES
R=Path(sys.argv[2])
ds=[];ev=[];sp=[];words=0
for code in range(2):
 for st in range(4):
  for fmt,es in SIZES.items():
   for sis in [0,1,3]:
    for dis in [0,1,2]:
     local=0x100000+(fmt%4)*es;dest=65529;sb=(code<<37)|(st<<35)|local;n=19;m=3
     desc=0|(fmt<<2)|(sb<<5)|(512<<45)|(sis<<77)|(1<<93)|((5 if fmt==5 else 0)<<95)|(dest<<98)|(128<<138)|(dis<<170)|(m<<186)|(n<<206)
     start=len(ev);items=[]
     for row in range(m):
      rowbase=(((st+row)%4 if code else st)<<35)+local+row*512
      if sis and dis:items+=plan(source_base=rowbase,vm_base=dest+row*128,n=n,source_istride=sis,vm_istride=dis,fmt=fmt,buffer_bank=0,epoch=19)
      else:
       for i in range(n):items+=plan(source_base=rowbase+i*sis*es,vm_base=dest+row*128+i*dis,n=1,fmt=fmt,buffer_bank=0,epoch=19)
     for i,q in enumerate(items):
      cmd=int(q['command'],16);cnt=q['elements'];w=q['source_window'];leaf=q['landing_bank'];quad=2 if q['landing_quad']=='NW' else 3
      fields=[(q['source_first_byte'],40),(q['vm_first_word'],40),(fmt,3),(cnt,4),(int(i==len(items)-1),1),(cmd,62),(leaf,3),(quad,2),(w['row'],15),(w['col'],4),(0,1),(19,16)]
      v=0;bits=0
      for val,width in fields:v=v<<width|val;bits+=width
      assert bits==191
      ev.append(f'{v:048x}');words+=cnt
     ds.append(f'{desc:057x}');sp.append(f'{(start<<32)|len(items):016x}')
(R/'coalesce_desc.mem').write_text('\n'.join(ds)+'\n');(R/'coalesce_expect.mem').write_text('\n'.join(ev)+'\n');(R/'coalesce_span.mem').write_text('\n'.join(sp)+'\n')
print(len(ds),len(ev),words)
