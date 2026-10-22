"""Opt-in source-complete core publisher; local edge price is separate from die transport."""
import hashlib
from pathlib import Path
CONTRACTS = {'1': {'master': 'qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1', 'source': 'rtl/qwen_dv/headprep13/corepub39/qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1.sv', 'sha256': 'e95e85e7b41551258e3b50b5bed95806d7968a548540d2dffedfc1af59fb8806', 'publisher_stages': 1, 'gi_to_output_core_edges': 1, 'calendar_to_output_core_edges': 2}, '2': {'master': 'qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_2', 'source': 'rtl/qwen_dv/headprep13/corepub39/qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_2.sv', 'sha256': '6b6c3fa18de62ec8528099c0edae4db6f3069f91976f81dd23eda29fbcbbb974', 'publisher_stages': 2, 'gi_to_output_core_edges': 2, 'calendar_to_output_core_edges': 3}}
BANK = 'rtl/qwen_dv/headprep13/corepub39/qfd_hp13_corepub39.sv'
BANK_SHA = '7db853e9efab5755151aa9b8da28175614031b5ad7fe6e2d1a1a7fbd4b47f69c'

def contract(value):
    if value not in CONTRACTS:
        raise ValueError('OT_QWEN_HP13_COREPUB must be 0 (legacy), 1 (MAIN), or 2 (FB)')
    return CONTRACTS[value]

def select(root, value):
    c=contract(value); root=Path(root)
    for path, expected in [(c['source'],c['sha256']),(BANK,BANK_SHA)]:
        if hashlib.sha256((root/path).read_bytes()).hexdigest()!=expected:
            raise ValueError('core publisher source identity differs: '+path)
    return c['master'],c['source']
