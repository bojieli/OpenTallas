#!/usr/bin/env python3
"""Observable DUT-source fault controls; production RX RTL is never modified."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--mut',type=int,choices=[5,6],required=True);p.add_argument('--out',required=True);a=p.parse_args()
source=ROOT/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxh.sv';original=source.read_text()
old,new=("mx <= (x_q[31] && !x_nan) ? 32'd0 : x_q;","mx <= x_q;") if a.mut==5 else ("cj <= {8{oi_a[1:0]}};","cj <= 16'd0;")
assert original.count(old)==1,(a.mut,original.count(old))
s=original.replace(old,new);out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(s)
out.with_suffix('.json').write_text(json.dumps(dict(mut=a.mut,scope='actual copied DUT-source fault; production source unchanged',source=str(source.relative_to(ROOT)),original_sha256=hashlib.sha256(original.encode()).hexdigest(),mutated_sha256=hashlib.sha256(s.encode()).hexdigest(),old=old,new=new),indent=1)+'\n')
