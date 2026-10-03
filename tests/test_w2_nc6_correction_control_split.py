"""Helper-only executable RTL tests; codec is an unchanged archived input fixture."""
import importlib.util
import json
import subprocess
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/w2_nc6_correction_control_split_20261003'
RTL=ROOT/'rtl/experimental/w2_nc6_correction_control_split_20261003/ot_w2_nc6_correction_control.sv'
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
G=load(ROOT/'tools/w2_nc6_correction_control_split.py','correction')
INPUT=ROOT/'results/uarch/w2_nc6_correction_control_20261003/inputs'
C=load(INPUT/'source_codec.py','fixture_codec')
ROWS=json.loads((INPUT/'canonical_map.json').read_text())['rows']
MASK=(1<<44)-1

def packed(values,width):return sum(v<<(width*i) for i,v in enumerate(values))
class Memory:
    def __init__(self): self.raw=[C.seal(0,17,i,r['kind']) for i,r in enumerate(ROWS)]
    def setctx(self,e,value):
        for t in range(3):
            i=145+3*e+t;self.raw[i]=C.seal((value>>(44*t))&MASK,17,i,ROWS[i]['kind'])
    def view(self):
        payload=[];fixed=[];clean=ce=bad=0
        for i,r in enumerate(ROWS):
            p,status,f=C.unseal(self.raw[i],17,i,r['kind'],r['payload_bits'])
            payload.append(p or 0);fixed.append(f or 0)
            if status=='CLEAN':clean|=1<<i
            elif status=='CE':ce|=1<<i
            else:bad|=1<<i
        ctx=[payload[145+3*e]|payload[146+3*e]<<44|payload[147+3*e]<<88 for e in range(8)]
        ctxclean=sum(int(all((clean>>(145+3*e+t))&1 for t in range(3)))<<e for e in range(8))
        return dict(enable=1,context_current=packed(ctx,96),context_clean=ctxclean,current_raw=packed(self.raw,72),current_fixed=packed(fixed,72),current_payload=packed(payload,44),current_clean=clean,current_ce=ce,current_bad=bad,retire_ready=0)

FIELDS={'enable':1,'context_current':768,'context_clean':8,'current_raw':15768,'current_fixed':15768,'current_payload':9636,'current_clean':219,'current_ce':219,'current_bad':219,'retire_ready':8}
OUTPUTS={'context_next':768,'context_we':8,'scrub_v':8,'scrub_index':80,'scrub_original':576,'scrub_candidate':576,'busy':1,'error':1}

def cap(a,phase=0):return G.pack_context(original=0,address=a,syndrome=0,overall=0,phase=phase,status=1,valid=1)
def fix(m,a,phase=3):
    syn,odd=C.syndrome(m.raw[a]);return G.pack_context(original=m.raw[a],address=a,syndrome=syn,overall=odd,phase=phase,status=0,valid=1)

