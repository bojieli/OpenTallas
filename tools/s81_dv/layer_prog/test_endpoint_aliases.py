import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from endpoint_aliases import direct_child_input

def test_real_hbc_direct_wrapper_inputs_and_slice_alias():
    body='m #(.D(2)) u_hbc(.status_t_host(hb_status_t_host),.job_active(hb_status_t_host[65]),.starter_armed(hb_starter_armed));'
    ports={'hb_status_t_host','hb_starter_armed'}
    assert direct_child_input(body,'u_hbc','status_t_host',ports)=='hb_status_t_host'
    assert direct_child_input(body,'u_hbc','job_active',ports)=='hb_status_t_host'
    assert direct_child_input(body,'u_hbc','starter_armed',ports)=='hb_starter_armed'
    assert direct_child_input(body,'u_hbc','mu_c',ports) is None

@pytest.mark.parametrize('body',[
    'm u_hbc(.p(~root));', 'm u_hbc(.p(root ^ other));',
    'm u_hbc(.p(alias)); assign alias=root;',
    'm u_hbc(.p(root)); m u_hbc(.p(root));',
    'm u_hbc(.p(root[index]));'])
def test_unproven_alias_controls_rejected(body):
    assert direct_child_input(body,'u_hbc','p',{'root'}) is None
