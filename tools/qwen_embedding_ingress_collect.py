#!/usr/bin/env python3
"""Export a qualified ingress island with source hashes bound before/after export.
Run on the host containing the original completed ORFS job. Output is immutable.
"""
import argparse,json,shutil,subprocess,math
from pathlib import Path
from qwen_embedding_parent_binding import sha,qualify,alias_bytes,APPROVED_TOPS
ROOT=Path(__file__).resolve().parents[1]


def collect(kind,state_path,out,source_top):
    state=json.loads(state_path.read_text());spec=state['spec'];source=spec['source']['commit']
    if source_top not in APPROVED_TOPS:
        raise ValueError('unapproved source top')
    if spec['block'] not in ('qfd_embed_ingress_'+kind, 'qfd_embed_ingress_'+kind+'_padded') or state.get('commit_full')!=source:
        raise ValueError('wrong component or unresolved source pin')
    benches=state.get('benches',{})
    if not spec['stages']['bench']:
        raise ValueError('nonempty exactness inventory required')
    for bench in spec['stages']['bench']:
        result=benches.get('bench_'+bench['name'])
        if not result or result.get('ok') is not True:raise ValueError('incomplete exactness: '+bench['name'])
    if state['metrics'].get('drc')!=0 or not state.get('checks',{}).get('physical_metadata_storage',{}).get('ok'):
        raise ValueError('DRC/storage qualification missing')
    corner_path=Path(state['metrics']['corner_sta'][0]);corner=json.loads(corner_path.read_text())
    for key in ('setup_ss','hold_ff'):
        slack=corner[key].get('worst_slack_ps')
        if not isinstance(slack,(int,float)) or not math.isfinite(slack) or slack<15 or corner[key].get('errors'):raise ValueError('fresh corner fails15ps: '+key)
    orfs=Path(state['metrics']['orfs_dir']);bases=list((orfs/'results/asap7').glob('*/base'))
    if len(bases)!=1:raise ValueError('ambiguous ORFS design')
    physical={key:sha(bases[0]/filename) for key,filename in [('odb_sha256','6_final.odb'),('spef_sha256','6_final.spef'),('sdc_sha256','6_final.sdc')]}
    if any(corner[c][k]!=v for c in ('setup_ss','hold_ff') for k,v in physical.items()):raise ValueError('physical artifacts changed since fresh STA')
    synthesis_path=corner_path.parent/'metadata_storage_synthesis.json'
    routed_path=corner_path.parent/'metadata_storage.json'
    routed=json.loads(routed_path.read_text())
    synthesis=None
    if source_top=='ot_qwen_embedding_ingress_padded':
        synthesis=json.loads(synthesis_path.read_text())
        for record,filename in ((routed,'6_final.v'),(synthesis,'1_2_yosys.v')):
            if record.get('verdict')!='PASS' or record.get('netlist_sha256')!=sha(bases[0]/filename):
                raise ValueError('full-shape pad topology not bound to actual netlist: '+filename)
        if routed.get('input_padding')!=synthesis.get('input_padding'):
            raise ValueError('fixed pad topology changed after synthesis')
    if out.exists():raise ValueError('refusing to overwrite collected evidence')
    out.mkdir(parents=True);view=out/('qfd_embed_ingress_'+kind);view.mkdir();receipt=out/'receipt';receipt.mkdir()
    shutil.copyfile(ROOT/'physical/qwen_embedding_parent/island_interface.sdc',view/'interface.sdc')
    subprocess.run(['python3',str(ROOT/'tools/hbm_fmax_attn_abstract.py'),'--orfs-dir',str(orfs),'--name',view.name,'--out',str(view),'--image','openroad/orfs:asap7lock','--interface-sdc',str(view/'interface.sdc')],check=True)
    after={key:sha(bases[0]/filename) for key,filename in [('odb_sha256','6_final.odb'),('spef_sha256','6_final.spef'),('sdc_sha256','6_final.sdc')]}
    if after!=physical:raise ValueError('physical artifacts changed during export')
    abstract=json.loads((view/'abstract.json').read_text());abstract['source_artifacts']=physical;abstract['source_commit']=source
    raw=view/'export_original';raw.mkdir()
    original_hashes={}
    for suffix in ('.lef','_ss.lib','_ff.lib'):
        path=view/(view.name+suffix)
        shutil.copyfile(path,raw/path.name)
        original_hashes[path.name]=sha(path)
        path.write_bytes(alias_bytes(path.read_bytes(),suffix,source_top,view.name))
        abstract['files'][path.name]=sha(path)
    abstract['identifier_alias']=dict(source_top=source_top,target_top=view.name,original_sha256=original_hashes)
    (view/'abstract.json').write_text(json.dumps(abstract,indent=2)+'\n')
    shutil.copyfile(corner_path,receipt/'corner_sta.json');shutil.copyfile(corner_path.parent/'metadata_storage.json',receipt/'metadata_storage.json')
    for c in ('ss','ff'):shutil.copyfile(orfs/f'w18_sta_{c}.log',receipt/f'w18_sta_{c}.log')
    if synthesis is not None:shutil.copyfile(synthesis_path,receipt/'metadata_storage_synthesis.json')
    (receipt/'qualification.json').write_text(json.dumps(dict(source_commit=source,drc=0,exactness_pass=True,
        corner_sta_sha256=sha(receipt/'corner_sta.json'),metadata_storage_sha256=sha(receipt/'metadata_storage.json'),
        job_state_sha256=sha(state_path),bench_results=benches,
        routed_netlist_sha256=sha(bases[0]/'6_final.v'),
        synthesis_netlist_sha256=sha(bases[0]/'1_2_yosys.v'),
        metadata_storage_synthesis_sha256=sha(receipt/'metadata_storage_synthesis.json') if synthesis is not None else None),indent=2)+'\n')
    bound=qualify(kind,view,receipt,source)
    (out/'binding.json').write_text(json.dumps(bound,indent=2)+'\n')
    (out/'clock_reference.tcl').write_text(f"set embedding_ref_internal_setup_ps {bound['setup_internal_clock_ps']:.9f}\nset embedding_ref_internal_hold_ps {bound['hold_internal_clock_ps']:.9f}\n")
    print('PASS immutable ingress export and parent clock binding: '+str(out))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=['code','scale'],required=True);p.add_argument('--job-state',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--source-top',choices=APPROVED_TOPS,required=True);a=p.parse_args();collect(a.kind,a.job_state,a.out,a.source_top)
