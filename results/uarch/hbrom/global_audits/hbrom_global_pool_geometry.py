import math,json,hashlib,pathlib
R=pathlib.Path('/home/ubuntu/OpenTallas')
paths=[R/'tools/uarch_model.py',R/'results/uarch/v41_rom_depth_study.json',pathlib.Path('/tmp/hbrom-global-compact-layout.json'),pathlib.Path('/tmp/hbrom-weight-network.json'),pathlib.Path(__file__)]
PW,PH=125.28,125.82
DFF,MUX,UTIL=.2916,.2,.5
rows=[]
for N in [356,448,456,560,712,776,908,936,984,1024]:
 S=N//4;L=math.ceil(math.log2(S)); P=2**L
 opts=[]
 for x in range(1,S+1):
  y=math.ceil(S/x);w=x*PW+(x-1)*32;h=y*PH+(y-1)*32
  if max(w,h)/min(w,h)>2:continue
  opts.append(((2*w+112)*(2*h+112),w+h,x,y,w,h))
 _,_,nx,ny,qw,qh=min(opts)
 width,height=2*qw+112,2*qh+112
 occupied_macro=N*PW*PH/1e6
 blank=(4*nx*ny-N)*PW*PH/1e6
 slot_rectangle=4*nx*ny*PW*PH/1e6
 bbox=width*height/1e6
 channels=bbox-slot_rectangle
 levels=[math.ceil(S/2**l) for l in range(1,L+1)]
 mux_nodes=4*(S-1);register_nodes=4*sum(levels)
 pair_mux=N;capture=548*N;pair_regs=306*N;tree_regs=306*register_nodes
 # Conservative separated wire budget for each quadrant. Reach includes request return but excludes compute.
 wire=math.ceil((qw+qh)/504)
 latency=2+1+L+wire+1
 # Uniform extra wire stages on every surviving tree node plus roots: intentionally conservative register bound.
 wire_ff_lower=1288*wire
 wire_ff_upper=(306*register_nodes+1288)*wire
 control_ff=4096+16*(32+10+16+8)+128*32
 # Mutable FIFO positive SECDED geometry reservation; not an implementation/protection claim.
 fifo_macros=6;fifo_mm2=fifo_macros*94.824*41.04*1.31/1e6
 cell_logic_base=(capture+pair_regs+tree_regs+control_ff)*DFF+274*(mux_nodes+pair_mux)*MUX+4096
 net_lower=(cell_logic_base+wire_ff_lower*DFF)/UTIL/1e6+fifo_mm2
 net_upper=(cell_logic_base+wire_ff_upper*DFF)/UTIL/1e6+fifo_mm2
 # Pipeline-stage cells are charged outside ROM rectangle to avoid assuming channels are free cell placement.
 rows.append({'pairs_per_pool':N,'pairs_per_stream':S,'virtual_leaves_per_stream':P,'physically_omitted_virtual_pairs':4*P-N,'mux_levels':L,'surviving_registered_nodes_each_level_per_stream':levels,'data_mux_nodes_four_trees':mux_nodes,'registered_nodes_four_trees':register_nodes,'unary_pipeline_nodes_four_trees':register_nodes-mux_nodes,'quadrant_columns':nx,'quadrant_rows':ny,'quadrant_width_um':qw,'quadrant_height_um':qh,'empty_rectangular_slots_total':4*nx*ny-N,'pool_width_um':width,'pool_height_um':height,'raw_macro_mm2':occupied_macro,'empty_slot_area_mm2':blank,'reserved_channels_mm2':channels,'ROM_rectangle_mm2':bbox,'capture_ff_bits':capture,'pair_select_ff_bits':pair_regs,'registered_tree_ff_bits':tree_regs,'wire_stage_allowance':wire,'wire_ff_lower':wire_ff_lower,'wire_ff_conservative_upper':wire_ff_upper,'network_placement_plus_fifo_mm2_lower':net_lower,'network_placement_plus_fifo_mm2_conservative_upper':net_upper,'pool_plus_network_mm2_lower':bbox+net_lower,'pool_plus_network_mm2_conservative_upper':bbox+net_upper,'packed_response_latency_cycles_budget':latency,'roundtrip_credit_budget':2*latency+2,'reorder_request_entries':16,'FIFO_line_capacity':128,'FIFO_macro_count':fifo_macros,'FIFO_area_mm2':fifo_mm2,'payload_Bpc_if_calendar_feasible':128,'SM_line_Bpc_if_calendar_feasible':136,'payload_Bpc_same_bank_worst_case':64,'physical_qualified':False})
