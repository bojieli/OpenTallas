import pathlib,struct,json,time
base=pathlib.Path('/home/ubuntu/w17-L0-live-probe-20261001');pid=620383
vtable=0x5d392e9a66a0+16
maps=(pathlib.Path('/proc')/str(pid)/'maps').read_text().splitlines();heap=next(x for x in maps if '[heap]' in x);lo,hi=[int(x,16) for x in heap.split()[0].split('-')]
f=open('/proc/620383/mem','rb',buffering=0);needle=struct.pack('<Q',vtable);found=[]
for addr in range(lo,min(hi,lo+64*1024*1024),1024*1024):
 f.seek(addr);b=f.read(min(1024*1024,hi-addr));at=b.find(needle)
 while at>=0:
  if (addr+at)%8==0:found.append(addr+at)
  at=b.find(needle,at+1)
assert len(found)==1,found
obj=found[0]
def ptr(a):f.seek(a);return struct.unpack('<Q',f.read(8))[0]
die=ptr(obj+0x690)
lines=(base/'offsets.txt').read_text().splitlines();root=ptr(die+int(lines[0].split()[1]));values={}
for line in lines[1:]:
 name,off,size=line.split();size=int(size)
 if size>8:continue
 f.seek(root+int(off));values[name]=int.from_bytes(f.read(size),'little')
pcptr=ptr(die+0xd8);f.seek(pcptr);pc=int.from_bytes(f.read(2),'little')
r=dict(time=time.time(),pid=pid,object=hex(obj),die=hex(die),root=hex(root),PC=pc,values=values,read_only=True,coherent_clock_edge=False)
print(json.dumps(r,indent=2))
