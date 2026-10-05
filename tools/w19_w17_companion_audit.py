#!/usr/bin/env python3
"""Compose W17 companions in a private index; audit W19 imports and regressions.

Never checks out main, edits a live source tree, or invokes engine builds. Only
source files needed for admission/source-list regressions are exported. PASS is
source composition and software regression evidence, not full-runtime evidence.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def git(*args,env=None):
    return subprocess.check_output(['git',*args],cwd=ROOT,env=env)


def sha(data):return hashlib.sha256(data).hexdigest()


def definitions(data,names):
    tree=ast.parse(data)
    nodes={n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    globals_ast=ast.dump(ast.Module(body=[n for n in tree.body if not isinstance(n,(ast.FunctionDef,ast.ClassDef))],type_ignores=[]),include_attributes=False)
    return {n:nodes[n] for n in names},globals_ast


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-pin',default='HEAD',help='Immutable source base; main may be audited without checkout')
    ap.add_argument('--w17-pin',default='a7ee63c37')
    ap.add_argument('--w17-base',default='b93ee074')
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--record',type=Path,required=True)
    a=ap.parse_args()
    if a.record.exists():raise SystemExit('Refusing to overwrite companion audit evidence')
    a.work.mkdir(parents=True,exist_ok=True)
    source=git('rev-parse',a.source_pin+'^{commit}').decode().strip()
    parent=git('rev-parse','main').decode().strip()
    pin=git('rev-parse',a.w17_pin+'^{commit}').decode().strip()
    base=git('rev-parse',a.w17_base+'^{commit}').decode().strip()
    patch=git('diff','--binary',base,pin)
    (a.work/'w17.patch').write_bytes(patch)
    with tempfile.TemporaryDirectory(prefix='w19-w17-index-') as temp:
        env=dict(os.environ,GIT_INDEX_FILE=str(Path(temp)/'index'))
        git('read-tree',source,env=env)
        checked=(subprocess.run(['git','apply','--cached','--check','-'],cwd=ROOT,env=env,input=patch,capture_output=True)
                 if patch else subprocess.CompletedProcess([],0,b'',b''))
        if checked.returncode:
            (a.work/'apply.log').write_bytes(checked.stdout+checked.stderr)
            a.record.write_text(json.dumps(dict(status='fail',source_commit=source,w17_pin=pin,patch_sha256=sha(patch),
                reason='Private-index composition failed; no runtime or main edits'),indent=2)+'\n')
            return 1
        if patch: subprocess.run(['git','apply','--cached','-'],cwd=ROOT,env=env,input=patch,check=True)
        tree=git('write-tree',env=env).decode().strip()
        paths=git('ls-files',env=env).decode().splitlines()
        export=a.work/'composed-source';export.mkdir()
        selected=[p for p in paths if p.startswith(('tools/','rtl/')) or
                  (p.startswith('physical/asap7_memory_macros/') and p.endswith(('.v','.sv','.vh','.svh'))) or
                  p=='results/rtl/v41_attention_elaboration_archive/tools/v41_attention_hierarchy.vlt']
        # Batch cat-file avoids one git process per source file and any checkout.
        query=''.join(':'+p+'\n' for p in selected).encode()
        data=subprocess.check_output(['git','cat-file','--batch'],input=query,cwd=ROOT,env=env)
        pos=0;size=0;export_hashes={}
        for p in selected:
            end=data.index(b'\n',pos);head=data[pos:end].decode().split();length=int(head[2]);pos=end+1
            blob=data[pos:pos+length];pos+=length+1
            dest=export/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(blob)
            export_hashes[p]=sha(blob);size+=length
        imports={}
        required=['tools/rtl_v41_fullshape_layer_campaign.py','tools/w19_sm_real_ops.py',
                  'tools/rtl_gpu_sm_exact.py','tools/hdc_golden.py','tools/hdc_golden_v41.py',
                  'rtl/hdc/kv/ot_hdc_hbm_model.sv','rtl/gpu/ot_gpu_payload_assemble.sv']
        for p in required:
            original=git('show',source+':'+p)
            composed=(export/p).read_bytes()
            if original!=composed:raise SystemExit('Companions unexpectedly changed W19 prerequisite: '+p)
            entry=dict(w19_sha256=sha(original),composed_sha256=sha(composed),unchanged_in_composition=True)
            try:other=git('show',pin+':'+p)
            except subprocess.CalledProcessError:other=None
            entry['w17_snapshot_sha256']=sha(other) if other is not None else None
            entry['w17_snapshot_identical']=other==original
            if p.endswith('layer_campaign.py'):
                b,g=definitions(original,['Checkpoint','LazyWeights','build_model']);o,og=definitions(other,list(b))
                entry.update(required_definitions_identical=b==o,module_globals_imports_identical=g==og)
                parent_blob=git('show',parent+':'+p)
                pd,pg=definitions(parent_blob,list(b))
                entry.update(reviewed_main_sha256=sha(parent_blob),main_required_definitions_identical=pd==b,
                             main_module_globals_imports_identical=pg==g)
            imports[p]=entry
        regressions=[]
        for test in ('tools/test_w17_runtime_integration.py','tools/test_w17_l20_build_gate.py'):
            run=subprocess.run(['python3',str(export/test),'-v'],cwd=export,capture_output=True,text=True,timeout=60)
            log=a.work/(Path(test).stem+'.log');log.write_text(run.stdout+run.stderr)
            regressions.append(dict(test=test,source_sha256=export_hashes[test],returncode=run.returncode,
                                    log_sha256=sha(log.read_bytes())))
        status='pass' if all(r['returncode']==0 for r in regressions) else 'fail'
        result=dict(schema='opentallas.w19.w17_companion_audit.v1',status=status,source_commit=source,
                    reviewed_main_commit=parent,w17_pin=pin,w17_base=base,private_tree=tree,patch_sha256=sha(patch),
                    exported_source_bytes=size,exported_source_files=len(selected),imports=imports,regressions=regressions,
                    auditor_source_commit=git('rev-parse','HEAD').decode().strip(),
                    auditor_sha256=sha(Path(__file__).read_bytes()),
                    w19_helper_caveat=('W17 snapshot predates W19 sim_runner injection; compose only its diff, preserving the W19 helper.'
                        if not imports['tools/w19_sm_real_ops.py']['w17_snapshot_identical']
                        else 'This W17 snapshot already contains the identical W19 helper.'),
                    claim_boundary='Private-index W19 + recovered W17 companion source composition, importer AST comparison, W17 admission/source-list regressions only; no engine builds, 96-rank runtime or physical qualification.')
        a.record.write_text(json.dumps(result,indent=2)+'\n')
        print(status,tree,regressions,flush=True)
    return 0 if status=='pass' else 1

if __name__=='__main__':raise SystemExit(main())
