from pathlib import Path
import numpy as np,sys,json,hashlib,shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.s81_head.hd_reskew_images import encode,decode
out=Path("images");out.mkdir(exist_ok=True);mut=Path("images_bad_skew");mut.mkdir(exist_ok=True)
logical=np.zeros((8192,16),dtype=np.uint32)
for g in range(8192):
 for j in range(16):logical[g,j]=(0x3b80|((g*17+j*19)%128))|(0x8000 if (g//64+j)%3==0 else 0)
p=np.arange(8192);record={}
for name,sk in [("gold",11),("new",4)]:
 phys=np.zeros_like(logical)
 for j in range(16):phys[:,j]=logical[(p-sk*(j%8))%8192,j]
 for bank in (0,1):encode(phys[bank::2],out/f"{name}_{bank}.viamap.hex")
 decoded=np.zeros_like(logical)
 decoded[0::2]=decode(out/f"{name}_0.viamap.hex");decoded[1::2]=decode(out/f"{name}_1.viamap.hex")
 inv=np.zeros_like(logical)
 for j in range(16):inv[(p-sk*(j%8))%8192,j]=decoded[:,j]
 assert np.array_equal(logical,inv)
 record[name]=dict(sk=sk,logical_sha256=hashlib.sha256(inv.tobytes()).hexdigest())
for bank in (0,1):
 for name in ("gold","new"):shutil.copy2(out/f"gold_{bank}.viamap.hex",mut/f"{name}_{bank}.viamap.hex")
Path("image_record.json").write_text(json.dumps(record,indent=2)+"\n")
