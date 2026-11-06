#!/usr/bin/env python3
"""Fresh HEAD RXQ overlay; never modify the donor or canonical adapter.

The default-off parameter is appended to the private RXQ module. Selecting1
is an explicit private adapter binding and does not change any main recipe.
"""
import argparse, hashlib, json
from pathlib import Path

def patch_rxq(text, expected_sha=None):
    digest=hashlib.sha256(text.encode()).hexdigest()
    if expected_sha and digest!=expected_sha:raise ValueError('RXQ source differs from the selected exact donor')
    old='module ot_s81hd_pdie_q #(parameter integer PMA_LAT = 4, parameter integer EMUT = 0, parameter integer DMUT = 0) ('
    new=old.replace('DMUT = 0)', 'DMUT = 0, parameter bit RX_FIRST_FALL = 0)')
    if text.count(old)!=1:raise ValueError('exact RXQ top parameter declaration required')
    text=text.replace(old,new)
    old='ot_s81_pma_bm #(.W(544), .LAT(PMA_LAT)) u_prx'
    new='ot_s81hd_pma_rx_capture #(.W(544), .LAT(PMA_LAT), .FIRST_FALL(RX_FIRST_FALL)) u_prx'
    if text.count(old)!=1:raise ValueError('exact single RX capture instance required')
    return text.replace(old,new)

def patch_adapter(text, first_fall):
    old='ot_s81hd_pdie_q #(.PMA_LAT(PMA_LAT)) u_link'
    if text.count(old)!=1:raise ValueError('exact private RXQ adapter required; canonical source is not activated here')
    return text.replace(old,f'ot_s81hd_pdie_q #(.PMA_LAT(PMA_LAT), .RX_FIRST_FALL({first_fall})) u_link')

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--rxq',type=Path,required=True);a.add_argument('--adapter',type=Path,required=True);a.add_argument('--expected-rxq-sha256',required=True);a.add_argument('--first-fall',type=int,choices=(0,1),default=0);a.add_argument('--out',type=Path,required=True);a=a.parse_args()
    if a.out.exists():a.error('fresh output required; preserve old source/verdicts')
    rxq=patch_rxq(a.rxq.read_text(),a.expected_rxq_sha256);adapter=patch_adapter(a.adapter.read_text(),a.first_fall)
    helper=Path(__file__).resolve().parents[2]/'rtl/dsrom_sys/s81_head/ot_s81hd_pma_rx_capture.sv'
    if not helper.is_file():raise ValueError('actual HEAD capture RTL missing')
    helper_text=helper.read_text()
    a.out.mkdir(parents=True)
    (a.out/helper.name).write_text(helper_text)
    (a.out/'overlay.f').write_text(a.rxq.name+'\n'+a.adapter.name+'\n'+helper.name+'\n')
    for n,s in [(a.rxq.name,rxq),(a.adapter.name,adapter)]: (a.out/n).write_text(s)
    (a.out/'binding.json').write_text(json.dumps(dict(source='exact private RXQ donor',helper_sha256=hashlib.sha256(helper_text.encode()).hexdigest(),overlay_files=[a.rxq.name,a.adapter.name,helper.name],old_source_closure='retained donor dependencies still required; overlay.f is only replacements/addition',first_fall=a.first_fall,default_parameter=0,rxq_input_sha256=a.expected_rxq_sha256,rxq_output_sha256=hashlib.sha256(rxq.encode()).hexdigest(),adapter_output_sha256=hashlib.sha256(adapter.encode()).hexdigest(),stages=4,width=544,stage0_edge='fall' if a.first_fall else 'rise',remaining_edges='rise',tx_change=0,external_transport_age='must remeasure; no fixed core/HOST age inherited'),indent=1)+'\n')
if __name__=='__main__':main()
