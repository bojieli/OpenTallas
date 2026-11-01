#!/usr/bin/env python3
"""Actual NPC2 conversion/packet/native-VM payload fixture; no PHY/index mapper adoption."""
import argparse,hashlib,json,math,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
REF='24de429cd';FIX='79d539a81';ND=48;FMTS=[0,1,2,4,5,6]
F32=[0,0x80000000,1,0x007fffff,0x00800000,0x3f800000,0xbf800000,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7fc12345,0xffc12345,0x7fa12345,0xffa12345,0xdeadbeef]
BF16=[0,0x8000,1,0x007f,0x0080,0x3f80,0xbf80,0x7f7f,0xff7f,0x7f80,0xff80,0x7fc1,0xffc1,0x7f81,0xff81,0x55aa]
def show(ref,path):return subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT)
def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def decode(raw,fmt):
 if fmt in (0,5):return raw
 if fmt==1:return raw<<16
 if fmt==4:return bits(raw if raw<128 else raw-256)
 if fmt==6:return bits(float('nan'))if raw==255 else bits(math.ldexp(1.0,raw-127))
 s,e,m=raw>>7,(raw>>3)&15,raw&7
 value=float('nan')if e==15 and m==7 else math.ldexp(m,-9)if e==0 else math.ldexp(1+m/8,e-7)
 return bits(-value if s else value)
def sector(fmt,b,g,slot,nan=False):
 a=bytearray()
 if fmt in (0,5):
  for w in range(8):a.extend(struct.pack('<I',F32[(slot*8+w+b*3+g*5)%len(F32)]))
 elif fmt==1:
  for w in range(16):a.extend(struct.pack('<H',BF16[(slot*16+w+b*3+g*5)%len(BF16)]))
 else:
  for w in range(32):
   code=(slot*32+w+b*17+g*53)&255
   if fmt==2 and not nan and code in (127,255):code-=1
   a.append(code)
 return bytes(a)
def source_byte(b,g,slot,offset):
 x=(20752<<20)|((slot>>5)<<12)|(((slot>>2)&7)<<17)|((slot&3)<<5)
 pc=b+8*g;x|=(pc^((x>>12)&31)^((x>>17)&31))<<7
 return(2<<35)|x|offset
def source_raw(address,fmt,nan):
 x=address&((1<<35)-1);pc=((x>>7)^(x>>12)^(x>>17))&31;slot=((x>>12)&1)*32+((x>>17)&7)*4+((x>>5)&3)
 n=4 if fmt in(0,5)else 2 if fmt==1 else 1
 return int.from_bytes(sector(fmt,pc&7,(pc>>3)&1,slot,nan)[x&31:(x&31)+n],'little')
