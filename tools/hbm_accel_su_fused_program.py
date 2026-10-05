#!/usr/bin/env python3
"""Default-off source-ordered saved SU program dispatcher.

The native fallback executes the EXISTING archived Vtb, without schedule(),
reference arithmetic, inference, rebuilding, or guessed latency. Mixed dispatch
requires an actual shared-VM lease owner; standalone family receipts cannot
supply VM state. Absence of that owner is a fail-closed integration hold.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import numpy as np
from hbm_accel_su_fused_compile import compile_saved
from hbm_accel_su_fused_compile_cases import load_cases
from hbm_accel_su_fused_runtime import bits, write_words


class IntegrationHold(RuntimeError):
    pass


def native_word(op, fields):
    if set(op)!=set(fields):
        raise ValueError('saved fields do not match the archived bench-word ABI')
    word=0; offset=0
    for key,width in fields.items():
        value=int(op[key])
        if value<0 or value>=1<<width:raise ValueError('native word bounds')
        word |= value<<offset;offset+=width
    return word,offset


def load_hex(path):
    tokens=[]
    for line in Path(path).read_text().splitlines():
        tokens.extend(line.split('//',1)[0].split())
    return np.array([int(x,16) for x in tokens],dtype=np.uint32)


class NativeRetainedBackend:
    """Concrete archived native runner, explicit ABI manifest, no rebuild."""
    def __init__(self, executable, contract):
        self.executable=Path(executable).resolve()
        self.contract=json.loads(Path(contract).read_text())
        digest=hashlib.sha256(self.executable.read_bytes()).hexdigest()
        if digest!=self.contract['binary_sha256']:
            raise ValueError('archived executable source binding mismatch')
        if self.contract.get('scope')!='actual archived SU bench-word ABI':
            raise ValueError('missing actual archived ABI, not inferred from file presence')

    def execute_retained(self, state, ops, indexes, work):
        # Saved raw ops are NOT executable scheduling words: schedule() added
        # producer credits/waits to the original archived prog.hex. Reuse those
        # actual words verbatim; never regenerate the oracle or rebase debt.
        if list(indexes)!=list(range(state['original_op_count'])):
            raise IntegrationHold('partial retained dispatch needs the actual shared issuer credit sequence')
        program=self.contract.get('scheduled_programs',{}).get(state['case_name'])
        if program is None:
            raise IntegrationHold('missing pinned archived scheduled prog.hex for this saved case')
        path=Path(program['path']);payload=path.read_bytes()
        if hashlib.sha256(payload).hexdigest()!=program['sha256']:
            raise ValueError('archived scheduled native words changed')
        fields=self.contract['word_fields']
        width=sum(fields.values());scheduled=[int(x,16) for x in payload.decode().split()]
        if len(scheduled)!=len(ops):raise ValueError('archived original instruction count')
        control={'ch_src','ch_seq','ch_lead','ch_mul','w_idle','w_rseq_en','w_rseq','w_dseq_en','w_dseq','x_start'}
        for op,word in zip(ops,scheduled):
            offset=0
            for key,size in fields.items():
                actual=(word>>offset)&((1<<size)-1);offset+=size
                if key not in control and actual!=int(op[key]):
                    raise ValueError('archived instruction semantics differ from saved source')
        words=[(word,width) for word in scheduled]
        work=Path(work);work.mkdir(parents=True,exist_ok=False)
        if not words:raise ValueError('empty native dispatch')
        width=words[0][1]
        write_words(work/'vm.hex',state['vm']);write_words(work/'kv.hex',state['kv'])
        cr=(state['cr_hi'].astype(np.uint64)<<32)|state['cr_lo'].astype(np.uint64)
        (work/'cr.hex').write_text(''.join(f'{int(x):016x}\n' for x in cr))
        (work/'wr.hex').write_text(''.join(f'{int(x):04x}\n' for x in state['wr']))
        (work/'prog.hex').write_text(''.join(f'{w:0{(width+3)//4}x}\n' for w,_ in words))
        (work/'xb.hex').write_text('00000000\n')
        args=[str(self.executable),*[f'+{k}={work.resolve()/v}' for k,v in
            [('VM','vm.hex'),('KV','kv.hex'),('CR','cr.hex'),('WR','wr.hex'),
             ('PROG','prog.hex'),('XB','xb.hex'),('VMO','vmo.hex'),('KVO','kvo.hex')]],
            f'+NPROG={len(ops)}']
        result=subprocess.run(args,capture_output=True,text=True)
        (work/'run.log').write_text(result.stdout+result.stderr)
        (work/'run.rc').write_text(str(result.returncode)+'\n')
        end=[x for x in result.stdout.splitlines() if x.startswith('END ')]
        if result.returncode or not end or end[-1].split()[2:]!=['ok'] or any(
                x.startswith(('F ','O ')) for x in result.stdout.splitlines()):
            raise IntegrationHold('native retained sequence did not drain exactly')
        vm,kv=load_hex(work/'vmo.hex'),load_hex(work/'kvo.hex')
        if vm.size!=state['vm'].size or kv.size!=state['kv'].size:
            raise IntegrationHold('native readback size differs from actual memory ABI')
        updated=dict(state,vm=vm,kv=kv)
        return updated,dict(path='native_retained',original_op_indexes=list(indexes),
            accepted_original_ops=len(ops),terminal=end[-1],binary_sha256=self.contract['binary_sha256'],
            actual_hardware_parent=False,reset_between_calls=True,headline_performance_eligible=False)


def sequence(record, enabled=False, bound_kinds=()):
    """Retain all original indexes once. No hoisting interleaved groups.

    Noncontiguous groups need the real issuer's interleaved outstanding-op
    contract and remain native until that contract is installed. This preserves
    Q/KV interleaving rather than asserting a new issuer/order authority.
    """
    ops=record['original_ops'];chosen={};covered=set()
    if enabled:
        for group in record['candidates']:
            indexes=group['original_op_indexes']
            if (group['selected'] and group['kind'] in bound_kinds and
                indexes==list(range(min(indexes),max(indexes)+1))):
                if covered.intersection(indexes):raise ValueError('overlapping fused groups')
                chosen[min(indexes)]=group;covered.update(indexes)
    steps=[];pending=[]
    def flush():
        if pending:steps.append(dict(path='native_retained',indexes=pending.copy()))
        pending.clear()
    for i in range(len(ops)):
        if i in chosen:
            flush();steps.append(dict(path='fused_vm',indexes=chosen[i]['original_op_indexes'],group=chosen[i]))
        elif i not in covered:pending.append(i)
    flush()
    flattened=[i for step in steps for i in step['indexes']]
    if flattened!=list(range(len(ops))):raise ValueError('source order/once-only invariant')
    return steps


def execute_saved(cases_path, case_index, backend, work, enabled=False):
    blob,pin=load_cases(Path(cases_path));compiled=compile_saved(Path(cases_path))
    case=blob['cases'][case_index];record=compiled['cases'][case_index]
    if enabled and not getattr(backend,'actual_shared_vm_parent',False):
        raise IntegrationHold('no actual VEC/fused shared-VM issuer/arbiter lease-transfer binding')
    c=backend.contract
    state=dict(case_name=case['name'],original_op_count=len(record['original_ops']),vm=np.zeros(1<<c['VMA'],dtype=np.uint32),kv=np.zeros(1<<c['KVA'],dtype=np.uint32),
               cr_lo=bits(case['cr_lo']).copy(),cr_hi=bits(case['cr_hi']).copy(),
               wr=np.zeros(1<<c['WRA'],dtype=np.uint16))
    if len(state['cr_lo'])!=1<<c['CRA'] or len(state['cr_hi'])!=1<<c['CRA']:
        raise ValueError('saved CR size disagrees with native ABI')
    for address,values in case['init']:
        if address<0 or address+len(values)>len(state['vm']):raise ValueError('actual VM bounds')
        state['vm'][address:address+len(values)]=bits(values)
    work=Path(work);work.mkdir(parents=True,exist_ok=False)
    receipts=[]
    for number,step in enumerate(sequence(record,enabled,getattr(backend,'bound_kinds',()))):
        indexes=step['indexes'];directory=work/f'step{number}'
        if step['path']=='native_retained':
            state,receipt=backend.execute_retained(state,[record['original_ops'][i] for i in indexes],indexes,directory)
        else:
            state,receipt=backend.execute_fused_vm(state,step['group'],indexes,directory)
            if receipt.get('write_debt')!=0 or receipt.get('read_debt')!=0:
                raise IntegrationHold('fused owner lease did not actually drain')
        receipts.append(receipt)
    checks=[]
    for label,address,want,kind in case['checks']:
        expected=bits(want);got=state['vm'][address:address+len(expected)]
        checks.append(dict(label=label,kind=kind,words=len(expected),
            mismatches=int(np.count_nonzero(got!=expected))))
    result=dict(cases_sha256=pin,case_index=case_index,name=case['name'],enabled=enabled,
        receipts=receipts,checks=checks,pass_exact=all(x['mismatches']==0 for x in checks),
        actual_parent_integration=bool(getattr(backend,'actual_shared_vm_parent',False)),adopted=False)
    (work/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cases',type=Path,required=True);ap.add_argument('--case-index',type=int,required=True)
    ap.add_argument('--native-executable',type=Path,required=True);ap.add_argument('--native-contract',type=Path,required=True)
    ap.add_argument('--work',type=Path,required=True);ap.add_argument('--enable-fused',action='store_true')
    a=ap.parse_args();backend=NativeRetainedBackend(a.native_executable,a.native_contract)
    result=execute_saved(a.cases,a.case_index,backend,a.work,a.enable_fused)
    raise SystemExit(0 if result['pass_exact'] else 1)
