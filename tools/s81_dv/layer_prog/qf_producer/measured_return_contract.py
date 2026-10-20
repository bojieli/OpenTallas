#!/usr/bin/env python3
"""Bounded replay of genuine measured frame returns; no generated Q values.

Frame RET times are kept as a relative calendar, NOT selected die ARR times.
The missing native link phase prevents a production source calendar claim.
"""
import argparse, hashlib, json, re
from pathlib import Path
from head_local_contract import ROOT, retag_return, config
from cap_model import model

def main():
    p=argparse.ArgumentParser();p.add_argument('--trace',required=True);p.add_argument('--meta',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();trace=Path(a.trace).read_text();meta=json.loads(Path(a.meta).read_text())
    assert re.search(r'END .*ret_words=8 .*fault=0(?: |\n)',trace)
    lane={}
    for edge,he in re.findall(r'^RET (\d+) ([0-9a-f]+)$',trace,re.M):
        w=int(he,16);assert w&1
        tag=(w>>1)&0xffffffff;d=(w>>33)&0xffffffff;err=(w>>65)&1
        dim=((tag>>13)&0x3fff)
        assert dim in range(6) and not err
        lane[int(edge)]=(retag_return(tag,head=0,dimension=dim),d,err,[f'actual_RET_{edge}'])
    assert len(lane)==8
    cfg=config(0,row_flags=1)
    def run(l,cfgs):return model([l]+[{} for _ in range(7)],cfgs)
    res=run(lane,[(0,cfg)])
    assert not res['faults'],res['faults']
    assert len(res['writes'])==6
    for wr in res['writes']:
        dim=wr[5]&0x3fff
        assert wr[4]==int(meta['rows'][str(dim)]['bf16'])<<16,(dim,wr)
    missing=dict(lane);missing.pop(min(missing))
    m=run(missing,[(0,cfg)])
    assert m['faults'] or len(m['writes'])!=6
    bad=run(lane,[(0,config(0,row_flags=0))]);assert any(f[0]=='F9' for f in bad['faults'])
    # cfg while the observed row2 partial is held; derive from actual event source,
    # not a new production timing profile. Tree depth three: ARR+1+3*13.
    busy_cfg=min(lane)+1+3*13+1
    b=run(lane,[(0,cfg),(busy_cfg,cfg)])
    assert any(f[0]=='F11' for f in b['faults']),b['faults']
    rec=dict(schema='opentallas.s81.measured_wqb_return_contract.v1',
      source_files={s:hashlib.sha256(Path(s).read_bytes()).hexdigest() for s in [a.trace,a.meta]},
      actual_numeric_trace=True,frame='u_f_0L00',semantic_rows=6,ret_words=8,
      measured_frame_edges=[min(lane),max(lane)],relative_cap_write_edges=[min(w[0] for w in res['writes']),max(w[0] for w in res['writes'])],
      writes=res['writes'],faults=res['faults'],original_bf16_gold_rows_equal=6,
      causal_missing_payload_rejected=True,causal_wrong_flag_rejected=True,
      causal_cfg_while_partial_open_rejected=True,cfg_busy_edge=busy_cfg,
      source_tag_flags_preserved=True,production_binding_changed=False,
      selected_die_arr_edges=None,selected_capture_clock_phase=None,
      actual_122_frame_calendar=None,actual_retire_deadline=None,
      qualification='ONE_MEASURED_FRAME_RELATIVE_CAP_MODEL_ONLY; not selected source/calendar/token proof')
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);(out/'measured_return_contract.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('MEASURED_RETURN_MODEL_PASS actual_words8 rows6 gold6 missing/flag/open_cfg_rejected; selected ARR/RETIRE UNPROVED')
if __name__=='__main__':main()
