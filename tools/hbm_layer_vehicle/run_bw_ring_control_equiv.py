#!/usr/bin/env python3
"""Source-80d cycle equivalence and regional count/pop negative controls."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
D = 'rtl/hbm_accel/loader/service_native/'
REF = 'rtl/test/hbm_accel/bw_ring_control/ref_ot_hbm_svc_pc_ctrl_leaf_cfg_safe_80d.sv'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--case', choices=['positive', 'count', 'pop', 'head'], default='positive')
    ap.add_argument('--occupied-reset', action='store_true')
    a = ap.parse_args()
    work = a.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('txn', ROOT/'tools/hbm_layer_vehicle/hbm_pc_bw_safe_txn.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sources = [s for s in mod.SOURCES if not s.endswith('tb_hbm_pc_bw_safe_txn.sv') and not s.endswith('ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv')]
    bench = (ROOT/(D+'tb_hbm_pc_bw_safe_txn.sv')).read_text()
    bench = bench.replace('ot_hbm_svc_pc_ctrl_leaf_cfg_h9b a(', 'ref_ot_hbm_svc_pc_ctrl_leaf_cfg_safe_80d a(')
    # The immutable reference runs the same SAFE controller, so cycle equality
    # is required in addition to the original full transaction comparisons.
    check = '''
  for(genvar r=0;r<22;r=r+1)begin:regional_check
    always @(posedge clk)if(b.region_rst_n[2] && b.lrst_n) begin
      if(b.g_kreg.g_control[r].count_q!==b.count ||
         b.g_kreg.u_kring.g_control[r].g_local.count_q!==b.g_kreg.n ||
         b.g_kreg.pop_regions[r]!==b.accepted ||
         b.g_kreg.push_regions[r]!==b.g_kreg.push_regions[0])
        $fatal(1,"BW_RING_REGIONAL_MISMATCH region%0d",r);
    end
  end
  for(genvar r=0;r<18;r=r+1)begin:kr_check
    always @(posedge clk)if(b.lrst_n && b.region_rst_n[3])begin
      if(b.g_krreg.head_valid_regions[r]!==b.head_valid ||
         b.g_krreg.admission_regions[r]!==b.j_v)
        $fatal(1,"BW_RING_REGIONAL_MISMATCH krregion%0d",r);
    end
  end
  always @(negedge clk)if(rst_n && now>24)begin
    if({k_rdy[0],kr_v[0],k_wr_done[0],row_v[0],col_v[0],col_we[0],pc_fault[0],of[0]} !==
       {k_rdy[1],kr_v[1],k_wr_done[1],row_v[1],col_v[1],col_we[1],pc_fault[1],of[1]} ||
       (kr_v[0] && {kr_tag[0],kr_beat[0],kr_data[0]}!=={kr_tag[1],kr_beat[1],kr_data[1]}) ||
       (row_v[0] && {row_op[0],row_bank[0],row_row[0]}!=={row_op[1],row_bank[1],row_row[1]}) ||
       (col_v[0] && {col_bank[0],col_col[0],col_data[0],col_strb[0]}!=={col_bank[1],col_col[1],col_data[1],col_strb[1]}))
       $fatal(1,"BW_RING_CYCLE_MISMATCH edge%0d",now);
  end
'''
    bench = bench.replace('  // per-DUT logs', check+'\n  // per-DUT logs')
    reset_sequence = '''
    if($test$plusargs("OCCUPIED_RESET"))begin
      repeat(2000)begin
        @(negedge clk); #1 rng=nx(rng); offer=(rng[2:0]!=0);rng=nx(rng);r_now=(rng[3:0]!=0);
      end
      if(idx[1]==0 || idx[1]>=NREQ || (b.count==0 && b.g_kreg.n==0))
        $fatal(1,"BW_RING_RESET_VACUOUS");
      @(negedge clk); #1 rst_n=0;offer=0;r_now=0;
      repeat(6)@(posedge clk);
      @(negedge clk); #1;
      for(d=0;d<2;d=d+1)begin idx[d]=0;nb[d]=0;nw[d]=0;nwd[d]=0;rqw[d]=0;rqr[d]=0;done_at[d]=0;end
      rst_n=1;
      repeat(24)@(negedge clk);
      $display("BW_RING_OCCUPIED_RESET_PASS");
    end
'''
    bench = bench.replace('    while(!(done_at', reset_sequence+'    while(!(done_at')
    (work/'tb.sv').write_text(bench)
    cfg = (ROOT/(D+'ot_hbm_svc_pc_ctrl_leaf_cfg_safe.sv')).read_text()
    if a.case == 'count':
        old = 'else count_q<=queue_count_next;'
        new = "else count_q<=queue_count_next+((r==1&&cv)?1'b1:1'b0);"
    elif a.case == 'pop':
        old = 'assign pop_regions[r]=valid_regions[r]&&ready_local;'
        new = 'assign pop_regions[r]=valid_regions[r]&&ready_local&&(r!=1 || !cv);'
    elif a.case == 'head':
        old = 'else head_valid_regions[r]<=head_valid_next;'
        new = 'else head_valid_regions[r]<=head_valid_next&&(r!=1 || !response_read);'
    if a.case != 'positive':
        assert cfg.count(old) == 1
        cfg = cfg.replace(old, new)
    (work/'cfg.sv').write_text(cfg)
    sources.remove(D+'ot_hbm_svc_pc_ctrl_leaf_cfg_safe.sv')
    files = sources+[REF, D+'tb_hbm_pc_bw_safe_txn.sv', D+'ot_hbm_svc_pc_ctrl_leaf_cfg_safe.sv', 'tools/hbm_layer_vehicle/hbm_pc_bw_safe_txn.py', str(Path(__file__).relative_to(ROOT))]
    pins = {s: hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in files}
    verilator = os.environ.get('VERILATOR', str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
    version = subprocess.check_output([verilator, '--version'], text=True).strip()
    assert re.search(r'Verilator 5\.050\b', version), version
    digest = hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()[:12]
    obj = work/('obj_'+digest)
    cmd = [verilator, '--binary', '--timing', '-Wno-fatal', '--top-module', 'tb', '-O2', '--Mdir', str(obj), '-j', '8', str(work/'tb.sv'), str(work/'cfg.sv')]
    cmd += [str(ROOT/s) for s in sources+[REF]]
    with (work/'build.log').open('w') as out:
        subprocess.run(cmd, stdout=out, stderr=subprocess.STDOUT, check=True)
    run = subprocess.run([str(obj/'Vtb')]+(['+OCCUPIED_RESET'] if a.occupied_reset else []), capture_output=True, text=True)
    log = run.stdout+run.stderr
    (work/'run.log').write_text(log)
    regex = r'BW_RING_REGIONAL_MISMATCH|BW_RING_CYCLE_MISMATCH|BW_SAFE_TXN_(?:BEAT|WCOL)_MISMATCH'
    passed = run.returncode == 0 and 'BW_SAFE_TXN PASS' in log if a.case == 'positive' else run.returncode != 0 and bool(re.search(regex, log))
    receipt = dict(case=a.case, occupied_reset=a.occupied_reset, verdict='PASS' if passed else 'FAIL', returncode=run.returncode, source_sha256=pins, generated_cfg_sha256=hashlib.sha256(cfg.encode()).hexdigest(), verilator=version, fail_regex=regex if a.case!='positive' else None)
    (work/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))
    print(log[-1500:])
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
