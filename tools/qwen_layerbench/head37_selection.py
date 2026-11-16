#!/usr/bin/env python3
"""Fail closed on one-sided HEAD37 selection or mismatched actual mask identity.

Validates source/configuration tuples, not physical adoption. A complete TT
parent must separately select the candidate calendar body before binding.
"""
import argparse,gzip,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'qwen_tokfunc/current_path'))
import table_roms as T
STAGE_SHA='03fa2dcff20b67032c63cf05f92f52454bc3d6bb9700d979a67f69038f482117'

def source(entry):
    p=Path(entry['source']);data=p.read_bytes()
    if hashlib.sha256(data).hexdigest()!=entry['source_sha256']:raise ValueError('selected source hash differs')
    m=re.search(r'^module '+re.escape(entry['master'])+r'\b.*?^endmodule\b',data.decode(),re.M|re.S)
    if not m:raise ValueError('selected master absent from source')
    return m[0]

def flag(entry,body):
    header=body.split(') (',1)[0]
    declared=re.findall(r'parameter\s+integer\s+HEAD_STAGE37\s*=\s*(\d+)',header)
    params=entry.get('parameters',{})
    if len(declared)>1:raise ValueError('ambiguous HEAD_STAGE37 declaration')
    if not declared:
        if params.get('HEAD_STAGE37',0):raise ValueError('selected source cannot accept HEAD_STAGE37 override')
        return 0
    if declared!=['0']:raise ValueError('candidate must remain default-off')
    value=params.get('HEAD_STAGE37',0)
    if type(value)is not int or value not in (0,1):raise ValueError('HEAD_STAGE37 must be literal0 or1')
    return value

