#!/usr/bin/env python3
"""Additive owner-budget fix; fixed-width epoch reuse requires old-row drain."""
import argparse,difflib,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'results/rtl/dsrom_window_owner_tag_gate_20261003'
def once(text,old,new):
    if text.count(old)!=1:raise ValueError('pinned source equation changed: '+old)
    return text.replace(old,new)
def generate(out):
    if out.exists():raise ValueError('fresh candidate directory required')
    for p in json.loads((BASE/'input_pins.json').read_text()):
        if hashlib.sha256((BASE/p['archive']).read_bytes()).hexdigest()!=p['sha256']:raise ValueError('source pin mismatch')
    pf=(BASE/'inputs/ot_chip_v41x_window_kv_prefetch.sv').read_text()
    pf=once(pf,'module ot_chip_v41x_window_kv_prefetch #(','module ot_chip_v41x_window_kv_prefetch_owner_safe #(\n    parameter bit REFILL_OWNER_SAFE = 0,')
    pf=once(pf,'localparam integer EPOCH_W = TAGW > 5 ? TAGW-5 : 1;','''// Client tags enter an outer two-owner-bit mux. Never spend owner bits
    // on epoch identity. Modulo reuse is legal only after all17 old sectors
    // have completed uniquely; reset additionally requires endpoint drain.
    localparam integer EPOCH_W = REFILL_OWNER_SAFE ?
        (TAGW > 7 ? TAGW-7 : 1) : (TAGW > 5 ? TAGW-5 : 1);''')
    pf=once(pf,'REFILL_CREDITS < 1 || REFILL_CREDITS > 16)','(REFILL_OWNER_SAFE && REFILL_CREDITS > 1 && TAGW < 8) ||\n            REFILL_CREDITS < 1 || REFILL_CREDITS > 16)')
    window=(BASE/'inputs/caller_ot_chip_v41x_window_attn_source.sv').read_text()
    window=once(window,'module ot_chip_v41x_window_attn_source #(','module ot_chip_v41x_window_attn_source_owner_safe #(\n    parameter bit REFILL_OWNER_SAFE=0,')
    window=once(window,'ot_chip_v41x_window_kv_prefetch #(','ot_chip_v41x_window_kv_prefetch_owner_safe #(.REFILL_OWNER_SAFE(REFILL_OWNER_SAFE),')
    die=(BASE/'inputs/caller_ot_chip_v41x_die.sv').read_text()
    die=once(die,'module ot_chip_v41x_die #(','module ot_chip_v41x_die_owner_safe #(\n    parameter bit WINDOW_REFILL_OWNER_SAFE = 0,')
    die=once(die,'ot_chip_v41x_window_attn_source #(','ot_chip_v41x_window_attn_source_owner_safe #(.REFILL_OWNER_SAFE(WINDOW_REFILL_OWNER_SAFE),')
    wrap=(BASE/'inputs/caller_ot_v41_rt_die_l20.sv').read_text()
    wrap=once(wrap,'module ot_v41_rt_die_l20 #(','module ot_v41_rt_die_l20_owner_safe #(\n    parameter integer WINDOW_REFILL_CREDITS = 1,\n    parameter bit WINDOW_REFILL_OWNER_SAFE = 0,')
    wrap=once(wrap,'ot_chip_v41x_die #(','ot_chip_v41x_die_owner_safe #(.WINDOW_REFILL_CREDITS(WINDOW_REFILL_CREDITS), .WINDOW_REFILL_OWNER_SAFE(WINDOW_REFILL_OWNER_SAFE),')
    files={'ot_chip_v41x_window_kv_prefetch_owner_safe.sv':pf,'ot_chip_v41x_window_attn_source_owner_safe.sv':window,'ot_chip_v41x_die_owner_safe.sv':die,'ot_v41_rt_die_l20_owner_safe.sv':wrap}
    originals=['ot_chip_v41x_window_kv_prefetch.sv','caller_ot_chip_v41x_window_attn_source.sv','caller_ot_chip_v41x_die.sv','caller_ot_v41_rt_die_l20.sv']
    out.mkdir(parents=True);diff=[]
    for (name,text),old in zip(files.items(),originals):
        (out/name).write_text(text)
        diff.extend(difflib.unified_diff((BASE/'inputs'/old).read_text().splitlines(True),text.splitlines(True),fromfile='inputs/'+old,tofile=name))
    (out/'exact_source.diff').write_text(''.join(diff))
    (out/'source_manifest.json').write_text(json.dumps({x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(out.iterdir())},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out)
