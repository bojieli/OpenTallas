#!/usr/bin/env python3
"""Freeze actual component RTL and canonical source lists for native join lint.

Private composite snapshot only; publisher adoption and physical/native proof
are separate. Exact source revisions and every input byte hash are retained.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from qwen_split.native_compute_join import ROOT,NODES

BASE='96f30a6a0'

def read(ref,path):
    return subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT)


def main():
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    paths=[]
    for f in('embedding_stage.f','su_static_math.f'):
        paths += read(BASE,'tools/qwen_split/'+f).decode().splitlines()
    paths += [v[1]for v in NODES.values()]
    paths += ['rtl/qwen_sys/static_schedule_20261014/'+s+'.sv'for s in(
       'ot_qfd_tt_ctlm_static_parent','ot_qfd_native_cmd_route','ot_qwen_tp8_rom_relocate','ot_qfd_tt_ctl_static')]
    paths += ['rtl/hdc/ot_qwen_me_spine_h_w12.sv','rtl/hdc/ot_qwen_w12_matvec.sv','rtl/hdc/ot_qwen_w12_arith.sv']
    paths += ['rtl/qwen_sys/dvm_20261014/'+s+'.sv'for s in('ot_qfd_xpf_dense_pw_loader','ot_qfd_xpf_static_schedule')]
    paths += ['rtl/qwen_split/'+s+'.sv'for s in('qfd_native59_q_export_control','qfd_native59_command_context','qfd_native59_static_service','qfd_native59_record_endpoint','qfd_kvn_static_transport')]
    paths += ['rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv','rtl/qwen_sys/vm_nox_20261014/qfd_vm_attention_commit_fence.sv','rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv']
    text=read('8d92a8870','tools/qwen_coll_tp8_static_links_bench.py').decode()
    block=text[text.index('SRC = '):text.index('RES = ')]
    io_paths=re.findall(r'"((?:rtl|physical)/[^\"]+\.(?:sv|v))"',block)
    paths += io_paths
    override={path:ref for top,path,ref in NODES.values()}
    for path in io_paths:override.setdefault(path,'8d92a8870')
    # Shared actual math source comes from the selected native compute profile;
    # avoid changing it merely because the IO proof used the same helper name.
    for path in io_paths:
        if path.startswith('rtl/hdc/'):override[path]=BASE
    main_ref=subprocess.check_output(['git','rev-parse','origin/main'],cwd=ROOT,text=True).strip()
    for path in ('rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv','rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv'):
        override[path]=main_ref
    manifest={};files=[];module_defs={}
    for path in dict.fromkeys(paths):
        if not path.strip()or'/tb_'in path or path.startswith('rtl/test/'):continue
        ref=override.get(path,BASE);data=read(ref,path)
        # Physical macro source lists contain two equivalent catalog copies.
        # One module definition is enough; require identical source semantics.
        mods=re.findall(rb'^\s*module\s+(\w+)',data,re.M)
        if len(mods)==1 and mods[0]in module_defs:
            old_path,old_data=module_defs[mods[0]]
            def norm(raw):
                s=raw.decode();s=re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S)
                return re.sub(r'\s+','',s)
            if norm(old_data)!=norm(data):raise ValueError(f'nonidentical duplicate module {mods[0]}: {old_path}, {path}')
            manifest[path]=dict(ref=ref,sha256=hashlib.sha256(data).hexdigest(),equivalent_module_source=old_path);continue
        for name in mods:module_defs[name]=(path,data)
        target=a.out/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        manifest[path]=dict(ref=ref,sha256=hashlib.sha256(data).hexdigest());files.append(path)
    # Keep include headers at their actual source paths.
    tree=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'rtl/hdc'],cwd=ROOT,text=True)
    for path in tree.splitlines():
        if path.endswith(('.vh','.svh')):
            data=read(BASE,path);target=a.out/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            manifest[path]=dict(ref=BASE,sha256=hashlib.sha256(data).hexdigest())
    rtl='rtl/qwen_split/qfd_native_compute_join.sv';data=(ROOT/rtl).read_bytes();target=a.out/rtl;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);files.append(rtl)
    manifest[rtl]=dict(ref='local_committed_join',sha256=hashlib.sha256(data).hexdigest())
    (a.out/'native_join.f').write_text('\n'.join(files)+'\n')
    (a.out/'source.json').write_text(json.dumps(dict(scope='actual full RTL composite for elaboration only',qualified=False,sources=manifest),indent=2)+'\n')
    print(json.dumps(dict(files=len(files),source_entries=len(manifest),path=str(a.out))))
if __name__=='__main__':main()
