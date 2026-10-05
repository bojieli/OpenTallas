"""Preserve45 bank conflicts; compact per-stage rows without new macros."""
import argparse,gzip,hashlib,json,subprocess,struct,math,re
from collections import defaultdict
import w17_crom_finite_prefetch as C

def sha(b):return hashlib.sha256(b).hexdigest()
def build():
    pins={}
    def load(n,ref,path):
        b=subprocess.check_output(['git','show',ref+':'+path]);pins[n]=dict(commit=ref,path=path,sha256=sha(b));return b
    union=json.loads(gzip.decompress(load('union','8e28902ff','results/uarch/w11_stage_crom_union_20261001/read_union.json.gz')))
    small=json.loads(load('existing_shallow_macro','d2c28c279','physical/asap7_memory_macros/ot_rom_1024x72_m8/ot_rom_1024x72_m8.json'))
    load('shallow_LEF','d2c28c279','physical/asap7_memory_macros/ot_rom_1024x72_m8/ot_rom_1024x72_m8.lef')
    load('shallow_SS','d2c28c279','physical/asap7_memory_macros/ot_rom_1024x72_m8/ot_rom_1024x72_m8_ss.lib')
    load('shallow_FF','d2c28c279','physical/asap7_memory_macros/ot_rom_1024x72_m8/ot_rom_1024x72_m8_ff.lib')
    wire=load('SS_wire_model','541a1d2f','tools/uarch_model.py').decode()
    fp=json.loads(load('SU_geometry','541a1d2f','results/floorplan/v41_pack_refit_w10_interim.json'))
    region=next(z for z in fp['soft_regions'] if z[0]=='HUB_SU_VECTOR')
    reach=float(re.search(r'^WIRE_REACH_SS_UM\s*=\s*([0-9.]+)',wire,re.M)[1])
    route=math.ceil((region[4]+region[5])/reach);assert route==17
    calendar=C.build(route=route);pins['calendar']=calendar['source_pins']
    stages=[];maxrows=0;reqmax=0;fillmax=0;digest=hashlib.sha256()
    for s in union['ranks'][0]['stages']:
        perbank=defaultdict(set)
        addresses=set(a for lo,hi in s['ranges'] for a in range(lo,hi))
        for a in addresses:perbank[(a//3)%45].add((a//3)//45)
        rowmap={bank:{row:i for i,row in enumerate(sorted(rows))} for bank,rows in perbank.items()}
        checked=0
        for a in sorted(addresses):
            bank=(a//3)%45;oldrow=(a//3)//45;slot=a%3
            newrow=rowmap[bank][oldrow]
            assert sorted(perbank[bank])[newrow]==oldrow
            restored=(oldrow*45+bank)*3+slot
            assert restored==a
            digest.update(struct.pack('<IIIII',a,bank,oldrow,newrow,slot));checked+=1
        maxstage=max(map(len,perbank.values()));maxrows=max(maxrows,maxstage)
        commands=[c for c in calendar['commands'] if c['layer']==s['layer']]
        req=3*sum(c['bank_waves'] for c in commands);fill=sum(c['fill_packets'] for c in commands)
        reqpages=(req//3+4095)//4096;fillpages=(fill+4095)//4096
        reqmax=max(reqmax,reqpages);fillmax=max(fillmax,fillpages)
        stages.append(dict(layer=s['layer'],unique_words=s['unique_words'],
            per_bank_distinct_oldrows=[len(perbank[b]) for b in range(45)],
            maximum_bank_rows=maxstage,oldrows_preserved_slot_holes=True,
            all_address_roundtrip_checks=checked,
            row_map_SHA256=sha(b''.join(struct.pack('<III',bank,row,i) for bank,rows in sorted(rowmap.items()) for row,i in sorted(rows.items()))),
            request_catalog_columns=3,request_words=req,request_pages_per_column=reqpages,
            fill_words=fill,fill_pages=fillpages,commands=commands))
    assert len(stages)==41 and maxrows<=1024
    capture_slack=1000/1.2-small['timing']['ss']['clk_to_q_ps']-25-60
    return dict(schema='opentallas.CROM45-stage-row-compaction.v1',source_pins=pins,
        SS_route_basis=dict(reach_um=reach,envelope_um=region[4]+region[5],stages_each_direction=route,
            historical11_qualified=False,actual1152bit_bus_capacity_and_reach_bound=False),
        max_regular_rows_per_bank=maxrows,stages=stages,
        exact_address_roundtrip_digest=digest.hexdigest(),
        nominal_service_ports=dict(banks=45,logical64_slots_per_bank=3,capture_coefficients=135,selected_FP32_outputs=16,
            same_bank_conflict_structure_preserved=True),
        regular_catalog=dict(request_columns=3,request_pages_per_column=reqmax,fill_pages=fillmax,
            existing4096x274_catalog_macros=3*reqmax+fillmax,current_compact_row_catalog_encoded=False),
        available_choices=[dict(name='existing4096x274',coefficient_macros=45,depth=4096,
            footprint_saved_by_logical_row_compaction=False,baseline_macro_depth_rule_preserved=True),
            dict(name='three_existing1024x72_per_bank',coefficient_macros=135,depth=1024,
            useful_bits_per_macro=64,ignored_padding_bits_per_macro=8,
            coefficient_macro_area_mm2=135*small['area']['macro_area_um2']/1000000,
            SS_clkq_ps=small['timing']['ss']['clk_to_q_ps'],SS_capture25_unc60_slack_before_route_ps=capture_slack,
            baseline4096_depth_rule_preserved=False,requires_explicit_model_contract_choice=True,
            new_macro_generated=False,physical_clock_endpoints_added=90,
            actual3macro_bank_capture_route_power_SSFF_unbound=True)],
        latency_comparison='Row renumbering preserves45bank waves; current17cycle SSminimum finitecalendar retained as candidate only, not actual route.',
        full_token_cycles=None,hardware_admission=False,
        missing=['L1invalidsource','newrow requestcatalog compiler publication','actual135macro port/capture/clock/power placement',
            'actual compacthome ownership/routing and SU nonoverlap'],
        checkpoint_reads=0,jobs_launched=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    with open(a.output,'w') as f:json.dump(build(),f,sort_keys=True,indent=2);f.write('\n')
