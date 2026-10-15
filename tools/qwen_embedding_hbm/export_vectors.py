#!/usr/bin/env python3
"""Export real released boundary rows for the selected HBM bootstrap/decoder RTL tests."""
import argparse,json,struct,subprocess,sys
from pathlib import Path
EDGE=[0,1,15,16,17,511,512,513,1023,1024,1025,2047,2048,8191,8192,65535,65536,131071,131072,151551,151552,151919,151920,151934,151935]
def main():
 p=argparse.ArgumentParser();p.add_argument('image',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False)
 subprocess.run([sys.executable,str(Path(__file__).with_name('emit_boot.py')),str(a.image),str(a.out/'boot.hex'),'--tokens',*map(str,EDGE)],check=True)
 subprocess.run([sys.executable,str(Path(__file__).with_name('emit_boot.py')),str(a.image),str(a.out/'host_hb283.hex'),'--format','hb283','--tokens',*map(str,EDGE)],check=True)
 meta=json.loads((a.out/'boot.hex.json').read_text())
 with (a.image/'embedding_codes.bin').open('rb') as c,(a.image/'embedding_scales_bf16.bin').open('rb') as s,(a.out/'gcode.hex').open('x') as gc,(a.out/'gfp.hex').open('x') as gf:
  for t in EDGE:
   c.seek(t*4096);raw=c.read(4096);s.seek(t*2);sb=int.from_bytes(s.read(2),'little')
   for i in range(64):gc.write(f'{int.from_bytes(raw[64*i:64*i+64],"little"):0128x}\n')
   gc.write(f'{sb:0128x}\n');scale=struct.unpack('<f',struct.pack('<I',sb<<16))[0]
   for code in struct.unpack('4096b',raw):
    fp=struct.unpack('<I',struct.pack('<f',code*scale))[0] if code else 0
    gf.write(f'{fp:08x}\n')
 (a.out/'tokens.hex').write_text(''.join(f'{t:05x}\n' for t in EDGE))
 (a.out/'meta.hex').write_text(''.join(f'{x:08x}\n' for x in [meta['sectors'],meta['checksum'],len(EDGE),meta['sectors'],5,len(EDGE)-1]+[0]*10))
 print('PASS actual released HBM boundary vectors',len(EDGE),'tokens',meta['sectors'],'sectors')
if __name__=='__main__':main()
