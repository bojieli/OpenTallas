#!/usr/bin/env python3
"""Make every prepared literal ring carry a sender word count and report its latency.

Input: a head_fault_1107 packet prepared with all parts. The ring, K, START and
reader origin stay literal; only d changes from zero to a word counter on the
forwarded clock. For each ring the bench prints the first sender START edge, one
word seen at the reader and the reader edge time; read_lat.py removes the profile
clock arrivals, which leaves an exact integer count of cycles in the nominal frame.
Local to the crossings: no codecs, no arithmetic, no whole-die token.
"""
import argparse
import re
from pathlib import Path

RING = re.compile(r"^(ot_dp_clk_landing_cas #\(.*?\) probe_(\w+)\(\.fclk\((\w+)\),\.t_rst_n\((\w+)\),"
                  r"\.clk\((\w+)\),.*?)\.d\((\d+)'d0\),", re.M)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('packet', type=Path)
    a = ap.parse_args()
    tb = a.packet / 'tb.sv'
    s = tb.read_text()
    add, show = [], []
    labels = []

    def edit(m):
        head, label, fclk, start, clk, w = m.groups()
        w = int(w)
        labels.append(label)
        pad = f"{w-32}'d0," if w > 32 else ''
        word = f"w_{label}" if w >= 32 else f"w_{label}[{w-1}:0]"
        cmp_q = f"q_{label}[31:0]" if w >= 32 else f"q_{label}"
        add.extend([
            f"reg [31:0] w_{label}=0;realtime t0_{label}=0;always@(posedge {fclk})if(!{start})w_{label}<=0;"
            f"else begin if(t0_{label}==0)t0_{label}=$realtime;w_{label}<=w_{label}+1;end",
            f"integer n_{label}=0;reg [31:0] v_{label}=0;realtime tr_{label}=0;",
            f"always@(posedge {clk})begin #0.001;if(ready_{label}&&!fault_{label}&&n_{label}<40)begin "
            f"v_{label}={cmp_q};tr_{label}=$realtime-0.001;n_{label}++;end end"])
        show.append(f'$display("LAT {label} ready%0d fault%0d n%0d t0 %0.6f v %0d tr %0.6f",'
                    f'ready_{label},fault_{label},n_{label},t0_{label},v_{label},tr_{label});')
        return f"{head}.d({{{pad}{word}}}),"

    s, count = RING.subn(edit, s)
    if not count:
        raise ValueError('no literal rings found')
    marker = 'always@(negedge refclk)if(cycles==800)begin'
    if s.count(marker) != 1:
        raise ValueError('final marker')
    s = s.replace(marker, '\n'.join(add) + '\n' + marker + '\n' + '\n'.join(show))
    tb.write_text(s)
    print('LAT_READY', count, 'rings')


if __name__ == '__main__':
    main()
