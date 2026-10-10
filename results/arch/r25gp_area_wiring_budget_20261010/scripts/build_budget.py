import json, sys
B = '/tmp/claude-1000/r25gp_budget/'
x = json.load(open(B + 'xsec_r25gph.json'))
vm = json.load(open(B + 'vm_synth.json')) if len(sys.argv) > 1 else None
DFF_UM2, UTIL = 0.2916, 0.60
RELAY_UM2_PER_BIT = round(DFF_UM2 / UTIL, 4)      # 0.486 um2 per registered bit-stage
V_DER, H_DER = x['V_DER'], x['H_DER']
die = dict(variant='r25gp (geometry) / r25gph (HGI dispatch nets)', source_commit='origin/main 516a70462',
           w_um=31734.288, h_um=25282.8, mm2=802.33, grade='measured (generator plan, legality 0 overlap / 0 outside)',
           brief_outline_note='brief quotes 31,734 x 25,162 = 798.5 mm2 (R25G hub); R25GP on main adds 2 x 4 x 15.12 um of hub (attention hi half 689.04 um) -> 25,282.8',
           placed_footprint_mm2=dict(r25gp=491.89, r25gph=493.61), utilisation_of_outline=0.613,
           whitespace_mm2=308.72,
           reticle=dict(mm2=858.0, axes_um=[33000, 26000], growth_mm2=55.67, growth_x_um=1265.7, growth_y_um=717.2,
                        note='26 x 33 mm field: y can grow 717 um, x 1,266 um (both = ~+55.7 mm2 only if both are used)'),
           spine_column=dict(rect_um=[14736.0, 6322.32, 16135.656, 18960.48], mm2=17.69, blocks_mm2=11.67, free_mm2=6.02,
                             free_gaps_um=[[18149.8, 18960.5, 'top, 810 um (1.13 mm2)'], [15452.6, 15923.5, 'legacy VM -> quant, 471 um (0.66 mm2)'],
                                           [8681.0, 9104.4, 'mtp -> loader, 423 um (0.59 mm2)'], [6976.8, 7188.5, 'hgi_idx -> hgi_vm, 212 um'],
                                           [9342.0, 9670.4, 'loader -> router, 328 um'], [9996.7, 10322.6, 'router -> cmdproc, 326 um']]),
           hub_slots_mm2=dict(su_quarter=7.775, sfu_quarter=4.41, hc_quarter=3.046, coll=1.965, cmdproc=1.965, quant=0.502, hgi_vm=1.512,
                              loader=0.333, idx_score_grid=6.001, attn_tile_lo_hi=2.674))
tracks = dict(layers_um={'M4': 0.048, 'M5': 0.048, 'M6': 0.064, 'M7': 0.064, 'M8': 0.080, 'M9': 0.080},
              grt_derate_pct={'M4': 29.35, 'M5': 29.67, 'M6': 14.75, 'M7': 14.69, 'M8': 15.01, 'M9': 15.0},
              derate_source='hbm_r25gp case grt_sta.log GRT-0053 (EPYC1 die-evidence-2, 2026-10-10 06:30)',
              vertical_tracks_per_um_derated=round(V_DER, 2), horizontal_tracks_per_um_derated=round(H_DER, 2),
              pin_rule='die pins at 2 tracks a bit (0.096 um) on 2 pin layers per face => capacity = perimeter_um / 0.048 bits',
              owner_target_use=0.60)
ch = x['channels']
def chan(k): return ch[k]
items = []
def it(n, name, area_mm2, grade, method, src, slot, die_bits, wiring, successor_note=''):
    items.append(dict(n=n, name=name, added_mm2=area_mm2, area_grade=grade, method=method, source=src, slot=slot,
                      added_die_bits=die_bits, wiring=wiring, successor=successor_note))
