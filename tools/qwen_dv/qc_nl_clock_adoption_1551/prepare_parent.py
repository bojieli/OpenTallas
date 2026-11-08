#!/usr/bin/env python3
"""Private actual-parent form: captured routing logic + explicit accepted NL1.

No cached strict PASS is rewritten or claimed for this candidate. All original
files stay read-only. Outputs are regular owned files in a fresh directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
from kit_library_profile import _modules

TYPE='cbx_q10__cl94a12200'
REPLACE={
 'qfd_tile_nl_a0c':'rtl/physical/a0_core/qfd_tile_nl_a0c.sv',
 'qfd_tile_nl_rp2_45':'rtl/physical/a0_rc14_selected_2000/qfd_tile_nl_rp2_45.sv',
 'ot_qwen_rom_tile_nk':'rtl/physical/ot_qwen_rom_tile_nk.sv',
 'ot_qwen_rom_tile_w12':'rtl/physical/a0_rc15_selected_2000/ot_qwen_rom_tile_w12_land32.sv',
 'ot_qwen_w12_matvec':'rtl/physical/a0_rc14_selected_2000/ot_qwen_w12_matvec_land32.sv'}


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def explicit_idle(text):
    pattern=r'(?m)^(\s*)qfd_tile_nl_a0c\s+u_t30\s*\('
    out,n=re.subn(pattern,r'\1qfd_tile_nl_a0c #(.IDLE_UCK(1)) u_t30 (',text)
    if n!=1: raise ValueError(f'expected one unparameterized captured NL u_t30, got {n}')
    return out


def apply_patch(plan,operations):
    for op in operations:
        parts=op['path'].strip('/').split('/'); obj=plan
        for key in parts[:-1]: obj=obj[int(key)] if isinstance(obj,list) else obj[key]
        key=int(parts[-1]) if isinstance(obj,list) else parts[-1]
        if op['op']=='test':
            if obj[key]!=op['value']: raise ValueError('private event input mismatch: '+op['path'])
        elif op['op'] in ('add','replace'): obj[key]=op['value']
        else: raise ValueError('unsupported event operation')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--captured-attempt',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args(); out=a.out.resolve(); attempt=a.captured_attempt.resolve()
    if out.exists(): raise ValueError('new destination required; original/failed outputs are preserved')
    if not (attempt/'rtl/kit_rtl.f').is_file(): raise ValueError('missing exact captured RTL filelist')
    artifact=ROOT/'results/physical/qc_nl_clock_adoption_1551'
    original_f=(attempt/'rtl/kit_rtl.f').read_text().splitlines()
    inputs=[Path(s.strip()) for s in original_f if s.strip() and not s.lstrip().startswith('#')]
    if not inputs or any(not f.is_file() for f in inputs): raise ValueError('captured source closure missing')
    if len({f.name for f in inputs})!=len(inputs): raise ValueError('captured basename collision needs explicit handling')
    texts={f:f.read_text() for f in inputs}; inventory={}
    for f,text in texts.items():
        for module in _modules(text):
            if module in inventory: raise ValueError('ambiguous captured module '+module)
            inventory[module]=f
    replacements={}
    for module,rel in REPLACE.items():
        old=inventory[module]; new=ROOT/rel
        if not new.is_file(): raise ValueError('missing current explicit source '+str(new))
        oldnames=set(_modules(texts[old]));newnames=set(_modules(new.read_text()))
        if not oldnames<=newnames: raise ValueError('current source loses captured modules')
        if any(n in inventory and inventory[n]!=old for n in newnames):
            raise ValueError('current source collides with another captured file')
        if 'IDLE_UCK' not in new.read_text(): raise ValueError('current source lacks explicit IDLE_UCK contract')
        replacements[old]=new
    bound=next((f for f in inputs if TYPE+'_bound' in _modules(texts[f])),None)
    if bound is None: raise ValueError('captured bound parent missing')
    candidate_bound=explicit_idle(texts[bound])
    out.mkdir(parents=True);(out/'.keep').write_text('Owned private NL parent access pilot; no count/POR adoption.\n')
    shutil.copytree(attempt/'rtl',out/'captured_rtl',symlinks=False)
    rtl=out/'rtl';rtl.mkdir(); selected=[]; records=[]
    for f in inputs:
        src=replacements.get(f,f);dst=rtl/src.name
        if dst.exists(): raise ValueError('candidate basename collision')
        if f==bound: dst.write_text(candidate_bound)
        else: shutil.copyfile(src,dst)
        selected.append(str(dst));records.append(dict(original=str(f),original_sha256=sha(f),
            selected=str(dst),selected_sha256=sha(dst),current_source=str(src),
            action='explicit IDLE_UCK=1 on captured u_t30' if f==bound else
                   ('current IDLE_UCK library' if f in replacements else 'byte-identical captured source')))
    for f in (attempt/'rtl').iterdir():
        if f.is_file() and f.suffix in ('.json','.tcl') and f.name!='kit_rtl.json': shutil.copyfile(f,rtl/f.name)
    meta=json.loads((attempt/'rtl/kit_rtl.json').read_text())
    meta['files']=selected
    meta['private_parent_source_event']=dict(status='NEW_PRIVATE_SOURCE_UNQUALIFIED_CURRENT_POR',
        parent_body='captured exact body plus sole explicit u_t30.IDLE_UCK=1 change',
        original_bind_out=meta.get('bind_out'),cached_strict_pass_reused=False,
        source_base='66d55c026ad',core_params={'IDLE_UCK':1})
    (rtl/'kit_rtl.json').write_text(json.dumps(meta,indent=2)+'\n')
    (rtl/'kit_rtl.f').write_text('\n'.join(selected)+'\n')
    plan=json.loads((attempt/'plandir/die_plan.json').read_text())
    apply_patch(plan,json.loads((artifact/'access_v4/proposed_event.patch.json').read_text()))
    # Preserve every original plan-relative pin table as a read-only explicit
    # input; the selected NL pin table comes from this private event instead.
    for typ in plan['partition_types'].values():
        for core in typ.get('hard_cores',[]):
            pin=core.get('pins_file')
            if pin and not Path(pin).is_absolute():
                core['pins_file']=str((ROOT/pin).resolve() if pin.startswith('results/') else
                                      (attempt/'plandir'/pin).resolve())
            if core.get('module')=='qfd_tile_nl_a0c' and core.get('clock_entry_access'):
                core['lef']=str(artifact/'private_view/qfd_tile_nl_a0c_tc.lef')
                core['lib']=str(artifact/'private_view/qfd_tile_nl_a0c_tc.lib')
    (out/'plan.json').write_text(json.dumps(plan,indent=1)+'\n')
    record=dict(schema='opentallas.private_source_form.v1',type=TYPE,original_attempt=str(attempt),
        source_base='66d55c026ad',original_strict_context_preserved=True,
        current_POR_binding_qualified=False,new_parent_EQ=False,core_params={'IDLE_UCK':1},
        zero_PIN_data_valid_status_cycle_delta=True,files=records,
        accepted_child_record='epyc2:/srv/opentallas-scratch3/claude/dq90_nl/resign_idleuck/signoff/signoff.json',
        scope='ONE private geometry/clock/PG-access pilot; no canonical activation/count/child re-sign')
    (out/'parent_source_form.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(prepared=str(out),type=TYPE,files=len(selected),new_source=True,cached_strict_pass=False)))

if __name__=='__main__':main()
