"""Single fullgeometry opt-in staged DIG8 source preparation. No tool launch."""
import argparse
import hashlib
import json
from pathlib import Path
import prepare_topk_station_caller_fence as F
import prepare_dsrom_full_selector_dma_fixture as V
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/rtl/dsrom_balanced_selector_candidate_prepare_20261002'
SOURCE=ROOT/(V.ORIGIN+'ot_coll_topk_merge.sv')
PARAMS=['N','NMAX','LW','LDW','P','PF','DIG','RB','CAP','CB','WB','OW']
PORTS=['clk','rst_n','ld_valid','ld_id','ld_rank','ld_word','ld_data','go','n','k','stride','busy','done','fault','out_valid','out_nw','out_data','out_last','stat_cycles']

def replace(s,a,b):return F.replace_once(s,a,b)
def bits():
    return dict(hist_internal=256*sum((64>>l)*(l+1) for l in range(1,6)),hist_valid_net=5,
        suffix_up=255*14,suffix_down_internal=254*14,
        choose_lower_and_modular_sum=256*15,choose_predicate=256,choose_internal=254*23,choose_root_valid=1,
        pick_counter_net=3,eq_prefix_counts=64*sum(range(2,8)),eq_payload=34*64*6,eq_valid=6,
        sort_internal_records=20*64*39,take_popcount_internal=sum((64>>l)*(l+1) for l in range(1,6)),
        take_count_carrier=15*7,sort_valid=20)

