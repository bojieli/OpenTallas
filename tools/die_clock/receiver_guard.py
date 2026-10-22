"""Fail-closed ODB preflight for removing an explicitly modeled clock receiver."""
import re

RECEIVER_MASTERS = {'qfd_clkrx', 'qfd_clkrx_qclk'}  # exact clone produced by qwen_clkrx_ports.py


def scalar_port(it):
    return re.sub(r'\[0\]$', '', it.getMTerm().getName())


def pin_name(it):
    return f'{it.getInst().getName()}/{it.getMTerm().getName()}'


def _loads(net):
    if net is None:
        return [], []
    return ([it for it in net.getITerms() if it.getIoType() in ('INPUT', 'INOUT')], list(net.getBTerms()))


def preflight(source, member_buffers, member_roots, modeled):
    """Return receiver input ITerms only after every output is accounted for.

    BTerms are never disposable: an output/inout BTerm is a real boundary load;
    an input BTerm is an additional source. The explicit model remains MODEL_ONLY.
    """
    if source.getIoType() != 'OUTPUT' or source.getNet() is None:
        raise ValueError('receiver removal: missing/output-direction clock source')
    if source.getInst().getMaster().getName() != 'qfd_ckbump' or scalar_port(source) != 'pll_ck':
        raise ValueError('receiver removal: unknown/non-clock source; requires actual qfd_ckbump.pll_ck')
    net = source.getNet()
    drivers = [it for it in net.getITerms() if it.getIoType() in ('OUTPUT', 'INOUT')]
    if len(drivers) != 1 or pin_name(drivers[0]) != pin_name(source) or list(net.getBTerms()):
        raise ValueError('receiver removal: unknown or multiple source clock root/BTerm')
    inputs, _ = _loads(net)
    receivers = []
    for it in inputs:
        if it.getInst().getName() in member_buffers:
            continue
        if it.getInst().getMaster().getName() not in RECEIVER_MASTERS or scalar_port(it) != 'pll_fwd':
            raise ValueError(f'receiver removal: non-clock receiver input or non-member {pin_name(it)}')
        receivers.append(it)
    if len(receivers) != 1:
        raise ValueError('receiver removal requires exactly one actual qfd_clkrx.pll_fwd')
    proof = modeled.get('qfd_clkrx', {})
    if proof.get('view') != 'MODEL_PASS_THROUGH_R0' or proof.get('physical_qualification_eligible') is not False or \
            not re.fullmatch('[0-9a-f]{64}', proof.get('rtl_sha256', '')):
        raise ValueError('receiver removal requires explicit identity model proof; qualification remains MODEL_ONLY')
    rx = receivers[0].getInst()
    for it in rx.getITerms():
        port = scalar_port(it)
        if it.getIoType() == 'INPUT':
            if port != 'pll_fwd':
                raise ValueError(f'receiver removal: non-clock/reset/data input {pin_name(it)}')
            continue
        if it.getIoType() != 'OUTPUT' or not re.fullmatch(r'pll_(?:root|d2d|coll|serial|serdes[0-9]*|r[0-9]+)', port):
            raise ValueError(f'receiver removal: non-clock/reset/data output {pin_name(it)}')
        loads, boundary = _loads(it.getNet())
        if boundary:
            raise ValueError(f'receiver removal: output still drives BTerm {pin_name(it)}')
        if loads and (pin_name(it) not in member_roots or
                      any(ld.getInst().getName() not in member_buffers for ld in loads)):
            raise ValueError(f'receiver removal: output still drives non-member loads {pin_name(it)}')
    return receivers


def assert_disconnected(receiver):
    for it in receiver.getITerms():
        if it.getIoType() == 'OUTPUT':
            loads, boundary = _loads(it.getNet())
            if loads or boundary:
                raise ValueError(f'receiver removal: output still drives loads/BTerm {pin_name(it)}')
