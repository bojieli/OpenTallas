#!/usr/bin/env python3
"""Resolve actual generated successor members through the existing accessor."""
from pathlib import Path
import tempfile
import qwen_rom_combined_access as predecessor

TOP='ot_qwen_rom_combined_dspark_die'
BASE_TOP='ot_qwen_rom_combined_die'


def emit(die_header,tile_header,hbm_header,out,**parameters):
    actual=Path(die_header).read_text()
    if TOP+'__DOT__' not in actual:raise ValueError('actual combined DSpark generated root required')
    with tempfile.TemporaryDirectory() as t:
        header=Path(t)/'Vdie___024root.h';header.write_text(actual.replace(TOP,BASE_TOP))
        predecessor.emit(header,tile_header,hbm_header,out,**parameters)
    path=Path(out)/'combined_access.hpp';generated=path.read_text()
    if BASE_TOP+'__DOT__' not in generated:raise ValueError('actual successor members unresolved')
    path.write_text(generated.replace(BASE_TOP,TOP))
