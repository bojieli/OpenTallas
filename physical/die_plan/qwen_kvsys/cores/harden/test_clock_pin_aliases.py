import copy
from gen_core_kit_kv import clock_pin_aliases, io_tcl


def test_existing_one_bit_clock_keeps_plan_center_and_gets_clock_geometry():
    cj=dict(pin_class={'ck':'clk','ck[0]':'stale_in'},port_decl={'ck':['input',0,0]})
    pins=[dict(name='ck[0]',layer='M5',x=95.064,y=90.72)]
    assert clock_pin_aliases(cj,pins)==[dict(logical='ck',physical='ck[0]',role='clk',added_cycles=0)]
    assert cj['pin_class']=={'ck[0]':'clk'}
    text,rows=io_tcl(pins,190.08,181.44,'astk',cj['pin_class'])
    assert len(rows)==1 and rows[0]['clock'] and rows[0]['size']==[0.048,0.48]
    assert '{95.0640 90.7200}' in text


def test_alias_only_applies_to_exact_one_bit_input_clock():
    for port,role in ((['input',1,0],'clk'),(['output',0,0],'clk'),(['input',0,0],'in')):
        cj=dict(pin_class={'ck':role,'ck[0]':'stale_in'},port_decl={'ck':port})
        before=copy.deepcopy(cj)
        assert clock_pin_aliases(cj,[dict(name='ck[0]')])==[] and cj==before


def test_matching_reset_entry_uses_same_planned_one_bit_port():
    cj=dict(pin_class={'rst_n':'in','rst_n[0]':'stale_in'},port_decl={'rst_n':['input',0,0]})
    assert clock_pin_aliases(cj,[dict(name='rst_n[0]')])==[
        dict(logical='rst_n',physical='rst_n[0]',role='in',added_cycles=0)]
    assert cj['pin_class']=={'rst_n[0]':'in'}
