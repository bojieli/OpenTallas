#!/usr/bin/env python3
"""Additive source prepreview only: no compiler, RTL simulation, physical tool or payload reads."""
import argparse, hashlib, json, subprocess
from pathlib import Path
import dsrom_l20_banked_collector_contract as B
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_l20_scale_optin_preparation_20261002'
FIX=ROOT/'tests/fixtures/dsrom_l20_scale_optin_20261002'
REAL=B.REAL
PINS={}
def read(path):
 b=subprocess.check_output(['git','show',REAL+':'+path],cwd=ROOT)
 PINS[path]={'commit':REAL,'path':path,'sha256':hashlib.sha256(b).hexdigest()}
 return b

def emit(path,data):
 b=data.encode() if isinstance(data,str) else (json.dumps(data,indent=2,sort_keys=True)+'\n').encode()
 if path.exists(): assert path.read_bytes()==b, str(path)
 else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b)

def variant(source):
 s=source.decode().replace('module ot_hdc_fp4qdq (','''// Additive review candidate; no QE/core/tile integration. Both controls default off.
module ot_hdc_fp4qdq_l20_scale_optin #(
    parameter integer QDQ4E_GOLDEN_SAT448 = 0,
    parameter integer CKV_PACKED_SIDEBAND = 0
) (''',1)
 s=s.replace('amax / 6 (no saturation)', 'amax / 6 (default legacy; opt-in existing-golden min448)',1)
 s=s.replace('output reg           fault\n','''output reg           fault,
    output wire          packed_valid,
    output wire [127:0]  packed_codes,
    output wire [15:0]   packed_scales,
    output wire          packed_fault
''',1)
 anchor="                s3_qs[b] <= ea - 10'sd6;\n            end\n"
 assert s.count(anchor)==1
 s=s.replace(anchor,anchor+'''            // Existing golden min(RNE(amax/6),448). Tie at2784 remains448.
            // Preserve original invalid-row path; its fault forbids publication.
            if (QDQ4E_GOLDEN_SAT448 != 0 && !s2_nf && s2_amax[b] > 31'h452e0000) begin
                s3_n[b] <= 5'd14;
                s3_qs[b] <= 10'sd5;
            end
''')
 s=s.replace('endmodule\n','''    generate if (CKV_PACKED_SIDEBAND != 0) begin : g_packed
        // Serialize the SAME post-S3 scale used by thresholds, codes and BF16.
        function automatic [7:0] pack_scale(input [4:0] n, input signed [9:0] qs);
            reg [4:0] nn;
            reg signed [9:0] qq;
            reg [7:0] ee;
            begin
                nn=n; qq=qs;
                if(nn==16) begin nn=8; qq=qs+10'sd1; end
                ee=qq+10'sd10;
                if(qq == -10'sd9 && nn<8) pack_scale={3'd0,nn};
                else pack_scale={ee[3:0],3'b000} | (nn-5'd8);
            end
        endfunction
        reg [15:0] s4_scales, s5_scales, s6_scales;
        reg [127:0] s6_codes;
        integer pb, pi;
        always @(posedge clk) begin
            for(pb=0;pb<2;pb=pb+1) s4_scales[8*pb +: 8] <= pack_scale(s3_n[pb],s3_qs[pb]);
            s5_scales <= s4_scales;
            s6_scales <= s5_scales;
            for(pi=0;pi<32;pi=pi+1) s6_codes[4*pi +: 4] <= {s5_sgn[pi],s5_c[pi]};
        end
        assign packed_codes=s6_codes;
        assign packed_scales=s6_scales;
        assign packed_fault=fault;
        assign packed_valid=vo && !fault && (QDQ4E_GOLDEN_SAT448 != 0);
        // Sideband without finite-domain repair is deliberately not admissible.
    end else begin : g_no_packed
        assign packed_valid=1'b0;
        assign packed_codes=128'd0;
        assign packed_scales=16'd0;
        assign packed_fault=1'b0;
    end endgenerate
endmodule
''',1)
 return s

