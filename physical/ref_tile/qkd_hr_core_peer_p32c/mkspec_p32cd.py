import json,sys,copy
WT=sys.argv[1]
base=json.load(open(f'{WT}/physical/ref_tile/qkd_hr_core_peer_p32a/spec.json'))
BOOT=['slice_boot_done','slice_boot_ok','u_rank__guarded_tk','local_service_epoch','local_kst']
TX=['u_rank__tx_d','u_rank__tx_v','u_rank__tx_cr']; RAW=['u_rank__raw_rx_d','u_rank__raw_rx_v','u_rank__raw_rx_cr']
SB=['u_rank__service_begin_epoch','u_rank__service_begin_v']
for v,bface in (('c','W'),('d','E')):
    s=copy.deepcopy(base); s['name']=f'qkd_hr_core_peer_p32{v}'
    for f in s['pins']: s['pins'][f]=[p for p in s['pins'][f] if p not in BOOT]
    s['pins'][bface]+= BOOT
    r=s['pin_ranges']
    for p in BOOT: r[p]=[64.8,453.6]
    # Codex phase model (rtl/test/host_peer_main_fixture_1020/primitive32/physical_review_0720/pin_model_expanded_phase.py):
    # TX on E beside the lower-right TX SRAM, raw RX on S beside the lower-left SRAM, service-begin beside RX reader
    for p in TX: r[p]=[64.8,178.0]
    for p in SB: r[p]=[180.0,192.0]
    for p in RAW: r[p]=[59.4,200.0]
    for p in s['pins']['E']:
        if p not in TX+SB and p!='ck_core' and p in r: r[p]=[196.0,453.6]
    for p in s['pins']['S']:
        if p not in RAW and p in r: r[p]=[205.0,415.8]
    at={m['inst']:m for m in s['macros']}
    at['u74592_c0/u_cell']['at']=[259.2,43.2]; at['u74646_c0/u_cell']['at']=[43.2,43.2]
    s['structural_change']={'kind':'floorplan_change','reason':
      f'p32a/b + PEER refusal fix: qkd_hr_core_peer_n32 FF u73608_c0 (AND of 128 slice_boot_done + 128 slice_boot_ok + 93 guarded_tk + local_service_epoch/local_kst pin regs) read pins on BOTH W and E faces (~459 um apart, Codex phase15530 REFUSED). All five buses only feed that reducer (+2 summaries), so they move together to the {bface} face. Lower SRAM identities swapped and TX(E 64.8..178)/rawRX(S 59.4..200) windows per Codex phase model (1058 boundary-macro pairs <=351 um nominal). Source unchanged (sha 1277bb49), 0 added edges.'}
    ck=s['safe_design_checklist']; ck['2_reach']=f'FIXED: boot reducer inputs on one face ({bface}); TX/rawRX windows beside their SRAMs (model 1058 pairs <=351 um); actual placed reach audit after gate.'
    ck['3_fanout']='PRE-GATE NATIVE: source unchanged (1277bb49) -> Codex primitive32 resynth census 62936 roots max32/0 (reset nets incl.) still applies; pin/macro moves only.'
    d=f'{WT}/physical/ref_tile/qkd_hr_core_peer_p32{v}'
    import os; os.makedirs(d,exist_ok=True); json.dump(s,open(d+'/spec.json','w'),indent=1)
    print(v, {f:len(l) for f,l in s['pins'].items()})