def staged(source):
    s=replace(source,'module ot_coll_topk_merge #(','module ot_coll_topk_merge_staged_impl_prepare #(\n    parameter integer MUTANT = 0,')
    # Both arrays retain source load/key/ID ordering and word addressing.
    s=replace(s,'    reg              h0_v, h1_v, h2_v;','    reg h0_v,h1_v;\n    wire h2_v;\n    reg [5:0] hist_valid;\n    assign h2_v=hist_valid[5];\n    always @(posedge clk or negedge rst_n)\n      if(!rst_n) hist_valid<=0; else hist_valid<={hist_valid[4:0],h1_v};')
    start=s.index('        for (b = 0; b < NBIN; b = b + 1) begin : pc')
    stop=s.index('\n    end\n\n    // ---- PICK',start)
    s=s[:start]+s[stop:]
    hist=[]
    for l in range(1,7):
        count=64>>l;width=l+1
        if l<6:hist.append(f'    reg [{width-1}:0] hist_pc_{l}[0:NBIN-1][0:{count-1}];')
        hist.append(f'    generate for(genvar hb{l}=0;hb{l}<NBIN;hb{l}=hb{l}+1) begin:g_hist_{l}')
        hist.append(f'      for(genvar hi{l}=0;hi{l}<{count};hi{l}=hi{l}+1) begin:g_pair')
        if l==1:a=f'h1_hot[hb{l}][2*hi{l}]';b=f'h1_hot[hb{l}][2*hi{l}+1]'
        else:a=f'hist_pc_{l-1}[hb{l}][2*hi{l}]';b=f'hist_pc_{l-1}[hb{l}][2*hi{l}+1]'
        dst=f'hist_pc_{l}[hb{l}][hi{l}]' if l<6 else f'h2_pc[hb{l}]'
        hist += [f"        always @(posedge clk) {dst}<={width}'({a})+{width}'({b});",'      end','    end endgenerate']
    s=replace(s,'    // ---- PICK', '\n'.join(hist)+'\n\n    // ---- PICK')
    s=replace(s,'    reg  [1:0]      pk;','    reg [4:0] pk;\n    reg pvalid;')
    s=replace(s,"wpr <= NMAX / LW; h0_v <= 1'b0; h1_v <= 1'b0; h2_v <= 1'b0;","wpr <= NMAX / LW; h0_v <= 1'b0; h1_v <= 1'b0; pvalid <= 0;")
    s=replace(s,'            h2_v <= h1_v;','            // Final six-level histogram token is h2_v.')
    decl=[]
    for l in range(8):
        decl += [f'    reg [CB-1:0] suffix_up_{l}[0:{(256>>(l+1))-1}];',
                 f'    generate for(genvar su{l}=0;su{l}<{256>>(l+1)};su{l}=su{l}+1) begin:g_up_{l}']
        a=f'cnt[2*su{l}]' if l==0 else f'suffix_up_{l-1}[2*su{l}]'
        b=f'cnt[2*su{l}+1]' if l==0 else f'suffix_up_{l-1}[2*su{l}+1]'
        decl += [f'      always @(posedge clk) if(st==S_PICK && pk=={l}) suffix_up_{l}[su{l}]<=CB\'({a}+{b});','    end endgenerate']
    for l in range(8):
        if l<7:decl.append(f'    reg [CB-1:0] suffix_down_{l}[0:{(2<<(l))-1}];')
        count=1<<l
        parent="CB'(0)" if l==0 else f'suffix_down_{l-1}[sd{l}]'
        right=f'suffix_up_{6-l}[2*sd{l}+1]' if l<7 else f'cnt[2*sd{l}+1]'
        arr=f'suffix_down_{l}' if l<7 else 'suf'
        decl += [f'    generate for(genvar sd{l}=0;sd{l}<{count};sd{l}=sd{l}+1) begin:g_down_{l}',
                 f"      always @(posedge clk) if(st==S_PICK && pk=={8+l}) begin\n        {arr}[2*sd{l}]<=CB'({parent}+{right});\n        {arr}[2*sd{l}+1]<={parent};\n      end",'    end endgenerate']
    decl += ['    reg [CB:0] choose_lower_sum[0:NBIN-1];','    reg [NBIN-1:0] choose_pred;',
      '    generate for(genvar cp=0;cp<NBIN;cp=cp+1) begin:g_predicate',
      "      always @(posedge clk) begin\n        if(st==S_PICK && pk==16) choose_lower_sum[cp]<={(suf[cp]<rr),CB'(suf[cp]+cnt[cp])};\n        if(st==S_PICK && pk==17) choose_pred[cp]<=choose_lower_sum[cp][CB] && (rr<=choose_lower_sum[cp][CB-1:0]);\n      end",'    end endgenerate']
    for l in range(7):
        count=128>>l
        decl += [f'    reg [CB+DIG:0] choose_node_{l}[0:{count-1}];',f'    generate for(genvar cw{l}=0;cw{l}<{count};cw{l}=cw{l}+1) begin:g_winner_{l}']
        if l==0:
            a=f"{{choose_pred[2*cw{l}],DIG'(2*cw{l}),suf[2*cw{l}]}}"
            b=f"{{choose_pred[2*cw{l}+1],DIG'(2*cw{l}+1),suf[2*cw{l}+1]}}"
            v=f'choose_pred[2*cw{l}+1]'
        else:a=f'choose_node_{l-1}[2*cw{l}]';b=f'choose_node_{l-1}[2*cw{l}+1]';v=b+'[CB+DIG]'
        decl += [f'      always @(posedge clk) if(st==S_PICK && pk=={18+l}) choose_node_{l}[cw{l}]<={v}?{b}:{a};','    end endgenerate']
    decl += ['    wire [CB+DIG:0] choose_root=choose_node_6[1][CB+DIG]?choose_node_6[1]:choose_node_6[0];']
    s=replace(s,'    // ---- FILTER', '\n'.join(decl)+'\n\n    // ---- FILTER')
    start=s.index('                    if (pk == 0) begin : sufs')
    stop=s.index('                        prefix <=',start)
    s=s[:start]+'''                    if(pk==25) begin
                        pvalid<=choose_root[CB+DIG];
                        if(choose_root[CB+DIG]) begin
                            pbin<=choose_root[CB+DIG-1:CB];pgt<=choose_root[CB-1:0];
                        end
                    end
                    if (pk == 26) begin
'''+s[stop:]
    s=replace(s,'{{(32-DIG){1\'b0}}, pbin}',"{{(32-DIG){1'b0}}, (pbin ^ DIG'(MUTANT==1))}")
    # Prefix eq count and ID/mask carriers: exactly six registered Hillis-Steele levels.
    eq=[]
    for l in range(6):
        eq += [f'    reg [{l+1}:0] eq_count_{l}[0:PF-1];',f'    reg [32*PF-1:0] eq_id_{l};',f'    reg [PF-1:0] eq_gt_{l},eq_mask_{l};',f'    reg eq_v_{l};',
               f'    always @(posedge clk or negedge rst_n) if(!rst_n) eq_v_{l}<=0; else eq_v_{l}<='+( 'f1_v;' if l==0 else f'eq_v_{l-1};'),
               f'    always @(posedge clk) begin\n      eq_id_{l}<='+( 'f1_id;' if l==0 else f'eq_id_{l-1};')+f'\n      eq_gt_{l}<='+( 'f1_gt;' if l==0 else f'eq_gt_{l-1};')+f'\n      eq_mask_{l}<='+( 'f1_eq;' if l==0 else f'eq_mask_{l-1};')+'\n    end']
        a=f'f1_eq[ep{l}]' if l==0 else f'eq_count_{l-1}[ep{l}]'
        b=f'f1_eq[ep{l}-{1<<l}]' if l==0 else f'eq_count_{l-1}[ep{l}-{1<<l}]'
        eq += [f'    generate for(genvar ep{l}=0;ep{l}<PF;ep{l}=ep{l}+1) begin:g_eq_{l}',
               f"      if(ep{l}>={1<<l}) always @(posedge clk) eq_count_{l}[ep{l}]<={l+2}'({a})+{l+2}'({b});",
               f"      else always @(posedge clk) eq_count_{l}[ep{l}]<={l+2}'({a});",'    end endgenerate']
    s=replace(s,'    wire             fpipe = f0_v || f1_v || f2_v || f3_v || f4_v;', '    wire fpipe=f0_v || f1_v || f2_v || f3_v || f4_v || '+ ' || '.join(f'eq_v_{l}' for l in range(6))+' || (|sort_valid);')
    # Registered bitonic network, records are {invalid,lane,id}; key width7.
    sort=['    reg [19:0] sort_valid;',"    always @(posedge clk or negedge rst_n)\n      if(!rst_n) sort_valid<=0; else sort_valid<={sort_valid[18:0],f3_v};"]
    stages=[];k=2
    while k<=64:
        j=k//2
        while j:
            stages.append((k,j));j//=2
        k*=2
    for stage,(k,j) in enumerate(stages,1):
        if stage<21:sort.append(f'    reg [38:0] sort_record_{stage}[0:PF-1];')
        sort.append(f'    generate for(genvar si{stage}=0;si{stage}<PF;si{stage}=si{stage}+1) begin:g_sort_{stage}')
        a=f'{{f3_tp[si{stage}],f3_id[32*si{stage}+:32]}}' if stage==1 else f'sort_record_{stage-1}[si{stage}]'
        partner=f'(si{stage}^{j})'
        b=f'{{f3_tp[{partner}],f3_id[32*{partner}+:32]}}' if stage==1 else f'sort_record_{stage-1}[{partner}]'
        sort += [f'      wire [38:0] here={a},other={b};',f'      wire ascending=(si{stage}&{k})==0;',f'      wire lower_lane=(si{stage}&{j})==0;',
                 '      wire choose_min=(ascending==lower_lane);',
                 '      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;']
        if stage<21:sort.append(f'      always @(posedge clk) sort_record_{stage}[si{stage}]<=chosen;')
        else:sort.append(f"      always @(posedge clk) f4_c[32*si{stage}+:32]<=chosen[38]?32'd0:chosen[31:0];")
        sort.append('    end endgenerate')
    for l in range(1,6):
        count=64>>l
        sort += [f'    reg [{l}:0] take_count_{l}[0:{count-1}];',f'    generate for(genvar tc{l}=0;tc{l}<{count};tc{l}=tc{l}+1) begin:g_take_count_{l}']
        a=f'f3_take[2*tc{l}]' if l==1 else f'take_count_{l-1}[2*tc{l}]'
        b=f'f3_take[2*tc{l}+1]' if l==1 else f'take_count_{l-1}[2*tc{l}+1]'
        sort += [f"      always @(posedge clk) take_count_{l}[tc{l}]<={l+1}'({a})+{l+1}'({b});",'    end endgenerate']
    for l in range(6,21):
        sort.append(f'    reg [6:0] take_total_{l};')
        val="7'(take_count_5[0])+7'(take_count_5[1])" if l==6 else f'take_total_{l-1}'
        sort.append(f'    always @(posedge clk) take_total_{l}<={val};')
    s=replace(s,'    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) begin', '\n'.join(eq+sort)+'\n\n    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) begin')
    start=s.index('                    // f2: take')
    stop=s.index('                    // f5: append',start)
    s=s[:start]+'''                    // Fullsource row-order quota feedback after six prefix edges.
                    f2_v<=eq_v_5; f2_id<=eq_id_5;
                    for(l=0;l<PF;l=l+1) begin
                        if(l==0) f2_take[l]<=eq_v_5 && (eq_gt_5[l] || (eq_mask_5[l] && (MUTANT==2 ? CB'(0)<=eq_left : CB'(0)<eq_left)));
                        else f2_take[l]<=eq_v_5 && (eq_gt_5[l] || (eq_mask_5[l] && (MUTANT==2 ? CB'(eq_count_5[l-1])<=eq_left : CB'(eq_count_5[l-1])<eq_left)));
                    end
                    if(eq_v_5) eq_left<=CB'(eq_count_5[PF-1])<eq_left ? eq_left-CB'(eq_count_5[PF-1]) : CB'(0);
                    // Reuse f3 key storage for stable {invalid,original_lane} sorting.
                    f3_v<=f2_v;f3_id<=f2_id;f3_take<=f2_take;
                    for(l=0;l<PF;l=l+1) f3_tp[l]<={!f2_take[l],6'(l)};
                    f3_n<=0; // retained gross-model allowance, not a state credit.
                    f4_v<=sort_valid[19];f4_n<=sort_valid[19]?take_total_20:7'(0);
'''+s[stop:]
    # Full geometry only when staged implementation elaborates; no shape fallback.
    s=replace(s,'    localparam integer NR', '''    initial begin
        if(N!=4 || NMAX!=2048 || LW!=16 || LDW!=4 || P!=64 || PF!=64 || DIG!=8 || CB!=14)
            $fatal(1,"BALANCED_FULL_GEOMETRY_REQUIRED");
        if(MUTANT<0 || MUTANT>2) $fatal(1,"UNKNOWN_CORE_MUTANT");
    end
    // Source cycle comment remains historical; runtime calibration is a gate.
    localparam integer NR''')
    return "// SOURCE PREPARATION ONLY. Historical source clock comments below are not qualification.\n"+s

