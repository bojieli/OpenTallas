#!/usr/bin/env python3
"""DH81-HOST 11-07: private hd_host form vC from a generated l48uj kit. Candidate only, DO_NOT_COUNT, no POR change.

GEOMETRY read on vA 3_5_place_dp: the E macro grid is a translation of the W grid (W to E: fifo, rb, sf, head), but its hub
is on its west side, so lane1's frame path crosses the gap, then its own grid, and doubles back to the S pins.
Changes, each against a measured problem:
  RTL   OT_S81HD_HOST_XGRID: lane1 RX +2, TX +1 at the lane/hub boundary (ot_s81hd_host_xgrid).
  MACRO E grid columns reversed, so head faces the hub and sf faces coll_o1; rb|sf channel 17.3 -> 21.6 um W, 25.9 um E.
  PLACE host_xgrid_anchor.tcl: crossing stages in the gap, hub codecs under their N pins.
  CLOCK OT_TAP_MAX_SINKS 3500, OT_TAP_REASSIGN_UM 320: the 19 existing taps share the sinks within each grid.
"""
import argparse,json,re,shutil,sys
from pathlib import Path

W_COLS={285.228:289.548,337.068:354.348}
E_C=[924.588,976.428,1028.268,1080.108,1131.948,1183.788]
E_NEW=[E_C[0]-8.64,E_C[1]-8.64,E_C[2],E_C[3],E_C[4],E_C[5]]
E_COLS={E_C[5-i]:E_NEW[i] for i in range(6)}
RECTS=[
 (r'u_core[.]u_xg[.](rq1|rv1|fl1)',560,300,572,450),
 (r'u_core[.]u_xg[.](tq0|tv0)',650,265,662,415),
 (r'u_core[.]u_xg[.](rq0|rv0|fl0)',740,230,752,380),
 (r'u_core[.]u_ctl_tx[.]',332,395,396,480),
 (r'u_core[.]u_ctl_rx[.]',402,395,470,480),
]
SIZE={'ot_sram_1r1w2c_256x64_m1':(34.56,41.4),'ot_sram_1r1w2c_32x64_m1':(32.0,17.3)}
LEDGER={'schema':'opentallas.pin_cycles.candidate.v1','module':'ot_s81hd_host_ep','form':'hd_host_vC_XGRID',
 'baseline':'l48uj hd_host vA','enable':'-DOT_S81HD_HOST_XGRID in VERILOG_DEFINES','DO_NOT_COUNT':True,
 'added_cycles':{'coll_i1_to_h_rx_o_csr_type6':2,'coll_i1_fault_to_status':2,'h_tx_i_to_coll_o1_status_type8':1,
  'coll_i0_to_h_rx_o_hfwd_type7':0,'h_tx_i_to_coll_o0_result_type9':0,'hbc_boot_dates':0},
 'clock_ps':833,
 'model_status':'CANDIDATE ONLY: compiler re-dates host1 CSR frames +2; STATUS +1; no POR change',
 'notes':'lane1 carries CSR in and STATUS out only. A lane1 CSR arriving +2 must still miss fw and the 3-cycle rx_gap, else a schedule fault.'}

def move_macros(t):
    def f(m):
        x=float(m.group(2)); nx=W_COLS.get(x,E_COLS.get(x))
        return m.group(0) if nx is None else f'{m.group(1)}{nx:.4f} {m.group(3)}'
    t2,n=re.subn(r'(place_macro .*?-location \{)([0-9.]+) ([0-9.]+\} -orientation R0 -exact)',f,t)
    assert n==110,n
    return t2