vmw = vm['wide_minus_base_um2'] / 1e6 if vm else None
it(1, '32R+32W wide VM lane clients (SM x-load, ATT, HC, FUSED, SU, SFU)',
   dict(as_requested_per_client_lanes=0.75, shared_groups_option=0.39, vm_edge_synth_delta=vmw),
   'estimate (relays, queues) + synth (VM edge, ot_hgi_vm_unit RP/W2 32 vs 0)' if vm else 'estimate',
   'lane = read {v,sec15}+{v,data256} 273 b, write {v,sec15,data256,mask8} 280 b (ot_hgi_vm_unit 34c89274a); per client 32R+32W = 17,792 b; '
   'relay bit-stages x 0.486 um2 (DFFHQNx1 0.2916 um2 at 60 %); client queues LQ 8 x 257 x 32 + skid 2 x 280 x 32 = 83.7k b/client',
   'rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv @34c89274a (claude/hgi-unitrate-vmlanes-20261010); tools/hgi_die_dispatch.py VMW_BITS; 51ae5ce55',
   'hb_hgi_vm (spine 1,399.7 x 1,080 at y 7,188-8,268) + clients: hb_cmdproc (ATT, SM x-load), hb_quant (FUSED), hb_su_SW / hb_sfu_SW / hb_hc_SW (SW quarter)',
   dict(as_requested=97632, shared_two_groups=35584, existing_hgi_vm=13907),
   dict(vm_pin_fill_as_requested=round((13907 + 97632) / (4959.3 / 0.048), 3), vm_pin_fill_shared=round((13907 + 35584) / (4959.3 / 0.048), 3),
        w_spine_channel_at_vm_face_as_requested=round((53376 + 1836) / (1080 * H_DER), 3),
        w_spine_channel_at_vm_face_shared=round((17792 + 1836) / (1080 * H_DER), 3),
        spine_side_channels_vertical_as_requested=round((8746 + 44352 / 2) / (1244.16 * V_DER), 3),
        note='as requested: 6 private lane sets -> VM perimeter 108 %, W channel 132 % at the VM face; shared: one lane group daisy-chained SU->SFU->HC and one for the spine clients (CP ATT/x-load, quant) with the spine reordered so VM abuts CP and quant'))
it(2, 'ATT bound to striped KV lines', dict(bind_to_attention_tiles=0.10, own_striped_lanes_in_cp=0.35), 'estimate',
   '(b) ATT records execute on the 64/32 attention tiles, whose svc->tile KV lines exist (per stack kv 1,041 + ks0-7 8 x 1,102 = 9,857 b, 36 chains die-wide 39,428 b): add a record/descriptor broadcast ~1,250 b per quadrant root + tile-side record decode; '
   '(a) ATT unit in the CP block with its own striped lanes: ~99 sectors/cycle die-wide = 4 x 6.7k b over ~10 mm per stack (+ 10k-sector reorder ~320 KB SRAM)',
   'ot_hgi_att_unit :344-372 (budget audit row hbm_att_unit_hbm_lane); kv_rows / ks buses in the R25GPH netlist',
   '(b) attention quadrant roots (hub W/E) + hb_cmdproc record port; (a) hb_cmdproc', dict(bind_to_tiles=5000, own_lanes=26800),
   dict(option_b='~+6 % on the spine side channels (4 x 1.25k b crossing)', option_a='+26.8k b through the SM row channels, already ~122 % (estimate) -> infeasible without a new channel; REJECT (a)'))
it(3, 'Multi-position HC (npos up to 6)', 0.03, 'estimate',
   'per-position record state + accumulator bank select in ot_hgi_hc_unit; data rides the item-1 lanes', 'budget audit ds_mtp_hc_verify; hgi-1010 (d)',
   'hb_hc_SW (550.8 x 5,529.6 = 3.05 mm2)', 8, dict(note='record n/pos field only (+3..8 b on the HC record bus)'))
it(4, 'Hardware row-gather engine (COLL.ROW_GATHER G25, rgx)', 0.064, 'synth (yosys ASAP7 RVT TT: src 3,982 um2 + sink 5,374 um2 cells) + macro LEF (14 x ot_sram_1r1w_128x256 94.824 x 41.064 = 3,894 um2: ring 2, sink queues 12)',
   'cells + macros = 63.9k um2; slot ~0.08 mm2 at 55 % logic util', 'claude/hgi-rowgather-hw-20261010 f09c6d4e6 (unpushed worktree /home/ubuntu/wt/hgi-rowgather-1010); synth logs ot-epyc2 /srv/opentallas-scratch/claude/r25gp-budget-synth',
   'hb_coll (1,399.7 x 1,404 = 1.965 mm2); if coll is full: the 13,342-13,452 gap + grow coll N by ~110 um', 2900,
   dict(note='new coll <-> HBM path: 2 sector lanes hq 88 b / hr 530 b + list lq/lr 546 b (to the loader kport, 2.6 mm down the spine) + delivery 4 x 568 b; spine-internal, < 10 % of a side channel'))
