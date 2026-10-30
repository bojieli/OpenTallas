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
    # The recovered C45 wrapper predates the exported local-install predicate.
    # program_ready waits for a peer witness carried AFTER this boot epoch.
    # Import the rank-services output; never use that witness-dependent predicate.
    if 'wire program_installed_local;' not in text:
        anchor='generate if(MU==0)begin:g_plain'
        if text.count(anchor)!=1:
            raise ValueError('expected one native HOST generate')
        text=text.replace(anchor,'wire program_installed_local;\n'+anchor)
        anchor='end else begin:g_mu'
        if text.count(anchor)!=1:
            raise ValueError('expected one native HOST MU branch')
        text=text.replace(anchor,'assign program_installed_local=program_ready;\n'+anchor)
        begin=text.index('qkd_host_rank_services_admission_obsx #')
        end=text.index(');',begin)
        rank=text[begin:end]
        anchor='.program_ready(program_ready),'
        if rank.count(anchor)!=1:
            raise ValueError('expected one rank-services programme output')
        rank=rank.replace(anchor,anchor+'.program_installed_local(program_installed_local),')
        text=text[:begin]+rank+text[end:]
    old='.installed(static_setup_ready && program_ready'
    if text.count(old)>1:
        raise ValueError('ambiguous ordered boot install predicate')
    text=text.replace(old,'.installed(static_setup_ready && program_installed_local')
    if 'REQUIRE_MISSION_START' not in text:
        replacements=[
            ('parameter integer D2D_BOOT_ORDER=0)(',
             'parameter integer D2D_BOOT_ORDER=0, parameter integer REQUIRE_MISSION_START=0)('),
            (' input wire static_setup_ready,',
             ' input wire static_setup_ready,\n input wire mission_start,'),
            ('.installed(static_setup_ready && program_installed_local), .boot_begin(d2d_boot_begin)',
             '.installed(static_setup_ready && program_installed_local && (!REQUIRE_MISSION_START || mission_start)), .boot_begin(d2d_boot_begin)'),
        ]
        for old,new in replacements:
            if text.count(old)!=1:
                raise ValueError(f'expected one native HOST source anchor: {old}')
            text=text.replace(old,new)
    required=[
        'wire program_installed_local;',
        'assign program_installed_local=program_ready;',
        'parameter integer REQUIRE_MISSION_START=0',
        'input wire mission_start,',
        '.program_installed_local(program_installed_local),',
        '.installed(static_setup_ready && program_installed_local && (!REQUIRE_MISSION_START || mission_start)), .boot_begin(d2d_boot_begin)',
    ]
    if any(text.count(anchor)!=1 for anchor in required):
        raise ValueError('incomplete HOST local-install/mission START patch')
    return text

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source',type=Path)
    ap.add_argument('output',type=Path)
    a=ap.parse_args()
    a.output.write_text(patch(a.source.read_text()))
