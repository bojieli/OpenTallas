#!/usr/bin/env python3
"""Size the concrete held quarter implementations before RTL/hardening.
Uses unified uarch_model proposal widths/area constants; no new adoption row.
"""
import hashlib,json
from pathlib import Path
import uarch_model as U
ROOT=Path(__file__).resolve().parents[1]
P=U.PRESETS['proposal']; SF=P['sfu_lanes']//4; HC_MACS=5120//4; NG=HC_MACS//20; HC=NG*4
# Actual canonical port widths follow source engine semantics, not historical
# input-only die stubs. A wire framing adapter must be owned/bound separately.
def bank(bits):
 words=(bits+63)//64
 return dict(payload_bits=bits,data_words=words,storage_ff=72*(words+5)+2,
             check_bits=8*words,control_words=5,repair='existing W2 five-edge CE repair; permissions fail closed')
def held(i,o):
 req=bank(i+1);rsp=bank(o+1);ctl=bank(64)
 ff=req['storage_ff']+rsp['storage_ff']+ctl['storage_ff']
 return dict(request=req,response=rsp,controller=ctl,wrapper_ff=ff,
             wrapper_dff_area_lower_um2=ff*U.DFF_UM2,
             combinational_SECDED_mux_fanout_area='must measure; not zero or counted as closed',
             outstanding_transactions=1,request_capture=1,prime=1,dispatch=1,response_capture=1,
             no_backpressure_loss='request held until response consumed; response held in protected cut',
             parent_clock_closed=False,ICG_replicas=1,ICG_clock_load_area='must measure actual parent; no leaf insertion inheritance',clock_freezes_on='CE repair or protected controller nonnormal',engine_reset_policy='POR or normal IDLE only; no reset during CE repair',latency_delta_cycles=1,state_ff_delta=0,reset_fanout_cost='real reset fanout/CTS/load cost remains to be measured; not free')
sfu_i=SF*32+3+32;sfu_o=SF*32+1+32
hc_i=NG*160+640+32;hc_o=NG*128+1+32
r=dict(schema='opentallas.hbm.compute.quarter_size.v1',
 model_source='tools/uarch_model.py PRESETS.proposal sfu_lanes / 4, hbm_gpu_design(v41) HC 5120 / 4',
 model_sha256=hashlib.sha256((ROOT/'tools/uarch_model.py').read_bytes()).hexdigest(),
 protection_source='rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv',
 sfu=dict(top='ot_hbm_sfu_quarter',lanes=SF,replicas=4,opcodes=list(range(8)),
          port_bits=dict(request=sfu_i,response=sfu_o),port_bytes=dict(request=sfu_i/8,response=sfu_o/8),
          clock_ps=833.3333333333334,MLAT=6,ALAT=6,DDIV=21,SIDEX=4,
          primitives='c12 exp/divider/side arithmetic from adopted SU; completion exported from same side result register',
          composed_cycles='request capture + PRIME (1 added root/engine edge) + dispatch + existing opcode pipeline + protected result capture; engine completion drives retirement, no invented zero latency',
          expected_engine_depth=dict(exp=94,sigm=121,silu=121,rsqrt=77,sqrt=35,softplus_sqrt=276,egate=158),
          held=held(sfu_i,sfu_o)),
 hc=dict(top='ot_hbm_hc_quarter',output_lanes=HC,groups=NG,replicas=4,fp32_mac_budget=HC_MACS,operation='HC_POST',
         coverage='HC_POST only. HC_PRE/projection/Sinkhorn/selection remain source-owner dependencies, no whole mHC claim',
         port_bits=dict(request=hc_i,response=hc_o),port_bytes=dict(request=hc_i/8,response=hc_o/8),
         ML=6,AL=5,WIN=0,WOUT=0,
         primitives='ot_dsrom_su_hcpost_group/lane, closed lane_m6a5 SS+.56 FF+4.47; no parent clock inheritance',
         fp32_mul_replicas=5*HC,fp32_add_replicas=4*HC,golden_order='r0*c0+r1*c1; +r2*c2; +r3*c3; +y*p; BF16 RNE',
         composed_cycles='request capture + PRIME (1 added root/engine edge) + dispatch + unchanged group input and HC-post pipeline + protected result capture',
         held=held(hc_i,hc_o)),
 physical=dict(utilization=[.55,.60],SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
               slot_fit='OPEN: actual protected parent geometry/load/CTS/PG/routing inventory not measured; historical outlines not inherited',
               routing='real port bit count above; tracks/serialized 1024b framing require corrected generator consumer binding'),
 adopted=False,per_user_gain_claim=False)
p=ROOT/'results/physical/hbm_die_abstracts_20261006/compute/quarter_size.json'
p.write_text(json.dumps(r,indent=2)+'\n');print('sfu_lanes',SF,'HCpost_groups',NG,'wrappers_FF',r['sfu']['held']['wrapper_ff'],r['hc']['held']['wrapper_ff'])
