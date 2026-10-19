"""Price actual source inventory and analytical whole-interface repair; no EDA."""
import contextlib, io, json, math, re
import gzip
from pathlib import Path
with contextlib.redirect_stdout(io.StringIO()):
    import model as M
P=M.P;I=M.I
price={};allcells={}
if (I/'used_native_cell_prices.json').exists():
    allcells=json.loads((I/'used_native_cell_prices.json').read_text())
else:
    # Full source-library reconstruction when exact files are restored by hash.
    for co in ['TT','FF']:
        text=M.read('asap7sc7p5t_SEQ_RVT_'+co+'_nldm_220123.lib.gz')
        text+='\n'+M.read('asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz' if co=='TT' else 'simple_ff.lib.gz')
        for family,date in [('AO','211120'),('OA','211120'),('INVBUF','220122')]:
            text+='\n'+M.read('asap7sc7p5t_'+family+'_RVT_'+co+'_nldm_'+date+'.lib.gz')
        allcells[co]={}
        for n,b in M.blocks(text,'cell'):
            allcells[co][n]=dict(area_um2=M.scalar(b,'area'),caps_ff={pn:M.scalar(pb,'capacitance') for pn,pb in M.blocks(b,'pin') if M.scalar(pb,'capacitance') is not None})
for which in ['old','current_sfo','current_sfo_narrow']:
    f=P/(which+'_complete_census.json')
    j=json.loads(f.read_text() if f.exists() else gzip.open(str(f)+'.gz','rt').read());fp=j['copy_fixedpoint'];out={}
    for co,cells in allcells.items():
        known={n:v for n,v in j['types'].items() if n in cells};unknown={n:v for n,v in j['types'].items() if n not in cells}
        assert len(unknown)==1 and next(iter(unknown)).startswith('ot_sram'),unknown
        extra={n:v for n,v in fp['extra_by_master'].items() if v}
        out[co]=dict(std_master_area_um2=sum(cells[n]['area_um2']*v for n,v in known.items()),
                     ff_clock_cap_ff=sum(cells[n]['caps_ff'].get('CLK',0)*v for n,v in known.items()),
                     all_cell_input_cap_ff=sum(sum(cells[n]['caps_ff'].values())*v for n,v in known.items()),
                     repair_extra_std_area_um2=sum(cells[n]['area_um2']*v for n,v in extra.items()),
                     repair_extra_ff_clock_cap_ff=sum(cells[n]['caps_ff'].get('CLK',0)*v for n,v in extra.items()),
                     repair_extra_all_input_cap_ff=sum(sum(cells[n]['caps_ff'].values())*v for n,v in extra.items()),
                     repair_extra_async_reset_set_cap_ff=sum(sum(v for pn,v in cells[n]['caps_ff'].items() if pn in ['RESETN','SETN'])*ct for n,ct in extra.items()),
                     macro_masters_excluded=unknown)
    price[which]=dict(mapped_sha256=j['sha256'],mapped_cells=j['cells'],source_inventory_only=out,
                     independent_root_lowerbounds=j['independent_root_copy_lowerbounds'],
                     fixedpoint_iterations=fp['iterations'],fixedpoint_extra_cells=fp['extra_cells'],
                     no_unresolved_input_macro_demand=(len(fp['unresolved_input_or_macro'])==0),
                     qualification='Arithmetic model of same-master-D/reset kept copies, not emitted, optimized, simulated or physically qualified')
