"""Offline verification of actual D1 first-prime and KV contributor observations."""
import re


def fields(log,prefix):
    pairs=re.findall(r'^'+prefix+r' ([^=\n]+)=0x([0-9a-f]+)$',log,re.M)
    if len({name for name,value in pairs})!=len(pairs):
        raise ValueError('repeated observation field')
    return {name:int(value,16) for name,value in pairs}


def verify(receipt,log):
    prime=fields(log,'D1_FIRST_PRIME_READY_SAMPLE')
    fatal=fields(log,'D1_FATAL_FIELD')
    if len(prime)!=8 or len(fatal)!=39:
        raise ValueError('incomplete approved observation packet')
    if prime!=receipt.get('first_prime_fields') or fatal!=receipt.get('fatal_fields'):
        raise ValueError('observation/receipt mismatch')
    if receipt.get('GDB_exit_code')!=0 or receipt.get('inferior_exit_code')!=1:
        raise ValueError('original failed terminal not preserved')
    if 'D1_SOURCE_OR_LEDGER_FAULT' not in log:
        raise ValueError('original fatal missing')
    if receipt.get('input_postcheck') is not True or receipt.get('input_hashes_before')!=receipt.get('input_hashes_after'):
        raise ValueError('input identities changed')
    if receipt.get('simulator_launches')!=1 or receipt.get('compiler_or_link_launches')!=0:
        raise ValueError('wrong execution scope')
    if receipt.get('runtime_qualification') is not False or receipt.get('fulltoken') is not False:
        raise ValueError('diagnostic failure cannot qualify runtime')
    if receipt.get('prefetch_fault_code') is not None:
        raise ValueError('pruned code cannot become an observed value')
    if prime['external_rst_n']!=1 or prime['clock']!=1 or prime['rst_s']!=1:
        raise ValueError('first-prime reset attribution differs')
    if any(prime[k]!=1 for k in ('bench_prime_v','source_prime_ready','prime_ready_i','window_prime_v')) or prime['bench_prime_row']!=0:
        raise ValueError('first-prime handshake attribution differs')
    if any(fatal[k]!=v for k,v in {'fault_r':64,'dbg_fs':0,'violations':0,
            'pf_fault':1,'schedule_fault':1,'descriptor_fault':1,'merge_fault':0,
            'unsupported_read':0,'bad_block':0,'rope_fault':0,'prefetch_row':0,
            'window_active_row':0,'window_user':0,'window_state':0,'block_valid[0]':0}.items()):
        raise ValueError('KV contributor or missing-first-row attribution differs')
    for kind in ('row_valid','row_active'):
        if [fatal[f'{kind}[word{i}]'] for i in range(4)]!=[0xfffffffe,0xffffffff,0xffffffff,0xffffffff]:
            raise ValueError('row0-only missing state differs')
    if fatal['row_tag[1]']!=1 or fatal['row_tag[127]']!=127:
        raise ValueError('retained primed-row identities differ')
    return {'status':'OBSERVED_ROW0_RESET_PRIMING_FAILURE',
            'first_prime_internal_rn':prime['rst_s']>>1,
            'bench_ready_sample':True,'reset_qualified_DUT_acceptance':False,
            'missing_valid_rows':[0],'missing_active_rows':[0],
            'observed_KV_faults':{k:fatal[k] for k in ('pf_fault','schedule_fault',
                 'descriptor_fault','merge_fault','unsupported_read','bad_block','rope_fault')},
            'actual_masks':{k:fatal[k] for k in ('fault_r','dbg_fs','violations')},
            'prefetch_fault_code':None,'fulltoken':False,
            'original_PC24_cause':'UNOBSERVED','service_bound':'BOUND_MISSING'}
