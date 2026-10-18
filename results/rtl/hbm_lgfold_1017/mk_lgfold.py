import json,copy,sys
from pathlib import Path
RT=Path('physical/ref_tile')
base=json.loads((RT/'hbm_sfu_lg_pair_leaf_2330/spec.json').read_text())
def ranges(order,bits,lo,hi):
    tot=sum(bits[p] for p in order); out={}; y=lo
    for p in order:
        w=(hi-lo)*bits[p]/tot; out[p]=[round(y,3),round(y+w,3)]; y+=w
    return out
SRC=["rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_tap_leaf.sv","rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_leaf.sv",
     "rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_pair_tap.sv","rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv",
     "rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank_term.sv","rtl/hdc/ot_hdc_delay.sv"]
B=dict(c_rq=34,c_wq=562,c_rr=514,c_w_done=2,far_rq=34,far_wq=562,far_rr=514,far_w_done=2,near_rq=34,near_wq=562,near_rr=514,near_w_done=2,
       clk=1,rst_n=1,local_read=2,local_write=2,fault=1)
def mk(term):
    s=copy.deepcopy(base)
    for k in ('io_tcl','pin_reg_split','hold_pad'): s.pop(k,None)
    W=H=216.0
    name='hbm_hc_lg_pair_tap_leaf_term_1017' if term else 'hbm_sfu_lg_pair_tap_leaf_1017'
    s['name']=name; s['top']='ot_hgi_sfu_lg_pair_tap_leaf_term' if term else 'ot_hgi_sfu_lg_pair_tap_leaf'
    s['sources']=SRC; s['params']={'READ_RETURN':18,'WRITE_RETURN':15} if term else {'READ_RETURN':14,'WRITE_RETURN':11}
    s['outline']={'w':W,'h':H,'exact':True}; s['recipe']=4
    s['route']={"pd":0.5,"threads":4,"peak_ram_gb":6,"hold_margin_ns":0.03,"macro_halo_um":5.4,"pin_h":"M4","pin_v":"M3 M5",
                "pin_balance":{"h":"M4","v":"M3 M5","group_max":1},"io_hold_margin_ns":0.0}
    s['io_flop_at_pins']={"cols":4,"allow_none":True}; s['inhold']=False; s['outhold']=False; s['keep_pin_regs']=True; s['hold_budget']='die'
    s['std_area_um2']=1600 if not term else 1250
    ctl=['local_read','local_write','clk','rst_n','fault']
    if term:
        # W = core pair slice (c_*), E = near (toward the SFU-level taps), N = clock/reset/calendar selects (centre)
        pins={'W':['c_rq','c_wq','c_rr','c_w_done'],'E':['near_rq','near_wq','near_rr','near_w_done'],'N':ctl}
    else:
        # W = far (HC-level taps), E = near (SU level / VM bank), N = core request side, S = core return side
        pins={'W':['far_rq','far_wq','far_rr','far_w_done'],'E':['near_rq','near_wq','near_rr','near_w_done'],
              'N':['c_rq','c_wq'][:1]+['local_read','local_write','clk','rst_n','fault']+['c_wq'],'S':['c_rr','c_w_done']}
    s['pins']=pins
    pr={}
    for f,order in pins.items():
        if f=='N' and term: pr.update(ranges(order,{p:(1 if B[p]<3 else B[p]) for p in order},W/2-12,W/2+12)); continue
        pr.update(ranges(order,{p:max(B[p],4) for p in order},4.0,(W if f in 'NS' else H)-4.0))
    if not term:
        pr.update({'c_rr':[4.0,103.0]}); pr.update(ranges(ctl,{p:1 for p in ctl},104.0,112.0)); pr.update(ranges(['c_rq','c_w_done'],{'c_rq':34,'c_w_done':4},113.0,212.0))
    s['pin_ranges']=pr
    s['pin_regs']={'enable':False,'reason':'Every boundary bit already has its register in RTL: the pair leaf registers core<->tap one edge each way and each tap registers local/far/near inputs at the pins and its mux/output stage; reset is one pin register. Wrapper flops would add edges to the fixed calendar.'}
    s['structural_change']=('LG tap FOLD (coordinator 0db 10-17): the bank-pair LG leaf and its two static LG taps ('+
        ('ot_hbm_vm_lg_static_bank_term, HC level 18/15' if term else 'ot_hbm_vm_lg_static_bank, SFU level 14/11 as parameters, no rret/wret straps')+
        ') are ONE tile; the 37.8-um tap slots and the 1,112-bit leaf<->tap seam disappear. Same edges as the discrete composition '+
        '(lockstep bench tools/hbm_static/lg_fold_run.sh PASS, payload-mux mutant FAILS). Pin-bound square 216x216: '+
        ('W core 1,112 / E near 1,112 (5.1/um), clk+rst+selects N centre.' if term else 'W far 1,112 / E near 1,112 (5.1/um), N core write request 562 full face; S core return 514, then clk/rst/selects at the S centre, then core read request 34 + done; register mass = pin flops on every face.'))
    j=s['job']; j['owner']='Claude:HBM-TILES-B'; j['branch']='claude/hbm-lgfold-1017'; j['tag']='f1'
    j['purpose']='LG tap fold into its consumer tile (0db): '+('HC-level pair leaf + 2 terminal taps' if term else 'SFU-level pair leaf + 2 taps')
    j['record_to']='results/rtl/ref_tile/'+name; j['views_to']=f'physical/ref_tile/{name}/views'; j['auto_merge']=False
    j['extra_paths']=['tools/hbm_static/lg_fold_run.sh','rtl/test/hbm_accel/generic/tb_hgi_lg_pair_tap_fold.sv']
    j['benches']=[{"name":"fold_lockstep","cmd":"bash tools/hbm_static/lg_fold_run.sh {RUN}/bench/pos 0","expect":"pass","pass_regex":"LG_FOLD PASS","min_count_regex":"checks=(\\d+)","threads":1,"peak_ram_gb":2,"needs":["iverilog"]},
                  {"name":"fold_mutant","cmd":"bash tools/hbm_static/lg_fold_run.sh {RUN}/bench/mut 1","expect":"fail","fail_regex":"LG_FOLD FAIL","threads":1,"peak_ram_gb":2,"needs":["iverilog"]}]
    (RT/name).mkdir(exist_ok=True)
    p=RT/name/'spec.json'; p.write_text(json.dumps(s,indent=1)+'\n'); print(p)
mk(False); mk(True)
