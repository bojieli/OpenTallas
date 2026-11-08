#!/usr/bin/env python3
"""Apply a private physical plan delta to a newer plan; reject any touched-field conflict.
Lists remain atomic. No key deletion, clock/latency relaxation, or field conflict is hidden.
"""
import argparse,copy,json
from pathlib import Path
def apply(base,changed,target,path=()):
    if base==changed:return copy.deepcopy(target),[]
    if isinstance(base,dict) and isinstance(changed,dict) and isinstance(target,dict):
        out=copy.deepcopy(target);paths=[]
        for key in sorted(base.keys()|changed.keys()):
            if key not in changed:raise ValueError("deletion prohibited: "+str(path+(key,)))
            if key not in base:
                if key in target and target[key]!=changed[key]:raise ValueError("new-key conflict: "+str(path+(key,)))
                out[key]=copy.deepcopy(changed[key]);paths.append(path+(key,));continue
            if key not in target:raise ValueError("target key missing: "+str(path+(key,)))
            out[key],ps=apply(base[key],changed[key],target[key],path+(key,));paths+=ps
        return out,paths
    if target!=base and target!=changed:raise ValueError("touched-field conflict: "+str(path))
    return copy.deepcopy(changed),[path]
if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("base");a.add_argument("changed");a.add_argument("target");a.add_argument("out");a.add_argument("report");n=a.parse_args()
    b,c,t=(json.load(open(p)) for p in (n.base,n.changed,n.target))
    out,paths=apply(b,c,t)
    Path(n.out).write_text(json.dumps(out,indent=1)+"\n")
    Path(n.report).write_text(json.dumps({"base":n.base,"changed":n.changed,"target":n.target,"changed_paths":[list(p) for p in paths],"verdict":"COMPOSED_PRIVATE_NOT_BOUND"},indent=1)+"\n")
    print("composed",len(paths),"leaf/list fields; no conflicts")
