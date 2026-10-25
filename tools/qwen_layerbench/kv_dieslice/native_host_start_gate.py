#!/usr/bin/env python3
"""Add an off-default mission START input to the recovered native C45 HOST.

Bootstrap reset, image admission/replay and HBM boot_go are unchanged. Only
D2D mission admission waits for both installed images and the delivered START.
Use on an owned source copy; the binder must wire mission_start from its local
registered START tap and select REQUIRE_MISSION_START=1 for the native vehicle.
"""
import argparse
from pathlib import Path

def patch(text):
    if 'REQUIRE_MISSION_START' in text:
        if text.count('input wire mission_start,') != 1:
            raise ValueError('incomplete HOST mission START patch')
        return text
    replacements=[
        ('parameter integer D2D_BOOT_ORDER=0)(',
         'parameter integer D2D_BOOT_ORDER=0, parameter integer REQUIRE_MISSION_START=0)('),
        (' input wire static_setup_ready,',
         ' input wire static_setup_ready,\n input wire mission_start,'),
        ('.installed(static_setup_ready && program_ready), .boot_begin(d2d_boot_begin)',
         '.installed(static_setup_ready && program_ready && (!REQUIRE_MISSION_START || mission_start)), .boot_begin(d2d_boot_begin)'),
    ]
    for old,new in replacements:
        if text.count(old)!=1:
            raise ValueError(f'expected one native HOST source anchor: {old}')
        text=text.replace(old,new)
    return text

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source',type=Path)
    ap.add_argument('output',type=Path)
    a=ap.parse_args()
    a.output.write_text(patch(a.source.read_text()))
