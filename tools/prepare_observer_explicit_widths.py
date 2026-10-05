"""New simulation-only copies with explicit unsigned padding; no compiler calls."""
import copy,hashlib,json,re,subprocess
from pathlib import Path
import prepare_observer_lint_gate as closure
import prepare_observer_l0_structural as l0
import plan_observer_hierarchy_gate as source
import prepare_simulation_observation_wrapper as packet
PRIOR='results/rtl/observer_frontend_resource_model_4e383_20261002/plan.json'
OUT='results/rtl/observer_explicit_widths_4e383_20261002'
COPIES=[('rtl/test/v41_runtime/ot_v41_rt_die_sim_observe_l0_window.sv','ot_v41_rt_die_sim_observe_l0_window','rtl/test/v41_runtime/ot_v41_rt_die_sim_observe_l0_window_widths.sv','ot_v41_rt_die_sim_observe_l0_window_widths'),('rtl/test/v41_runtime/ot_v41_rt_die_l20_sim_observe.sv','ot_v41_rt_die_l20_sim_observe','rtl/test/v41_runtime/ot_v41_rt_die_l20_sim_observe_widths.sv','ot_v41_rt_die_l20_sim_observe_widths')]
REPLACEMENTS=[(".att_packed_kv_w('0)",".att_packed_kv_w(16960'd0)"),("wire [31:0] dbg_faults = {11'd0,","wire [31:0] dbg_faults = {12'd0,"),("assign dbg_state = {dbg_fsticky,","assign dbg_state = {4'd0, dbg_fsticky,")]
def digest(b):return hashlib.sha256(b).hexdigest()
def render(text,index):
    _,oldtop,_,top=COPIES[index]
    for a,b in [(f'module {oldtop} #(',f'module {top} #('),*REPLACEMENTS]:
        if text.count(a)!=1:raise ValueError('width transform must match exactly once')
        text=text.replace(a,b)
    return text

def inverse(text,index):
    _,oldtop,_,top=COPIES[index]
    for a,b in reversed([(f'module {oldtop} #(',f'module {top} #('),*REPLACEMENTS]):
        if text.count(b)!=1:raise ValueError('width inverse must match exactly once')
        text=text.replace(b,a)
    return text

def terms(text,name):
    pattern=(r'wire \[31:0\] dbg_faults = \{(.*?)\};' if name=='dbg_faults' else r'assign dbg_state = \{(.*?)\};')
    m=re.search(pattern,text,re.S)
    if not m:raise ValueError('packing expression missing')
    return [t.strip() for t in m.group(1).split(',')]

def widths(name):
    if name=='dbg_faults':
        seq=['dut.u_tile.qrom_rom_fault','dut.u_tile.rope_read_fault','dut.u_tile.idx_user_fault','dut.u_tile.kb_ring_fault']
        seq+=['dut.u_tile.u_core.'+s for s in ['coll_fault','rope_pf_fault','win_fault','win_capture_fault','rom_fault_w','he_fault','xu_fault','qe_fault','su_fault','me_fault','e_fault','fuse_orphan']]
        return {s:4 if s.endswith('.e_fault') else 1 for s in seq}
    return dict([('dbg_fsticky',32),("4'(dut.u_tile.u_core.st)",4),('dut.u_tile.u_core.d_unit',3),('dut.u_tile.u_core.idles',5)]+[(s,1) for s in ['dut.coll_busy','dut.u_tile.u_core.waited','dut.u_cdma.busy','dut.u_cdma.e_mode','dut.u_cdma.fault','dut.e_valid','dut.e_ready','dut.o_valid','dut.o_ready']])

def mapping(text,name):
    # Each symbolic bit is independent and may be 0/1/X/Z. Concatenation is
    # unsigned; assignment pads on the left with known zeros, never sign bits.
    result=[];w=widths(name)
    for term in terms(text,name):
        literal=re.fullmatch(r"(\d+)'[bd]0",term)
        if literal:result.extend(['0']*int(literal[1]))
        elif term in w:result.extend([term+'['+str(i)+']' for i in reversed(range(w[term]))])
        else:raise ValueError('unknown packing term: '+term)
    target=32 if name=='dbg_faults' else 64
    if len(result)>target:raise ValueError('packing overflow')
    return ['0']*(target-len(result))+result

def prove_mapping(before,after):
    result={}
    for name in ['dbg_faults','dbg_state']:
        a=mapping(before,name);b=mapping(after,name)
        if a!=b:raise ValueError('field mapping changed: '+name)
        result[name]={str(len(a)-1-i):bit for i,bit in enumerate(a)}
    if ".att_packed_kv_w('0)" not in before or '.att_packed_kv_w(16960\'d0)' not in after:raise ValueError('zero input transform missing')
    return dict(proof='Exact symbolic per-bit equality for every independent 0/1/X/Z field bit; unsigned concatenation assignment zero-extension. Constant input all16960bits known0 in both.',maps=result)

