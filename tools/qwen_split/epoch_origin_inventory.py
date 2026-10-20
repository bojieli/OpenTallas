#!/usr/bin/env python3
"""Source-bound existing-event endpoints for a future static shared-origin receipt."""
import argparse, hashlib, json, re
from pathlib import Path

ROLES={
 'package_clock_reset':('ckb_rom',['pll_ck','rs']),
 'forwarded_clock_roots':('clk_rx',['pll_fwd','pll_d2d','pll_r54','pll_r55']),
 'package_run_epoch':('bump_fwd_epoch',['o']),
 'face_run_anchor':('sys_face',['ck','rst_n','fwd_epoch','cal_start','cal_seg','tt_layer_context_v','tt_command_stage']),
 'producer_calendar_and_slots':('d2d_rom',['ck','por_n','rst_n','fwd_epoch','cal_start','cal_seg','native_tx_slot','native_tx_slot_kind','native_tx_slot_beat']),
 'consumer_command_context':('tt_ctlm',['ck','rst_n','native_cmd','layer_context_v','command_stage','native_tok','native_pos','dc']),
 'consumer_service_inputs':('native59',['ck','rst_n','tx_slot','tx_slot_kind','tx_slot_beat','native_cmd','layer_context_v','command_stage']),
 'current_landing':('rly_lnk_native_tx_slot_0',['ck_s','en','ck','rs','a','b','k0','k1','k2'])}

def inventory(text,source_commit):
    instances={}
    for line in text.splitlines():
        m=re.match(r'\s*(\w+)\s+(?:#\(.*?\)\s+)?(\w+)\s+\(',line)
        if m:
            master,name=m.groups(); instances[name]=dict(master=master,ports=dict(re.findall(r'\.(\w+)\((\w+)\)',line)))
    endpoints={};errors=[]
    for role,(inst,ports)in ROLES.items():
        if inst not in instances:errors.append('MISSING_INSTANCE:'+inst);continue
        rec=instances[inst]
        missing=[p for p in ports if p not in rec['ports']]
        if missing:errors.append('MISSING_PORTS:'+inst+':'+','.join(missing))
        endpoints[role]=dict(instance=inst,master=rec['master'],pins={inst+'/'+p:rec['ports'].get(p)for p in ports})
    fields=['global_source_to_consumer_edges','source_to_native_input_edges','native_output_to_consumer_edges',
            'cal_start_face_global_edge','face_to_cal_start_pin_edges','first_event_dt','last_cfg_core_global_edge',
            'context_pin_global_edge','context_to_first_slot_edges','shared_epoch_global_edge','compiled_boot_edges',
            'source_stores_ready_global_edge']
    c=dict(enabled=False,mode='static_existing_events',upstream_clock_reset_correlated=False,origin_receipt_sha256=None,
           period_ps=833.333,calendar_input_pr_edges=1,calendar_output_pr_edges=1,native_kind=None,cases=None)
    c.update({k:None for k in fields})
    c['provenance']=dict(compute_source_commit=source_commit,netlist_sha256=hashlib.sha256(text.encode()).hexdigest(),
                         local_PR_price_scope='actual qfd_d2d_static PR default1; prove selected parameters on a successor',
                         current_native_class='D4; cannot qualify D8 from this instance')
    c['actual_endpoints']=endpoints;c['inventory_errors']=errors
    c['source_gaps']=['Package/PLL reset waveform and actual run-epoch strobe provider beyond hard macro bump models',
       'One source-clocked semantic epoch receipt joining face/cal_start and tt_ctlm native context instruction origins',
       'Actual image-pinned first dt, final cal_start transport and complete valid/kind/beat bundle ages',
       'First-use context installation relation from selected native59 RTL (v3 alignment is unadmitted)',
       'Actual D8 four-strap native instance, raw en/rs corner cases, phase, resets and warm/first-valid receipts']
    return c

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--netlist',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=inventory(a.netlist.read_text(),a.source_commit);a.out.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(dict(roles=len(r['actual_endpoints']),errors=r['inventory_errors'],production_ready=False)))
if __name__=='__main__':main()
