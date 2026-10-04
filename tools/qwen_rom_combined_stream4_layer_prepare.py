#!/usr/bin/env python3
"""Reuse the exact cached P8191 input preparer with the STREAM4 source selection."""
import argparse
from pathlib import Path
import qwen_rom_combined_nearbaseline_layer_prepare as predecessor
import qwen_rom_combined_stream4_runtime_emit as runtime
import qwen_rom_combined_stream4_selection as selected


def prepare(*args,**kwargs):
    old_runtime,old_selection=predecessor.runtime,predecessor.selected
    try:
        predecessor.runtime=runtime;predecessor.selected=selected
        return predecessor.prepare(*args,**kwargs)
    finally:
        predecessor.runtime=old_runtime;predecessor.selected=old_selection


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('selection','oracle-root','history','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--oracle-sha256',required=True);p.add_argument('--layer',type=int,required=True)
    p.add_argument('--images',nargs=4,type=Path,required=True)
    command,_=prepare(**vars(p.parse_args()));print(__import__('json').dumps(dict(command=command,status='prepared')))
