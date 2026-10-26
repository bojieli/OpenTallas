#!/usr/bin/env python3
"""Restore the production default lost when the native ASTK module is extracted."""
import argparse,re,importlib.util
from pathlib import Path
DEFAULT='`ifndef KVD_STMUT\n`define KVD_STMUT 0\n`endif\n'
def patch(text):
    if not re.search(r'\bmodule\s+qkd_astk_ctl_s_g0\b',text):
        raise ValueError('expected isolated native AM35 ASTK controller')
    if '`KVD_STMUT' not in text:raise ValueError('source has no static mutant use')
    if re.search(r'^\s*`define\s+KVD_STMUT\b',text,re.M):
        if DEFAULT not in text:raise ValueError('unexpected source-local mutant definition')
        return text
    return DEFAULT+text
def close(text, producer):
    text=patch(text)
    spec=importlib.util.spec_from_file_location('astk_timing_source',producer)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    for name in ('qkd_astk_rep4','qkd_astk_rep5'):
        if not re.search(r'\b'+name+r'\s+(?:#\s*\(|[A-Za-z_]\w*\s*\()',text):continue
        if re.search(r'\bmodule\s+'+name+r'\b',text):continue
        body=re.search(r'\(\* keep_hierarchy \*\) module '+name+r'\b.*?endmodule',mod.REP_MODS,re.S)
        if body is None:raise ValueError('replica definition missing in producer')
        text+='\n'+body.group(0)+'\n'
    return text

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('source',type=Path);ap.add_argument('output',type=Path);ap.add_argument('--replica-producer',type=Path);a=ap.parse_args();a.output.write_text(close(a.source.read_text(),a.replica_producer) if a.replica_producer else patch(a.source.read_text()))
