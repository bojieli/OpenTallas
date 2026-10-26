#!/usr/bin/env python3
"""Stage a QC bound top with its recursive functional RTL closure and relative file lists."""
import argparse, hashlib, json, os, re, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import bind_smoke as B
import bind_elab as E
import importlib.util

def stage(bound, recipe, revision, out):
    if out.exists(): raise ValueError(f'refuse to overwrite {out}')
    ab=json.loads(recipe.read_text()); S=B.Sources.__new__(B.Sources); S.E=E
    roots=ab.get('rtl_roots',['rtl'])
    S.base=B.src_tree(revision,ROOT,roots+B.MACRO_DIRS+ab.get('files',[])+ab.get('prefer',[])+ab.get('portbind_prefer',[]))
    S.bound=bound; generated=sorted(str(p) for p in (bound/'rtl').glob('*.sv'))
    S.idx=E.module_index(roots,ab.get('files',[])+generated,S.base)
    choices=[]
    recorded_leaves={}
    for raw in ((bound/'bind.f').read_text().splitlines() if not (bound/'source_leaves.json').is_file() else []):
        if not raw.strip():continue
        p=Path(raw)
        if not p.is_absolute(): continue
        for prefix in ('rtl/','physical/'):
            if '/'+prefix in str(p):
                candidate=S.base/(prefix+str(p).split('/'+prefix,1)[1])
                if not candidate.is_file():raise ValueError(f'bound source missing at pinned revision: {candidate}')
                if p.is_file() and p.read_bytes()!=candidate.read_bytes():raise ValueError(f'bound source differs at pinned revision: {p}')
                choices.append(str(candidate));recorded_leaves[str(candidate.relative_to(S.base))]=hashlib.sha256(candidate.read_bytes()).hexdigest();break
    if (bound/'source_leaves.json').is_file():
        recorded_leaves=json.loads((bound/'source_leaves.json').read_text())
        choices=[]
        for name,digest in recorded_leaves.items():
            candidate=S.base/name
            if hashlib.sha256(candidate.read_bytes()).hexdigest()!=digest:raise ValueError(f'leaf digest mismatch: {name}')
            choices.append(str(candidate))
    spec=importlib.util.spec_from_file_location('s8_profile',ROOT/'tools/qwen_tokfunc/s8die_srcs.py')
    P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
    shutil.copyfile(ROOT/'rtl/test/qwen_dv/s5/run_s8.sh',S.base/'rtl/test/qwen_dv/s5/run_s8.sh')
    profile=[str(S.base/p) for p in reversed(P.s8_files(S.base))]
    chosen=[str(S.base/p) for p in ('rtl/hdc/ot_hdc_prefix.sv','rtl/qwen_dv/headprep13/physical_abi/qfd_dv_typed_witness_control_frozen.sv','rtl/physical/a0_rc14_selected_2000/qfd_tile_nk_rp2_45.sv','rtl/physical/a0_rc14_selected_2000/qfd_tile_nl_rp2_45.sv','rtl/physical/a0_rc14_selected_2000/ot_qwen_me_array_w12.sv','rtl/physical/a0_rc14_selected_2000/ot_qwen_w12_matvec.sv','rtl/physical/a0_rc14_selected_2000/ot_qwen_rom_tile_w12.sv','rtl/qwen_dv/headprep13/native32/qfd_tt_ctlm_dv_hp13_rrloc_helpers.sv')]
    S.prefer=profile+chosen+generated+choices+[str(S.base/p) for p in ab.get('prefer',[])+ab.get('portbind_prefer',[])]+[str(S.base/p) for p in B.MACRO_DIRS]
    S.defines=ab.get('defines',[])
    files,amb,missing=S.closure(['qwen_compute_bound_top']);includes,dirs=S.includes(files)
    if amb or missing:raise ValueError(json.dumps(dict(missing=missing,ambiguous=amb)))
    out.mkdir(parents=True);entries=[];hashes={};mods={}
    def rel(p):
        p=Path(p)
        if p.is_relative_to(bound):return Path('bound')/p.relative_to(bound)
        return p.relative_to(S.base)
    for p in list(files)+list(includes):
        p=Path(p);r=rel(p);dest=out/r;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);hashes[str(r)]=hashlib.sha256(p.read_bytes()).hexdigest()
    for p in files:
        entries.append(str(rel(p)))
        for name in re.findall(r'^\s*(?:module|primitive)\s+(\w+)',Path(p).read_text(),re.M):
            if name in mods and mods[name]!=str(rel(p)):raise ValueError(f'duplicate module {name}: {mods[name]} vs {rel(p)}')
            mods[name]=str(rel(p))
    (out/'files.f').write_text('\n'.join(entries)+'\n')
    (out/'incdirs.f').write_text(''.join('+incdir+'+str(rel(Path(p)/'x').parent)+'\n' for p in dirs))
    (out/'defines.f').write_text(''.join('+define+'+p+'\n' for p in S.defines))
    report=dict(source_revision=revision,bound_top_sha256=hashes['bound/rtl/qwen_compute_bound_top.sv'],files=len(files),modules=len(mods),sha256=hashes,scope='Functional source closure only; no RTL or token verdict.')
    (out/'source_leaves.json').write_text(json.dumps(recorded_leaves,indent=1)+'\n')
    (out/'closure.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='sha256'}))
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('bound','recipe','out'):ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--revision',required=True);a=ap.parse_args();stage(a.bound.resolve(),a.recipe.resolve(),a.revision,a.out.resolve())