it(5, 'Pipelined ALL_GATHER endpoint (EQ 4 epochs)', 0.03, 'estimate',
   '4 epoch contexts / slice tables / O base + early-epoch parking (~27k b at 0.486 um2/b + logic)', 'hgi-1010/b 08:10 (ot_hgi_coll_ep PIPE=1, 2,950 vs 9,752 cycles)',
   'hb_coll', 0, dict(note='epoch tag rides the existing multicast dst field: no die nets'))
it(6, 'CP burst fetch (native 8-sector bursts, NO 8 outstanding)', 0.01, 'estimate',
   'kport per-lane outstanding table 8 x ~50 b; svc boundary owner FIFO 8 x ~45 b per stack; loader_cp 16-deep queue already merged (516a70462)',
   '[svc] interface note 2026-10-10 (lq 346 -> 350 b, rsp_last), 516a70462', 'hb_loader (spine) + svc boundary bands', 20,
   dict(note='lq_<st> +4 b x 4 stacks, rsp_last +1 b x 4: negligible'))
it(7, 'FP8 x-path / QDQ -> SM', dict(qdq_cells_in_slot=0.023, xload_decode=0.02), 'synth (QDQ 23.2k um2 cells, hgi-1010 07:13) + estimate (xload FP8/FP4 decode, 32 lanes)',
   'QDQ cells fit the 0.502 mm2 quant slot at 4.6 %; its pd50 failure is a floorplan (1,800 x 600 outline, spread sinks), not area', 'hgi-1010.log 07:13 QDQ pd50; budget audit ds_sm_xload_fp8_fp4_no_peer',
   'hb_quant (spine) + hb_cmdproc (ot_hgi_sm_xload); x store fill rides the existing x trunks', dict(via_vm_lanes=0, direct_quant_to_xroot=1024),
   dict(note='do NOT widen x trunks: SM row channel and SW group-edge strips already ~82-122 % (estimate); quant sits 471 um above the legacy VM x root'))
it(8, 'SU tile (hfd_su_tile_xl 187.056 x 164.16, pk2 lane 85.32 um)', 0.0, 'measured outline (generator floorplan su/rtl_tiled_xl_r25: 6 columns, 3 x 80.352-um channels, quarter 1,406.136 x 5,529.576); tile route live',
   '192 tiles x 30,707 um2 = 5.896 mm2 per quarter = 75.8 % of the 7.775 mm2 quarter', 'claude/hbmphys-cpsu-20261010 physical/hbm_accel_die_views/su/rtl_tiled_xl_r25/floorplan.json, rtl_tile_xl_r25gpht4/tile.json',
   'hb_su_* quarters (unchanged outline)', 0, dict(quarter_channel_um=80.352, quarter_channel_vertical_tracks_derated=int(80.352 * V_DER),
   note='quarter faces unchanged (R25GPHT4 ports + cg_en)'))
it(9, 'VM8 vertical halves + bank clock taps', 0.002, 'measured pilot (+258.3 um2 clock buffers, hbm_vm8bank_sew_cf7c9ca2a CTS) x 8 = estimate; outline measured unchanged (half slot 349,075.5 um2)',
   'same 2 x 2 legacy-VM footprint (1,399.7 x 2,000.1) cut into 8 halves; taps 82 -> 1,056 are local clock leaves inside the footprint',
   'c3e005089 results/physical/vm8_clock_cost_20261010/bank_sew_cts/comparison.json', 'hb_vm_* (spine 13,452-15,453)', 0,
   dict(note='die clock tree: ~1,000 extra sinks in 2.8 mm2 = ~70-125 leaf buffers; outer perimeter unchanged (legacy VM quads at 37 % pin fill)'))
it(10, 'Clock gating (ICG per tile / group: SM, HC, attention quad, SU)', 0.001, 'measured (attn_quad_cg, sm_be wg/eg cg routed in their existing outlines; SU tile_xl ICG inside the tile outline) + estimate (~1,300 ICGs x ~0.44 um2)',
   'ICG cells only; wake/lockup flops are inside the measured tile outlines', 'results/arch/redesign_hbm_cg_20261009/measured_gated_floors.json',
   'inside each block', 110, dict(note='cg_en die bits ~110 (32 SM + 4 HC + 4 SU quarters + 64/32 attention tiles + spares)'))
