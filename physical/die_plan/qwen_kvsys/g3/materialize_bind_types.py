#!/usr/bin/env python3
"""Materialize genuine native bind variants as separate physical plan masters.

Wiring/pad variants must be hardened independently. This copies existing
physical geometry and assigns each actual bound module its own plan type;
it changes neither RTL, instance placement, port windows nor lane cycles.
Apply to the final padded bind, then rebind/regenerate R8 and reset offsets.
"""
import argparse
import copy
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


def materialize(raw,report,top):
    declared={v['module']:name for name,v in report['types'].items()}
    parts=raw['partitions'] if isinstance(raw['partitions'],dict) else {p['name']:p for p in raw['partitions']}
    matches=re.findall(r'^\s+([A-Za-z_$][\w$]*)(?:\s+#\([^\n]*\))?\s+([A-Za-z_$][\w$]*)\s*\(',top,re.M)
    mods={inst:mod for mod,inst in matches if inst in parts}
    missing=sorted(set(parts)-set(mods))
    if missing:raise ValueError(f'bound top lacks partitions {missing}')
    groups=defaultdict(lambda:defaultdict(list))
    for inst,part in parts.items():groups[part['type']][mods[inst]].append(inst)
    changes=[];assignments={};original_types=len(raw['partition_types'])
    for old,variants in groups.items():
        original=copy.deepcopy(raw['partition_types'][old]);base_module=original['module']
        geometry=hashlib.sha256(json.dumps({k:v for k,v in original.items() if k!='module'},sort_keys=True).encode()).hexdigest()
        ordered=sorted(variants,key=lambda mod:(mod!=base_module,mod))
        for j,mod in enumerate(ordered):
            if mod not in declared:raise ValueError(f'bound top master {mod} absent from bind_report.types')
            name=old if j==0 else declared[mod]
            if j and name in raw['partition_types']:
                raise ValueError(f'variant name collision {name}; do not silently merge unrelated physical masters')
            ty=copy.deepcopy(original);ty['module']=mod
            raw['partition_types'][name]=ty
            for inst in variants[mod]:parts[inst]['type']=name;assignments[inst]=dict(type=name,module=mod)
            if len(variants)>1:
                changes.append(dict(original_type=old,type=name,module=mod,instances=sorted(variants[mod]),geometry_sha256=geometry))
    return dict(schema='opentallas.kv_native_type_materialization.v1',before_types=original_types,
                after_types=len(raw['partition_types']),split_families=sum(len(v)>1 for v in groups.values()),
                unchanged_lane_cycles=True,unchanged_instance_origins=True,variants=changes,assignments=assignments,
                next='Rebind on this plan, regenerate R8 and wavefront reset offsets, then require TYPE_SPLIT zero.')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('bind_dir');ap.add_argument('out')
    args=ap.parse_args();d=Path(args.bind_dir);raw=json.loads(Path(args.plan).read_text());report=json.loads((d/'bind_report.json').read_text())
    top=d/'rtl'/f"{report['die']}_bound_top.sv"
    receipt=materialize(raw,report,top.read_text())
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    (out/'die_plan.json').write_text(json.dumps(raw,indent=1)+'\n');(out/'type_materialization.json').write_text(json.dumps(receipt,indent=1)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['variants','assignments']}))

if __name__=='__main__':main()
