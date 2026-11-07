#!/usr/bin/env python3
"""Add per-form word-age probes to a head_fault_1107 packet of the nst4 rings.

Reads the literal probe_nst4__* rings that prepare.py wrote into tb.sv, and for
each ring adds a sender word counter plus twin rings on the same clocks, START
and reader origin:
  main   the literal ring and K of the selected top (FREG form);
  oldK   the same FREG ring with K-2, what a top without the event would tie;
  old    the pre-event ring (no WREG/DSREP/FREG) with K-2, the l48uh form;
  kp1    the FREG ring with K+1, a one-count control.
age = sender counter - word seen at the reader, on each reader rising edge
while ready and not faulted, so age(main)-age(old) is the data cycles the event
adds. This is local to the four rings: no codecs, no whole-die token.
"""
import argparse
import re
from pathlib import Path

RING = re.compile(r"^ot_dp_clk_landing_cas( #\(.*?\)) probe_(nst4__\w+)\(\.fclk\((\w+)\),\.t_rst_n\((\w+)\),"
                  r"\.clk\((\w+)\),\.rst_n\(([\w.]+)\),\.strap_k\((.*?)\+\(\$test\$plusargs.*?\.d\((\d+)'d0\),", re.M)
FORMS = {'main': (None, 0), 'oldK': (None, -2), 'old': ('old', -2), 'kp1': (None, 1)}


def old_params(params):
    out = re.sub(r",\s*\.(WREG|DSREP|FREG)\(\d+\)", "", params)
    if out == params:
        raise ValueError('ring is not the event form: ' + params)
    return out


def twin(params, label, fclk, start, clk, rst, k, w):
    lines = [f"reg [31:0] w_{label}=0;always@(posedge {fclk})if(!{start})w_{label}<=0;else w_{label}<=w_{label}+1;"]
    for form, (kind, dk) in FORMS.items():
        p = old_params(params) if kind == 'old' else params
        n = f'{form}_{label}'
        lines += [f"wire [{w-1}:0] q_{n};wire ready_{n},fault_{n};",
                  f"ot_dp_clk_landing_cas{p} ring_{n}(.fclk({fclk}),.t_rst_n({start}),.clk({clk}),.rst_n({rst}),"
                  f".strap_k({k}+6'd{dk & 63}),.d({{{w-32}'d0,w_{label}}}),.q(q_{n}),.ready(ready_{n}),.fault(fault_{n}));",
                  f"integer n_{n}=0,lo_{n}=1000000,hi_{n}=-1000000,a_{n};",
                  f"always@(posedge {clk})begin #0.001;if(ready_{n}&&!fault_{n})begin a_{n}=$signed(w_{label}-q_{n}[31:0]);"
                  f"n_{n}++;if(a_{n}<lo_{n})lo_{n}=a_{n};if(a_{n}>hi_{n})hi_{n}=a_{n};end end"]
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('packet', type=Path)
    a = ap.parse_args()
    tb = a.packet / 'tb.sv'
    s = tb.read_text()
    rings = list(RING.finditer(s))
    if len(rings) != 4:
        raise ValueError(f'four literal nst4 rings required, found {len(rings)}')
    add, show = [], []
    for m in rings:
        params, label, fclk, start, clk, rst, k, w = m.groups()
        add += twin(params, label, fclk, start, clk, rst, k, int(w))
        for form in FORMS:
            n = f'{form}_{label}'
            show.append(f'$display("AGE {label} {form} ready%0d fault%0d checks%0d lo%0d hi%0d",'
                        f'ready_{n},fault_{n},n_{n},lo_{n},hi_{n});')
    marker = 'always@(negedge refclk)if(cycles==800)begin'
    if s.count(marker) != 1:
        raise ValueError('final marker')
    s = s.replace(marker, '\n'.join(add) + '\n' + marker + '\n' + '\n'.join(show))
    tb.write_text(s)
    print('AGE_READY', len(rings), 'rings', len(FORMS), 'forms')


if __name__ == '__main__':
    main()