existing_hot = {k: v for k, v in ch.items()}
succ = dict(
    name='right-sized R25GP successor (owner Option A, 2026-10-10, updated: attention 32 tiles, target ~50 %)', counts=dict(sm=32, attention_tiles=32, su_lanes=512, sfu='half width', hc_quarters=4, idx_score_lanes=36), target_density=0.50, grade='estimate (proportional to unit counts on the R25GP slots)',
    freed_mm2=dict(attention_64_to_32=dict(mm2=85.57, basis='32 tiles x (1.448 lo + 1.226 hi) mm2 slot'),
                   su_1024_to_512=dict(mm2=15.55, basis='half the 4 x 7.775 mm2 quarters (96 tiles a quarter at the measured 75.8 % tile fill)'),
                   sfu_half=dict(mm2=8.82, basis='half of 4 x 4.41 mm2'),
                   hc=dict(mm2=0.0, basis='kept'),
                   idx_score_64_to_36=dict(mm2=10.50, basis='36/64 of 4 x 6.001 mm2 grids'),
                   total=120.44),
    added_mm2=dict(wide_vm_lanes_shared=0.39, cp_seq_ring_macros_mtp_ports=0.03, su_tile=0.0, vm8=0.002, items_2_to_7_10=0.28, total=0.70),
    net_mm2=-119.74,
    placed_footprint_mm2=round(493.61 - 119.74, 2), outline_mm2_brief=798.5,
    placed_density=round((493.61 - 119.74) / 798.5, 3),
    placed_density_r25gph=round(493.61 / 802.33, 3))
out = dict(schema='opentallas.r25gp-area-wiring-budget.v1', date='2026-10-10', die=die, tracks=tracks, items=items,
           totals=dict(as_requested_cells_mm2=1.10, as_requested_slot_growth_mm2=2.77, shared_option_cells_mm2=0.75,
                       vs_spine_free_mm2=6.02, vs_whitespace_mm2=308.72, vs_reticle_growth_mm2=55.67,
                       verdict='area fits easily (<1 % of whitespace); wiring at the HGI VM does not as requested'),
           channels_existing=existing_hot,
           channel_model='estimate: centre-to-centre L-route bit model on the R25GPH generator netlist (1,787 buses), max cross-section per channel, derated tracks; the R25GP die GRT (EPYC1 de2_hbm_r25gp_grt) is still at extra iteration 1/10',
           hot_spots=[
               dict(where='HGI VM perimeter (hb_hgi_vm 1,399.7 x 1,080)', existing=0.135, as_requested=1.12, shared=0.48, cause='item 1'),
               dict(where='W spine channel at the VM face (1,080 um window, horizontal)', existing=0.04, as_requested=1.32, shared=0.47, cause='item 1 SU/SFU/HC lanes'),
               dict(where='spine side channels, vertical (VM -> CP / quant runs)', existing=0.18, as_requested=0.64, shared_reordered=0.20, cause='item 1 spine clients'),
               dict(where='SM row channel 520 um (y 2,728-3,248), SE group', existing=existing_hot['SM_row_ch_520']['use'], cause='existing: x_leaf + index_native + weight; item 2(a) or wider x trunks would add'),
               dict(where='SW group east strip (x 10,786-11,050)', existing=existing_hot['SW_grp_E']['use'], cause='existing x trunks / index_native'),
               dict(where='hub S edge channel (y 5,772-6,322)', existing=existing_hot['hub_S_edge_ch(SM N row->hub)']['use'], cause='existing kv / ks rows')],
           floorplan_changes=[
               'FORCED: one shared 32R+32W lane group per client cluster, not private lane sets (SW quarter SU->SFU->HC daisy chain; spine CP-ATT/x-load/quant group). The RTL (34c89274a) already has one RP group + one W2 group.',
               'FORCED (cheap): reorder the spine bottom so hgi_vm abuts cmdproc (hgi_idx, mtp, loader, router, hgi_vm, cmdproc) and move hfd_quant (1,399.7 x 358.5) into a gap next to the VM (8,681-9,104 is 423 um); no die growth.',
               'ATT: bind records to the attention tiles (existing striped KV lines); reject a CP-local ATT with its own striped lanes.',
               'Not forced by the additions but already hot: the SM row channel / SW group-edge strip (x_leaf + index_native) -- the right-sized successor frees ~120 mm2: put it into SM-row and hub-edge channels.'],
           successor=succ)
json.dump(out, open(B + 'out/R25GP_area_wiring_budget.json', 'w'), indent=1)
print(json.dumps(out['totals']), succ['placed_density'])
