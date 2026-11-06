"""Actual compiler-byte round trips and causal dimension controls; no RTL run."""
import ast
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from layer_prog import native_csr_image as N


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,required=True)
    p.add_argument('--initializer',type=Path,required=True);p.add_argument('--decoder-source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    images=[];cases=[]
    for i in range(8):
        words=[int(x,16)for x in(a.input_dir/f'job{i}/host_boot.memh').read_text().split()]
        image=N.decode_image(words);assert N.encode_image(image)==words;images.append(image)
        cases.append(dict(case=f'actual_job{i}_byte_exact',passed=True,rows=image['nops'],templates=len(image['templates']),CF=len(image['CF']),HOST_words=len(words)))
    assert (images[0]['nops'],len(images[0]['CF']))==(128,63)
    def reject(name,f):
        try:f()
        except ValueError as e:cases.append(dict(case=name,passed=True,rejection=str(e)))
        else:raise AssertionError('accepted '+name)
    bad=copy.deepcopy(images[0]);bad['nops']=127
    reject('inconsistent_declared_rows',lambda:N.encode_image(bad))
    original=[int(x,16)for x in(a.input_dir/'job0/host_boot.memh').read_text().split()]
    reject('missing_row_part',lambda:N.decode_image(original[:2]+original[3:]))
    wrong=original.copy();wrong[1]^=1<<(9+33)
    reject('header_length_changed',lambda:N.decode_image(wrong))
    cfword=next(w for w in original if(w>>1)&255==0x14)
    reject('duplicate_actual_CF',lambda:N.decode_image(original+[cfword]))
    badcf=copy.deepcopy(images[0]);del badcf['CF'][next(iter(badcf['CF']))]
    reject('missing_decoded_CF',lambda:N.encode_image(badcf))
    badorder=copy.deepcopy(images[0]);badorder['order'].pop()
    reject('missing_template_or_CF_order_record',lambda:N.encode_image(badorder))
    changed=copy.deepcopy(images[0]);key=next(iter(changed['templates']));changed['templates'][key]^=1
    encoded=N.encode_image(changed);assert sum(x!=y for x,y in zip(encoded,original))==1
    assert N.decode_image(encoded)['templates'][key]==images[0]['templates'][key]^1
    cases.append(dict(case='template_field_controls_new_encoding',passed=True))
    reject('initializer_cannot_be_defaulted',lambda:N.with_initializer(images[0],[],lambda x:{}))
    # Use the existing production decoder body, without importing its unrelated
    # source-binding CLI dependencies in this serializer test.
    tree=ast.parse(a.decoder_source.read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='decode_initialization')
    env={};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(a.decoder_source),'exec'),env)
    init=[int(x,16)for x in a.initializer.read_text().split()]
    combined,receipt=N.with_initializer(images[0],init,env['decode_initialization'])
    assert combined==init+original and not receipt['lifetime_qualified']
    cases.append(dict(case='actual35_explicit_initializer_no_body_changes',passed=True,slots=len(receipt['config']['events'][0]['attributes'])))
    reject('incomplete_actual_MU_initializer',lambda:N.with_initializer(images[0],init[:-1],env['decode_initialization']))
    report=N.compatibility(images);assert not report['single_armed_RL_compatible'] and report['shared_KIT_row_done_only_lower_bound']==7163
    result=dict(verdict='PASS',cases=cases,compatibility=report,legacy104_entry_encoder_changed=False,
                actual_production_bootstrap_emitted=False,retiming_or_row_reindexing_performed=False,
                source_scope='generic byte serializer; existing104 entry encoder remains untouched',full_token=False)
    a.out.write_text(json.dumps(result,indent=2)+'\n');print('PASS',len(cases),'actual8 images plus dimension/initializer controls')


if __name__=='__main__':main()
