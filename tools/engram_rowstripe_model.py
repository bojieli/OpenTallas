#!/usr/bin/env python3
"""Evaluate only the Engram function of the unified analytical model.

The implementation remains tools/uarch_model.py. Loading that function alone
avoids unrelated rack history and software benchmark dependencies on the
minimum component sizing vehicle.
"""
import argparse,ast,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context',type=int,default=1048576)
    parser.add_argument('--users',type=int,default=64)
    args=parser.parse_args()
    if args.context<=0 or args.users<=0:raise ValueError('context/users must be positive')
    source=R/'tools/uarch_model.py';tree=ast.parse(source.read_text())
    fn=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='dsrom_engram_rowstripe_model')
    namespace={};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),namespace)
    record=namespace[fn.name](context=args.context,users=args.users)
    record['unified_model_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    print(json.dumps(record,indent=1))
    return int(not record['matched_context_capacity_pass'])
if __name__=='__main__':raise SystemExit(main())
