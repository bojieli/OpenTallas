#!/usr/bin/env python3
"""Explicit compact COLL physical recipe, applied ONLY to a fresh generated kit."""
import argparse, hashlib, json, re, shutil, subprocess
from pathlib import Path

SOURCE_REVISION = '336bbc9add43'
SOURCE_FILES = {
    'coll/ot_s81ph_coll_lane_safe4.sv':'47b0d96ec8e42a4113e59b18469d7b3ee5bb82561e92d07f1c9458cbeb66449b',
    'ot_s81ph_link_ep_safe4.sv':'2e99835088b276d193fad614267f87763afeee89cdc23591f5254de238356f55',
    'ot_s81ph_link_gbx_safe3.sv':'d2097a89255af417d83044a37c8eff889b1bbfe4ec1defae0e6b1c73c5695b0a'}
CLOCK_PIN_SHA256 = 'e7b51a243359373541376444eb9555de51822bdf3387bf024b8e7f3156f9bc72'

def declare_clock_pin(kit):
    kit=Path(kit)
    # DIE-S81-62: the reviewed hook changes native metal, never the plan anchor.
    for filename in ('pins.json','audit_pins.json'):
        path=kit/filename
        if not path.exists(): continue
        rows=json.loads(path.read_text())
        selected=[p for p in rows if p['bus']=='ck' and p.get('bit')==0]
        assert len(selected)==1, 'exact ck[0] metadata required'
        pin=selected[0]
        assert pin['layer']=='M5' and [pin['x'],pin['y']]==[147.948,236.520]
        assert pin.get('native_rects') in (None, [['M5',147.924,236.280,147.972,236.760]], [['M5',147.924,236.232,147.972,236.760]]), 'unexpected prior native pin geometry'
        pin['native_rects']=[['M5',147.924,236.232,147.972,236.760]]
        pin['native_rects_review']='DIE-S81-62; ck0_pin.tcl sha256 '+CLOCK_PIN_SHA256
        path.write_text(json.dumps(rows,indent=1)+'\n')


def replay(repo, kit, ckpin):
    repo,kit,ckpin=map(Path,(repo,kit,ckpin))
    f=json.loads((kit/'freeze.json').read_text())
    assert f['module'] in ('dsfd_coll_lane_e_safe8_ntf','dsfd_coll_lane_w_safe8_ntf')
    assert f['outline_um']==[295.92,444.96] and f['pins']==2143
    assert f['insertion_ps']==405 and f['insertion_ff_ps']==340
    assert hashlib.sha256(ckpin.read_bytes()).hexdigest()==CLOCK_PIN_SHA256
    assert not (kit/'run').exists(), 'replay requires an unstarted fresh kit'
    # Exact already-proved inherited RBL1 form, still deliberately off main.
    source_revision, files = SOURCE_REVISION, SOURCE_FILES
    for name,digest in files.items():
        data=subprocess.check_output(['git','-C',str(repo),'show',source_revision+':rtl/dsrom_sys/s81_ph/'+name])
        assert hashlib.sha256(data).hexdigest()==digest, name
        (kit/'rtl'/Path(name).name).write_bytes(data)
    (kit/'source_overlay.json').write_text(json.dumps(dict(source_revision=source_revision,
        sha256=files,proof='COORD queue 2026-11-05 07:43: positive loop/miter PASS; all8 mutants FAIL',
        latency='existing RBL1 form +1TX already priced; zero extra versus inherited kits'),indent=1)+'\n')
    pdn=(kit/'pdn.tcl').read_text()
    assert '-pins {M6}' in pdn and '-layers {M5 M6}' in pdn
    assert pdn.count('-halo {2.0 2.0}')==1
    (kit/'pdn.tcl').write_text(pdn.replace('-halo {2.0 2.0}','-halo {2.0 1.08}'))
    cfg=(kit/'config.mk').read_text()
    def setvar(name,value):
        nonlocal cfg
        pat=r'(?m)^(?:override )?export '+re.escape(name)+r' = .*$'
        if re.search(pat,cfg): cfg=re.sub(pat,'export '+name+' = '+value,cfg)
        else:cfg+='\nexport '+name+' = '+value+'\n'
    for k,v in dict(MACRO_PLACE_HALO='4.32 1.08',MACRO_ROWS_HALO_Y='1.08',
        CTS_ARGS='-sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.5 -root_buf BUFx24_ASAP7_75t_R -buf_list BUFx12_ASAP7_75t_R',
        OT_CKKM_K='32', OT_CKKM_PORT='ck[0]', PRE_CTS_TCL='/work/form_pre_cts.tcl',
        OT_HOLD_STOP='grt:2000',DETAIL_PLACEMENT_ARGS='-use_diamond_legalizer',
        OT_GRT_DPL_ARGS='-use_diamond_legalizer',PRE_DETAIL_ROUTE_TCL='/work/ck0_pin.tcl').items():setvar(k,v)
    (kit/'config.mk').write_text(cfg)
    shutil.copyfile(repo/'physical/common_flow/clock_split_km.tcl',kit/'clock_split_km.tcl')
    shutil.copyfile(ckpin,kit/'ck0_pin.tcl')
    declare_clock_pin(kit)
    (kit/'form_pre_cts.tcl').write_text('source /work/hold_budget.tcl\nsource /work/clock_split_km.tcl\n')
    p=kit/'grt_pre_core.tcl';s=p.read_text()
    assert 'set_routing_layers -signal M2-M6 -clock M4-M5' not in s
    p.write_text(s+'\n# Exact reviewed compact M6 signal/clock ceilings.\nset_routing_layers -signal M2-M6 -clock M4-M5\n')
    (kit/'compact_form_replay.json').write_text(json.dumps(dict(schema='opentallas.compact_coll_form.v1',
        geometry='original 295.92x444.96; exact55 macro sites from inherited vC/vD',
        pg_interface='actual M6; parent M7 landing owed',rtl_changes='exact pinned inherited RBL1 source overlay336bbc9add43',added_cycles=0,
        note='Private trial; parent reservation, routed signoff and LEC still owed'),indent=1)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('repo');p.add_argument('kit');p.add_argument('ckpin')
    a=p.parse_args();replay(a.repo,a.kit,a.ckpin)
