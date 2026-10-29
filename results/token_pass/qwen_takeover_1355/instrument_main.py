#!/usr/bin/env python3
"""Instrument a PRIVATE copy of an existing Verilator main, without re-Verilating."""
import argparse
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('main', type=Path)
p.add_argument('header', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
if a.output.resolve() == a.main.resolve():
    p.error('write to a private output; never replace an inherited build main')
s = a.main.read_text()
h = a.header.read_text()
base = 'tb_kvslice__DOT__dut__DOT__sys_c__DOT__u_d2d_kv__DOT__u_core__DOT__u_end__DOT__u_link__DOT__u_ctl__DOT__'
fields = {'nf': base+'new_fault', 'ov': base+'cmd_ov', 'ev': base+'ev', 'rv': base+'rv', 'unread': base+'unread_slot', 'cycle':'tb_kvslice__DOT__cyc_core', 'abort':'tb_kvslice__DOT__dut__DOT__sys_c__DOT__u_d2d_kv__DOT__u_core__DOT__ab'}
for name in fields.values():
    if name+';' not in h:
        p.error('actual generated model lacks '+name)
if s.count('topp->eval();') != 1 or 'FIRSTLINKOBS' in s:
    p.error('require exactly one uninstrumented eval site')
s = s.replace('#include "Vtb_kvslice.h"', '#include "Vtb_kvslice.h"\n#include "Vtb_kvslice___024root.h"\n#include <cstdio>')
gets = '\n'.join(f'const unsigned {k} = topp->rootp->{v};' for k,v in fields.items())
observer = '''
        // Passive observation only; no simulation inputs/time/event changes.
        { static unsigned old_nf=0, old_abort=0, lines=0;
        GETS
        if (cycle >= 30000 && lines < 100 && ((nf && nf != old_nf) || abort != old_abort)) {
            std::printf("FIRSTLINKOBS cyc %u new_fault %02x abort %u observed %u ev %u rv %u unread %u\\n", cycle,nf,abort,ov,ev,rv,unread);
            std::fflush(stdout); ++lines;
        }
        old_nf=nf; old_abort=abort; }
'''.replace('GETS', gets)
s=s.replace('topp->eval();','topp->eval();'+observer)
a.output.write_text(s)
