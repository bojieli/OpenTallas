#!/usr/bin/env python3
"""Private t16 TX+8-cycle, compact-encoder PLACE prototype; never changes a POR."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

def ignore(directory, names):
    return [n for n in names if n in {'run','signoff','lec','views','render','__pycache__','kwrs_make.sh'}
            or n.startswith(('.kwrs_done','sta_','postcts_gate_','insertion_band'))
            or n in {'PROVENANCE.json','image.txt'} or n.endswith('.log')]

def kit_column(s):
    # The kit's _bb.v abstracts define ot_s81_pma_txm/rxm; the repo column file's behavioural copies stop LEC elaboration.
    i=s.index('module ot_s81_pma_txm');j=s.rfind('// ----',0,s.rfind('// ----',0,i));tail=s[j:]
    if tail.count('module ')!=2 or tail.count('endmodule')!=2 or 'ot_s81_pma_rxm' not in tail:raise SystemExit('unexpected PMA tail in column RTL; destination retained')
    return s[:j].rstrip()+'\n'
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('baseline',type=Path);p.add_argument('destination',type=Path)
    p.add_argument('--column-rtl',type=Path,required=True)
    p.add_argument('--clock-taps',type=Path,required=True,help='RCK-4 candidate supporting OT_TAP_GROUP_ALIAS')
    a=p.parse_args();src=a.baseline.resolve(strict=True);dst=a.destination.absolute()
    if dst.exists():raise SystemExit('destination exists; no overwrite')
    if 'serdes__t16' not in (src/'config.mk').read_text():raise SystemExit('this profile is t16 only')
    if 'OT_TAP_GROUP_ALIAS' not in a.clock_taps.read_text():raise SystemExit('required existing alias mechanism absent')
    shutil.copytree(src,dst,ignore=ignore)
    rtl=dst/'rtl';(rtl/'ot_pdie_serdes_col.sv').write_text(kit_column(a.column_rtl.read_text()))
    bound=rtl/'s81p_serdes__t16_bound.sv';text=bound.read_text()
    text,n=re.subn(r'(\.TXL\()2(\)\) u_core)',r'\g<1>7\2',text)
    if n!=1:raise SystemExit(f'TXL2 target count {n}, destination retained')
    bound.write_text(text)
    here=Path(__file__).resolve().parent
    shutil.copy2(here/'rck_tx_compact.tcl',dst/'rck_tx_compact.tcl')
    shutil.copy2(a.clock_taps,dst/'clock_taps.tcl')
    config=(dst/'config.mk').read_text()
    wrappers={
      'PRE_GLOBAL_PLACE_TCL':'source /work/rck_tx_compact.tcl\nrck_tx_compact_regions\nrck_tx_pin_positions\nsource {old}\nrck_tx_pin_positions\n',
      'PRE_DETAIL_PLACE_TCL':'source /work/rck_tx_compact.tcl\nsource {old}\nrck_tx_compact_regions\nrck_tx_pin_positions\nsource /work/chain_even_cfg.tcl\nlappend ::ot_chain_res [list {u_bin_coll_i0[./]q} {u_tx_pin[./]pin_q}]\nlappend ::ot_chain_res [list {u_tx_pin[./]u_enc[./]p_d} {u_txl[./]}]\nlappend ::ot_chain_res [list {u_tx_pin[./]u_enc[./]p_v} {u_txl[./]}]\nsource /work/chain_even.tcl\nsource /work/clock_taps.tcl\nrck_tx_release_regions\n'}
    extra=['\n# PRIVATE RCK TX PIN/compact form; no POR adoption.','export VERILOG_DEFINES += -DOT_S81_SERDES_COL_PIN','override export OT_TAP_MAX_SINKS = 6500']
    for key,body in wrappers.items():
        values=re.findall(r'^(?:override\s+)?export\s+'+key+r'\s*=\s*(.+)$',config,re.M)
        if not values or not values[-1].startswith('/work/'):raise SystemExit(f'unresolved {key}; destination retained')
        name='rck_tx_'+key.lower()+'.tcl';(dst/name).write_text(body.replace('{old}',values[-1].strip()))
        extra.append(f'override export {key} = /work/{name}')
    (dst/'config.mk').write_text(config+'\n'.join(extra)+'\n')
    report={'baseline':str(src),'prototype':str(dst),'POR_changed':False,
       'TX_cycles_vs_current_COL_TXL2':8,'TX_cycles_vs_untried_vF_COL_TXL2':8,
       'TX_breakdown':{'coherent_input_stages':3,'old_TXL':2,'new_TXL':7},
       'TX_added_ns_at_833ps':6.664,'encoder_reset_release_added_edges':3,
       'encoder_fault_calendar_added_edges':3,
       'RX_cycles_vs_current_POR':'inherited RM_STAGED +1 is still unadopted; not assumed part of POR',
       'RX_cycles_vs_untried_vF':0,
       'changes':['BIN local to CLAND; no BIN/ENC alias','200x200um encoder registered-cone region at fixed clk_t34','3 coherent input stages and 7 output relay rows','actual per-bit chain placement with existing chain_even','6500 max sinks; encoder plus final input row fits ~6439 sinks'],
       'proof_required':'final PAD7 actual encoder lockstep + bypass mutant; mapped/routed LEC still required',
       'holds':['PLACE images and actual hop lengths before CTS/GRT','RX rck and FT clock classes remain open; no whole-RCK closure claim'],
       'column_rtl_sha256':hashlib.sha256((rtl/'ot_pdie_serdes_col.sv').read_bytes()).hexdigest(),
       'clock_taps_candidate_sha256':hashlib.sha256(a.clock_taps.read_bytes()).hexdigest()}
    (dst/'SOURCE_PROFILE.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
