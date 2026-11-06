"""Exact releases never expand to active, qualified, or unique source artifacts."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess

SPEC=importlib.util.spec_from_file_location('released_reaper',Path(__file__).with_name('ot-reaper.py'))
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)

def worker(tmp_path):
    tree=ast.parse(M.RELEASED_HOST_PY)
    definitions=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef,ast.Assign)) and not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='headroom' for t in n.targets))]
    ns=dict(os=os,json=json,re=re,stat=stat,subprocess=subprocess,hashlib=hashlib,A={'refs':[]},BLOB='',DRY=False,procs=lambda:'',rm=lambda p,d:os.unlink(p))
    exec(compile(ast.Module(body=definitions,type_ignores=[]),'<released-host>','exec'),ns)
    ns['SAFE_RELEASE_ROOTS']=(str(tmp_path)+'/',)
    return ns

def release(tmp_path):
    root=tmp_path/'lane'/'obj';root.mkdir(parents=True)
    source=root/'Vold.cpp';source.write_text('// Verilated generated cache')
    header=root/'Vneeded.h';header.write_text('DPI header retained')
    s=source.stat()
    return source,header,dict(id='sample',path=str(root),kind='generated-cache',creator_release='creator terminal job release',released_suffixes=['.cpp'],files=[dict(path=str(source),bytes=s.st_size,inode=s.st_ino,mtime_ns=s.st_mtime_ns)])

def test_exact_release_is_idempotent_and_keeps_needed_header(tmp_path):
    ns=worker(tmp_path);source,header,row=release(tmp_path)
    assert ns['apply_release'](row)['status']=='APPLIED'
    assert not source.exists() and header.read_text()=='DPI header retained'
    assert ns['apply_release'](row)['status']=='ALREADY_REMOVED'

def test_fresh_live_reference_at_unlink_preserves_batch(tmp_path):
    ns=worker(tmp_path);source,_,row=release(tmp_path)
    def newly_live():
        ns['A']['refs']=[str(source)]
        return ''
    ns['procs']=newly_live
    result=ns['apply_release'](row)
    assert result['status']=='SKIP' and 'live/reference' in result['reason'] and source.exists()

def test_qualified_and_keep_states_are_protected(tmp_path):
    ns=worker(tmp_path);source,_,row=release(tmp_path)
    signoff=source.parent.parent/'signoff';signoff.mkdir()
    (signoff/'signoff.json').write_text(json.dumps({'verdict':'SIGNED'}))
    assert ns['apply_release'](row)['status']=='SKIP' and source.exists()
    (signoff/'signoff.json').unlink()
    marker=source.parent.parent/'.keep';marker.write_text('')
    assert ns['apply_release'](row)['status']=='SKIP' and source.exists()
    row['empty_ancestor_keep_exception']=True
    assert ns['apply_release'](row)['status']=='APPLIED' and marker.exists()

def test_unique_source_and_changed_cache_are_refused(tmp_path):
    ns=worker(tmp_path);source,_,row=release(tmp_path)
    source.write_text('changed cache')
    assert ns['apply_release'](row)['status']=='SKIP' and source.exists()
    unique=source.parent/'manual.cpp';unique.write_text('unique hand code')
    s=unique.stat();row['files']=[dict(path=str(unique),bytes=s.st_size,inode=s.st_ino,mtime_ns=s.st_mtime_ns)]
    assert ns['apply_release'](row)['status']=='SKIP' and unique.exists()


def test_duplicate_requires_actual_retained_hash(tmp_path):
    ns=worker(tmp_path);source,_,row=release(tmp_path)
    payload=source.with_suffix('.odb');source.rename(payload)
    data=payload.read_bytes();row.update(host='localtest',kind='duplicate-bulk',destination='localtest:'+str(tmp_path/'retained'))
    row['files']=[dict(path=str(payload),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())]
    assert ns['apply_release'](row)['status']=='SKIP' and payload.exists()
    retained=tmp_path/'retained';retained.mkdir();(retained/payload.name).write_bytes(b'wrong')
    assert ns['apply_release'](row)['status']=='SKIP' and payload.exists()
    (retained/payload.name).write_bytes(data)
    assert ns['apply_release'](row)['status']=='APPLIED' and not payload.exists()


def test_dpi_header_and_nested_symlink_escape_are_refused(tmp_path):
    ns=worker(tmp_path);source,_,row=release(tmp_path)
    dpi=source.with_name('Vtop__Dpi.h');dpi.write_text('required DPI interface')
    st=dpi.stat();row.update(released_suffixes=['.h'],files=[dict(path=str(dpi),bytes=st.st_size,inode=st.st_ino,mtime_ns=st.st_mtime_ns)])
    assert ns['apply_release'](row)['status']=='SKIP' and dpi.exists()
    outside=tmp_path/'outside';outside.mkdir();unique=outside/'Vunique.cpp';unique.write_text('unique')
    (source.parent/'escape').symlink_to(outside,target_is_directory=True)
    path=source.parent/'escape/Vunique.cpp';st=path.stat()
    row.update(released_suffixes=['.cpp'],files=[dict(path=str(path),bytes=st.st_size,inode=st.st_ino,mtime_ns=st.st_mtime_ns)])
    assert ns['apply_release'](row)['status']=='SKIP' and unique.exists()


def test_tracked_git_cpp_inside_obj_is_source_not_cache(tmp_path):
    ns=worker(tmp_path);source,_,row=release(tmp_path)
    repo=source.parent.parent
    subprocess.run(['git','init','-q',str(repo)],check=True)
    subprocess.run(['git','-C',str(repo),'add','obj/'+source.name],check=True)
    result=ns['apply_release'](row)
    assert result['status']=='SKIP' and 'tracked Git source' in result['reason'] and source.exists()
