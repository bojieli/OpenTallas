#!/usr/bin/env python3
"""Read only emitted bound top and80 native wrapper headers/ports for K PREP."""
import argparse,json,re
from pathlib import Path


def literal(s):
    s=s.strip().replace('_','')
    m=re.fullmatch(r"(?:(\d+))?'([sS]?)([bBoOdDhH])([0-9a-fA-F]+)",s)
    if m:return int(m[4],{'b':2,'o':8,'d':10,'h':16}[m[3].lower()])
    if re.fullmatch(r'\d+',s):return int(s)
    raise ValueError('actual strap is not a literal: '+s)


def check(top_path,proposal):
    top=top_path.read_text();cache={};rows=[];errors=[]
    desired=proposal['candidate_native_parameter_overrides']
    if len(desired)!=80 or len({r['native_part']for r in desired})!=80:
        raise ValueError('exact80 distinct nativepart proposal required')
    for row in desired:
        part,key=row['native_part'],row['parameter']
        h=re.search(r'^\s*(\w+)(?:[ \t]+#\(([^\n]*?)\))?[ \t]+'+re.escape(part)+r'\s*\(',top,re.M)
        if not h:errors.append(dict(part=part,reason='selected native part missing'));continue
        master=h[1];file=top_path.parent/(master+'.sv')
        if file not in cache:cache[file]=file.read_text()
        body=cache[file]
        declared=re.search(r'\bparameter\b[^\n,;]*?\b'+re.escape(key)+r'\s*=\s*([^,\n]+)',body)
        hooked=len(re.findall(r'\.k\(\s*'+re.escape(key)+r'\[2:0\]\s*\)',body))
        if not declared or hooked!=1:errors.append(dict(part=part,parameter=key,reason='actual native VQ strap declaration/hookup differs'));continue
        overrides=dict(re.findall(r'\.(\w+)\(([^()]*)\)',h[2]or''))
        value=literal(overrides.get(key,declared[1]));r=dict(native_part=part,native_master=master,parameter=key,
            candidate_expected=row['candidate'],actual=value,selection='topoverride'if key in overrides else'nativedefault')
        rows.append(r)
        if value!=row['candidate']:errors.append(dict(**r,reason='candidate K mismatch'))
    return dict(schema='opentallas.s81.bound_K_candidate.v1',status='PASS_EXACT80_BOUND_K_CANDIDATE'if len(rows)==80 and not errors else'FAIL_EXACT80_BOUND_K_CANDIDATE',
        bound_top=str(top_path),checked=len(rows),errors=errors,records=rows,
        source_configuration_adopted=False,physical_qualified=False,global_calendar_qualified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bound-top',type=Path,required=True);p.add_argument('--proposal',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('fresh output required')
    r=check(a.bound_top,json.loads(a.proposal.read_text()));a.out.write_text(json.dumps(r,indent=1)+'\n');print(r['status'],r['checked'],'checked',len(r['errors']),'errors');raise SystemExit(0 if not r['errors']and r['checked']==80 else 1)