def vectors():
 # Full512-value row: 16 independent 32-element beats, two16-element scales/beat.
 env,functions=B.golden_functions()
 import numpy as np
 rows=[]
 for e in range(255):
  keys=[]
  for beat in range(16):
   k=(e<<23)|[0,1,0x3fffff,0x400000,0x7fffff][beat%5]
   keys.extend([k]*16+[(k|0x80000000)]*16)
  rows.append(('finite_exponent_'+str(e),keys))
 boundary=[0x452dffff,0x452e0000,0x452e0001,0x45bfffff,0x45c00000,0x45c00001,0x7f7fffff]
 for k in boundary:
  keys=[]
  for beat in range(16):
   low=0x42e00000+(beat%3)-1
   keys.extend([k]+[low]*15+[(k|0x80000000)]+[(low|0x80000000)]*15)
  rows.append(('cap_midpoint_'+hex(k),keys))
 rows.append(('signed_zero_subnormal',[0x80000000,0,0x80000001,1]*128))
 # Every finite scale-grid transition with immediate binary32 neighbors.
 import struct
 for qs in range(-9,124):
  for n in range(8,16):
   try:k=struct.unpack('>I',struct.pack('>f',float(3*(2*n+1)*B.p2(qs))))[0]
   except OverflowError:continue
   if k+1>=0x7f800000:continue
   rows.append((f'grid_{qs}_{n}',[v for beat in range(16) for v in [k+[-1,0,1][beat%3]]*32]))
 data=[];meta=[]
 for name,keys in rows:
  rowout=[];rc=[];rs=[]
  for beat in range(16):
   ks=keys[beat*32:beat*32+32];q=B.qdq_model(ks,True)
   with np.errstate(all='ignore'):g=env['qdq_fp4_e4m3'](np.array(ks,dtype=np.uint32).view(np.float32),16).view(np.uint32)>>16
   assert q['BF16']==g.tolist(),name
   # Direct native decoder provenance: FP4 signed values * positive E4M3 scale.
   for i,c in enumerate(q['codes']):
    mag=B.Fraction([0,1,2,3,4,6,8,12][c&7],2)*q['scales'][i//16]
    assert mag<=2688
   def pack(v,w):return ''.join(f'{x:0{w}x}' for x in reversed(v))
   data.append((pack(ks,8),pack(q['BF16'],4),pack(q['codes'],1),pack(q['scale_codes'],2),0))
   rowout.extend(q['BF16']);rc.extend(q['codes']);rs.extend(q['scale_codes'])
  meta.append({'name':name,'BF16_8192hex':pack(rowout,4),'codes_2048hex':pack(rc,1),'scales_256hex':pack(rs,2)})
 # Invalid rows exercise fault / publication, no NaN payload equivalence asserted.
 for k in [0x7f800000,0xff800000,0x7fc00001,0x7f800001]:
  for beat in range(16):data.append((''.join(f'{v:08x}' for v in reversed([k]+[0]*31)), '0'*128,'0'*32,'0000',1))
 return data,meta,functions

BENCH='''`timescale 1ns/1ps
module tb_l20_scale_optin;
reg clk=0; always #0.5 clk=~clk;
reg rst_n=0,v=0; reg [1023:0] x=0;
wire vo,fo,pv,pf,ov,of,dv,df; wire [511:0] y,oy,dy;
wire [127:0] codes,dc;wire [15:0] scales,ds;wire dp, dpf;
ot_hdc_fp4qdq original(clk,rst_n,v,x,ov,oy,of);
ot_hdc_fp4qdq_l20_scale_optin defaults(.clk(clk),.rst_n(rst_n),.v(v),.x(x),.vo(dv),.y(dy),.fault(df),.packed_valid(dp),.packed_codes(dc),.packed_scales(ds),.packed_fault(dpf));
ot_hdc_fp4qdq_l20_scale_optin #(.QDQ4E_GOLDEN_SAT448(1),.CKV_PACKED_SIDEBAND(1)) repaired(.clk(clk),.rst_n(rst_n),.v(v),.x(x),.vo(vo),.y(y),.fault(fo),.packed_valid(pv),.packed_codes(codes),.packed_scales(scales),.packed_fault(pf));
localparam N=__N__;
reg [1023:0] xin[0:N-1];reg [511:0] gold[0:N-1];reg [127:0] ec[0:N-1];reg [15:0] es[0:N-1];reg ef[0:N-1];
integer send=0,recv=0,cycle=0,j,epoch=0;integer due[0:N-1];
reg [8191:0] rowbf;reg [2047:0] rowcodes;reg [255:0] rowscales;
initial begin
$readmemh("inputs.hex",xin);$readmemh("golden.hex",gold);$readmemh("codes.hex",ec);$readmemh("scales.hex",es);$readmemh("faults.hex",ef);
repeat(4) @(negedge clk);rst_n=1;
while(send<N) begin
@(negedge clk);v=(send%19!=3 || cycle%2==0);
if(v) begin x=xin[send];due[send]=cycle+8;send=send+1;end
end
@(negedge clk);v=0;
wait(recv==N);repeat(12)@(negedge clk);
// Reset and drain exclude stale publication; no collector epoch implementation inferred.
rst_n=0;repeat(3)@(negedge clk);rst_n=1;repeat(12)@(negedge clk);
if(vo||pv||ov||dv)$fatal(1,"stale valid after reset/drain");
$display("PASS %0d beats including full512 rows, sidebands, optoff equality, invalid fault",N);$finish;
end
always @(posedge clk) begin
cycle=cycle+1;
#0.01;
if(rst_n) begin
if({dv,df,dy} !== {ov,of,oy})$fatal(1,"default-off differs original");
if(dp||dc!==0||ds!==0||dpf)$fatal(1,"default sideband not disabled");
if(vo!==ov)$fatal(1,"pipeline valid mismatch");
if(vo) begin
if(recv>=send || cycle!=due[recv])$fatal(1,"latency/order %0d cycle%0d due%0d",recv,cycle,due[recv]);
if(fo!==ef[recv]||pf!==fo||pv!==!ef[recv])$fatal(1,"fault/publication %0d",recv);
if(ef[recv] && {fo,y} !== {of,oy})$fatal(1,"invalid-row path changed");
if(!ef[recv])begin
if(y!==gold[recv]||codes!==ec[recv]||scales!==es[recv])$fatal(1,"golden/sideband mismatch beat%0d",recv);
rowbf[512*(recv%16)+:512]=y;rowcodes[128*(recv%16)+:128]=codes;rowscales[16*(recv%16)+:16]=scales;
if(recv%16==15)begin
for(j=0;j<16;j=j+1)begin
if(rowbf[512*j+:512]!==gold[recv-15+j]||rowcodes[128*j+:128]!==ec[recv-15+j]||rowscales[16*j+:16]!==es[recv-15+j])$fatal(1,"fullrow packing");
end end end
recv=recv+1;
end end end
initial begin repeat(__LIMIT__)@(posedge clk);$fatal(1,"bounded watchdog");end
endmodule
'''

def main():
 source=read('rtl/hdc/v41/ot_hdc_fp4qdq.sv')
 delay=read('rtl/hdc/ot_hdc_delay.sv')
 prior=json.loads((ROOT/'results/uarch/dsrom_l20_banked_collector_contract_20261002/model.json').read_text())
 # Source-matched inventory and conservative reservation, no historical qualification transfer.
 paths=['rtl/test/v41_runtime/ot_v41_rt_die_l20.sv','tools/w17_current_fastpp_die_rt.py','rtl/chip/ckvsel/ot_chip_v41x_tile.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_pool_adapt.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_pool_batch.sv','rtl/hdc/v41x/ot_hdc_v41x_wgt_tile.sv','rtl/hdc/v41x/ot_hdc_v41x_vec.sv','rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv','results/arch/arch_budget_v41.json','results/floorplan/v41_pack_refit_w18_e8p5.json','results/floorplan/v41_rtl_engine_profile.json','rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv','rtl/w17_runtime/hdc/v41x/fastpp_pc21/l20/ot_hdc_core_v41x.sv','tools/uarch_model.py']
 texts={p:read(p).decode() for p in paths}
 u=json.loads(texts['results/arch/arch_budget_v41.json'])['unit_areas_um2']
 su_cell=192*u['su_light_lane_um2']+63*u['su_lane_um2']+u['su_lane0_um2']
 listed=prior['state_ports_area']['full_listed_attention_service_candidate_mm2']
 fp=json.loads(texts['results/floorplan/v41_pack_refit_w18_e8p5.json'])
 regions=[{'name':r[0],'kind':r[1],'origin_um':r[2:4],'bbox_um':r[4:6],'gross_mm2':r[4]*r[5]/1e6} for r in fp['soft_regions'] if r[0].startswith('HUB_')]
 citations={}
 for path,needles in {paths[0]:['SUN = 256','SUM = 64'],paths[1]:['-GX_IDX=2'],paths[3]:['if(RING != 0)','s<4','idx_pool_batch #'],paths[4]:['wgt_tile #'],paths[6]:['KIND((l == 0)','u_red'],paths[-2]:['MP    = 1','idx_pool_adapt #','idx_pool_kwr #'],paths[-1]:['def dedicated_ledger','replicas=rep_i','hardened_record']}.items():
  citations[path]=[{'line':i,'text':line.strip()} for i,line in enumerate(texts[path].splitlines(),1) if any(n in line for n in needles)]
  assert citations[path],path
 reservation={'schema':'opentallas.dsrom.L20-co-resident-reservation-review.v1','status':'FAIL_NO_SOURCE_MATCHED_FREE_ISLAND',
 'source':REAL,'source_citations':citations,'retained_co_resident_regions':regions,'retained_hub_unit_reservations':fp['refit']['hub_units'],
 'uarch_entry_schema_binding':{'entry':'tools/uarch_model.py:dedicated_ledger','row_fields':['design','ctx','layer','T','positions','keys_per_die','units','hub_logic_mm2','hub_avail_mm2','discrepancies'],'units':['indexer','idx_reader','attention','stream_unit'],'unit_fields':['element','replicas','ports_total','storage_bits','area_mm2','area_basis','hardened','ops'],'adoption':'Add source-matched collector unit and current pooled-index inventory through owner-reviewed additive intake; existing preset slice arithmetic not substituted for actual pooled source.'},
 'available_hub_mm2':41.0935,'banked_attention_service_listed_mm2':listed,
 'historical_indexer_reservation_mm2_retained':21.677,'total_with_retained_indexer_mm2':listed+21.677,
 'minimum_excess_with_retained_indexer_mm2':listed+21.677-41.0935,
 'actual_hierarchy':{'indexer':'X_IDX2 IDX_RING1: four kstream_ring NPC32 WB32 GA24 + quarter_join + one idx_pool_batch G4 M=MP + finish + SUN256 keywriter; no sixteen-slice production substitution',
 'index_products_per_cycle_formula':'8*G*MP*32 =1024*MP; source core default MP1 =>1024, not262144',
 'SU_N256_M64_lane_counts':{'KIND2':1,'KIND1':63,'KIND0':192},'SU_area_proxy_cell_um2':su_cell,'SU_placed_proxy_mm2_at50pct':su_cell/500000,
 'SU_scope':'primitive model proxy; reducer/controller/side/VM and buffers excluded; not hardened full hierarchy. Retained SU occupies HUB_SU_VECTOR, not free ATTENTION space; no borrowing or release.',
 'source_equivalent_indexer_area':'NOT_CERTIFIED; retain historical21.677 reservation instead of crediting substitute block-dot estimate'},
 'slot':prior['physical_proposal'],'no_double_count_rule':'SU estimate is separate disclosed lower-bound inventory, not credited or subtracted from listed attention/service. Indexer reservation retained until current hierarchical ledger and actual regions replace it explicitly.',
 'required_reservation_decision':{'action':'Provide a source-pinned refit with current indexer, attention, SU, VM, clock/CDC, links and service all allocated; enlarge/move/reduce only through composed model review.',
 'minimum_area_to_recover_mm2_before_other_omitted_residents':listed+21.677-41.0935,
 'channel_demand_tracks':20909,'layers':'M2/M4 with36 SRAM M1-M4 OBS; no higher-layer capacity borrowing',
 'SS_route_plus_receiver_setup_budget_ps':prior['physical_proposal']['SS_remaining_route_and_receiver_setup_ps_at1p2'],
 'physical_slot_bound':False},
 'admission':{'joint_ready':'same epoch/user/layer/GID: own9 distinct backend visible completions AND window128 AND selected512 fault-free committed rows',
 'retirement':'QK actual credits/completion then PV actual credits/completion; drain VM/ME and all old local/peer/backend intents before epoch/reset/reuse',
 'finite_constraints':'512 row reservations, four ingress packets, five-way per-bank RR commit ACK,3 peerTX skids and reverse credits; no free consumer service guarantee',
 'common_controller_cut_cycles':2,'mandatory_repair_is_not_timing_cut':True},
 'original_failed_screens':prior['original_failed_screens_preserved'],'four_targets':prior['four_targets'],'application':'DeepSeek ROM fullL20 only. Qwen ROM unaffected; Qwen/DeepSeek HBM retain ordinary GPU organisation; no dedicatedROMnovelty transfer.','pins':PINS.copy(),'engine_RTL_build_ready':False}
 emit(OUT/'reservation.json',reservation)
 # Preparation follows existing0e15 model; never edits retained source or engine hierarchy.
 data,rows,functions=vectors()
 emit(FIX/'source/original/ot_hdc_fp4qdq.sv',source.decode())
 emit(FIX/'source/original/ot_hdc_delay.sv',delay.decode())
 emit(FIX/'source/optin/ot_hdc_fp4qdq_l20_scale_optin.sv',variant(source))
 emit(FIX/'tb_l20_scale_optin.sv',BENCH.replace('__N__',str(len(data))).replace('__LIMIT__',str(len(data)*3+100)))
 for col,name in enumerate(['inputs','golden','codes','scales','faults']):emit(FIX/(name+'.hex'),'\n'.join(str(row[col]) for row in data)+'\n')
 emit(OUT/'row_oracles.json',{'finite_rows':len(rows),'row_width':512,'rows':rows,'actual_golden_AST':functions,'oracle':'Fraction RNE postcap scale/midpoint/sign + actual pinned golden BF16; synthetic only, expected memories never fed into DUT', 'nonfinite_beats':64})
 files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(FIX.rglob('*')) if p.is_file()}
 record={'schema':'opentallas.dsrom.L20-optin-scale-source-prepreview.v1','source':REAL,'prior_model':'0e15e9f255ed34046947633eec101253dbdab4c3','execution':'PREPARED_NOT_COMPILED_NOT_SIMULATED','generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'default_parameters':{'QDQ4E_GOLDEN_SAT448':0,'CKV_PACKED_SIDEBAND':0},'cap_stage':'S3 afterRNE beforeS4; !s2_nf and amax>0x452e0000 =>n14 qs5; same scale feeds thresholds/code/BF16/packed',
 'ports':{'x':1024,'y':512,'packed_codes':128,'packed_scales':16,'packed_valid':1,'packed_fault':1},'sideband_without_cap':'publication disabled; not admitted',
 'NF_policy':'original data/fault path preserved; packed_valid false onfault, no invalid arithmetic equality claim','finite_rows':len(rows),'total_beats':len(data),'latency':'input edge0 tooutput edge7, source8registeredstages; nextQEedge8 thenservicecaptureedge9 not implemented here',
 'state_added_bits':176,'extra_pipeline_cycles':0,'S3_timing':'unqualified compare/select price retained from0e15; commoncontroller+2cycles separate',
 'compile_scope':'unchanged delay and quantizer + additive variant + isolated bench; noQE or16inactiveblockdot elaboration','full_engine_connections':'QE/core/tile/service rawcodes/scales and registered address/epoch/user/layer/fault remain required; no reencoder',
 'copied_source_pins':[PINS['rtl/hdc/v41/ot_hdc_fp4qdq.sv'],PINS['rtl/hdc/ot_hdc_delay.sv']], 'preserved_inputs':prior['preserved_inputs'],'files_sha256':files,
 'review_required_before_compile':True,'collector_engine_RTL_allowed':False,'physical_reservation_closed':False}
 emit(OUT/'preparation.json',record)
 print(json.dumps({'prepared_finite512_rows':len(rows),'beats':len(data),'reservation_excess_mm2':reservation['minimum_excess_with_retained_indexer_mm2'],'compiled':False}))
if __name__=='__main__':main()
