#!/usr/bin/env python3
"""Compile genuine entry inputs and NORMR/GO literals from emitted slice sources.

This view supplies SIDs and PDSK only. It deliberately supplies no transport,
partial-arrival, reset, launch, global exchange or retirement dates.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent),str(HERE)]
import dv_layer_compile as D
from layer_prog.emitted_norm_source import EmittedNormSource
from layer_prog.entry_inputs import compile_inputs
from layer_prog.entry_norm import compile_norm
from layer_prog.bound_control import retime_norm
from layer_prog.entry_write_calendar import encode_unsealed


def check_control(program,die):
    """Decode every actual payload/row and check issuer-only resource bounds."""
    rows=program['rows'];templates=program['templates'];commands=program['commands']
    if len(rows)!=96 or len(templates)!=96 or len(commands)!=96:
        raise ValueError('require80 NORMR and16 GO native commands')
    if sorted(t['i']for t in templates)!=list(range(96)):
        raise ValueError('complete unique native template slots required')
    payloads={t['i']:int(t['payload186'],16)for t in templates}
    rowmap={r['tix']:r for r in rows}
    if len(rowmap)!=96 or set(rowmap)!=set(payloads):raise ValueError('native row/template identity differs')
    eps=int(program['eps_fp32_bits'],16);slots=set();alignments={};kinds=[];gos=[]
    if program['die_sha256']!=die.die_sha:raise ValueError('norm control and actual emitted source differ')
    for c in commands:
        sid=c['sid'];sl=c['slice'];r=rowmap[c['template']]
        if die.slices()[sl]['sid']!=sid:raise ValueError('actual source SID differs')
        if r['eng']!=(D.ENG['VN']if sid&1 else D.ENG['VS'])or r['arg']!=c['template']or r['issue']!=c['issue']or r['done']!=r['issue']+5:
            raise ValueError('native issuer/ACK fields differ')
        if not 0<=r['issue']<=r['done']<1<<24 or (r['eng'],r['issue'])in slots:
            raise ValueError('native counter width or engine collision')
        slots.add((r['eng'],r['issue']))
        if int(r['row76'],16)!=D.pack_row(r['done'],r['issue'],r['eng'],r['arg']):raise ValueError('native PW row differs')
        p=payloads[c['template']];mask=p&65535;target=(p>>16)&31;leafmask=(p>>21)&31;body=p>>26
        if mask!=1<<sid or not 0<=p<1<<186:raise ValueError('native source mask/width differs')
        if c['kind']=='NORMR':
            k=c['leaf']
            if (target,leafmask,body&15,(body>>4)&1023,(body>>14)&1023,(body>>24)&255,body>>32)!=(0,1<<k,7,1008,5*sid+k,1,0):
                raise ValueError('actual NORMR payload differs')
            alignments.setdefault(sl,[]).append((k,r['issue']+die.deskew[sl][k]))
        elif c['kind']=='XFIN_GO':
            if (target,leafmask,body)!=(1,0,eps):raise ValueError('actual GO epsilon/mode payload differs')
            gos.append(sid)
        else:raise ValueError('unexpected command in norm page')
        kinds.append(c['kind'])
    if kinds.count('NORMR')!=80 or sorted(gos)!=list(range(16)):raise ValueError('native norm cohort differs')
    for sl,pairs in alignments.items():
        if sorted(k for k,_ in pairs)!=list(range(5))or len({a for _,a in pairs})!=1:
            raise ValueError('literal PDSK does not align five issuer-relative controls')
    live={eng:max(sum(r['eng']==eng and r['issue']<=edge<=r['done']for r in rows)
        for edge in range(min(r['issue']for r in rows),max(r['done']for r in rows)+1))for eng in (0,1)}
    # Count the ACK edge conservatively against each engine's eight entries.
    if max(live.values())>8 or len(rows)>128 or len(templates)>128:raise ValueError('native counter/slot capacity exceeded')
    return dict(command_count=96,normr_count=80,go_count=16,rows=96,templates=96,
        first_issue=min(r['issue']for r in rows),last_issue=max(r['issue']for r in rows),
        last_posted_ack=max(r['done']for r in rows),max_live_issuer_rows_by_engine=live,
        pdsk_control_alignment={sl:pairs[0][1]for sl,pairs in alignments.items()},
        alignment_scope='issuer issue plus literal PDSK; no transport or partial-arrival qualification')


def check_host(program,words):
    """Independently decode the selected native LEN/PW/template-only stream."""
    cells={};templates={};lengths=[]
    if len(words)!=385:raise ValueError('unsealed native word count differs')
    for word in words:
        if type(word)is not int or not 0<=word<1<<515 or word&1!=1 or word>>513:
            raise ValueError('native HOST valid/type/width differs')
        x=word>>1;op=x&255
        if op==0x11:
            lengths.append((x>>32)&255)
            if x!=(op|((x>>32)&255)<<32):raise ValueError('native LEN reserved bits differ')
        elif op==0x10:
            a=(x>>96)&127;d=(x>>32)&((1<<28)-1);part=d>>26;key=(a,part)
            if part>=3 or key in cells or x!=(op|d<<32|a<<96):raise ValueError('native PW header/duplicate/reserved bits differ')
            cells[key]=d&((1<<26)-1)
        elif op==0x13:
            a=(x>>8)&127;p=(x>>16)&((1<<186)-1)
            if a in templates or x!=(op|a<<8|p<<16):raise ValueError('native template duplicate/reserved bits differ')
            templates[a]=p
        else:raise ValueError('unsealed norm stream contains an unexpected HOST operation')
    if lengths!=[96]or set(cells)!={(i,p)for i in range(96)for p in range(3)}:
        raise ValueError('native norm PW coverage differs')
    for i,r in enumerate(program['rows']):
        if sum(cells[i,p]<<(26*p)for p in range(3))!=int(r['row76'],16):raise ValueError('native norm PW bytes differ')
    if templates!={t['i']:int(t['payload186'],16)for t in program['templates']}:raise ValueError('native norm payload bytes differ')


def compile_selected(die,entry,eps_bits,first_issue):
    p=retime_norm(compile_norm(die,entry,eps_bits,first_issue),die,deskew_by_slice=die.deskew)
    p.update(schema='opentallas.s81.selected_entry_norm_control.v1',status='UNSEALED_SOURCE_CONTROL',
        source_view_sha256=die.source_record['source_view_sha256'],
        source_inventory=die.source_record,transport_dates_qualified=False,
        input_residency_required='fresh same-source target5/HLOAD/GAIN entry programme completed before launch',
        timebase='explicit issuer-relative command age; no physical KS/START or reset date',
        kit_emitted=False,end_emitted=False,begin_emitted=False,seal_emitted=False,
        mu_initialization_emitted=False,entry_rl489_adopted=False,added_rtl_cycles=0)
    p['retime']['go_dates']='fresh generated issuer positions; actual first-partial/GO readiness remains open'
    p['control_check']=check_control(p,die)
    p['holds']+=['fresh emitted-cohort target5/HLOAD/GAIN transport and store readiness',
        'actual selected NORMR transport and partial arrival; PDSK alone does not qualify GO',
        'global XFIN/NX/RSTD and VQ K-profile/source publication',
        'per-resource MU return calendar, KIT/END and actual global physical START']
    return p


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-inventory',type=Path,required=True)
    p.add_argument('--fixtures',type=Path,required=True)
    p.add_argument('--entry-engram-inputs',type=Path,required=True)
    p.add_argument('--inference-config',type=Path,required=True)
    p.add_argument('--first-issue',type=int,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('preserve prior result; choose fresh output')
    die=EmittedNormSource(a.source_inventory)
    config_sha=hashlib.sha256(a.inference_config.read_bytes()).hexdigest()
    key='compiler/models/deepseek-v4.1-flash/inference_config.json'
    if json.loads((a.fixtures/'meta.json').read_text())['sources'].get(key)!=config_sha:
        raise ValueError('model config does not match genuine fixture source')
    config=json.loads(a.inference_config.read_text())
    eps=struct.unpack('<I',struct.pack('<f',config['norm_eps']))[0]
    entry=compile_inputs(die,a.fixtures,a.entry_engram_inputs)
    result=compile_selected(die,entry,eps,a.first_issue)
    result['epsilon_source']=dict(path=key,sha256=config_sha,key='norm_eps',value=config['norm_eps'])
    words=encode_unsealed(result)
    check_host(result,words)
    result.update(host_boot_file='norm.unsealed.host_boot.memh',host_word_count=len(words),
        local_host_slots_at_5_edges_per_word=len(words)*5,host_word_source='LEN +96x3 PW +96 templates only')
    a.out.mkdir(parents=True)
    (a.out/'entry_inputs.json').write_text(json.dumps(entry,indent=1)+'\n')
    (a.out/'norm_control.json').write_text(json.dumps(result,indent=1)+'\n')
    (a.out/'norm.unsealed.host_boot.memh').write_text(D.memh(words,515))
    print(json.dumps(dict(status=result['status'],source_top_sha256=die.die_sha,
        fresh_entry_rows=entry['row_count'],host_words=len(words),**result['control_check']),sort_keys=True))


if __name__=='__main__':main()
