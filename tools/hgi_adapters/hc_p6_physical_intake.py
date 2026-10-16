#!/usr/bin/env python3
"""Source-bound structural inventory; no synthesis, floorplan or timing qualification."""
import argparse, hashlib, json, re, subprocess
from pathlib import Path

def blob(ref, path):
    return subprocess.check_output(['git','show',f'{ref}:{path}'])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',default='8fe5d18bd'); ap.add_argument('--out',required=True); a=ap.parse_args()
    source=subprocess.check_output(['git','rev-parse',a.source],text=True).strip()
    path='rtl/hbm_accel/generic/peers/ot_hgi_hc_eng_ll.sv'
    raw=blob(source,path); text=raw.decode(); old=blob(source+'^',path).decode()
    def module(s,name):
        m=re.search(r'^module '+name+r'\b.*?^endmodule',s,re.M|re.S)
        assert m, name
        return m[0].encode()
    assert 'reg [255:0] xb [0:KX*NM-1], gb [0:NM-1]' in text
    assert '.W(271), .DEPTH(FD), .MACRO(0), .ESL(64)' in text
    assert '.D(D), .LQ(LQ), .FD(FD)' in text
    assert module(text,'ot_hgi_hc_lane_sl') == module(old,'ot_hgi_hc_lane_sl')
    changed=subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r',source],text=True).splitlines()
    hashes={p:hashlib.sha256(blob(source,p)).hexdigest() for p in changed}
    D=5120; nm=D//256; lanes=32; slices=lanes*8
    # These are declared array capacities, NOT an optimized mapped cell census.
    lane_arrays={'xb':2*nm*256,'gb':nm*256,'asb':5*256,'op':5*256,'wt':1024,'rha':8*32}
    old_lane_arrays={'xb':nm*256,'gb':nm*256,'asb':5*256,'op':5*256,'wt':640}
    candidates=[]
    for name,groups,nx,ny in [('A_contiguous',1,8,4),('B_quadrant_local',4,4,2)]:
        w=nx*648+(nx-1)*20; h=ny*648+(ny-1)*20
        candidates.append({'name':name,'groups':groups,'lanes_per_group':nx*ny,'width_um':w,'height_um':h,'area_mm2_before_controller':groups*w*h/1e6,'status':'REQUEST_ONLY_NOT_ASSIGNED_NOT_PROVEN_FIT','basis':'Historical 648um lane candidate envelope, with 20um between lanes; P6 added state may require growth. Controller, global reduction, die feedthroughs and clock distribution require additional explicitly assigned homes.'})
    report={'qualification':'PHYSICAL_INTAKE_ONLY_NATIVE_OPEN','source_commit':source,'changed_files_sha256':hashes,'parameters':{'D':D,'LQ':32,'FD':64,'RL':10,'HSL':1,'KX':2,'MUT':0},'structure':{'lanes':lanes,'fp_slices':slices,'fp_slice_module':'ot_hgi_hc_lane_sl','fp_slice_body_unchanged_from_parent':True,'fp_slice_body_sha256':hashlib.sha256(module(text,'ot_hgi_hc_lane_sl')).hexdigest(),'write_fifo_macros':{'master':'ot_sram_1r1w_64x512_m1_r2c2','count':32,'capacity_bits':32*64*512,'payload_width_bits':271,'source':'ot_fifo_sram_fwft MACRO=0'},'declared_lane_arrays_bits':lane_arrays,'declared_lane_arrays_total_bits':sum(lane_arrays.values()),'declared_parent_lane_arrays_total_bits':sum(old_lane_arrays.values()),'declared_lane_arrays_delta_bits':sum(lane_arrays.values())-sum(old_lane_arrays.values()),'declared_xb_gb_bits_all_lanes':lanes*(lane_arrays['xb']+lane_arrays['gb']),'controller_chunk_fifo_declared_bits':32*32*32,'controller_scalar_buffer_declared_bits':8*256,'lane_vm_boundary_bits_all_lanes':lanes*(16+1+257+280+1+1),'clock_ports_in_current_rtl':1,'physical_independent_child_roots_exposed':False},'fit_screen':{'retained_hc_eng_reservation_um':[560,1785.714],'retained_hc_eng_area_mm2':560*1785.714/1e6,'retained_four_boundary_windows_um':[500,500],'boundary_windows_are_not_ll_arithmetic_grants':True,'historical_slice_candidate_um':[140.4,140.4],'historical_slice_failure':'140.4um candidate failed FLOORPLAN_MARGIN at64.7percent; later158.76um successor and151.2um variant existed. No closed current slice view found.','256_slice_candidate_reuse_area_mm2':slices*140.4**2/1e6,'is_universal_lower_bound':False,'full_lane_candidate_reuse_area_mm2':lanes*648**2/1e6,'canonical_pin_file_exists':False,'conclusion':'Existing 1mm2 hc_eng window does not hold the historical candidate outline hierarchy. Actual new-source mapped area and whole-group placement are unmeasured.'},'home_requests':candidates,'required_before_gate':['H-DIE assigns connected full-engine home and exact face/bit/layer pin file','Actual source-pinned lane shell and controller sequential/root census; split buffers/controller roots or measure compliant CTS','Expose independent physical child clock entries; deliver phi-R per child; common RTL clk is not a physical clock proof','Prove fixed production memory/command/calendar slots and no normal runtime credit/backpressure scheduling; inherited cr, xslot_ok, blk_rdy and grant gating are not a compiler schedule','Bind post-descriptor-guard source, full P6 positive/numerical mutant, restart II and exact memory images','Price every physical relay and register stage; prove TT setup/FF hold/DRC0 and native L220/C190/sp80'], 'throughput_scope':'56320-word/1451-cycle result reported by H-MTP is numerical component evidence; post-descriptor-guard exact source receipt and static integrated calendar still pending.'}
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'source':source,'lane_declared_array_bits':sum(lane_arrays.values()),'slice_reuse_area_mm2':report['fit_screen']['256_slice_candidate_reuse_area_mm2'],'home_requests':candidates},indent=2))
if __name__=='__main__': main()
