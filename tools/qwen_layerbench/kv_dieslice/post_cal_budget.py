#!/usr/bin/env python3
"""Add an opt-in observation deadline measured from the actual producer calendar.

Only simulation termination changes. No traffic, clock, reset or DUT edge changes.
Used for old staged bench copies too, preserving their bound hierarchy rewrites.
"""
from pathlib import Path
import argparse


def add(text):
    if 'POST_CAL_BUDGET=%d' in text:
        return text
    decl = 'reg far_en = 0,'
    parse = 'if (!$value$plusargs("POST=%d", post)) post = 0;'
    old = 'if (post > 0) begin\n            repeat (post) @(posedge ck_core);'
    for marker in (decl, parse, old):
        if text.count(marker) != 1:
            raise ValueError(f'expected exactly one observation marker: {marker!r}')
    text = text.replace(decl, 'integer post_cal_budget = 0;\n    ' + decl)
    text = text.replace(parse, parse + '\n        void\'($value$plusargs("POST_CAL_BUDGET=%d", post_cal_budget));')
    new = '''if (post > 0 || post_cal_budget > 0) begin
            if (post_cal_budget > 0) begin
                if (!far_en) $fatal(1, "POST_CAL_BUDGET requires FAR=1");
                while (u_far.lay_cs[0] < 0 && cyc_core < maxcyc) @(negedge ck_core);
                if (u_far.lay_cs[0] < 0) $fatal(1, "POST_CAL_BUDGET: no producer layer0 calendar before MAXCYC");
                $display("KVSLICE_POST_CAL first_cal %0d budget %0d end %0d", u_far.lay_cs[0], post_cal_budget,
                         u_far.lay_cs[0] + post_cal_budget);
                while (u_far.cyc < u_far.lay_cs[0] + post_cal_budget && cyc_core < maxcyc) @(negedge ck_core);
                if (cyc_core >= maxcyc) $fatal(1, "POST_CAL_BUDGET exceeded MAXCYC");
            end else repeat (post) @(posedge ck_core);'''
    return text.replace(old, new)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('bench', type=Path)
    a = ap.parse_args()
    a.bench.write_text(add(a.bench.read_text()))


if __name__ == '__main__':
    main()
