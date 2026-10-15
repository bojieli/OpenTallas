#!/usr/bin/env python3
"""Emit the complete selected static controller from its canonical ABI template.

Historical physical-slot sources omit the real XPF monitor and cannot generate
this master. The selected TP8 graph has exactly three result serializers; every
fault input and engine-enable output names one of those real endpoints.
"""
from pathlib import Path
import argparse,hashlib,re
ROOT=Path(__file__).resolve().parents[2]
TEMPLATE=ROOT/'rtl/qwen_sys/static_schedule_20261014/qfd_tt_ctlm_static_s.sv.in'
OUTPUT=TEMPLATE.with_suffix('')
SERIALIZERS=3

def render():
    text=TEMPLATE.read_text()
    values=dict(SERIALIZER_ENABLE_PORTS=','.join(f'mer{k}'for k in range(SERIALIZERS)),
        SERIALIZER_FAULT_PORTS=','.join(f'rf{k}'for k in range(SERIALIZERS)),
        SERIALIZER_ENABLE_ASSIGNMENTS=''.join(f'assign mer{k}=w_me_clk_en;'for k in range(SERIALIZERS)),
        SERIALIZER_FAULT_OR='|'.join(f'rf{k}'for k in range(SERIALIZERS)))
    for key,value in values.items():
        marker='@'+key+'@'
        if text.count(marker)!=1:raise ValueError('canonical ABI template missing/duplicate '+key)
        text=text.replace(marker,value)
    if re.search(r'@[A-Z_]+@|\b(?:mer|rf)[345]\b',text):raise ValueError('unresolved or nonexistent selected controller endpoint')
    for key in ('cp_active','native_ret','su_observe','su_image_ready','ck_head','ck_tree','ck_xpf','ck_me_sched'):
        if not re.search(r'\b'+key+r'\b',text):raise ValueError('canonical controller dropped actual '+key)
    return text

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--output',type=Path,default=OUTPUT);a=p.parse_args()
    text=render()
    if a.check:
        if not a.output.is_file()or a.output.read_text()!=text:raise SystemExit('FAIL selected controller differs from canonical template')
    else:a.output.write_text(text)
    print('PASS selected NB3 static controller ABI '+hashlib.sha256(text.encode()).hexdigest())
if __name__=='__main__':main()
