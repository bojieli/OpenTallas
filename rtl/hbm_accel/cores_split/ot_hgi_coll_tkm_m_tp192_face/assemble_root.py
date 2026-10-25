#!/usr/bin/env python3
"""PATH-HBM/TOK 2026-10-25: face-path root core = re-extracted remainder module (rest_extract.sh of
ot_hgi_coll_tkm_m_tp192_pf) + the canonical root core's wrapper module VERBATIM (same rest_wrap.py output: named port
connections, 64 unread del_flit bits tied 0).  Fails unless the new remainder has exactly the canonical port set."""
import re, sys
ext, canon, out = sys.argv[1:4]
E = open(ext).read(); C = open(canon).read()
def body(txt, name):
    m = re.search(r'(?ms)^module\s+\\?' + re.escape(name) + r'\b.*?^endmodule\s*$', txt)
    assert m, name
    return m.group(0)
def ports(mod):
    return sorted((d, w or '', n.lstrip('\\')) for d, w, n in
                  re.findall(r'(?m)^  (input|output)\s+(?:\[(\d+:\d+)\]\s*)?(\S+)\s*;', mod))
xn = body(E, 'ot_hgi_coll_tkm_tp192_root_core_x'); xo = body(C, 'ot_hgi_coll_tkm_tp192_root_core_x')
pn, po = ports(xn), ports(xo)
if pn != po:
    sys.exit(f'PORT MISMATCH new {len(pn)} old {len(po)}: +{sorted(set(pn)-set(po))[:8]} -{sorted(set(po)-set(pn))[:8]}')
wrap = body(C, 'ot_hgi_coll_tkm_tp192_root_core')
hdr = ('// GENERATED (PATH-HBM/TOK 2026-10-25) by rest_extract.sh from ot_hgi_coll_tkm_m_tp192_pf (twin '
       'ot_hgi_coll_tkm_static_p PIPE 1 HOP 2 FRT 4 CB 14) minus the 32 tiles + the canonical rest_wrap.py wrapper '
       '(assemble_root.py). Do not edit.\n`timescale 1ns/1ps\n')
open(out, 'w').write(hdr + xn + '\n\n' + wrap + '\n')
print(f'ROOT_ASSEMBLED ports {len(pn)} identical; bits_in/out unchanged')