def vectors():
    cases=[]
    def add(name,m,updates=None,offers=None,error=0,busy=1,overrides=None):
        inp=m.view();inp.update(overrides or {})
        exp=dict(context_next=inp['context_current'],context_we=0,scrub_v=0,scrub_index=0,scrub_original=0,scrub_candidate=0,busy=busy,error=error)
        for e,value in (updates or {}).items():
            exp['context_next']=(exp['context_next']&~(((1<<96)-1)<<(96*e)))|(value<<(96*e));exp['context_we']|=1<<e
        for e,a in (offers or {}).items():
            exp['scrub_v']|=1<<e;exp['scrub_index']|=a<<(10*e);exp['scrub_original']|=m.raw[a]<<(72*e);exp['scrub_candidate']|=C.decode(m.raw[a])[2]<<(72*e)
        cases.append(dict(name=name,inputs=inp,expected=exp))
    m=Memory();add('all219_clean_idle',m,busy=0)
    m.raw[0]^=1;add('reserve_bank0',m,{0:cap(0)})
    m.setctx(0,cap(0))
    for ph in range(4):
        update=cap(0,ph+1) if ph<3 else fix(m,0,0)
        add('CAP_fourth_capture_'+str(ph),m,{0:update});m.setctx(0,update)
    for ph in range(3):
        update=fix(m,0,ph+1);add('FIX_quiet_'+str(ph),m,{0:update});m.setctx(0,update)
    add('FIX_fourth_offer_held',m,offers={0:0})
    add('held_repeat_no_hidden_state',m,offers={0:0})
    add('disabled_phase3_no_offer',m,overrides={'enable':0})
    add('actual_retire_only',m,{0:0},{0:0},overrides={'retire_ready':1})
    m.raw[0]=C.decode(m.raw[0])[2];m.setctx(0,0);add('clean_after_retirement',m,busy=0)
    m=Memory()
    for a in [0,16,32,48,64,80,96,97]:m.raw[a]^=1
    add('eight_disjoint_reservations',m,{e:cap(a) for e,a in enumerate([0,16,32,48,64,80,96,97])})
    # Every physical target is offered by its legal owner, including 24 context CW.
    for a in range(219):
        m=Memory();e=a//16 if a<96 else (7 if 163<=a<=165 else 6)
        m.raw[a]^=1;m.setctx(e,fix(m,a));add('global_target_'+str(a),m,offers={e:a})
        updates={e:0}
        if 145<=a<169:updates[(a-145)//3]=0
        add('global_retire_'+str(a),m,updates,{e:a},overrides={'retire_ready':1<<e})
    # Raw parity, data, metadata bits exercise captured syndrome and candidate identity.
    for bit in range(72):
        m=Memory();m.raw[0]^=1<<bit;m.setctx(0,fix(m,0));add('physical_bit_'+str(bit),m,offers={0:0})
    # Dirty control data cannot authorize the owner; peer reserves context first.
    for owner in range(8):
        m=Memory();m.raw[133]^=1;m.raw[145+3*owner]^=1
        rescuer=7 if owner==6 else 6
        add('context_priority_owner_'+str(owner),m,{rescuer:cap(145+3*owner)})
    # Restore a valid owner's FIX snapshot, but restart phase0, never old phase3.
    m=Memory();m.raw[0]^=1;old=fix(m,0);m.setctx(0,old);m.raw[145]^=1;m.setctx(6,fix(m,145))
    restored=old&~(7<<90)
    add('peer_restores_restart_phase0',m,{0:restored,6:0},{6:145},overrides={'retire_ready':1<<6})
    m.raw[145]=C.decode(m.raw[145])[2];m.setctx(0,restored);m.setctx(6,0)
    for ph in range(3):
        update=fix(m,0,ph+1);add('restored_FIX_quiet_'+str(ph),m,{0:update});m.setctx(0,update)
    add('restored_FIX_fourth_offer',m,offers={0:0})
    m=Memory();m.setctx(0,cap(16));m.raw[145]^=1;m.setctx(6,fix(m,145))
    add('invalid_restored_peer_before_offer',m,error=1)
    add('invalid_restored_peer_ready_high',m,error=1,overrides={'retire_ready':1<<6})
    # Only current_payload changes: it must be in the combinational sensitivity.
    m=Memory();m.raw[0]^=1;m.setctx(0,fix(m,0));m.raw[145]^=1;m.setctx(6,fix(m,145))
    add('decoded_payload_sensitivity_baseline',m,offers={6:145})
    add('decoded_payload_only_change_rejects',m,error=1,overrides={'current_payload':m.view()['current_payload']^(1<<(44*146+32))})
    # Atomic negative controls: no context mutation or scrub even for a second good actor.
    m=Memory();m.raw[163]^=1;m.raw[166]^=1;add('both_utilities_dirty',m,error=1)
    m=Memory();m.raw[145]^=1;m.raw[146]^=1;add('remaining_two_not_clean',m,error=1)
    for e,a in [(0,16),(6,0),(6,163),(7,166),(0,219)]:
        m=Memory();m.setctx(e,cap(a));add('illegal_scope_'+str(e)+'_'+str(a),m,error=1)
    m=Memory();m.raw[133]^=1;m.setctx(6,fix(m,133));m.setctx(7,fix(m,133));add('duplicate_reservation',m,error=1)
    for field,value in [('phase',4),('status',2),('overall',0),('syndrome',7)]:
        m=Memory();m.raw[0]^=1;kw=G.unpack_context(fix(m,0));kw[field]=value;m.setctx(0,G.pack_context(**kw));add('invalid_'+field,m,error=1)
    m=Memory();m.raw[0]^=1;m.setctx(0,fix(m,0));m.raw[0]^=3;add('stale_original_different_CE',m,error=1)
    m=Memory();m.raw[0]^=1;m.setctx(0,fix(m,0));v=m.view();add('wrong_current_candidate',m,error=1,overrides={'current_fixed':v['current_fixed']^2})
    m=Memory();m.raw[0]^=1;v=m.view();add('contradictory_status',m,error=1,overrides={'current_clean':v['current_clean']|1})
    m=Memory();v=m.view();add('missing_current_status',m,error=1,overrides={'current_clean':v['current_clean']&~1})
    m=Memory();m.raw[100]^=3;add('uncorrectable_global_word',m,error=1)
    m=Memory();m.raw[0]^=1;add('disabled_no_reservation',m,overrides={'enable':0})
    return cases

def execute(directory,source=None,cases=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    src=directory/'helper.sv';src.write_text(source or RTL.read_text());cases=vectors() if cases is None else cases
    tb=['module tb;']
    for k,w in FIELDS.items():tb.append(f'reg [{w-1}:0] {k};')
    for k,w in OUTPUTS.items():tb.append(f'wire [{w-1}:0] {k};')
    tb.append('ot_w2_nc6_correction_control dut('+','.join('.'+k+'('+k+')' for k in FIELDS|OUTPUTS)+'); initial begin')
    for i,c in enumerate(cases):
        for k,v in c['inputs'].items():tb.append(f"{k}={FIELDS[k]}'h{v:x};")
        tb.append('#1;')
        for k,v in c['expected'].items():tb.append(f"if({k} !== {OUTPUTS[k]}'h{v:x}) $fatal(1,\"case {i} {c['name']} {k} got=%h expected={v:x}\",{k});")
    tb.append(f'$display("PASS {len(cases)} helper vectors"); $finish; end endmodule')
    (directory/'tb.sv').write_text('\n'.join(tb)+'\n')
    comp=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(directory/'gate.vvp'),str(src),str(directory/'tb.sv')],text=True,capture_output=True)
    assert comp.returncode==0,comp.stderr
    run=subprocess.run(['vvp',str(directory/'gate.vvp')],text=True,capture_output=True)
    (directory/'compile.log').write_text(comp.stdout+comp.stderr);(directory/'run.log').write_text(run.stdout+run.stderr)
    return run


