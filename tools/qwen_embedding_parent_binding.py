#!/usr/bin/env python3
"""Bind qualified ingress views and measured internal clock latency to a parent.

An existing unqualified or provenance-free macro is never accepted. Inputs are
immutable collected component artifacts; this command does not run P&R.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Only explicitly reviewed ingress implementations may furnish a parent view.
APPROVED_TOPS = ('ot_qwen_embedding_ingress_island', 'ot_qwen_embedding_ingress_padded', 'ot_qwen_embedding_ingress_numeric')


def alias_bytes(data, suffix, source, target):
    """Rename just the exported top identifier, preserving every other byte."""
    if source not in APPROVED_TOPS or not re.fullmatch(r'qfd_embed_ingress_(code|scale)', target):
        raise ValueError('unapproved component alias')
    old, new = source.encode(), target.encode()
    if suffix == '.lef':
        patterns = [rb'(?m)^(MACRO[ \t]+)' + re.escape(old) + rb'([ \t]*\r?$)',
                    rb'(?m)^(END[ \t]+)' + re.escape(old) + rb'([ \t]*\r?$)']
    else:
        patterns = [rb'(\bcell\s*\(\s*"?)' + re.escape(old) + rb'("?\s*\))']
    result = data
    for pattern in patterns:
        result, count = re.subn(pattern, lambda m: m[1]+new+m[2], result)
        if count != 1:
            raise ValueError('export must contain exactly one source top declaration: '+suffix)
    return result


def audit_alias(view, abstract, name):
    alias = abstract.get('identifier_alias', {})
    source = alias.get('source_top')
    if source not in APPROVED_TOPS or alias.get('target_top') != name:
        raise ValueError('approved export alias provenance required')
    for suffix in ('.lef', '_ss.lib', '_ff.lib'):
        filename = name+suffix
        original = view/'export_original'/filename
        if not original.is_file() or sha(original) != alias.get('original_sha256', {}).get(filename):
            raise ValueError('original export missing or hash mismatch: '+filename)
        if alias_bytes(original.read_bytes(), suffix, source, name) != (view/filename).read_bytes():
            raise ValueError('export modification extends beyond top identifier: '+filename)


def clock_reference(log):
    if '[ERROR' in log:
        raise ValueError('clock reference log contains an error')
    rows=re.findall(r'^QDM reference pin (\S+) clock arrival max (\S+) min (\S+) skew 90 hold 50$',log,re.M)
    if len(rows)!=1 or 'valid_q' not in rows[0][0]:
        raise ValueError('exactly one real valid_q reference clock required')
    pin,hi,lo=rows[0];hi,lo=float(hi),float(lo)
    if not all(math.isfinite(x) and x>=0 for x in (hi,lo)) or hi<lo:
        raise ValueError('invalid reference clock arrival')
    return dict(pin=pin,max_ps=hi,min_ps=lo)


def qualify(kind, view, receipt, source_pin):
    if not re.fullmatch('[0-9a-f]{40}',source_pin):
        raise ValueError('an actual full source commit is required')
    name='qfd_embed_ingress_'+kind
    required=[view/(name+s) for s in ('.lef','_ss.lib','_ff.lib')]
    required += [view/'interface.sdc',view/'abstract.json',receipt/'corner_sta.json',receipt/'metadata_storage.json',
                 receipt/'qualification.json',receipt/'w18_sta_ss.log',receipt/'w18_sta_ff.log']
    missing=[str(p) for p in required if not p.is_file()]
    if missing:raise ValueError('required real component artifacts absent: '+', '.join(missing))
    corner=json.loads((receipt/'corner_sta.json').read_text())
    metadata=json.loads((receipt/'metadata_storage.json').read_text())
    evidence=json.loads((receipt/'qualification.json').read_text())
    abstract=json.loads((view/'abstract.json').read_text())
    if evidence.get('source_commit')!=source_pin or evidence.get('drc')!=0 or evidence.get('exactness_pass') is not True:
        raise ValueError('pinned source, DRC0 and completed exactness qualification required')
    if evidence.get('corner_sta_sha256')!=sha(receipt/'corner_sta.json') or evidence.get('metadata_storage_sha256')!=sha(receipt/'metadata_storage.json'):
        raise ValueError('qualification receipt hash mismatch')
    for key in ('setup_ss','hold_ff'):
        row=corner[key]
        if not isinstance(row.get('worst_slack_ps'),(int,float)) or not math.isfinite(row['worst_slack_ps']) or row['worst_slack_ps']<15 or row.get('errors'):
            raise ValueError(key+' is not qualified at +15ps')
    for key in ('odb_sha256','spef_sha256','sdc_sha256'):
        source=corner['setup_ss'][key]
        if source!=corner['hold_ff'][key] or abstract.get('source_artifacts',{}).get(key)!=source:
            raise ValueError('fresh corner/export physical source mismatch: '+key)
    if abstract.get('interface_sdc',{}).get('sha256')!=sha(view/'interface.sdc'):
        raise ValueError('interface extraction constraints are not bound')
    if abstract.get('source_commit') != source_pin:
        raise ValueError('export source pin mismatch')
    if abstract.get('ok') is not True:
        raise ValueError('macro export not complete')
    for p in required[:3]:
        if abstract.get('files',{}).get(p.name)!=sha(p):raise ValueError('export view hash mismatch: '+p.name)
    audit_alias(view, abstract, name)
    for suffix in ('ss','ff'):
        text=(view/f'{name}_{suffix}.lib').read_text()
        if not re.search(r'cell\s*\(\s*"?'+re.escape(name)+r'"?\s*\)',text):
            raise ValueError('Liberty cell name does not match parent hard macro')
    lef=(view/f'{name}.lef').read_text()
    if not re.search(r'^MACRO\s+'+re.escape(name)+r'\s*$',lef,re.M):raise ValueError('LEF macro name mismatch')
    size=re.search(r'\bSIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)\s*;',lef)
    if not size or any(float(x)>15.12+1e-6 for x in size.groups()):raise ValueError('island exceeds modeled slot')
    width=12 if kind=='code' else 18
    counts={'address_q':width,'address_n':width,'valid_q':1,'valid_n':1,'credit_q':1,'credit_n':1}
    if metadata.get('verdict')!='PASS' or metadata.get('counts')!=counts or metadata.get('width')!=width:
        raise ValueError('full independent ingress storage gate missing')
    padding=metadata.get('input_padding')
    if abstract['identifier_alias']['source_top'] in ('ot_qwen_embedding_ingress_padded','ot_qwen_embedding_ingress_numeric'):
        if not isinstance(padding,dict):raise ValueError('mapped fixed padding topology required')
        synth_path=receipt/'metadata_storage_synthesis.json'
        if not synth_path.is_file() or sha(synth_path)!=evidence.get('metadata_storage_synthesis_sha256'):
            raise ValueError('synthesis pad topology receipt missing or changed')
        synth=json.loads(synth_path.read_text())
        if metadata.get('netlist_sha256')!=evidence.get('routed_netlist_sha256') or not re.fullmatch('[0-9a-f]{64}',metadata.get('netlist_sha256','')):
            raise ValueError('routed pad topology is not bound to the final netlist')
        if synth.get('verdict')!='PASS' or synth.get('netlist_sha256')!=evidence.get('synthesis_netlist_sha256') or not re.fullmatch('[0-9a-f]{64}',synth.get('netlist_sha256','')) or synth.get('input_padding')!=padding:
            raise ValueError('synthesis and routed pad topology disagree')
        required.append(synth_path)
        stages=padding.get('stages_per_input')
        if type(stages) is not int or stages<1 or padding.get('input_bits')!=width+3 or padding.get('fixed_buffer_cells')!=stages*(width+3) or padding.get('cell_type')!='BUFx2_ASAP7_75t_R' or padding.get('connectivity_verified') is not True:
            raise ValueError('fixed input padding topology does not match full shape')
    clocks={c:clock_reference((receipt/f'w18_sta_{c}.log').read_text()) for c in ('ss','ff')}
    if clocks['ss']['pin']!=clocks['ff']['pin']:raise ValueError('different reference FF across corners')
    return dict(schema='opentallas.qwen.embedding_parent_binding.v1',source_commit=source_pin,
                macro=name,input_padding=padding,reference_macro_pin='u_ingress/clk',clock=clocks,
                setup_internal_clock_ps=clocks['ss']['max_ps'],hold_internal_clock_ps=clocks['ff']['min_ps'],
                files={('view/' if p.parent==view else 'receipt/')+p.name:sha(p) for p in required},shape_um=[float(x) for x in size.groups()],
                parent_physical_closed=False)


def verify_binding(kind, view, receipt, source_pin=None):
    binding=json.loads((view.parent/'binding.json').read_text())
    pin=source_pin or binding.get('source_commit', '')
    result=qualify(kind,view,receipt,pin)
    if binding != result:
        raise ValueError('stale parent binding or source artifacts')
    expected=(f"set embedding_ref_internal_setup_ps {result['setup_internal_clock_ps']:.9f}\n"
              f"set embedding_ref_internal_hold_ps {result['hold_internal_clock_ps']:.9f}\n")
    if (view.parent/'clock_reference.tcl').read_text()!=expected:
        raise ValueError('stale parent clock offsets')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kind',choices=['code','scale'],required=True)
    p.add_argument('--view',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True)
    p.add_argument('--source-pin')
    p.add_argument('--out',type=Path)
    p.add_argument('--verify',action='store_true')
    a=p.parse_args()
    if a.verify:
        verify_binding(a.kind,a.view,a.receipt,a.source_pin)
        print('PASS immutable parent binding and clock offsets')
        return
    if not a.source_pin:raise ValueError('source pin required for new binding')
    result=qualify(a.kind,a.view,a.receipt,a.source_pin)
    if a.out is None or a.out.exists():raise ValueError('new output directory required')
    a.out.mkdir(parents=True)
    (a.out/'binding.json').write_text(json.dumps(result,indent=2)+'\n')
    (a.out/'clock_reference.tcl').write_text(f"set embedding_ref_internal_setup_ps {result['setup_internal_clock_ps']:.9f}\n"
        f"set embedding_ref_internal_hold_ps {result['hold_internal_clock_ps']:.9f}\n")
    print('PASS qualified ingress binding; parent physical closure remains open')
if __name__=='__main__':main()
