#!/usr/bin/env python3
"""Prepare a separate source candidate for an approved constant VQ timing table.

This never edits the source or binding manifest supplied by the caller. The
output requires a separate coordinator-approved candidate bind; production
programme and physical adoption do not follow from generation.
"""
import argparse,hashlib,json,re
from pathlib import Path


def prepare(source,proposal):
    rows=proposal['candidate_native_parameter_overrides']
    records=proposal['current']
    if len(rows)!=80 or proposal.get('candidate_adopted')is not False:
        raise ValueError('exact unadopted80-strap candidate required')
    sid_leaf={}
    for sl,r in records.items():
        for leaf in r['leaves']:
            sid_leaf[(sl,leaf['leaf'])]=leaf['sid']
    table={}
    for sl,grp in proposal['both_families_per_slice_k0to4'].items():
        for leaf,k in enumerate(grp['profile']):
            sid=sid_leaf[(sl,leaf)]
            if not 0<=k<5 or (sid,leaf)in table:raise ValueError('qualified K0..4 unique source ownership required')
            table[sid,leaf]=k
    if len(table)!=80 or set(table)!={(s,k)for s in range(16)for k in range(5)}:
        raise ValueError('exact16x5 constant source table required')
    start=source.index('module ot_s81sl_leaf #(');end=source.index('\nendmodule',start)
    leaf=source[start:end]
    m=re.search(r'ot_s81sl_vq\s+#\(.*?\)\s+u_vq\s*\((.*?)\);',leaf,re.S)
    if not m or len(re.findall(r'\.k\(k\)',m[0]))!=1:
        raise ValueError('selected native leaf VQ k hookup differs')
    fn=['    // Candidate-only source timing constants; sid/k remain unchanged elsewhere.',
        '    function automatic [2:0] candidate_vq_timing(input [3:0] s, input [2:0] l);',
        '        begin case ({s,l})']
    fn += [f"            7'd{8*s+k}: candidate_vq_timing = 3'd{v};"for(s,k),v in sorted(table.items())]
    fn+=['            default: candidate_vq_timing = l;','        endcase end','    endfunction','']
    pos=leaf.rfind('`ifndef OT_S81SL_HARD',0,m.start())
    if pos<0 or m.start()-pos>40:raise ValueError('actual hard/functional VQ branch differs')
    changed=leaf[:pos]+'\n'.join(fn)+leaf[pos:m.end()].replace('.k(k)','.k(candidate_vq_timing(sid,k))')+leaf[m.end():]
    return source[:start]+changed+source[end:]


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--source',type=Path,required=True);a.add_argument('--proposal',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--manifest',type=Path);a.add_argument('--manifest-out',type=Path);a.add_argument('--source-entry');x=a.parse_args()
    if x.out.exists():raise ValueError('choose a fresh candidate output')
    raw=x.source.read_text();out=prepare(raw,json.loads(x.proposal.read_text()));x.out.write_text(out)
    print('CANDIDATE_SOURCE_ONLY',x.out,'source_sha256',hashlib.sha256(raw.encode()).hexdigest(),'candidate_sha256',hashlib.sha256(out.encode()).hexdigest())

    if any((x.manifest,x.manifest_out,x.source_entry)):
        if not all((x.manifest,x.manifest_out,x.source_entry))or x.manifest_out.exists():raise ValueError('fresh explicit candidate manifest and exact selected source-entry required')
        if x.out.is_absolute():raise ValueError('candidate source must use a repository-relative path in manifest')
        manifest=json.loads(x.manifest.read_text());n=0
        for key in ('files','prefer'):
            if manifest.get(key,[]).count(x.source_entry)!=1:raise ValueError('one selected source in files/prefer required')
            manifest[key]=[str(x.out)if p==x.source_entry else p for p in manifest[key]];n+=1
        manifest['note']=manifest.get('note','')+' | COORD-approved independent K0..4 dual-family SOURCE CANDIDATE PREP ONLY; no canonical adoption or global/physical/finalPOST authority.'
        x.manifest_out.write_text(json.dumps(manifest,indent=1)+'\n')
        print('CANDIDATE_MANIFEST_ONLY',x.manifest_out,'selected_source_references',n)