def boxes(t):
    r=[]
    for m in re.finditer(r'-macro_name \{(\S+)\} -location \{([0-9.]+) ([0-9.]+)\}',t):
        big='g_256' in m.group(1); w,h=SIZE['ot_sram_1r1w2c_256x64_m1' if big else 'ot_sram_1r1w2c_32x64_m1']
        r.append((m.group(1),float(m.group(2)),float(m.group(3)),w,h))
    return r

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('src',type=Path); ap.add_argument('out',type=Path)
    ap.add_argument('--core',type=Path,required=True); ap.add_argument('--anchor',type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists(): sys.exit('refusing existing '+str(a.out))
    (a.out/'hd_host').mkdir(parents=True)
    S=a.src/'hd_host'; K=a.out/'hd_host'
    src_mtime=(S/'config.mk').stat().st_mtime
    for p in S.iterdir():
        if p.name in ('run','lec','physical_completion','preflight_history','__pycache__','lec_async.runs'): continue
        if p.stat().st_mtime>src_mtime+3600: continue     # results of the vA run, not kit inputs
        if p.is_dir(): shutil.copytree(p,K/p.name,symlinks=True)
        else: shutil.copy2(p,K/p.name)
    for n in ('_rtl',):
        shutil.copytree(a.src/n,a.out/n,symlinks=True)
    shutil.copy2(a.src/'run_kit.sh',a.out/'run_kit.sh')
    shutil.copy2(a.core,K/'rtl'/'ot_s81hd_host_ep_core.sv')
    shutil.copy2(a.anchor,K/'host_xgrid_anchor.tcl')
    t=(K/'macro_place.tcl').read_text(); t2=move_macros(t); (K/'macro_place.tcl').write_text(t2)
    c=(K/'config.mk').read_text()
    x='-DOT_COLL_NATIVE32_OFF\n'; assert c.count(x)==1
    c=c.replace(x,'-DOT_COLL_NATIVE32_OFF -DOT_S81HD_HOST_XGRID\n')
    for k,v in (('OT_TAP_MAX_SINKS',3500),('OT_TAP_REASSIGN_UM',320)):
        c,n=re.subn(rf'^export {k} = .*$',f'export {k} = {v}',c,flags=re.M); assert n==1
    rects=' '.join('{%s} %s %s %s %s'%r for r in RECTS)
    c+=f'export OT_HOST_XGRID = 1\nexport OT_HOST_XGRID_RECTS = {rects}\n'
    (K/'config.mk').write_text(c)
    f=(K/'face_flops.tcl').read_text()
    y='# OT_GPL_GUARD begin'; assert f.count(y)==1
    f=f.replace(y,'# DH81-HOST: opt-in crossing stages and hub codecs FIRM before GPL\nif {[file exists /work/host_xgrid_anchor.tcl] && [info exists ::env(OT_HOST_XGRID)]} { source /work/host_xgrid_anchor.tcl }\n'+y)
    (K/'face_flops.tcl').write_text(f)
    (K/'added_rx_clk_PIN_cycles.json').write_text(json.dumps(LEDGER,indent=2)+'\n')
    (K/'DO_NOT_COUNT').write_text('Private DH81-HOST XGRID candidate from l48uj vA. lane1 RX +2, TX +1, E grid columns reversed. Adoption, compiler pricing and plan event required.\n')
    (K/'HOLD_ROUTE').write_text('DH81-HOST: place and geometry only. Route release is DIE-HEAD-81 / COORD.\n')
    # collisions of interior pins and reset relays with the moved macros
    w=(K/'rtl'/'ot_s81hd_host_ep.sv').read_text(); bad=[]
    B=boxes(t2)
    pts=[('rrl '+m.group(1),float(m.group(2)),float(m.group(3))) for m in re.finditer(r'(?m)^.*?u_rrl_(\d+).*@ \(([0-9.]+), ([0-9.]+)\)',w)]
    for m in re.finditer(r'place_pin -pin_name (\S+) -layer \S+ -location \{([0-9.]+) ([0-9.]+)\}.*interior',(K/'io.tcl').read_text()):
        pts.append((m.group(1),float(m.group(2)),float(m.group(3))))
    for nm,x,y in pts:
        for b in B:
            if b[1]-1<x<b[1]+b[3]+1 and b[2]-1<y<b[2]+b[4]+1: bad.append((nm,x,y,b[0][:50],b[1],b[2]))
    print('OVERLAY OK',K,'interior points checked',len(pts),'inside moved macros',len(bad))
    for r in bad[:30]: print(' HIT',r)
if __name__=='__main__': main()
