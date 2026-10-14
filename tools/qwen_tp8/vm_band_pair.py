"""Measured, insertion-compensated TT reach for a concrete pair of leaf pins."""
import json,sys
from functools import lru_cache
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
from pinreg_audit import parse_lib,clock_refs,pin_metrics


@lru_cache(None)
def timing(view):
    p=ROOT/view;lib=parse_lib(next(p.glob('*_tt.lib')))
    refs=clock_refs(lib,json.loads((p/'insertion.json').read_text()),'tt')
    return pin_metrics(lib,refs),refs


@lru_cache(None)
def reach(launch_view,launch_bit,capture_view,capture_bit):
    lm,lr=timing(launch_view);cm,cr=timing(capture_view)
    l=lm[f'q[{launch_bit}]'];c=cm[f'd[{capture_bit}]']
    if l['out'] is None or c['inp'] is None or not l['clk'] or not c['clk']:
        raise ValueError('missing real sequential pin timing; cannot assign reach')
    a=lr[l['clk'][0]];b=cr[c['clk'][0]]
    o=l['out']+a['bmax']-a['rise'];s=c['inp']+b['rise']-b['bmin']
    skew=90 if max(a['rise'],b['rise'])<=300 else 150
    return min(500,(833.3333333333-60-skew-o-s)/.76)
