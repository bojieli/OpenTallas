#!/usr/bin/env python3
"""Fail closed on one-sided HEAD37 selection or mismatched actual mask identity.

Validates source/configuration tuples, not physical adoption. A complete TT
parent must separately select the candidate calendar body before binding.
"""
import argparse,gzip,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'qwen_tokfunc/current_path'))
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

def validate_tt_parent(selection,ct,parent):
    chain=selection.get('ctlm_parent_chain')
    if chain:
        if chain[0]!=parent:raise ValueError('actual TT root differs from source-complete parent chain')
        if [e['master']for e in chain]!=['qfd_tt_ctlm_dv_lpf_hp13_lp','qfd_tt_ctlm_dv_gi_hp13']:
            raise ValueError('unknown actual frozen TT frontend chain')
        raw=Path(selection['tt_frontend_receipt']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=selection.get('tt_frontend_receipt_sha256'):
            raise ValueError('actual frozen TT frontend receipt identity differs')
        fr=json.loads(raw)
        if fr.get('CALREG')!=1 or fr.get('HEAD_STAGE37_default')!=0 or fr.get('default_off_source_delta_reversible')is not True:
            raise ValueError('actual TT source successor changed frozen CALREG1/default-off contract')
        expected={v['path']:v['candidate_sha256']for v in fr['files']}
        for entry,child in zip(chain,[chain[1]['master'],ct['master']]):
            pb=source(entry)
            if flag(entry,pb)!=1 or not re.search(r'\b'+re.escape(child)+r'\s*#\(',pb) or '.HEAD_STAGE37(HEAD_STAGE37)'not in pb:
                raise ValueError('actual TT source chain does not propagate stage37 to its selected child')
        for entry in chain+[ct]:
            if expected.get(entry.get('source_relative'))!=entry['source_sha256']:
                raise ValueError('TT chain source is not from the exact reconstructed frozen frontend')
        if ct['master']!='qfd_dv_cmd_cal_mu' or ct['parameters'].get('CALREG')!=1:
            raise ValueError('actual frozen TT chain requires its CALREG1 FQREG cal alias')
    else:
        pb=source(parent)
        if flag(parent,pb)!=1 or 'qfd_dv_cmd_cal_mu_head37'not in pb or '.HEAD_STAGE37(HEAD_STAGE37)'not in pb:
            raise ValueError('actual TT parent does not select the candidate stage37 calendar source')

def validate(selection,*,component_only=False,require_source_complete_tt_parent=False):
    import table_roms as T
    if selection.get('schema')!='opentallas.qc-head37-selection.v1':raise ValueError('wrong selection schema')
    ct=selection['ctlm'];body=source(ct);cf=flag(ct,body)
    if cf:
        if ct['master']not in ('qfd_dv_cmd_cal_mu_head37','qfd_dv_cmd_cal_mu') or 'HEAD_STAGE37 ? 6\'d37 : 6\'d36' not in body:
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
            validate_tt_parent(selection,ct,parent)
            import head37_windows
            wp=Path(selection['loader_windows'])
            window=json.loads(wp.read_text())
            if window.get('table_mask_receipt_sha256')!=hashlib.sha256(rp.read_bytes()).hexdigest():
                raise ValueError('loader windows do not select the actual complete table-mask receipt')
            head37_windows.load(wp,require_all=True)
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
    for e in [s['ctlm']]+s['loaders']+([s['ctlm_parent']]if 'ctlm_parent'in s else[])+s.get('ctlm_parent_chain',[]):
        if not Path(e['source']).is_absolute():e['source']=str((base/e['source']).resolve())
    for k in ['selected_identity','mask_receipt','masks','physical_assignment','native_window','complete_manifest','loader_windows','tt_frontend_receipt']:
        if k in s and not Path(s[k]).is_absolute():s[k]=str((base/s[k]).resolve())
    return s

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--selection',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--require-source-complete-tt-parent',action='store_true');ap.add_argument('--component-only',action='store_true',help='explicit partial coupon mode; never global activation')
    a=ap.parse_args();r=validate(resolve(json.loads(a.selection.read_text()),a.selection.parent),component_only=a.component_only,require_source_complete_tt_parent=a.require_source_complete_tt_parent)
    a.out.write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
if __name__=='__main__':main()
