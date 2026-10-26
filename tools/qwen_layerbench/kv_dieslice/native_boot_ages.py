#!/usr/bin/env python3
"""Make native dispatcher target-10 length agree with the real AGES1 receiver."""
import argparse,re
from pathlib import Path

def dispatch(text):
    headers=list(re.finditer(r'(module qkd_static_kv_boot_dispatch(?:_mu)?_(?:nc32|c32)\s*#\()(.*?)(\)\s*\()',text,re.S))
    if len(headers)!=2:raise ValueError('expected dispatcher and MU wrapper')
    for m in reversed(headers):
        body=m.group(2)
        if 'parameter integer AGES=0' not in body:
            a='parameter integer DIECAP=0,'
            if body.count(a)!=1:raise ValueError('dispatcher parameter anchor changed')
            body=body.replace(a,a+'parameter integer AGES=0,')
            text=text[:m.start(2)]+body+text[m.end(2):]
    old='32+NRST+1+((DIECAP!=0)?1:0)';new=old+'+((AGES!=0)?19:0)'
    if new not in text:
        if text.count(old)!=1:raise ValueError('dispatcher target10 count anchor changed')
        text=text.replace(old,new)
    old='.DIECAP(DIECAP),.SRQ(SRQ)';new='.DIECAP(DIECAP),.AGES(AGES),.SRQ(SRQ)'
    if new not in text:
        if text.count(old)!=1:raise ValueError('MU wrapper pass-through anchor changed')
        text=text.replace(old,new)
    return text

def control(text):
    if not re.search(r'qkd_kv_die_cfg_a_c32\s*#\([^;]*\.AGES\(1\)',text):raise ValueError('native receiver is not AGES1')
    rx=r'(qkd_static_kv_boot_dispatch_mu_(?:nc32|c32)\s*#\()([^;]*?)(\)\s+u_boot\s*\()'
    matches=list(re.finditer(rx,text));
    if len(matches)!=1:raise ValueError('expected one native boot dispatcher')
    m=matches[0];body=m.group(2)
    if re.search(r'\.AGES\(1\)',body):return text
    a='.DIECAP(1)'
    if body.count(a)!=1:raise ValueError('native dispatcher capability anchor changed')
    body=body.replace(a,a+', .AGES(1)')
    return text[:m.start(2)]+body+text[m.end(2):]

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('mode',choices=['dispatch','control']);ap.add_argument('source',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args();a.output.write_text((dispatch if a.mode=='dispatch' else control)(a.source.read_text()))
