#!/usr/bin/env python3
"""Select the compiler's internal IDX transmitter latency from its actual source.

This is separate from tl/ca/cb plan transport. Use the environment only for
compiling the source cohort named in this record; no global default changes.
"""
from pathlib import Path
import argparse,hashlib,json,re

def profile(path):
    data=Path(path).read_bytes();s=data.decode()
    s=re.sub(r'/\*.*?\*/|//[^\n]*',' ',s,flags=re.S)
    body=s.split('module dsdv_bk_sel_vmtx',1)
    if len(body)!=2:raise ValueError('selected source must declare dsdv_bk_sel_vmtx')
    rows=re.findall(r'\bdsdv_idx_tx_n32\s*#\s*\((.*?)\)\s*u_tx\s*\(',body[1].split('endmodule',1)[0],re.S)
    if len(rows)!=1:raise ValueError('need exactly one actual dsdv_idx_tx_n32 u_tx')
    params=dict(re.findall(r'\.(\w+)\s*\(\s*([^()]+)\s*\)',rows[0]))
    raw=params.get('FACE','0').strip()
    if not re.fullmatch(r'[012]',raw):raise ValueError('FACE must be an explicit supported literal0/1/2')
    face=int(raw);delta=(0,1,3)[face]
    return dict(schema='opentallas.s81.idx_tx_source_profile.v1',source=str(Path(path).resolve()),
        source_sha256=hashlib.sha256(data).hexdigest(),instance='dsdv_bk_sel_vmtx.u_tx',FACE=face,
        internal_output_edges=delta,environment={'OT_BK_TX_FACE':str(face)},
        affected_outputs=['tl_o','tx_st'],transport_included=False,
        transport_lanes=['tl__bk_sel__s_0N_LP'],
        rule='first_slot = CTL_vi_n + (5 + FWD-2 + OFACE + internal_output_edges) + DLY; require DLY>=1; reserve later slot when budget is exhausted',
        scope='Source-selected compiler profile; no new physical, exactness or whole-token qualification')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--out',type=Path)
    a=p.parse_args();r=profile(a.source);t=json.dumps(r,indent=2)+'\n'
    if a.out:a.out.write_text(t)
    print(t,end='')
if __name__=='__main__':main()
