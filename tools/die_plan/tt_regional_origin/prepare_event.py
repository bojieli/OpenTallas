#!/usr/bin/env python3
"""Build a default-OFF, paired TT_C regional-origin source/model proposal; never adopts a kit or plan."""
import argparse, hashlib, json, re
from pathlib import Path

def build(wrapper, mapping, homes, out, outer=None, raw_homes=None):
    text=wrapper.read_text()
    if text.count('ot_dp_landing_origin_s #(.PADW(1)) u_cland_origin')!=1:
        raise ValueError('Requires exact frozen TT_C PADW=1 origin; no generic source substitution')
    if len(mapping)!=37 or set(mapping.values())!={0,1,2,3}:
        raise ValueError('Requires all37 actual receiving instances and four nonempty regions')
    original=text
    text=re.sub(r'(module\s+qfd_qc_tt_ctlm_part_bound)\s*\(',r'\1 #(parameter integer OT_TT_REGIONAL_ORIGIN=0) (',text,count=1)
    text=text.replace('    wire cland_start;', '    wire [3:0] cland_start_r, cland_start_d_r, cland_raw_r;\n    wire cland_start;')
    raw='''    generate if (OT_TT_REGIONAL_ORIGIN != 0) begin : g_tt_raw_regions
        for (genvar r=0;r<4;r=r+1) begin : g_region
            (* keep=1, keep_hierarchy="yes" *) ot_dp_rrelay u_raw_copy (
                .clk(clk),.d(rst_rl_85),.q(cland_raw_r[r]));
        end
    end else begin : g_tt_raw_off
        assign cland_raw_r={4{rst_n_t0}};
    end endgenerate
'''
    text=text.replace('    assign cland_start_raw = rst_n_t0;',raw+'    assign cland_start_raw = rst_n_t0;')
    pat=r'ot_dp_landing_origin_s #\(\.PADW\(1\)\) u_cland_origin\s*\((.*?)\);'
    match=re.search(pat,text,re.S)
    args=match.group(1).replace('.rst_raw_n(rst_n_t0)', '.rst_raw_n(rst_n_t0), .rst_region_raw_n(cland_raw_r)').replace('.start(cland_start)', '.start_r(cland_start_r)').replace('.start_d(cland_start_d)', '.start_d_r(cland_start_d_r)')
    text=text[:match.start()]+'ot_dp_landing_origin_s_regional #(.PADW(1),.ENABLE(OT_TT_REGIONAL_ORIGIN)) u_cland_origin ('+args+');\n    assign cland_start=cland_start_r[0];\n    assign cland_start_d=cland_start_d_r[0];'+text[match.end():]
    used={}
    pat=re.compile(r'(^\s*ot_dp_(?:clk_landing_cas|landing_relay)(?:\s*#\([^\n]*\))?\s+(u_cland_\w+)\s*\()(.*?)(\);)',re.M|re.S)
    def replace(m):
        key='u_bound.'+m.group(2);body=m.group(3)
        if 'cland_start)' not in body and 'cland_start_d)' not in body:return m.group(0)
        if key not in mapping:raise ValueError('Unpriced receiver '+key)
        r=mapping[key];used[key]=r
        body=body.replace('.rst_n(cland_start)',f'.rst_n(cland_start_r[{r}])').replace('.d(cland_start_d)',f'.d(cland_start_d_r[{r}])').replace('.rst_raw_n(cland_start_raw)',f'.rst_raw_n(cland_raw_r[{r}])')
        return m.group(1)+body+m.group(4)
    text=pat.sub(replace,text)
    if used!=mapping:raise ValueError('Source/model receiver mismatch: '+str(set(mapping)-set(used)))
    out.mkdir(parents=True,exist_ok=True)
    target=out/'qfd_qc_tt_ctlm_part_bound_DISABLED.sv';target.write_text(text)
    event=dict(schema='opentallas.tt_regional_origin_event.v1',enabled=False,type='tt_ctlm',cohort='exact existing TT_C63tap',source_wrapper=str(wrapper),source_sha256=hashlib.sha256(original.encode()).hexdigest(),candidate_sha256=hashlib.sha256(text.encode()).hexdigest(),opt_in_parameter='OT_TT_REGIONAL_ORIGIN',default=0,padw=1,regions=4,receiver_regions=used,homes=homes,raw_regional_leaves=[dict(name=f'u_bound.g_tt_raw_regions.g_region[{h["region"]}].u_raw_copy/q',xy=h['xy'],parent='rst_rl_85',depth=3,clock='clk',role='raw') for h in homes if h['stage']=='s2'],clock_association='All moved old FFs and +13 new FFs require explicit existing63port same-cohort nearest metadata/radius200/max1200; old999 not transferred',price=dict(added_mission_cycles=0,added_boot_cycles=0,added_posedge_clock_sinks=13,added_raw_reset_sinks=9,added_upstream_reset_data_sinks=4,added_input_p_start_sinks=0,added_s0_data_sinks=3,added_strap_pad_mux_consumers=3,old_state_ff_including_parent_raw_leaf=6,new_state_ff_including_parent_and_copies=19,added_state_ff=13,clock='same existing clk, no new root/guide',reset='retain existing central rst_n_t0/u_rrl_87;4 same-D/CLK/depth copies from rst_rl_85; regional branch resets/FSTART take local copy; no new release edge'),preserved=['SF/S0 sampling and input fanout','all old start/start_d output functions','existing pins/macro homes/ports/type and pad count'],paired_gates=['native local reset64 lockstep and mutants','parent clock/reset load model and reset/source tree rederive as ONE event','typed all-pair geometry including actual macro ports','actual GEN/G0C0new/strictbind0/LOOK before physical','no partial45-only placement or full LEC rerun'])
    if raw_homes is not None:
        event['raw_regional_leaves']=[dict(name=f'u_bound.g_tt_raw_regions.g_region[{h["region"]}].u_raw_copy/q',xy=h['xy'],parent='rst_rl_85',depth=3,clock='clk',role='raw') for h in raw_homes]
    event['source_files']={'replace':{str(wrapper):str(target)},'append':[str(Path(__file__).with_name('ot_dp_landing_origin_s_regional.sv'))]}
    if outer is not None:
        outer_text=outer.read_text()
        if outer_text.count('qfd_qc_tt_ctlm_part_bound u_bound (')!=1:raise ValueError('Unexpected frozen outer wrapper')
        outer_text=re.sub(r'(module\s+qfd_qc_tt_ctlm_part)\s*\(',r'\1 #(parameter integer OT_TT_REGIONAL_ORIGIN=0) (',outer_text,count=1)
        outer_text=outer_text.replace('qfd_qc_tt_ctlm_part_bound u_bound (','qfd_qc_tt_ctlm_part_bound #(.OT_TT_REGIONAL_ORIGIN(OT_TT_REGIONAL_ORIGIN)) u_bound (')
        outer_target=out/'qfd_qc_tt_ctlm_part_DISABLED.sv';outer_target.write_text(outer_text)
        event['source_files']['replace'][str(outer)]=str(outer_target)
        event['top_parameter']='qfd_qc_tt_ctlm_part.OT_TT_REGIONAL_ORIGIN (default0; explicit1 only in reviewed disabled source-event snapshot)'
    (out/'regional_origin_event_DISABLED.json').write_text(json.dumps(event,indent=1)+'\n')
    return event
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--wrapper',type=Path,required=True);ap.add_argument('--regions',type=Path,required=True);ap.add_argument('--homes',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--outer',type=Path);ap.add_argument('--raw-homes',type=Path);a=ap.parse_args();e=build(a.wrapper,json.loads(a.regions.read_text()),json.loads(a.homes.read_text()),a.out,a.outer,json.loads(a.raw_homes.read_text()) if a.raw_homes else None);print('TT_REGIONAL_DISABLED_PREP',len(e['receiver_regions']),'receivers +13FF +0cycles')
