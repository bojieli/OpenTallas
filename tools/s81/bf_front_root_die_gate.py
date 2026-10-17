#!/usr/bin/env python3
"""Check source-only die ABI integration, actual emitted netlist and strict bind.

This declared-boundary fixture is not a full die, physical proof or token test.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from s81 import bf_root_die_abi as ABI
import dsrom_s81_fulldie as G


def model():
    it=SimpleNamespace(name='e0',master='dsfd_bf_front_static',w=116.64,h=198.72,orient='R0',kind='bf')
    buses=[('clock','col_clock',1,[('TOP','clock'),('e0','ck'),('e0','io_clk')]),
           ('x2','top_in',536,[('TOP','x2'),('e0','xb[0:535]')]),
           ('xa','top_in',283,[('TOP','xa'),('e0','xb[536:801]@0')]),
           ('xb','top_in',266,[('TOP','xb'),('e0','xb[802:1067]@0')])]
    ports={'c0':('output',776),'c1':('output',776),'qy0':('input',1),'qy1':('input',1),
           'x0':('input',283),'x1':('input',266),'go':('input',1),'cfg':('input',54),
           'st':('output',2),'rs':('input',1),'f_prog':('input',38)}
    for port,(direction,width) in ports.items():
        eps=[('e0',port),('TOP',port)] if direction=='output' else [('TOP',port),('e0',port)]
        buses.append((port,'top_out' if direction=='output' else 'top_in',width,eps))
    return dict(insts=[it],buses=buses)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    m=model();ABI.rewrite_front(m)
    joins=m['bf_front_root_abi']['operand_joins']['e0']
    for i in range(44):assert joins[f'xb_meta[{i}]']==('x2',i)
    for i in range(1024):
        expected=('x2',i+44) if i<492 else ('xa',i-492) if i<758 else ('xb',i-758)
        assert joins[f'xb_data[{i}]']==expected, (i,joins[f'xb_data[{i}]'],expected)
    clock=m['buses'][0][3]
    assert set(p for n,p in clock if n=='e0')==set(ABI.FRONT_CLOCK_PORTS)
    negatives={}
    for name in ['missing','duplicate']:
        bad=model()
        if name=='missing':bad['buses'][3]=(bad['buses'][3][0],bad['buses'][3][1],266,[('TOP','xb'),('e0','xb[802:1066]@0')])
        else:bad['buses'].append(('dup','top_in',1,[('TOP','dup'),('e0','xb[0:0]')]))
        try:ABI.rewrite_front(bad)
        except AssertionError:negatives[name]='FAIL_EXPECTED'
        else:raise SystemExit(f'ERROR: {name} operand producer survived')
    # Exercise the production netlist writer. Unused CFG/real-view metadata is
    # irrelevant to this one-front fixture, whose actual ports are RTL-bound.
    G.GEN='r8';G.RTL_BIND=True
    G.real_ports=lambda:{}
    G.real_lef=lambda _:dict(name='unused_cfg',pins={})
    G.die_master_params=lambda _:{}
    path=a.out/'die.v';G.write_netlist(m,1,path,top='bf_root_abi_fixture')
    text=path.read_text().replace('module bf_root_abi_fixture (','module bf_root_abi_fixture (n_clock, ',1)
    text=text.replace('  wire [0:0] n_clock;','  input [0:0] n_clock;',1)
    assert '.xb_data(' in text and '.xb_meta(' in text and '.xb(' not in text
    assert 'n_gap_' not in text
    path.write_text(text)
    command=[sys.executable,str(ROOT/'tools/die_port_bind.py'),str(path),'--top','bf_root_abi_fixture','--out',str(a.out/'bind.json')]
    result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
    (a.out/'bind.log').write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit('ERROR: actual emitted BF fixture strict die_port_bind failed')
    # The same production pin population must cover all3272 candidate pins.
    widths={'c0':776,'c1':776,'qy0':1,'qy1':1,'x0':283,'x1':266,'go':1,'cfg':54,'st':2,
            'ck':1,'rs':1,'xb_data':1024,'xb_meta':44,'f_prog':38,'io_clk':1,'io_n':1,'io_w':1,'io_e':1}
    master=SimpleNamespace(w=116.64,h=198.72,order=[],ports={})
    ABI.populate_front(master,{k:('input',w) for k,w in widths.items()})
    assert sum(len(p[1]) for p in master.ports.values())==3272
    (a.out/'receipt.json').write_text(json.dumps(dict(scope='SOURCE_ONLY_BOUNDARY_FIXTURE_NOT_DIE_QUALIFICATION',
                         literal_operand_joins=1068,physical_request_pins=3272,total_clock_roots=5,
                         negative_missing_and_duplicate=negatives,source=ABI.source_receipt()),indent=2)+'\n')
    print('PASS BF emitted die ABI:1068 source joins,3272 request pins,5 roots,strict bind; missing/duplicate mutants FAIL')


if __name__=='__main__':main()