def main(out,source_ref=REF):
 out.mkdir(parents=True,exist_ok=False);desc=[];steps=[];expected={False:[],True:[]};ends=[];meta=[]
 for phase,fmt in enumerate(FMTS):
  es=4 if fmt in(0,5)else 2 if fmt==1 else 1
  for case in range(ND):
   if case<32:b=g=0;slot=(case*8*es)//32;offset=(case*8*es)%32;n=8
   else:b=(case-32)%8;g=(case-32)//8;slot=(case*7)%64;offset=(32-3*es)if case%2 else 0;n=3
   src=source_byte(b,g,slot,offset);q=(case//8)%4;dst=q*65536+(case+1)*256+(case%8)*8+(case%8)
   d=(fmt<<2)|(src<<5)|(1<<77)|(1<<93)|((5 if fmt==5 else 0)<<95)|(dst<<98)|(1<<170)|(1<<186)|(n<<206);desc.append(d)
   sa,da,left=src,dst,n;count_steps=0
   while left:
    count=min(8,(32-(sa&31))//es,8-(da&7),left);assert count>0
    for nan in(False,True):
     mask=((1<<count)-1)<<(da&7);data=0
     for j in range(count):data|=decode(source_raw(sa+j*es,fmt,nan),fmt)<<((da%8+j)*32)
     expected[nan].append((1<<280)|((da>>3)<<264)|(data<<8)|mask)
    sa+=count*es;da+=count;left-=count;count_steps+=1
   steps.append(count_steps);meta.append(dict(format=fmt,source=src,destination=dst,words=n,packets=count_steps))
  ends.append(len(expected[False]))
 for name,values,width in [('format_desc.mem',desc,57),('format_steps.mem',steps,8),('format_ends.mem',ends,8),('format_expected.mem',expected[False],71),('format_expected_nan.mem',expected[True],71)]:
  (out/name).write_text(''.join(f'{x:0{width}x}\n'for x in values))
 for nan,name in[(False,'format_fill.mem'),(True,'format_fill_nan.mem')]:
  values=[]
  for fmt in FMTS:
   for b in range(8):
    for g in range(2):
     for slot in range(64):
      data=sector(fmt,b,g,slot,nan)
      values.extend(int.from_bytes(data[w:w+4],'little')for w in range(0,32,4))
  (out/name).write_text(''.join(f'{x:08x}\n'for x in values))
 np=len(expected[False]);tb=show(FIX,'results/tok_hbm_provider_1030/tb_vm_provider.sv').decode().replace('tb_vm_provider','tb_formats_provider')
 tb=tb.replace('desc_limit=14','desc_limit=48').replace('[0:13]','[0:287]').replace('[0:2687]',f'[0:{np-1}]')
 tb=tb.replace(' integer cyc=0,',' reg[31:0]fill_words[0:49151];reg[31:0]phase_end[0:5];integer nan_case=0,mut_offset=0,mut_format=0;\n integer cyc=0,')
 for old,new in [('fixture_desc.mem','format_desc.mem'),('fixture_steps.mem','format_steps.mem'),('fixture_expected.mem','format_expected.mem')]:tb=tb.replace(old,new)
 tb=tb.replace(' repeat(32)tick();rst_n=1;', ''' if($value$plusargs("NAN_SIGN=%d",nan_case))begin end
 if($value$plusargs("MUT_OFFSET=%d",mut_offset))begin end
 if($value$plusargs("MUT_FORMAT=%d",mut_format))begin end
 $readmemh("format_ends.mem",phase_end);
 if(nan_case!=0)begin $readmemh("format_fill_nan.mem",fill_words);$readmemh("format_expected_nan.mem",expected);end
 else $readmemh("format_fill.mem",fill_words);
 repeat(32)tick();rst_n=1;''')
 tb=tb.replace('phase<3','phase<6').replace('di<14','di<48').replace('steps[di]','steps[phase*48+di]').replace('descs[di]','descs[phase*48+di]')
 tb=tb.replace('fill_data[(b*2+g)*256+w*32+:32]=payload(phase,b,g,s,w);','fill_data[(b*2+g)*256+w*32+:32]=fill_words[phase*8192+b*1024+g*512+s*8+w];')
 tb=tb.replace('command[290:64]=descs[phase*48+di];','command[290:64]=descs[phase*48+di];\n if(mut_offset!=0&&phase==2)command[290:64]=command[290:64]^(227\'d1<<5);\n if(mut_format!=0&&phase==1)command[68:66]=3\'d4;')
 tb=tb.replace('(phase+1)*896','phase_end[phase]').replace('(phase+1)*14','(phase+1)*48').replace('phase*896','(phase==0?0:phase_end[phase-1])')
 tb=tb.replace('vm_dq!==expected[got]','(vm_dq[280:264]!==expected[got][280:264]||vm_dq[7:0]!==expected[got][7:0])')
 tb=tb.replace('if(latency<0)latency=cyc-sent_cycle[got];', '''for(integer vw=0;vw<8;vw=vw+1)if(expected[got][vw]&&vm_dq[8+vw*32+:32]!==expected[got][8+vw*32+:32])$fatal(1,"FORMAT_PAYLOAD_MISMATCH phase=%0d packet=%0d lane=%0d actual=%h expected=%h",phase,got,vw,vm_dq[8+vw*32+:32],expected[got][8+vw*32+:32]);
 if(latency<0)latency=cyc-sent_cycle[got];''')
 tb=tb.replace('rr0_bank[nb][255:0]!==expected[read_got][263:8]','1\'b0')
 tb=tb.replace('if(read_latency<0)read_latency=cyc-read_cycle[read_got];', '''for(integer rw=0;rw<8;rw=rw+1)if(expected[read_got][rw]&&rr0_bank[nb][rw*32+:32]!==expected[read_got][8+rw*32+:32])$fatal(1,"FORMAT_SRAM_MISMATCH phase=%0d packet=%0d",phase,read_got);
  if(read_latency<0)read_latency=cyc-read_cycle[read_got];''')
 tb=tb.replace('PASS NATIVE_VM_CP_PROVIDER','PASS ALL6_FORMAT_NATIVE_VM_CP_PROVIDER').replace('epochs=3','epochs=6').replace('got*8','6*304')
 (out/'tb_formats_provider.sv').write_text(tb)
 manifest=json.loads(show(FIX,'results/tok_hbm_provider_1030/timing833_source_dependencies.json'));paths=list(manifest['shared_repo_files'])
 # Keep exactly the native leaf/counter/constructor/CP and VM bank dependencies.
 paths=[x for x in paths if not any(y in x for y in ['vm_kshare','pc_ctrl','refresh','async_fifo','ring_h9','pin_skid','model_ready','rst_relay','rst_sync'])]
 for x in list(manifest['provider_files'])+['ot_hbm_static_load_cp_provider_quad.sv']:paths.append('rtl/hbm_accel/loader/service_native/split/'+x)
 sources=[];pins={}
 for x in paths:
  data=show(source_ref,x);p=out/'source'/x;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);sources.append(p.relative_to(out));pins[x]=hashlib.sha256(data).hexdigest()
 sources.append(Path('tb_formats_provider.sv'));(out/'sources.f').write_text('\n'.join(map(str,sources))+'\n')
 (out/'formats.json').write_text(json.dumps(dict(formats=FMTS,commands=288,words=6*304,packets=np,phase_packet_ends=ends,source_ref=source_ref,nan_sign_case='all256 E4 codes compared against unchanged HGI-signpreserving reference',scope='actual converted masked words and native SRAM; no dynamic index/physical address adoption',cases=meta,reference_model='tools/hgi_sim/machine.py decode_fmt/e4m3_table',reference_sha256=hashlib.sha256(show(REF,'tools/hgi_sim/machine.py')).hexdigest(),source_sha256=pins),indent=1)+'\n')
 print('STAGED ALL6',np,'packets',6*304,'words')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--source-ref',default=REF);a=p.parse_args();main(a.out.resolve(),a.source_ref)
