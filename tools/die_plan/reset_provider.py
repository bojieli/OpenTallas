#!/usr/bin/env python3
"""Build the explicit S81 four-ROM preservation contract from exact native Libs.

Generates a contract only; never edits a kit, reset tree, netlist or plan.
The owner must review it and validate it in the actual pre-CTS OpenDB session.
"""
import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path
import signoff as S


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,why):
    if not ok:raise ValueError(why)
def tq(value):
    value=str(value);need(not any(c in value for c in '{}\\\n'),'unsafe Tcl contract value')
    return '{'+value+'}'
def text(p):
    p=Path(p);return gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text()


def models(invlib, invsha, seqlib, seqsha):
    need(sha(invlib)==invsha and sha(seqlib)==seqsha,'native provider Liberty identity mismatch')
    buffers={}
    for master,body in S._lib_groups(text(invlib),'cell'):
        pins=dict(S._lib_groups(body,'pin'))
        if set(pins)!={'A','Y'}:continue
        f=re.search(r'\bfunction\s*:\s*"([^"\n]+)"',pins['Y'])
        if not f:continue
        f=re.sub(r'\s','',f[1])
        if f not in ('A','!A',"A'"):continue
        need(re.search(r'\bdirection\s*:\s*input\s*;',pins['A']) and
             re.search(r'\bdirection\s*:\s*output\s*;',pins['Y']),'buffer pin directions changed')
        buffers[master]=dict(input='A',output='Y',inverted=int(f!='A'))
    name='DFFHQNx1_ASAP7_75t_R'
    cells=[body for n,body in S._lib_groups(text(seqlib),'cell') if n==name]
    need(len(cells)==1,'native provider FF missing/ambiguous')
    ff=list(S._lib_groups(cells[0],'ff'));pins=dict(S._lib_groups(cells[0],'pin'))
    need(len(ff)==1 and ff[0][0].replace(' ','')=='IQN,IQNN','provider state identity changed')
    need(re.search(r'clocked_on\s*:\s*"CLK"',ff[0][1]) and
         re.search(r'next_state\s*:\s*"!D"',ff[0][1]) and
         not re.search(r'\b(clear|preset)\s*:',ff[0][1]),'provider FF clock/data/reset function changed')
    need(re.search(r'function\s*:\s*"IQN"',pins['QN']),'provider FF output polarity changed')
    return buffers,dict(master=name,output='QN',data='D',clock='CLK',inverted=1)


def generate(invlib,invsha,seqlib,seqsha):
    buffers,flop=models(invlib,invsha,seqlib,seqsha)
    # Yosys shares the first two equal D2/D15 states. Count the actual complete
    # lineage, not only the 13 instances whose name happens to contain D15.
    stages=['u_bound.u_d2_u_r0_u_cf_rs.r[0]$_DFF_P_', 'u_bound.u_d2_u_r0_u_cf_rs.q$_DFF_P_']
    stages += [f'u_bound.u_d15_u_r0_u_cf_rs.r[{n}]$_DFF_P_' for n in range(2,14)]
    stages += ['u_bound.u_d15_u_r0_u_cf_rs.q$_DFF_P_']
    c=dict(provider='u_bound.u_u_r0_u_cf',provider_master='dsfd_cfifo_crs4',provider_pin='rs',
           provider_clock='cr',source_clock_net='clk',sink_master='ot_v41_rom_elem_q_qxpq_w10_gb',
           sink_pin='rst_n',sink_clock='clk',tap_key='rst_n_t27')
    lines=['# Generated from exact hashed native Lib contracts; four explicit S81 ROMs only.',
           f'# INVBUF sha256 {invsha}',f'# SEQ sha256 {seqsha}',
           'proc ot_s81_cf_rom_provider_contract {tap_net tap_parity} {','  set c [dict create]']
    for key,value in c.items():lines.append(f'  dict set c {key} {tq(value)}')
    for path,digest in ((invlib,invsha),(seqlib,seqsha)):
        runtime='/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/'+Path(path).name
        lines.append('  dict set c libraries '+tq(runtime)+' '+tq(digest))
    lines += ['  dict set c tap_net $tap_net','  dict set c tap_parity $tap_parity',
              '  dict set c stages [list '+' '.join(tq(s) for s in stages)+']',
              '  dict set c sinks [list '+' '.join(tq('u_bound.u_u_r0_u_e'+str(n)) for n in (0,2,3,4))+']']
    for master,m in sorted(buffers.items()):
        lines.append('  dict set c buffers '+tq(master)+' [dict create '+' '.join(k+' '+tq(v) for k,v in m.items())+']')
    lines += ['  dict set c flop [dict create '+' '.join(k+' '+tq(v) for k,v in flop.items())+']',
              '  return $c','}']
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('invlib','invsha','seqlib','seqsha','out'):p.add_argument('--'+k,required=True)
    a=p.parse_args();Path(a.out).write_text(generate(a.invlib,a.invsha,a.seqlib,a.seqsha))
if __name__=='__main__':main()