out={'schema':'opentallas.hbrom.global_pool_geometry.v1','architecture_only':True,'qualified':False,'source_pins':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'topology':'Four physically separate equal S-pair quadrants, one S:1 registered tree each, common112um assembly corridor. One exact1088-bit line per compute-tile response; no crossbar or bank sharing across tiles.','assumptions':{'macro_pair_shape_um':[PW,PH],'leaf_channel_um':32,'common_corridor_um':112,'signal_layers_per_direction':2,'signal_pitch_um':.08,'clock_pg_reserved_fraction':.5,'leaf_bundle_bits':306,'leaf_track_capacity':400,'common_bundle_bits':1288,'common_track_capacity':1400,'wire_reach_um_per_stage':504,'wire_reach_basis':'Existing uarch_model WIRE_REACH_SS_UM; extracted from different reference topology, budget only.','clock_ghz':1.2,'capture_cycles':2,'pair_select_cycles':1,'pack_cycles':1,'mux_levels_per_stage':1,'DFF_cell_um2':DFF,'mux2_bit_cell_um2_proxy':MUX,'logic_util':UTIL,'control_ff_reservation':4096,'control_and_protection_comb_cell_um2_reservation':4096,'reorder_request_entries':16,'finite_FIFO':'6x128x256 SRAM permits128 lines with1120b data+tag encoded as35 groups39b SECDED=1365b/line;128*1536b physical. Existing protection must be integrated, this is capacity reservation not finished ECC design.','tree_wire_upper':'Extra wire stage allowance replicated on every existing tree node. Very conservative bound covers unknown branch placement; lower bound charges only four root trunks. Physical sizing must not claim lower bound is placement proof.'},'equations':{'mux_nodes':'4*(S-1); binary tree can prune all constant leaves','tree_register_nodes':'4*sum(ceil(S/2**l),l=1..ceil(log2(S)))','unary_nodes':'registered tree nodes minus mux nodes; keep pipeline flops on unary edges for uniform latency','rectangle':'Two-by-two quadrant rectangles, each nx columns byceil(S/nx) rows,32um inner channels,112um between quadrants. Enumerate integer nx with aspect<=2 and minimize complete pool rectangle area.','area_identity':'ROM rectangle = actual macro area + empty-slot slack + channels; no power2 macro credit or hidden phantom macro count','response_latency':'2capture+1pairselect+ceil(log2(S))+ceil((quadrantW+quadrantH)/504)+1pack; ignores separate prefetch startup pending exact read calendar','credits':'2*response_latency+2 plus16 requestlookahead reservation;128line FIFO covers both at all listed points','feed':'4selected274bitwords =>1088useful bits FP4; FP8/BF16 unused exponent bytes constant. Code bandwidth128B/clk if alternating-bank calendar feasible.'},'calendar_gate':{'status':'OPEN','evidence':'decode_layout: compact FP4 K5120 rowstride20,groups0/8/16 can request8 same-parity records in succession. Each physical macro read interval2cycles.','impact':'Two-cycle macro capture cannot sustain arbitrary same-bank demand1/clk. Without proven prefetch/reorder or offline bank remap, throughput may halve and latency budget excludes refill stalls.','proposed_allowance':'16 request lookahead entries plus existing128line finite responseFIFO; scheduler must prove this spans actual access schedule, tags, retained tail contexts and backpressure. Capacity reservation alone does not prove bandwidth.'},'candidates':rows,'not_included':['Compute/SU/SFU footprints and operand memories','Die-to-die or intertile activation networks','Existing reused SM bulk-copy ring; retain its separately priced footprint if this FIFO is additional','Extracted route/clocktree/power or SS/FF closure','Proof that binary tree physical routing fits every intermediate cut;track inequalities are necessary only']}
pathlib.Path('/tmp/hbrom-global-pool-geometry.json').write_text(json.dumps(out,indent=2)+'\n')
for r in rows:print(r['pairs_per_pool'],round(r['ROM_rectangle_mm2'],3),round(r['pool_plus_network_mm2_lower'],3),round(r['pool_plus_network_mm2_conservative_upper'],3),r['packed_response_latency_cycles_budget'],r['empty_rectangular_slots_total'])
