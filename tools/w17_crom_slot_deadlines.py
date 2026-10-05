"""Constructive local-slot rejection and encoded-PC finite prefetch calendar."""
import argparse,hashlib,json,re,subprocess
from decimal import Decimal as D
import w17_crom_finite_prefetch as C

def build():
    pins={}
    def load(n,ref,path):
        b=subprocess.check_output(['git','show',ref+':'+path]);pins[n]=dict(commit=ref,path=path,sha256=hashlib.sha256(b).hexdigest());return b
    fp=json.loads(load('floorplan','541a1d2f','results/floorplan/v41_pack_refit_w10_interim.json'))
    power=json.loads(load('typed_local','a9ad069bc','results/uarch/w10_frozen_crom_phase_budget_r1/budget.json'))
    lef=load('macro_LEF','d2c28c279','physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.lef').decode()
    w,h=map(D,re.search(r'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)',lef).groups())
    region=next(x for x in fp['soft_regions'] if x[0]=='HUB_SU_VECTOR')
    x,y,rw,rh=map(lambda z:D(str(z)),region[2:]);area=rw*rh/D(1000000)
    # Keep the smaller SU core reservation, not the larger hub allocation: even this fails.
    su=D(str(fp['refit']['hub_units']['stream_unit']['area_mm2']))
    coords=[dict(bank=i,role='parameter' if i<45 else 'catalog_dimension_reservation',
        x_um=str(x+(i%8)*w),y_um=str(y+(i//8)*h),w_um=str(w),h_um=str(h)) for i in range(61)]
    cases=[]
    calendar=C.build(route=11)
    pins['encoded_prefetch_inputs']=calendar['source_pins']
    for row in power['rows']:
        credit=row['credits'];added=D(row['recomputed_declared_reservation']['conditional_cell_plus_macro_area_mm2'])
        deficit=su+added-area
        assert deficit>0
        t=0;commands=[]
        for cmd in calendar['commands']:
            delivery=next(z for z in cmd['deliveries'] if z['credits']==credit)
            floor=(cmd['coefficient_reads']+15)//16
            fill=max(delivery['cold_fill_plus_credit_ticks'],floor*3)
            commands.append(dict(layer=cmd['layer'],PC=cmd['global_instruction'],
                coefficient_reads=cmd['coefficient_reads'],bank_read_waves=cmd['bank_waves'],
                fill_packets=cmd['fill_packets'],selected_output_floor_fast_cycles=floor,
                service_release_tick=t,cache_visible_and_credit_return_tick=t+fill,
                consumer_issue_not_before_service_tick=t+fill,
                source_gamma=cmd['gamma'],
                release_rule='previous coefficient command drained; actual prerequisite completion delays release',
                actual_program_absolute_release_tick=None))
            t+=fill+delivery['consumer_local_cache_read_ticks']
        assert len(commands)==491 and sum(z['coefficient_reads'] for z in commands)==549760
        required_width=(su+added)*1000000/rh
        blockers=[]
        for z in fp['soft_regions']:
            if z[0]==region[0] or z[1]=='ROM_MAC_strip': continue
            zx,zy,zw,zh=map(lambda a:D(str(a)),z[2:])
            ow=min(x+required_width,zx+zw)-max(x,zx)
            oh=min(y+rh,zy+zh)-max(y,zy)
            if ow>0 and oh>0: blockers.append(dict(region=z[0],overlap_um2=str(ow*oh)))
        assert any(z['region']=='HUB_HC' for z in blockers)
        cases.append(dict(credits=credit,
            unchanged_height_right_extension_blockers=blockers,retained_SU_core_mm2=str(su),added_CROM_capture_control_mm2=str(added),
            SU_slot_mm2=str(area),exclusive_area_deficit_mm2=str(deficit),
            minimum_required_width_um_at_current_height=str((su+added)*1000000/rh),
            placement_verdict='FAIL_EXISTING_SU_PLUS_CROM_EXCEEDS_SLOT',
            commands=commands,coefficient_only_serial_service_ticks=t,
            full_token_ticks=None,complete_operator_deadlines=False))
    return dict(schema='opentallas.CROM-slot-PC-deadline.v1',source_pins=pins,
        proposed61macro_coordinates=coords,
        coordinate_scope='macro-only candidate insideSU; not an accepted placement of retainedSU/cells/control',
        catalog_padded_layout_encoded=False,SU_region=region,
        candidates=cases,rank_equivalent_calendars=4,
        no_old_power_transfer=True,no_prefetch_overlap=True,
        gate='REJECT_LOCAL_SLOT_BEFORE_RTL',
        selected_port_floor_replaces_legacy=True,
        actual_deadline_gap_policy='block PC issue until owning fill, visibility and return; missing actual prerequisites cannot be assigned zero',
        minimum_correction='Explicitly enlarge or relocate coefficient home by stated exclusive deficit; preserve SU, then bind all obstacles/routes and catalog encoder before RTL',
        remaining=['L1 invalidsourcehole','actual current padded catalog re-encoding',
            'actual consumer/prerequisite cycles and absolutePC release times',
            'placedcapture/control/CTS/reset/CDC and selectedactivity'],
        hardware_admission=False,jobs_launched=0,checkpoint_reads=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    with open(a.output,'w') as f:json.dump(build(),f,sort_keys=True,indent=2);f.write('\n')
