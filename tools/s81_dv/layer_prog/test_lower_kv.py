"""Minimum compiler component replay; synthetic residency tests are not token proof."""
import copy
import ast
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from layer_prog import lower_kv as K

class Die:
    def slices(self):
        return {'u_s_3N': {'sid': 6}}

class Compiler:
    ENG = {'VN': 0}
    @staticmethod
    def ctl_path(die, sl):
        return dict(edges=9)

K._dvc = lambda: Compiler


def program(kind):
    name = dict(KV='attn.kv_rope_qdq', CN='attn.cmp.row_qdq', IK='attn.cmp.k_rope_qdq', CP='attn.cmp.pool')[kind]
    op = dict(id='op1', op=name)
    j = dict(kind=kind, owner='op1', covers=['op1'], issue=100, context=2,
             capture_offset=19, leaf_downrelay=4, done_age=K.ADAPTER_DONE[kind], release_edge=2000,
             source_receipt='synthetic compiler test only', output_ready_edge=19+100+K.ADAPTER_DONE[kind]+2, first_output_write_edge=119+(139 if kind=='CP' else 1030), residency=[], gain_set=3 if kind == 'CN' else 0,
             jid=19, drain_age=1024,
             gain_residency=dict(gain_set=3 if kind == 'CN' else 0, ready_edge=99, release_edge=2000, source_receipt='synthetic gain'))
    ranges = [(0,255),(256,511)] if kind == 'CP' else [(672,691),(692,787),(788,819)]
    j['residency'] = [dict(lo=a,hi=b,ready_edge=99,last_read_edge=498 if kind=='CP' else 150,release_edge=2000,producer='synthetic input',
                           source_receipt='synthetic receipt',format='fp32_zero_prefix384' if kind=='IK' and a==692 else 'input') for a,b in ranges]
    if kind == 'CP':
        j.update(slot0_base=0,slot1_base=256,output_base=692)
    return dict(schema='opentallas.s81.kv_program.v1',jobs=[j]), dict(ops=[op]), op


def reject(p, s, mutate):
    p=copy.deepcopy(p)
    mutate(p['jobs'][0])
    try:
        K.validate(p,s)
    except (ValueError, KeyError):
        return
    raise AssertionError('causal invalid programme accepted')


def run():
    cases=[]
    for kind in ('KV','CN','IK','CP'):
        p,s,o=program(kind)
        r=K.lower(Die(),o,dict(sched=s,kv_program=p))
        assert r['status']=='PARTIAL' and r['retire_not_before']==2000
        row=r['rows'][0]
        assert row['issue']==100 and row['arg']>>7==2
        payload=r['templates'][0][1]
        cmd=payload>>26
        assert payload&65535==1<<6 and (payload>>21)&31==1
        assert cmd&15==15 and (cmd>>24)&255==32 and (cmd>>32)&15==K.KINDS[kind]
        reject(p,s,lambda j:j['residency'].pop())
        reject(p,s,lambda j:j['residency'][0].update(ready_edge=119))
        reject(p,s,lambda j:j.update(done_age=0))
        reject(p,s,lambda j:j.update(context=4))
        reject(p,s,lambda j:j.update(kind='IK' if kind!='IK' else 'CN'))
        reject(p,s,lambda j:j.update(covers=['missing']))
        cases.append(kind)
    p,s,o=program('IK')
    reject(p,s,lambda j:j['residency'][1].update(format='ordinary'))
    p,s,o=program('CP')
    reject(p,s,lambda j:j.update(output_base=252))
    p,s,o=program('CN')
    reject(p,s,lambda j:j.update(gain_set=0))
    p['jobs'].append(copy.deepcopy(p['jobs'][0]))
    try: K.validate(p,s)
    except ValueError: pass
    else: raise AssertionError('port overlap accepted')
    # A producer row lease may span its consumer while the port is serial.
    p, s, cp_op = program('CP')
    p['jobs'][0].update(release_edge=1100)
    cn_p, _, cn_op = program('CN')
    cn_op.update(id='op2')
    cn=cn_p['jobs'][0]
    cn.update(owner='op2',covers=['op2'],issue=700,first_output_write_edge=1749,output_ready_edge=1939)
    for res in cn['residency']:
        res.update(ready_edge=600,last_read_edge=750)
        if res['lo']>=692: res['producer_job']='op1::CP'
    p['jobs'].append(cn)
    s['ops'].append(cn_op)
    K.validate(p,s)
    bad=copy.deepcopy(p)
    bad['jobs'][1]['residency'][1]['ready_edge']=510
    try: K.validate(bad,s)
    except ValueError: pass
    else: raise AssertionError('consumer read before producer SRAM availability accepted')
    bad=copy.deepcopy(p)
    bad['jobs'][1].update(issue=200,first_output_write_edge=1249,output_ready_edge=1439)
    try: K.validate(bad,s)
    except ValueError: pass
    else: raise AssertionError('overlapping actual adapter port reservations accepted')
    reject(*program('CN')[:2], lambda j:j.update(output_ready_edge=1337))
    print('PASS CP->CN direct row lifetime with separate serial port reservation; three causal lifetime faults caught')

    # Exercise a real gain upload prerequisite using its qualified finite bases.
    p,s,o=program('CN')
    gain=copy.deepcopy(p['jobs'][0])
    gain.update(kind='GK', covers=[], issue=1, capture_offset=19,
                done_age=1025, release_edge=1045, parameter_base=528, operand_base=896)
    gain['residency']=[dict(lo=a,hi=b,ready_edge=0,last_read_edge=100,release_edge=1045,producer='gain input',source_receipt='synthetic')
                       for a,b in ((528,531),(896,1023))]
    p['jobs'][0].update(issue=1100,release_edge=2400,output_ready_edge=2339,first_output_write_edge=2149)
    p['jobs'][0]['gain_residency'].update(ready_edge=1045,release_edge=2400)
    for res in p['jobs'][0]['residency']: res.update(last_read_edge=1200, release_edge=2400)
    p['jobs'].insert(0,gain)
    r=K.lower(Die(),o,dict(sched=s,kv_program=p))
    assert len(r['rows'])==2 and (r['templates'][0][1]>>58)&15==7
    # Replay the actual compiler Prog implementation over the128-template limit.
    source=Path(__file__).resolve().parents[1]/'dv_layer_compile.py'
    tree=ast.parse(source.read_text())
    node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Prog')
    env=dict(ENG=dict(VN=0,VS=1,GUNIT=2),SEQ=dict(done_v=5),re=re)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),env)
    prog=env['Prog'](Die())
    rr=dict(rows=[dict(eng=0,issue=i,arg=(i&127)|(2<<7),template_index=i) for i in range(140)],
            templates=[(str(i),i+1) for i in range(140)])
    prog.absorb('kv',o,rr)
    assert prog.rows[139]['tix']==139 and prog.rows[139]['arg']>>7==2
    print('PASS gain upload source7 with base528/896; real Prog.absorb140-template remap preserves context')
    print('PASS actual native encoders KV/CN/IK/CP; context bits; END fence; 31 causal rejection checks')
    print('SYNTHETIC compiler component only; no source arithmetic or current die binding claim')

if __name__=='__main__': run()
