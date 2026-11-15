"""Registration follows pure BUF/INV connectivity, not a bounded cell count."""
import re
from pathlib import Path
import geom_rules as G


def design(tmp_path, *, logic=False, clock=False, cycle=False, output_cycle=False, far=False):
    lines=['D\t0\t0\t600\t40',
           'C\t1\tS\tDFF\t9.5\t9.5\t10.5\t10.5\treg',
           'P\t0\ta\tINPUT\tSIGNAL\tM4\t0\t10',
           'P\t1\tz\tOUTPUT\tSIGNAL\tM4\t20\t10']
    if far: lines[1]='C\t1\tS\tDFF\t499.5\t9.5\t500.5\t10.5\treg'
    for base in (2,102):
        for i in range(base,base+24):
            kind='L' if logic and i==10 else 'B'
            lines.append(f'C\t{i}\t{kind}\tBUF\t9\t9\t10\t10\tb{i}')
    lines.append('N\tSIGNAL\tp0\ti2')
    for i in range(2,25):lines.append(f'N\tSIGNAL\ti{i}\ti{i+1}')
    lines.append('N\tSIGNAL\ti25\t'+('i2' if cycle else 'i1c' if clock else 'i1'))
    lines.append('N\tSIGNAL\t'+('i125' if output_cycle else 'i1')+'\ti102')
    for i in range(102,125):lines.append(f'N\tSIGNAL\ti{i}\ti{i+1}')
    lines.append('N\tSIGNAL\ti125\tp1')
    p=tmp_path/'dump.tsv';p.write_text('\n'.join(lines)+'\n')
    return G.Design(p)


def metrics(d):return G.pin_reg_metrics(d,re.compile(r'^strap_'))


def test_long_actual_buffer_chains_keep_first_register_and_distance_gate(tmp_path):
    m=metrics(design(tmp_path))
    assert m['pins_registered']==2 and m['pins_unregistered']==0
    assert m['pin_reg_p90']==10 and m['pin_reg_max']==10
    m=metrics(design(tmp_path,far=True))
    assert m['pins_registered']==2 and m['pin_reg_max']==500
    assert m['pin_reg_max']>G.PINREG_HARD  # Pure buffering never waives physical distance.


def test_logic_clock_and_pure_buffer_cycles_stay_unregistered(tmp_path):
    for kwargs in ({'logic':True},{'clock':True},{'cycle':True},{'output_cycle':True}):
        m=metrics(design(tmp_path,**kwargs))
        assert m['pins_registered']==1 and m['pins_unregistered']==1,kwargs
