#!/usr/bin/env python3
"""Bind combined runtime preloads/observations to actual generated members."""
import argparse
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
PUBLIC_CONFIG='''`verilator_config
public_flat_rw -module "ot_rom_4096x266_m8" -var "arr"
public_flat_rw -module "ot_sram_1r1w_128x256_m1_r2c2" -var "arr"
public_flat_rw -module "ot_qwen_hbm_model_ack" -var "mem"
public_flat_rd -module "ot_qwen_rom_combined_die" -var "kv_arm"
public_flat_rd -module "ot_qwen_nearhbm_realmem_service" -var "row_drained"
'''


def emit(die_header,tile_header,hbm_header,out,*,nport,scale_banks,code_banks,crom_words,hbm_layers,embed_rom):
    out=Path(out)
    for name in ('combined_access.hpp','hbm_access.hpp'):
        if (out/name).exists():raise ValueError('refuse existing generated accessor: '+name)
    spec=importlib.util.spec_from_file_location('_original_qwen_rm_access',ROOT/'tools/qwen_rom_rt_rm_access.py')
    access=importlib.util.module_from_spec(spec);spec.loader.exec_module(access)
    old='ot_qwen_rom_rt_die_w12_rm';new='ot_qwen_rom_combined_die'
    with tempfile.TemporaryDirectory() as temp:
        t=Path(temp)
        # Normalize only the top's identifier for the immutable accessor
        # generator, then restore every real member name in the result.
        (t/'die.h').write_text(Path(die_header).read_text().replace(new,old))
        subprocess.run([sys.executable,ROOT/'tools/qwen_rom_rt_rm_access.py',
                        '--die-header',t/'die.h','--tile-header',tile_header,
                        '--nport',str(nport),'--scale-banks',str(scale_banks),'--code-banks',str(code_banks),
                        '--crom-words',str(crom_words),'--hbm-layers',str(hbm_layers),
                        '--kv-ideal','1','--embed-rom',str(embed_rom),'--out',t/'base.hpp'],check=True)
        text=(t/'base.hpp').read_text().replace(old,new)
    hn=access.find(access.members(Path(hbm_header)),r'.*__DOT__mem','actual HBM backing array')
    if len(hn)!=1:raise ValueError('ambiguous actual HBM backing array')
    hbm='#pragma once\nstatic inline auto& combined_hbm_array(Vhbm___024root* r) {return r->'+hn[0]+';}\n'
    out.mkdir(parents=True,exist_ok=True)
    with (out/'combined_access.hpp').open('x') as f:f.write(text)
    with (out/'hbm_access.hpp').open('x') as f:f.write(hbm)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('die-header','tile-header','hbm-header','out'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('nport','scale-banks','code-banks','crom-words','hbm-layers','embed-rom'):
        p.add_argument('--'+name,type=int,required=True)
    a=p.parse_args();emit(**vars(a))


if __name__=='__main__':main()
