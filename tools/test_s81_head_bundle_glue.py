#!/usr/bin/env python3
"""Cycle lockstep against unmodified head-bundle glue with element traffic stubs."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run():
    paths=['rtl/hdc/ot_hdc_delay.sv','rtl/v41rom/ot_dsrom_head_bundle.sv','rtl/s81/ot_dsrom_head_bundle_glue.sv','rtl/test/s81/tb_head_bundle_glue.sv','rtl/s81/ot_s81_head_delay8x32.sv']
    original=(ROOT/paths[1]).read_text()
    # Icarus cannot elaborate $sformatf parameters. INSTANCE is unused by the
    # bench's element traffic stub; only these two string expressions change.
    reference=original.replace('$sformatf("%sb", INSTANCE)','"b"').replace('$sformatf("%sa%0d", INSTANCE, q)','"a"')
    rtl=(ROOT/paths[2]).read_text()
    mutants={'baseline':rtl,'demux':rtl.replace("4'd1 << bq","4'd2 << bq"),'tie':rtl.replace('v[48:32] < u[48:32]','v[48:32] > u[48:32]'),'skew':rtl.replace('chain[h+1]','chain[h]')}
    results={}
    with tempfile.TemporaryDirectory(prefix='s81-hbglue-') as tmp:
        d=Path(tmp);(d/'reference.sv').write_text(reference)
        for name,source in mutants.items():
            (d/'dut.sv').write_text(source)
            c=subprocess.run(['iverilog','-g2012','-s','tb','-Ptb.USE_HARD_DELAY8=1','-o',str(d/'sim'),str(ROOT/paths[0]),str(d/'reference.sv'),str(d/'dut.sv'),str(ROOT/paths[3]),str(ROOT/paths[4])],capture_output=True,text=True)
            if c.returncode:raise RuntimeError(c.stderr)
            p=subprocess.run(['vvp',str(d/'sim')],capture_output=True,text=True)
            results[name]={'returncode':p.returncode,'output':p.stdout.strip()}
            assert (p.returncode==0)==(name=='baseline'),results[name]
    invalid=subprocess.run(['iverilog','-g2012','-s','ot_dsrom_head_bundle_glue','-Pot_dsrom_head_bundle_glue.USE_HARD_DELAY8=1','-Pot_dsrom_head_bundle_glue.SK=9','-o','/dev/null',str(ROOT/paths[0]),str(ROOT/paths[2]),str(ROOT/paths[4])],capture_output=True,text=True)
    assert invalid.returncode != 0 and 'ERROR_hardened_head_delay_requires_SK8' in invalid.stderr
    results['unsupported_sk9']={'returncode':invalid.returncode,'output':invalid.stderr.strip()}
    out={'pass':True,'scope':'USE_HARD_DELAY8=1 native hierarchical glue cycle equivalence; element numerical datapaths replaced by traffic stubs in reference only','cycles':1200,'seed':12345,'added_cycles':0,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},'cases':results}
    print(json.dumps(out,indent=2))
if __name__=='__main__':run()
