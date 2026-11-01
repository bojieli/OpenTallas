"""Actual bit identity and coverage must survive nested parent receipt export."""
import copy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import io_hold_parent as I
import parent_core_hold as E
from test_io_hold import _plan
from test_io_hold_core_parent import core_sta


def rows(receiver='u_r0/u_bs0'):
    result=[]
    for bit in ('x_i[0]','x_i[1]'):
        result += [f'B\t{bit}\t{receiver}/{bit}\tsrc/q/Q\t{receiver}/f/D\t5.0\t100.0',
                   f'P\t{bit}\tsrc/q/Q\t{receiver}/f/D\t-2\t1\t3\t1\tclk\tclk\tsrc/q/CLK\t{receiver}/f/CLK\t0.0']
    return result


def test_exact_bits_min_arrival_and_clock_witnesses(tmp_path):
    p=tmp_path/'FF.tsv';p.write_text('\n'.join(rows()))
    r=E.parse_corner(p,{'x_i':['x_i[0]','x_i[1]']},'u_r0/u_bs0')
    assert r['exit']==0 and r['coverage']==dict(expected=2,timed=2,paired=2)
    assert r['bit_paths']['x_i[0]'][0]['capture_data_arrival_ps']==100
    pair=r['bit_pairs']['x_i[0]'][0]
    assert (pair['setup_ps'],pair['hold_ps'])==(-2,3)
    assert pair['capture_clock_pin']=='u_r0/u_bs0/f/CLK'


def test_missing_bit_wrong_receiver_and_missing_pair_cannot_qualify(tmp_path):
    good=rows()
    mutations=[good[:2], rows('u_r0/u_bs00'), [x for x in good if not x.startswith('P\t')],
               [x.replace('\t0.0','\t9.0') if x.startswith('P\t') else x for x in good]]
    for i,lines in enumerate(mutations):
        p=tmp_path/str(i);p.write_text('\n'.join(lines))
        r=E.parse_corner(p,{'x_i':['x_i[0]','x_i[1]']},'u_r0/u_bs0')
        assert r['exit']!=0 and r['errors']


def test_consumer_roundtrips_nested_receiver_without_changing_policy():
    sta=copy.deepcopy(core_sta());receiver='u_r0/u_bs0'
    sta['instances'][receiver]=sta['instances'].pop('pfb')
    for corner in sta['corners'].values():
        for name in ('seams','pairskew'):
            corner[name]={k.replace('->pfb/','->'+receiver+'/'):v for k,v in corner[name].items()}
    r=I.check(_plan(),sta,core_receiver=receiver,core_type='cfg7',core_ports=['x_i','z_i'])
    assert r['verdict']=='PASS'
    assert {q['dst'] for q in r['ports']}=={receiver}
    assert I.check(_plan(),sta,core_receiver=receiver+'0',core_type='cfg7',core_ports=['x_i','z_i'])['verdict']!='PASS'
