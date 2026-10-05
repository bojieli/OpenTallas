#!/usr/bin/env python3
"""Strict ordered accepted-issue/KV-state join against source-owned programs.

Consumes exports; never fabricates accepted events or lane payloads from PCs.
PASS means journal consistency only, not RTL/physical/calibration admission.
"""
import argparse, hashlib, json
from pathlib import Path
import hdc_isa as I
from hdc_qwen_fullshape_isa_w12 import decode_instruction
from qwen_rom_program_identity import decoded, sha, ROOT
from qwen_rom_kv_production_join import ProducerJoin
from qwen_rom_persistent_kv_g0 import Owner
from qwen_rom_kv_launch_readiness import FIELDS, instruction
SOURCE_PATHS=['rtl/hdc/ot_hdc_core_vector_weight.sv','rtl/hdc/ot_hdc_dyn_ttiles.sv',
              'tools/qwen_rom_kv_production_join.py','tools/qwen_rom_program_kv_journal.py']
def source_pins(): return {p:sha((ROOT/p).read_bytes()) for p in SOURCE_PATHS}

def me_fields(word, token, position):
    """Literal 18/24-bit DYN decode, split-aware current G6144/W16 rounds."""
    if type(token) is not int or not 0<=token<151936 or type(position) is not int or not 0<=position<8192:
        raise ValueError('source token/context aperture')
    f=decode_instruction(word)
    if f['unit']!=I.UNIT_ME: raise ValueError('ME source unit')
    split=f['me_split']
    if split>11: raise ValueError('dyn_ttiles invalid_split')
    dyn=[0,token*4096,position*64,(position//16)*2048+position%16,
         position*128,position+1,position//98304+1,0]
    result={name:f['me_'+name] for name,width in FIELDS}
    for name in ('nout','tiles','k','wbase','xbase','obase'):
        d=f['me_d_'+name]; offset=dyn[d]
        if name=='tiles' and d==6: offset=(position>>(15-split))//3+1
        width=dict(FIELDS)[name]
        result[name]=(result[name]+offset)&((1<<width)-1)
    return result

class StageJournal:
    def __init__(self, image, owner, token, position):
        self.owner=owner; self.token=token; self.position=position
        self.words=[int(w,16) for w in image.decode().split()]
        self.expected=[pc for pc,w in enumerate(self.words) if decode_instruction(w)['unit'] in (I.UNIT_SU,I.UNIT_ME)]
        self.cursor=0; self.last_edge=-1; self.last_issue_edge=-1; self.demands={};self.tickets=set()
        self.issue_ticket={}
        self.producer=ProducerJoin(image,owner,position)
        self.issues=0
    def event(self,e):
        if e['owner']!=vars(self.owner): raise ValueError('actual owner identity')
        edge=e['edge']
        if type(edge) is not int or edge<self.last_edge: raise ValueError('monotonic source edge')
        self.last_edge=edge
        pc=e['pc']
        if type(pc) is not int or not 0<=pc<len(self.words): raise ValueError('source PC')
        if e['word_sha256']!=sha(f'{self.words[pc]:0256x}'.encode()): raise ValueError('exact instruction identity')
        if e['kind']=='accepted_issue':
            if self.cursor>=len(self.expected) or pc!=self.expected[self.cursor]: raise ValueError('accepted PC sequence')
            if type(e['core_issue']) is not int or e['core_issue']!=1 or type(e['ticket']) is not int or e['ticket']<0 or e['ticket'] in self.tickets or edge<=self.last_issue_edge: raise ValueError('real unique issue receipt')
            self.last_issue_edge=edge
            self.tickets.add(e['ticket']);self.issue_ticket[pc]=e['ticket'];self.cursor+=1;self.issues+=1
            f=decode_instruction(self.words[pc])
            if f['unit']==I.UNIT_ME:
                fields=me_fields(self.words[pc],self.token,self.position)
                if e['me_go']!=1 or e['fields']!=fields or e['ib379']!=instruction(fields): raise ValueError('DYN/379-bit acceptance')
                self.demands[pc]={'owner':vars(self.owner),'pc':pc,'ticket':e['ticket'],'edge':edge,'fields':fields,
                                  'kind':'KV_READ' if fields['wsrc'] else 'ROM_READ'}
            elif e['su_go']!=1: raise ValueError('source SU issue')
            elif pc in self.producer.expected: self.producer.issue(pc)
        elif e['kind']=='kv_lane_write':
            if e['accepted_lane_write']!=1 or e['ticket']!=self.issue_ticket.get(pc): raise ValueError('real lane acceptance/ticket required')
            self.producer.lane_write(pc,e['address'],e['fp32_bits'])
        else: raise ValueError('unknown journal event')
    def finish(self):
        if self.cursor!=len(self.expected): raise ValueError('incomplete accepted program')
        state=self.producer.state()
        return {'owner':vars(self.owner),'accepted_issues':self.issues,'ME_demands':list(self.demands.values()),
                'K_hex':state['K'].hex(),'V_hex':state['V'].hex(),
                'state_sha256':sha(state['K']+state['V'])}

def check(bundle,journal):
    if journal is None:
        return {'status':'BLOCKED_NO_ACTUAL_ACCEPTED_JOURNAL','actual_KV_state':None,'actual_ME_count':None,
                'RTL_admission':False,'physical_adoption':False}
    if bundle['su_width']!=1024 or bundle['ar_words']!=256 or bundle['TP']!=4 or bundle['groups']!=6144:
        raise ValueError('current source program dimensions')
    if any(sha((ROOT/p).read_bytes())!=v for p,v in bundle['source_sha256'].items()):
        raise ValueError('current source emitter identity')
    header=journal['header']
    if header['program_bundle_sha256']!=sha(json.dumps(bundle,sort_keys=True,separators=(',',':')).encode()):
        raise ValueError('source-owned bundle identity')
    if header['source_sha256']!=source_pins(): raise ValueError('current producer/decode source identity')
    if header['position']!=0: raise ValueError('only retained single position0 scope')
    if header['origin']!='actual_source_export' or (len(header['raw_trace_sha256'])!=64 or set(header['raw_trace_sha256'])-set('0123456789abcdef')):
        raise ValueError('actual source export provenance required')
    rows=journal['stages']
    if set(rows)!={f'L{l}/die{r}' for l in range(36) for r in range(4)}: raise ValueError('full36layer4rank journal')
    states={}
    for key,events in sorted(rows.items()):
        layer,rank=key.split('/');owner=Owner(header['user'],int(rank[3:]),int(layer[1:]),header['epoch'])
        image=decoded(bundle['stages'][key]['files']['program.hex'])
        gate=StageJournal(image,owner,header['token'],header['position'])
        for e in events: gate.event(e)
        states[key]=gate.finish()
    return {'status':'PASS_JOURNAL_CONSISTENCY_ONLY','source_provenance_independently_qualified':False,
            'RTL_admission':False,'physical_adoption':False,'states':states,
            'actual_ME_count':sum(len(s['ME_demands']) for s in states.values())}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--journal',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    bundle=json.loads(__import__('gzip').decompress(a.bundle.read_bytes())) if a.bundle.suffix=='.gz' else json.loads(a.bundle.read_text())
    result=check(bundle,json.loads(a.journal.read_text()) if a.journal else None)
    with a.out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
if __name__=='__main__':main()