def test_generated_source_and_model():
    assert G.source()==RTL.read_text()
    assert json.dumps(G.model(),indent=2)+'\n'==(OUT/'model.json').read_text()
    assert len(ROWS)==219
    assert not any(token in RTL.read_text() for token in ['always_ff','posedge','negedge'])

@pytest.mark.parametrize('field,width',[('original',72),('address',10),('syndrome',7),('overall',1),('phase',3),('status',2),('valid',1)])
def test_context_pack_strict(field,width):
    for value in [-1,1<<width,True,1.5]:
        with pytest.raises(ValueError):G.pack_context(**{field:value})

def test_actual_helper_rtl(tmp_path):
    result=execute(tmp_path/'baseline');assert result.returncode==0,result.stdout+result.stderr

MUTANTS={
 'CAP_three_edges':('if(ph<3)begin','if(ph<2)begin'),
 'retire_without_ready':('if(scrub_v[r]&&retire_ready[r])begin','if(scrub_v[r])begin'),
 'missing_raw_snapshot':('current_raw[72*a+:72]!=rawword||',''),
 'both_utilities_not_failclosed':('if(!trusted[6]&&!trusted[7])error=1;',''),
 'peer_phase_not_restarted':('ack_restored[92:90]=0;','ack_restored[92:90]=ack_restored[92:90];'),
}
@pytest.mark.parametrize('name',list(MUTANTS))
def test_real_mutants_rejected(tmp_path,name):
    before,after=MUTANTS[name];assert before in G.source()
    result=execute(tmp_path/name,G.source().replace(before,after,1));assert result.returncode!=0,result.stdout
    assert 'FATAL:' in result.stdout


def test_ready_cone_structural_isolation():
    blocks=G.source().split(' always @* begin')[1:]
    assert len(blocks)==2
    import re
    assert 'retire_ready' not in re.sub(r'//[^\n]*','',blocks[0])
    for out in ['error','busy','scrub_v','scrub_index','scrub_original','scrub_candidate']:
        import re
        assert not re.search(r'\b'+out+r'\s*(?:\[[^\]]*\])?\s*=',blocks[1])
    assert G.model()['service']['recurring_engine_II_enabled_edges']==9
    assert G.model()['service']['CAP_enabled_edges']==4
    assert G.model()['service']['FIX_enabled_edges']==4


def test_all_ready_masks_do_not_change_validation_or_offers(tmp_path):
    m=Memory();targets=[0,16,32,48,64,80,96,97]
    for e,a in enumerate(targets):
        m.raw[a]^=1;m.setctx(e,fix(m,a))
    inp=m.view();ctx=inp['context_current'];offers={e:a for e,a in enumerate(targets)}
    cases=[]
    for mask in range(256):
        nxt=ctx
        for e in range(8):
            if mask>>e&1:nxt&=~(((1<<96)-1)<<(96*e))
        exp=dict(context_next=nxt,context_we=mask,scrub_v=255,
            scrub_index=packed(targets,10),scrub_original=packed([m.raw[a] for a in targets],72),
            scrub_candidate=packed([C.decode(m.raw[a])[2] for a in targets],72),busy=1,error=0)
        cases.append(dict(name='all_ready_mask_'+str(mask),inputs=inp|{'retire_ready':mask},expected=exp))
    result=execute(tmp_path/'ready_masks',cases=cases)
    assert result.returncode==0,result.stdout+result.stderr


def test_no_same_edge_freed_engine_reuse_II9(tmp_path):
    m=Memory();m.raw[0]^=1;m.raw[1]^=1;m.setctx(0,fix(m,0))
    inp=m.view();exp=dict(context_next=0,context_we=1,scrub_v=1,scrub_index=0,
        scrub_original=m.raw[0],scrub_candidate=C.decode(m.raw[0])[2],busy=1,error=0)
    cases=[dict(name='scrub8_no_load1_same_edge',inputs=inp|{'retire_ready':1},expected=exp)]
    m.raw[0]=C.decode(m.raw[0])[2];m.setctx(0,0)
    exp=dict(context_next=cap(1),context_we=1,scrub_v=0,scrub_index=0,scrub_original=0,scrub_candidate=0,busy=1,error=0)
    cases.append(dict(name='next_load9',inputs=m.view(),expected=exp))
    result=execute(tmp_path/'II9',cases=cases)
    assert result.returncode==0,result.stdout+result.stderr
