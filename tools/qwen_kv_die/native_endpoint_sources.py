#!/usr/bin/env python3
"""Explicit actual-source closure for the native endpoint (no blackbox/reference files)."""
import argparse
import hashlib
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def sources():
    build=(ROOT/'tools/qwen_attention_native/build.sh').read_text()
    paths=re.search(r'SRC="(.*?)"',build,re.S).group(1).split()
    paths=[p for p in paths if not p.startswith('rtl/test/') and not p.endswith('ot_qwen_tp8_attention_native_service.sv')]
    paths += ['rtl/qwen_sys/split_20261014/'+p+'.sv' for p in (
      'qkd_native_attention_endpoint','qkd_native_attention_programme','qkd_native_attention_static_ctl',
      'qkd_native59_descriptor_producer','qkd_native59_command_guard','qkd_native_attention_record',
      'qkd_native_attention_service_g3s2_gen','qkd_astk_native_stack_w4_gen','qkd_astk_native_er_service_w',
      'qkh_head_gather_stage','qkh_head_stages')]
    paths += ['rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv','rtl/hdc/nearhbm/ot_qwen_tp8_pv16_slice_gen.sv',
      'physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v']
    paths=list(dict.fromkeys(paths))
    for p in paths:
        if not (ROOT/p).is_file():raise FileNotFoundError(p)
    return paths

def main():
    p=argparse.ArgumentParser();p.add_argument('--json',action='store_true');a=p.parse_args();s=sources()
    if a.json:
        print(json.dumps(dict(top='qkd_native_attention_endpoint', sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in s},
                             native_full_layer=False,native_full_token=False),indent=2))
    else:print('\n'.join(s))
if __name__=='__main__':main()
