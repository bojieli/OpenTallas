#!/usr/bin/env python3
"""Unpack the exact PDK-couponed native candidate models for functional benches."""
import argparse,gzip,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'results/rtl/fp32_add_native_clone_1020/final_packet/cells.v.gz'
SHA='3606964bc33b09214c19c32b6d6bbab6cbf09f26d28d3aa9f9aec1571f657048'
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 data=gzip.decompress(MODEL.read_bytes())
 if hashlib.sha256(data).hexdigest()!=SHA:raise SystemExit('REFUSED: native model identity differs from canonical PDK coupon')
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(data)
 print('FAN32_MODELS_PASS sha256='+SHA+' out='+str(a.out))
if __name__=='__main__':main()
