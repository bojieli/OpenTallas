"""Native CAP/XR images preserve exact selected ranges and refuse missing source authority."""
import copy
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import final_ffn as F
from capture_payload_images import payload_files, checked_word

COUNTS=[107,107,53,53,107,107,53,53,53,53,107,107,53,53,107,107]

def source():
    spans=[];start=0
    for count in COUNTS:spans.append((start,count));start+=count
    phases=[]
    for chunk in range(2):
        slices=[]
        for sid,(start,count)in enumerate(spans):
            cfg=F.capture(0,sid,6,spans=spans,capture_only=True)
            tags=list(range(start+64*chunk,start+min(64*(chunk+1),count)))
            slices.append(dict(slice_index=sid,cfg=cfg,cfg_d=f'{checked_word(cfg):040x}',frame_tags={'0':tags}))
        phases.append(dict(phase=chunk+1,op='ffn.down',mat='shared.w2',chunk=chunk,slices=slices))
    return dict(layer='L0',capture_only={'enabled':True},faults=0,phases=phases,
                bound_source={'netlist_sha256':'a'*64},pairing_slot_collisions=[]), dict(
                layer='L0',op='ffn.down',nphases=2,phases=[dict(phase=71,tag=0),dict(phase=72,tag=2)])

def test_native_words_payloads_and_phase_mapping_are_complete():
    rec,cal=source();files=payload_files(rec,cal)
    manifest=json.loads(files['manifest.json'])
    assert len(files)==49 and manifest['total_descriptors']==32
    assert manifest['issue_epoch'] is None and not manifest['install_admitted']
    for sid in range(16):
        cfg=[int(x,16)for x in files[f's{sid:02d}/cfg_d.hex'].split()]
        ctl=[int(x,16)for x in files[f's{sid:02d}/ctl_payload.hex'].split()]
        beat=[int(x,16)for x in files[f's{sid:02d}/line_ctl.hex'].split()]
        for i in range(2):
            assert ctl[i]&65535==1<<sid
            assert (ctl[i]>>16)&31==3 and (ctl[i]>>21)&31==0
            assert ctl[i]>>26==cfg[i] and ctl[i]<1<<186
            assert beat[i]>>21==ctl[i] and beat[i]&1 and (beat[i]>>1)&7==0
        rows=manifest['source_phase_rows'][str(sid)]
        assert [r['field_phase']for r in rows]==[71,72]
        assert all(r['issue_cycle']is None for r in rows)

@pytest.mark.parametrize('mutation',['word','rank','missing_tag','source','calendar','phase','slots'])
def test_incoherent_inputs_refused(mutation):
    rec,cal=source()
    if mutation=='word':rec['phases'][0]['slices'][0]['cfg_d']='0'*40
    elif mutation=='rank':rec['phases'][0]['slices'][0]['frame_tags']['0'][0]=1279
    elif mutation=='missing_tag':rec['phases'][0]['slices'][0]['frame_tags']['0'].pop()
    elif mutation=='source':rec['bound_source']={}
    elif mutation=='calendar':cal['op']='ffn.router'
    elif mutation=='phase':cal['phases'][1]['phase']=71
    elif mutation=='slots':rec['pairing_slot_collisions']=[{'phase':1}]
    with pytest.raises(ValueError):payload_files(rec,cal)
