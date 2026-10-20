import copy
from types import SimpleNamespace as NS

import pytest
from receiver_guard import preflight, assert_disconnected


class Net:
    def __init__(self): self.its, self.bts = [], []
    def getITerms(self): return self.its
    def getBTerms(self): return self.bts


class Inst:
    def __init__(self, name, master): self.name, self.master, self.its = name, master, []
    def getName(self): return self.name
    def getMaster(self): return NS(getName=lambda: self.master)
    def getITerms(self): return self.its


class Pin:
    def __init__(self, inst, port, direction, net):
        self.inst, self.port, self.direction, self.net = inst, port, direction, net
        inst.its.append(self)
        if net: net.its.append(self)
    def getInst(self): return self.inst
    def getMTerm(self): return NS(getName=lambda: self.port)
    def getIoType(self): return self.direction
    def getNet(self): return self.net


def fixture():
    feed, out = Net(), Net()
    source = Pin(Inst('bump', 'qfd_ckbump'), 'pll_ck', 'OUTPUT', feed)
    rx = Inst('rx', 'qfd_clkrx')
    inp = Pin(rx, 'pll_fwd', 'INPUT', feed)
    output = Pin(rx, 'pll_r0', 'OUTPUT', out)
    ld = Pin(Inst('dc_root_r0', 'BUF'), 'A', 'INPUT', out)
    proof = {'qfd_clkrx': dict(view='MODEL_PASS_THROUGH_R0', physical_qualification_eligible=False,
                             rtl_sha256='a'*64)}
    return source, rx, inp, output, ld, proof


def test_explicit_model_with_only_member_clock_outputs_is_admitted():
    source, rx, inp, output, ld, proof = fixture()
    assert preflight(source, {'dc_root_r0'}, {'rx/pll_r0'}, proof) == [inp]
    output.net.its.remove(ld)
    assert_disconnected(rx)
    assert proof['qfd_clkrx']['physical_qualification_eligible'] is False


@pytest.mark.parametrize('change', ['bterm', 'data', 'reset', 'nonmember', 'multisource', 'source_input',
                                   'source_bterm', 'extra_input', 'no_proof', 'native_waiver', 'unknown_output',
                                   'data_source', 'unknown_source_master'])
def test_receiver_removal_refuses_unsafe_connections(change):
    source, rx, inp, output, ld, proof = fixture()
    if change == 'bterm': output.net.bts.append(NS(getIoType=lambda: 'OUTPUT'))
    if change == 'data': output.port = 'payload'
    if change == 'reset': output.port = 'rst_n'
    if change == 'nonmember': ld.inst.name = 'foreign_data_sink'
    if change == 'multisource': Pin(Inst('other', 'qfd_ckbump'), 'pll_ck', 'OUTPUT', source.net)
    if change == 'source_input': source.direction = 'INPUT'
    if change == 'source_bterm': source.net.bts.append(NS(getIoType=lambda: 'INPUT'))
    if change == 'extra_input': Pin(rx, 'reset', 'INPUT', None)
    if change == 'no_proof': proof = {}
    if change == 'native_waiver': proof['qfd_clkrx']['physical_qualification_eligible'] = True
    if change == 'unknown_output': output.port = 'pll_unknown'
    if change == 'data_source': source.port = 'payload'
    if change == 'unknown_source_master': source.inst.master = 'unknown_model'
    with pytest.raises(ValueError): preflight(source, {'dc_root_r0'}, {'rx/pll_r0'}, proof)


def test_final_check_refuses_remaining_boundary_load_even_without_iterm_input():
    _, rx, _, output, ld, _ = fixture()
    output.net.its.remove(ld)
    output.net.bts.append(NS(getIoType=lambda: 'OUTPUT'))
    with pytest.raises(ValueError, match='BTerm'): assert_disconnected(rx)


def test_actual_scalar_bus_pin_names_and_explicit_repaired_master():
    source, rx, inp, output, ld, proof = fixture()
    rx.master = 'qfd_clkrx_qclk'
    inp.port += '[0]'; output.port += '[0]'
    assert preflight(source, {'dc_root_r0'}, {'rx/pll_r0[0]'}, proof) == [inp]
