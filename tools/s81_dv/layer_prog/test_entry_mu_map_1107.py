"""Finite native CSR codec tests; no production event map or HWIN RTL claim."""
from copy import deepcopy
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/s81_dv'))
from layer_prog import entry_page_protocol as E
from layer_prog.native_mu_calendar import decode_initialization


def exercise():
    r=ROOT/'results/token_pass/native_mu_map_1107'
    timing=json.loads((r/'codec_timing.json').read_text())
    fixture=json.loads((r/'codec_fixture.json').read_text())
    edges=timing['masters']['dsdv_hostb_seqhost_mux']['edges']
    old=E.mu_boot_config(152,72,edges)
    old['launch']=fixture['launch']
    words,report=E.compile_boot(old,timing)
    # Independent literal legacy CSR sequence, including disabled replay on
    # both slots. The unchanged default must preserve every one of35 words.
    payload=[(0x15,(1<<25)|152),(0x15,(1<<25)|152),(0x15,(1<<25)|(1<<24)|79)]
    for i in range(8):
        payload.extend([(0x16,(1<<25)|i|(1<<8)),(0x16,(1<<25)|(1<<21)|(4+i)),
                        (0x16,(1<<25)|(2<<21)),(0x16,(1<<25)|(2<<21)|1)])
    assert words==[((op|(data<<32))<<1)|1 for op,data in payload]
    assert report['words']==35 and report['slots']==2
    passed=[]
    for explicit in (False,True):
        cfg=deepcopy(fixture)
        cfg['slot_gaps']=[152]*47 if explicit else [152]
        for i,event in enumerate(cfg['events']):
            event['delay']=49+i
            event['attributes']=[dict(ab=s%2,land=(s+i)%2)for s in range(47)]
        cfg=E.mu_boot_config(152,72,edges,cfg)
        encoded,emission=E.compile_boot(cfg,timing)
        decoded=decode_initialization(encoded)
        assert decoded=={k:cfg[k]for k in ('schema','slot_gaps','return_latency','events')}
        assert emission['words']==(440 if explicit else 394)
        # Exercise the real page decoder with an explicit full-width CSR map.
        page=dict(stage=0,start_phase=0,templates=[],local_mux_config=cfg,
                  MU_initialized_in_this_page=True,rows=[dict(row76=f'{i:019x}')for i in range(104)])
        suffix=[E.D.csr_len(104),E.D.csr_pw(0,E.D.pw_header(104,0,0))]
        for i,row in enumerate(page['rows']):suffix.extend(E.D.csr_pw(a,d)for a,d in E.D.pw_row_words(i,int(row['row76'],16)))
        suffix.append(E.D.csr_pw(0,E.D.pw_header(104,0,0,seal=True)))
        E.decode_check(page,encoded+suffix)
        try:E.decode_check(page,encoded[:35]+suffix)
        except ValueError:pass
        else:raise AssertionError('accepted obsolete35-word initialization prefix')
        mutations=[]
        for name,change in [('missing_attribute',lambda x:x['events'][0]['attributes'].pop()),
                            ('bad_copy',lambda x:x['events'][0]['attributes'][0].update(ab=2)),
                            ('wrong_return',lambda x:x.update(return_latency=80)),
                            ('nonuniform_gap',lambda x:x.update(slot_gaps=[152,156]))]:
            bad=deepcopy(cfg);change(bad)
            try:E.compile_boot(E.mu_boot_config(152,72,edges,bad),timing)
            except ValueError:mutations.append(name)
            else:raise AssertionError('accepted '+name)
        # Duplicate an encoded slot index: actual decoder must reject it.
        bad=list(encoded);first_attr=len(cfg['slot_gaps'])+3
        bad[first_attr+1]=bad[first_attr]
        try:decode_initialization(bad)
        except ValueError:mutations.append('duplicate_encoded_slot')
        else:raise AssertionError('accepted duplicate encoded slot')
        bad=list(encoded);bad[first_attr]^=1<<43
        try:E.decode_check(page,bad+suffix)
        except ValueError:mutations.append('wrong_valid_copy_map')
        else:raise AssertionError('accepted a different valid copy map')
        passed.append(dict(explicit47_gaps=explicit,words=len(encoded),slots=emission['slots'],
                           roundtrip=True,old_prefix_rejected=True,mutants_rejected=mutations))
    return dict(legacy35_bytes_unchanged=True,cases=passed,scope='CSR encoding/decoding only; explicit nonproduction fixture maps; no HWIN RTL/global booking qualification')


if __name__=='__main__':print(json.dumps(exercise(),indent=2))
