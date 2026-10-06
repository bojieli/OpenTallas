#!/usr/bin/env python3
"""Read literal CDC port contracts; reject bare pulse ACK as protected binding.

Source-only preparation. Does not compile/run or qualify a physical source.
The existing protected adapter may be used for additive port integration; the
owner r8 endpoint still requires a genuine protected source/physical handoff.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def ports(source, module):
    text=source.read_text()
    at=text.index('module '+module)
    end=text.index('\n);',at)
    header=text[at:end]
    # Literal ANSI port names (each declaration may carry several names).
    names=set()
    for decl in re.findall(r'\b(?:input|output)\s+(.*?)(?=\binput\b|\boutput\b|$)',header,re.S):
        decl=re.sub(r'\[[^\]]*\]|//[^\n]*','',decl)
        words=re.findall(r'\b[A-Za-z_]\w*\b',decl)
        names.update(w for w in words if w not in {'wire','reg','integer','signed'})
    return names


def inspect(source,module):
    names=ports(source,module)
    required={'clk','hclk','por_n','warm_rst_n','l_v','l_sec','l_row','l_data','l_pop',
              'w_v','w_sec','w_data','w_tag','w_room','wd_v','wd_tag','wd_accept',
              'h_lv','h_lsec','h_lrow','h_ldata','h_cred','h_wv','h_wsec','h_hand',
              'h_wcon','h_cv','h_csec','h_cdata','h_ctag','h_av','h_atag','c_fault','h_fault'}
    missing=sorted(required-names)
    return dict(source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),module=module,
                verdict='PORT_CONTRACT_READY_PHYSICAL_BINDING_PENDING' if not missing else 'REJECT_PROTECTED_PORT_BINDING',
                missing_required_ports=missing,ports=sorted(names),physical_qualified=False,
                qualification='port match alone never proves selected mutable-state protection or SS60FF25/slew closure')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--module',required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=inspect(a.source,a.module)
    a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(r['verdict'])
    raise SystemExit(1 if r['missing_required_ports'] else 0)