def wrapper(source):
    header=source[:source.index('    localparam integer NR')]
    header=replace(header,'module ot_coll_topk_merge #(','module ot_coll_topk_merge_balanced_prepare #(\n    parameter integer BALANCED = 0,\n    parameter integer MUTANT = 0,')
    parameters=', '.join('.'+p+'('+p+')' for p in PARAMS)
    ports=', '.join('.'+p+'('+p+')' for p in PORTS)
    return header+f'''    generate if(BALANCED!=0) begin:g_balanced
        ot_coll_topk_merge_staged_impl_prepare #(.MUTANT(MUTANT),{parameters}) u_core ({ports});
    end else begin:g_original
        ot_coll_topk_merge #({parameters}) u_core ({ports});
    end endgenerate
endmodule
'''

def caller(source):
    s=F.prepare(source)
    s=replace(s,'module ot_w15_coll_dma_station_prepare #(','module ot_w15_coll_dma_balanced_station_prepare #(')
    s=replace(s,'    parameter integer TK_STATION = 0,','    parameter integer TK_BALANCED = 0,\n    parameter integer TK_MUTANT = 0,\n    parameter integer TK_STATION = 0,')
    s=replace(s,'        ot_coll_topk_merge #(.N(N)', '        ot_coll_topk_merge_balanced_prepare #(.BALANCED(TK_BALANCED),.MUTANT(TK_MUTANT<3?TK_MUTANT:0),.N(N)')
    s=replace(s,'if (tk_drained_done) begin busy <= 0;', 'if (TK_MUTANT==3 ? tk_done : tk_drained_done) begin busy <= 0;')
    return s