macro_caps={}
for co in ['TT','FF']:
    text=M.read('ot_sram_1r1w_64x137_m1_r2c2_p192_'+co.lower()+'.lib');n,b=next(M.blocks(text,'cell'))
    caps={pn:M.scalar(pb,'capacitance') for pn,pb in M.blocks(b,'pin') if M.scalar(pb,'capacitance') is not None}
    for bn,bb in M.blocks(b,'bus'):
        cap=M.scalar(bb,'capacitance')
        if cap is None:continue
        bt=re.search(r'bus_type\s*:\s*(\S+)\s*;',bb).group(1)
        tb=dict(M.blocks(text,'type'))[bt]
        width=int(M.scalar(tb,'bit_width'))
        for bit in range(width):caps[bn+'['+str(bit)+']']=cap
    groups={}
    for pn,cap in caps.items():
        group=pn.split('[')[0];groups[group]=groups.get(group,0)+cap
    macro_caps[co]=dict(per_bank_pin_cap_ff=groups,all_four_clock_cap_ff=4*groups['clk'],all_four_pin_input_cap_ff=4*sum(caps.values()))
relay={}
for bits in [17,32]:
    total=548+bits;a=total//3;shards=[a,a,total-2*a]
    live_ff=11*total
    # Explicit conservative envelope: not a claimed minimum or an approved footprint.
    relay[str(bits)]=dict(payload_bits=548,predicate_bits=bits,real_bits=total,shards=shards,
        edges_per_stage=1,stages=11,clock_pins_per_stage=3,added_clock_entry_pins_vs_old=11,
        live_ff=live_ff,positive_capture_inv=live_ff,live_ff_area_um2=live_ff*.2916,
        positive_ff_and_inv_area_um2=live_ff*(.2916+.04374),
        live_clock_cap_ff={co:live_ff*M.libs[co][M.ff]['input_cap_ff']['CLK'] for co in M.libs},
        complete_13capture_payload_plus_flags_ff=13*total,
        new_full_outline_sum_um2=11*3*43.2**2,old_two_relay_outline_sum_um2=11*(21.6*82.08+12.96**2),
        additional_outline_sum_um2=11*(3*43.2**2-(21.6*82.08+12.96**2)),
        conservative_shard_outline_um=[43.2,43.2],maximum_face_density_per_um=max(shards)/43.2,
        minimum_pin_bound_face_length_um=max(shards)/6,
        candidate_signal_pin_layer='M4',candidate_signal_contact_pitch_um=.192,
        candidate_signal_contact_first_center_y_um=2.892,
        candidate_signal_contact_last_center_y_um=2.892+.192*(max(shards)-1),
        candidate_M4_track_y_offset_um=.012,candidate_M4_track_y_pitch_um=.048,
        all_contact_centers_on_native_track=all(abs(((2.892+.192*i)-.012)/.048-round(((2.892+.192*i)-.012)/.048))<1e-8 for i in range(max(shards))),
        candidate_signal_contact_shape_um=[.024,.024],max_contacts_any_one_um=6,
        M4_min_area_um2=.002,required_M4_metal_length_at_width024_um=.002/.024,
        minimum_contact_outward_extension_um=.002/.024-.024,
        PG_clock_access='Separate S/N clock and PG contacts require actual pin/via/rail inventory; no PG access credit yet',
        per_shard_total_ff_clock_and_signal_pin_count=[2*n+1 for n in shards],
        maximum_internal_corner_distance_um=86.4,
        minimum_shard_fill_fraction=min(shards)*.2916/(43.2**2),
        low_fill='Pin-bound conservative bound, requires ROOT review;43.2 is not mandatory for a standard-cell outline',
        route_tracks_per_cross_section=total,M6_M7_min_raw_track_width_um=total*.064,
        monolithic_alternative_outline_um=[64.8,108],monolithic_outline_sum_um2=11*64.8*108,
        parent_displacement=None,parent_overlap_check=None,new_routed_reach=None,new_clock_spread=None)
assert all(v['all_contact_centers_on_native_track'] for v in relay.values())
out=dict(source_prices=price,new_storage_pin_caps=macro_caps,whole_payload_relay_repair=relay,
         caveats=['All-cell capacitance sums are inventory loads, not total physical wire/clock power',
                  'Source price changes after optimization, macro swap and fixed-face legalization',
                  'The analytical copy fixedpoint must be rederived after adding new gates/ports',
                  'New sideband first-use and current GEN8 final binding remain unqualified'])
(P/'whole_price.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
