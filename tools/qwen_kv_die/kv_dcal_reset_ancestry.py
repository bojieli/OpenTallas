#!/usr/bin/env python3
"""Record exact source reset ownership; never infer native reset delivery."""
import argparse,hashlib,json,re
from pathlib import Path

def audit(path):
    raw=path.read_bytes();text=raw.decode();rows={}
    for line in text.splitlines():
        m=re.fullmatch(r'\s*(\w+)\s+(\w+)\s*\((.*)\);\s*',line)
        if m:
            master,name,body=m.groups();ports=dict(re.findall(r'\.(\w+)\(([^()]*)\)',body));rows[name]=(master,ports,line.strip())
    chain=['rrs_n_rst_link_t0__m_0__s0','rly_rst_link_t0_0','rly_pinfix_rst_link_t0_1__s0','rly_pinfix_rst_link_t0_0__s0']
    current='n_rrs_n_rst_link_t0__m_0__s0';proof=[]
    norm=lambda s:re.sub(r'\[0\]$','',s)
    for name in chain:
        master,ports,line=rows[name]
        if norm(ports['b'])!=current or ports['ck']!='n_clk_core_c':raise ValueError('reset ownership changed '+name)
        current=norm(ports['a']);proof.append(dict(instance=name,master=master,ports=ports,exact_line=line))
    if current!='n_rst_link_t0':raise ValueError('unexpected host reset root')
    hm,hp,hl=rows['host'];dm,dp,dl=rows['dcal']
    if hp['link_rst_n']!=current or dp['rst_n']!='n_rrs_n_rst_link_t0__m_0__s0[0]':raise ValueError('endpoint changed')
    return dict(schema='opentallas.kv_dcal_reset_ancestry.v1',qualified_release=False,raw_die_sha256=hashlib.sha256(raw).hexdigest(),
                producer=dict(instance='host',master=hm,port='link_rst_n',net=current),downstream_to_upstream=proof,
                dcal=dict(master=dm,ports=dp,exact_line=dl,clock='n_clk_core_c',internal_release='release_q[1]',internal_release_edges=2),
                nominal_plain_relay_edges=3,regional_reset_stage='rly_rst_link_t0_0',
                regional_parameters='Native bound source/strap and loaded clock proof required; do not treat region as a plain relay',
                clear_contract='Local rst_n assertion clears release_q, whose falling rl asynchronously clears fault and all cause FF; release requires two ck edges',
                unqualified=['host POR/clock-domain release','loaded native clock/reset skew and pulse arrival','regional dly/IGNORE/HOLD bound','all357source clearing and full transport flush','AHUB hf upstream clear and 34/37 drain','fixed admission and STATUS counter widths'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('die',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=audit(a.die);a.out.write_text(json.dumps(result,indent=2)+'\n');print('DCAL_RESET_ANCESTRY_EXACT_NATIVE_UNQUALIFIED')
