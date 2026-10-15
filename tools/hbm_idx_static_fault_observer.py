#!/usr/bin/env python3
"""Observe preserved generated model; no RTL change or arithmetic replacement."""
from pathlib import Path
import sys
root=Path(sys.argv[1]);s=(root/'Vtb_idx_parent_static__main.cpp').read_text()
s=s.replace('#include "Vtb_idx_parent_static.h"','#include "Vtb_idx_parent_static.h"\n#include "Vtb_idx_parent_static___024root.h"\n#include "Vtb_idx_parent_static_ot_hbm_idx_score_static.h"')
s=s.replace('    // Simulate until $finish','    unsigned prev=0;\n    // Simulate until $finish')
s=s.replace('        topp->eval();','''        topp->eval();
        auto*r=topp->rootp;
        unsigned bits=r->tb_idx_parent_static__DOT__dut__DOT__lf |
          (r->tb_idx_parent_static__DOT__dut__DOT__sf<<1)|
          (r->tb_idx_parent_static__DOT__dut__DOT__calendar_fault<<2)|
          (r->tb_idx_parent_static__DOT__dut__DOT__operands__DOT__face_fault<<3)|
          (r->__PVT__tb_idx_parent_static__DOT__dut__DOT__gscore__BRA__0__KET____DOT__scorer->fault<<4)|
          (r->__PVT__tb_idx_parent_static__DOT__dut__DOT__gscore__BRA__1__KET____DOT__scorer->fault<<5)|
          (r->__PVT__tb_idx_parent_static__DOT__dut__DOT__gscore__BRA__2__KET____DOT__scorer->fault<<6)|
          (r->__PVT__tb_idx_parent_static__DOT__dut__DOT__gscore__BRA__3__KET____DOT__scorer->fault<<7);
        if(bits!=prev){ VL_PRINTF("FAULT_OBS time=%llu bits=%u selectorq=%u op=%u addr=%u\\n",(unsigned long long)contextp->time(),bits,
          r->tb_idx_parent_static__DOT__dut__DOT__selector__DOT__qfault,r->tb_idx_parent_static__DOT__sel_op,r->tb_idx_parent_static__DOT__sel_addr);prev=bits; }
''')
(root/'idx_fault_observer.cpp').write_text(s)
