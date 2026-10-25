#!/usr/bin/env python3
"""Make native-only RTL copies that consume delivered synchronous reset.
The physical plan's u_rst_root owns the only core-die asynchronous synchronizer.
This overlay changes internal ot_rst_relay instances, not the root clock/POR box.
Their release latency remains SYNC_STAGES+TREE_STAGES; assertion propagates onclk.
"""
import argparse,json,re
from pathlib import Path

def patch(s):
    edits=[];count=0
    for m in re.finditer(r'\bot_rst_relay\s*#\s*\(',s):
        if re.search(r'\bmodule\s*$',s[max(0,m.start()-40):m.start()]):continue
        start=m.end();i=start;depth=1
        while i<len(s) and depth:
            depth+=(s[i]=='(')-(s[i]==')');i+=1
        assert depth==0,'unbalanced reset relay parameters'
        p=s[start:i-1]
        if '.SYNC_INPUT' in p:
            p,n=re.subn(r'\.SYNC_INPUT\(\s*[01]\s*\)','.SYNC_INPUT(1)',p);assert n==1,p
        else:p='.SYNC_INPUT(1), '+p
        edits.append((start,i-1,p));count+=1
    for a,b,t in reversed(edits):s=s[:a]+t+s[b:]
    # Unparameterised calls (the canonical declaration has module before its name).
    s,n=re.subn(r'(?m)^(\s*)ot_rst_relay\s+(\w+)\s*\(',r'\1ot_rst_relay #(.SYNC_INPUT(1)) \2 (',s)
    return s,count+n

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--files',required=True);ap.add_argument('--out-dir',required=True);ap.add_argument('--out-list',required=True);ap.add_argument('--manifest',required=True);a=ap.parse_args()
    out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True);rows=[];paths=[]
    for f in dict.fromkeys(Path(a.files).read_text().splitlines()):
        p=Path(f)
        if not p.is_file() or p.suffix not in ('.v','.sv'):continue
        src=p.read_text();dst,n=patch(src)
        if not n:continue
        # Preserve path identity even when unrelated directories use the same file name.
        q=out/str(p).lstrip('/');q.parent.mkdir(parents=True,exist_ok=True);q.write_text(dst)
        rows.append(dict(source=str(p),overlay=str(q),instances=n));paths.append(str(q))
    assert rows,'no internal reset relay instances found in native file list'
    Path(a.out_list).write_text('\n'.join(paths)+'\n')
    Path(a.manifest).write_text(json.dumps(dict(root_owner='physical plan u_rst_root; hb_ckgen POR sync must be bypassed in final bound composition',
        flat_bench='Existing clock/POR driver is a pre-bind delivery contract only',
        release_cycle_delta=0,assertion='synchronous propagation',instances=sum(x['instances'] for x in rows),files=rows),indent=1))
    print('B2_DELIVERED_RESET_OVERLAY',len(rows),'files',sum(x['instances'] for x in rows),'instances; release delta0')
if __name__=='__main__':main()