def prepare(out):
    if out.exists():raise ValueError('fresh candidate package required')
    model=json.loads((BASE/'implementation_model.json').read_text())
    for p,h in {**model['model_pins'],**model['tool_input_pins']}.items():
        if V.sha((ROOT/p).read_bytes())!=h:raise ValueError('implementation model pin changed: '+p)
    for p,h in V.PINS.items():
        if V.sha((ROOT/p).read_bytes())!=h:raise ValueError('original source pin changed: '+p)
    inventory=bits()
    if sum(inventory.values())!=model['added_state_bits_vs_original_model']:raise ValueError('staged register construction exceeds model')
    out.mkdir(parents=True)
    outputs={'ot_coll_topk_merge_staged_impl_prepare.sv':staged(SOURCE.read_text()),
       'ot_coll_topk_merge_balanced_prepare.sv':wrapper(SOURCE.read_text()),
       'ot_w15_coll_dma_balanced_station_prepare.sv':caller(F.SOURCE.read_text())}
    for name,text in outputs.items():(out/name).write_text(text)
    for p in V.PINS:(out/Path(p).name).write_bytes((ROOT/p).read_bytes())
    transpose=json.loads((BASE/'inputs/transpose_origin.json').read_text())
    raw=(BASE/'inputs/ot_chip_v41x_coll_transpose.sv').read_bytes()
    if V.sha(raw)!=transpose['sha256']:raise ValueError('transpose source archive changed')
    (out/'ot_chip_v41x_coll_transpose.sv').write_bytes(raw)
    (out/'ot_topk_fixed_packet_delay_prepare.sv').write_bytes((ROOT/'tools/rtl_templates/ot_topk_fixed_packet_delay_prepare.sv').read_bytes())
    record=dict(schema='opentallas.full-selector.candidate-source.v1',default_off=True,geometry=model['geometry'],
       implementation_model_sha256=V.sha((BASE/'implementation_model.json').read_bytes()),
       extra_state_bits_ledger=inventory,extra_state_bits=sum(inventory.values()),
       async_reset_master_debit=model['async_reset_master_debit'],
       state_accounting='Gross retained-state allowance; f3_n and root-total/pvalid can optimize away, no state/area credit taken.',
       service_increment_cycles=142,transport_increment_cycles=226,
       source_pins=V.PINS,transpose_origin=transpose,
       mutant_controls={'1':'threshold bin bit0 changed at commit','2':'equal quota exclusive-prefix <= instead of <','3':'caller retires before formed-write drain'},
       no_numerical_expectation_change=True,HDL_compiled=False,HDL_equivalence=False,compile_admitted=False,PR_admitted=False,
       remaining=['Complete fault/mutant harness and strict completion verifier','Independent generated source/interface review before source-bound GO','Arch/Maxwell378DBU terminal-site guard and extracted context closure'])
    V.write_json(out/'sourceplan.json',record)
    V.write_json(out/'artifact_manifest.json',{p.name:V.sha(p.read_bytes()) for p in sorted(out.iterdir()) if p.is_file()})
    return record

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=prepare(a.out);print(json.dumps({'extra_state_bits':r['extra_state_bits'],'compile_admitted':False}))
