import copy
from hbm_fused_vm_census import audit

def vehicle():
    cores=[dict(inst=n) for n in ['u_vmb_Q0','u_vmb_Q1','u_mu_fused_0','u_mu_fused_1','u_mu_fused_n1_q0']]
    st=[]
    for i in range(2):
        for kind,bits in [('rd',257),('rq',18),('wr',282)]:
            a,b=(f'u_vmb_Q{i}',f'u_mu_fused_{i}') if kind=='rd' else (f'u_mu_fused_{i}',f'u_vmb_Q{i}')
            st.append(dict(launch=a+'.'+kind,capture=b,bits=bits,conn=kind))
    return cores,st


def test_native_buddies_and_serialization_or_width_controls():
    c,s=vehicle();assert audit(c,s,2)['verdict']=='PASS'
    bad=copy.deepcopy(s);bad[0]['serial_k']=2
    assert audit(c,bad,2)['verdict']=='FAIL'
    bad=copy.deepcopy(s);bad[2]['bits']=273
    assert audit(c,bad,2)['verdict']=='FAIL'
    bad=copy.deepcopy(s);bad[0]['capture']='u_mu_fused_1'
    assert audit(c,bad,2)['verdict']=='FAIL'
