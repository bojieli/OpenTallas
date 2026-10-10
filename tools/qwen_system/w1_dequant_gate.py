from pathlib import Path
import struct,subprocess,json,hashlib
out=Path('vectors.txt')
with out.open('w') as f:
 for scale in range(65536):
  x=struct.unpack('<f',struct.pack('<I',scale<<16))[0]
  for quarter in range(4):
   codes=0;expected=0;bad=0
   for lane in range(64):
    byte=quarter*64+lane;codes|=byte<<(8*lane);integer=byte if byte<128 else byte-256
    if scale&0x7f80==0x7f80:bits=0;bad=1
    else:
     try:bits=struct.unpack('<I',struct.pack('<f',integer*x))[0]
     except OverflowError:bits=((integer<0)^(scale>>15))<<31|0x7f800000;bad=1
     if bits&0x7fffffff==0:bits=0
    expected|=bits<<(lane*32)
   f.write(f'{codes:0128x} {scale:04x} {expected:0512x} {bad}\n')
Path('golden_receipt.json').write_text(json.dumps({'method':'independent Python IEEE binary32 struct round of exact integer*BF16 expanded binary32; binary64 multiplication exact <=15significantbits','vectors':262144,'products':16777216,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()},indent=2))
src=['rtl/qwen_sys/dspark_native_20261009/ot_qwen_dspark_w1_dequant.sv','rtl/test/qwen_system/tb_qwen_dspark_w1_dequant.sv']
for mut in [0,1]:
 with open(f'compile_{mut}.log','w') as f:r=subprocess.run(['iverilog','-g2012','-s','tb_qwen_dspark_w1_dequant','-P',f'tb_qwen_dspark_w1_dequant.MUT={mut}','-o',f'deq{mut}',*src],stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:Path(f'status_{mut}').write_text(f'compile_rc={r.returncode}\n');break
 with open(f'run_{mut}.log','w') as f:r=subprocess.run(['vvp',f'deq{mut}','+VECTORS=vectors.txt'],stdout=f,stderr=subprocess.STDOUT)
 Path(f'status_{mut}').write_text(f'run_rc={r.returncode}\n')