def expected_modes(repo,prior):
    repo=Path(repo);modes=copy.deepcopy(prior['modes'])
    for i,m in enumerate(modes):
        oldpath,oldtop,path,top=COPIES[i];before=(repo/oldpath).read_text();after=render(before,i)
        assert inverse(after,i)==before;prove_mapping(before,after)
        if (repo/path).read_text()!=after:raise ValueError('new copy not exact reviewed derivative')
        inputs={p:(repo/p).read_text() if p==oldpath else source.blob(repo,p).decode() for p in m['source_sha256']}
        inputs.pop(oldpath);inputs[path]=after
        c=closure.closure(inputs,top)
        if c['ambiguous'] or set(c['unresolved'])-closure.GUARDS:raise ValueError('closure ownership changed')
        if set(c['files']+c['support'])!={p.replace(oldpath,path) for p in m['source_sha256']}:raise ValueError('ancestor census changed')
        m.update(top=top,copy=path,closure=c,source_sha256={p:digest(t.encode()) for p,t in inputs.items()},source_bytes=sum(len(t.encode()) for t in inputs.values()),argv=[a.replace(oldtop,top).replace(oldpath,path) for a in m['argv']])
    return modes

def validate_inverse_to_real(repo):
    repo=Path(repo);originals=[]
    for i,(oldpath,_,path,_) in enumerate(COPIES):
        before=(repo/oldpath).read_text();undo=inverse((repo/path).read_text(),i)
        if undo!=before:raise ValueError('protected copy inverse mismatch')
        if i==0:
            real=l0.inverse(undo);original=packet.ORIGINAL;l0.assert_l0_only((repo/path).read_text())
        else:
            real=closure.inverse_ckv(undo,(repo/source.COPY).read_text());original=closure.CKV_ORIGINAL
        data=source.blob(repo,original)
        if real.encode()!=data:raise ValueError('pinned original inverse mismatch')
        if 'parameter bit SIM_OBS_ENABLE = 0' not in before:raise ValueError('not default off')
        originals.append(dict(copy=path,protected_copy=oldpath,original=original,original_sha256=digest(data),exact_inverse_to_original=True,default_observation=0,proof=prove_mapping(before,(repo/path).read_text())))
    return originals


def declaration_width(text,name):
    hits=[]
    for line in text.splitlines():
        # Numeric declarations of the specific debug fields; no general SV parser.
        m=re.search(r'\b(?:wire|reg)\s*(?:signed\s*)?(?:\[(\d+):0\]\s*)?([^;]+)',line)
        if m and re.search(r'\b'+re.escape(name)+r'\b',m[2].split('=')[0]):
            hits.append((int(m[1])+1 if m[1] else 1,line))
    if len(hits)!=1:raise ValueError('ambiguous numeric declaration '+name)
    return hits[0]

def source_field_authority(repo,prior):
    repo=Path(repo);evidence=[]
    for m in prior['modes']:
        ownership=m['closure']['ownership'];paths={'dut.u_tile.u_core.':ownership['ot_hdc_core_v41x'],'dut.u_tile.':ownership['ot_chip_v41x_tile'],'dut.u_cdma.':ownership['ot_w15_coll_dma'],'dut.':ownership['ot_chip_v41x_die']}
        rows=[]
        for field,w in {**widths('dbg_faults'),**widths('dbg_state')}.items():
            if field=='dbg_fsticky':p=m['copy'];name=field
            elif field.startswith("4'("):p=ownership['ot_hdc_core_v41x'];name='st'
            else:
                prefix=next(k for k in paths if field.startswith(k));p=paths[prefix];name=field.split('.')[-1]
            data=(repo/p).read_bytes() if p==m['copy'] else source.blob(repo,p)
            actual,line=declaration_width(data.decode(),name)
            if actual!=w:raise ValueError('debug field width mismatch '+field)
            rows.append(dict(field=field,width=w,path=p,sha256=digest(data),declaration=line))
        parent=source.blob(repo,ownership['ot_chip_v41x_die'])
        if '[4*((FULL_SHAPE ? 512 : 32)/32)*265-1:0] att_packed_kv_w' not in parent.decode():raise ValueError('packed input width formula mismatch')
        if '.FULL_SHAPE(1)' not in (repo/m['copy']).read_text():raise ValueError('full shape changed')
        evidence.append(dict(mode=m['name'],fields=rows,packed_input=dict(path=ownership['ot_chip_v41x_die'],sha256=digest(parent),formula='4*((FULL_SHAPE ? 512 : 32)/32)*265',FULL_SHAPE=1,width=16960)))
    return evidence

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--repo',default='.');a=ap.parse_args();repo=Path(a.repo)
    for i,(oldpath,_,path,_) in enumerate(COPIES):
        with (repo/path).open('x') as f:f.write(render((repo/oldpath).read_text(),i))
    print(json.dumps(validate_inverse_to_real(repo),indent=2))