def validate(selection,*,component_only=False,require_source_complete_tt_parent=False):
    if selection.get('schema')!='opentallas.qc-head37-selection.v1':raise ValueError('wrong selection schema')
    ct=selection['ctlm'];body=source(ct);cf=flag(ct,body)
    if cf:
        if ct['master']!='qfd_dv_cmd_cal_mu_head37' or 'HEAD_STAGE37 ? 6\'d37 : 6\'d36' not in body:
            raise ValueError('actual CTLM candidate must implement bounded LOCAL4 stage37 acceptance')
        if any(ct['parameters'].get(k)!=1 for k in ('CALENDAR_ROM','TABLE_ROM')):
            raise ValueError('HEAD37 requires actual CALR and LOCAL4 table-ROM mode')
    identity=json.loads(Path(selection['selected_identity']).read_text())
    loaders=selection['loaders'];actual={r['actual']for r in identity['loaders']}
    if {r['actual']for r in loaders}!=actual or len(loaders)!=12:
        raise ValueError('exact selected twelve loader instances required')
    flags=[]
    for row in loaders:
        if row['master']not in ('qfd_dv_s6_stm','qfd_dv_s6_stm_se0'):raise ValueError('unknown actual STM wrapper')
        s=source(row);f=flag(row,s);flags.append(f)
        if f and s.count('.HEAD_STAGE37(HEAD_STAGE37)')!=3:
            raise ValueError('actual STM wrapper does not forward HEAD_STAGE37 on every source profile branch')
    if any(f!=cf for f in flags):raise ValueError('one-sided stage37 acceptance: CTLM and all selected loaders must match')
    if cf:
        missing=set(['mask_receipt','masks','physical_assignment','native_window'])-set(selection)
        if missing:raise ValueError('stage37 selected without required mask identity: '+','.join(sorted(missing)))
        if any(d in selection.get('verilog_defines',[])for d in ('OT_S6_SIM','OT_QC_TLOADCAP')):
            raise ValueError('HEAD37 candidate only qualifies actual C0/LOCAL0 loader profile')
        rp=Path(selection['mask_receipt']);r=json.loads(rp.read_text())
        if r.get('stage_sha256')!=STAGE_SHA:raise ValueError('wrong genuine HEAD37 stage identity')
        expected={f'table_s{s}_m{k}.viamap.hex'for s in range(12)for k in range(4)}
        if set(r.get('images',{}))!=expected:raise ValueError('exact48 HEAD mask identities required')
        masks=Path(selection['masks'])
        for name,want in r['images'].items():
            p=masks/name
            data=p.read_bytes()if p.is_file()else gzip.decompress((masks/(name+'.gz')).read_bytes())
            if hashlib.sha256(data).hexdigest()!=want:raise ValueError(f'wrong or stale selected mask {name}')
        assignment=json.loads(Path(selection['physical_assignment']).read_text())
        T.validate_assignment(identity,assignment['assignments'],r['images'])
        witness=json.loads(Path(selection['native_window']).read_text())
        if witness.get('status')!='PASS_COMPONENT' or witness.get('exact_payload_checks')!=400:
            raise ValueError('native HEAD37 loader positive authority missing')
        if not component_only:
            if r.get('complete_transformer_programme')is not True:
                raise ValueError('global stage37 selection rejects partial masks: actual transformer stages1..36 are absent')
            import programme_store as P
            mp=Path(selection['complete_manifest']);full=json.loads(mp.read_text())
            if hashlib.sha256(mp.read_bytes()).hexdigest()!=r.get('manifest_sha256'):
                raise ValueError('complete source-table manifest identity differs')
            logical=P.logical_images(full,head_stage37=True)
            for sid,words in enumerate(logical):
                if not any(w&((1<<1024)-1)for w in words[:3816]):
                    raise ValueError('global selection rejects empty transformer prefix')
                for lane in range(4):
                    encoded=(''.join(f'{v:0532x}\n'for v in P.physical_rows(words,lane))).encode()
                    if hashlib.sha256(encoded).hexdigest()!=r['images'][f'table_s{sid}_m{lane}.viamap.hex']:
                        raise ValueError('global masks do not preserve the complete actual transformer manifest prefix')
            parent=selection.get('ctlm_parent')
            if not parent or not selection.get('source_complete_tt_parent_selected',False):
                raise ValueError('real source-complete TT parent selection is missing')
            pb=source(parent)
            if flag(parent,pb)!=1 or 'qfd_dv_cmd_cal_mu_head37'not in pb or '.HEAD_STAGE37(HEAD_STAGE37)'not in pb:
                raise ValueError('actual TT parent does not select the candidate stage37 calendar source')
            window=json.loads(Path(selection['loader_windows']).read_text())
            if window.get('status')!='COMPLETE_SOURCE_SELECTED_LOCAL4_WINDOWS' or window.get('unresolved'):
                raise ValueError('actual complete loader-window join is missing')
            if {(v['slice'],v['user'])for v in window['windows']}!={(x,u)for x in range(12)for u in range(4)}:
                raise ValueError('all48 source-selected per-user loader windows are required')
        if require_source_complete_tt_parent and not selection.get('source_complete_tt_parent_selected',False):
            raise ValueError('actual source-complete TT parent has not selected the candidate CTLM body')
    return dict(schema='opentallas.qc-head37-selection-verdict.v1',status='DEFAULTS_OFF_COMPATIBLE'if not cf else('COMPONENT_PAIR_AND_MASKS_VALID_NOT_INSTALLED'if component_only else'COMPLETE_SOURCE_SELECTION_VALID_NOT_INSTALLED'),
                component_only=component_only,
                HEAD_STAGE37=cf,loaders=12,numeric_TSLICE_changed=False,
                source_complete_tt_parent_selected=selection.get('source_complete_tt_parent_selected',False),
                global_enable=False,physical_adoption=False,
                scope='Candidate component tuple plus exact selected mask identity; actual complete-parent binding is separate')

def resolve(selection,base):
    import copy
    s=copy.deepcopy(selection)
    for e in [s['ctlm']]+s['loaders']:
        if not Path(e['source']).is_absolute():e['source']=str((base/e['source']).resolve())
    for k in ['selected_identity','mask_receipt','masks','physical_assignment','native_window','complete_manifest','loader_windows']:
        if k in s and not Path(s[k]).is_absolute():s[k]=str((base/s[k]).resolve())
    return s

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--selection',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--require-source-complete-tt-parent',action='store_true');ap.add_argument('--component-only',action='store_true',help='explicit partial coupon mode; never global activation')
    a=ap.parse_args();r=validate(resolve(json.loads(a.selection.read_text()),a.selection.parent),component_only=a.component_only,require_source_complete_tt_parent=a.require_source_complete_tt_parent)
    a.out.write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
if __name__=='__main__':main()
