#!/usr/bin/env python3
"""Copy a pinned completed build, add simulation-only observation, rebuild incrementally."""
import pathlib,shutil,subprocess,shlex,json,hashlib
base=pathlib.Path('/srv/opentallas-scratch/claude/s81-suhc'); dst=base/'throughput-trace-3c';dst.mkdir(exist_ok=True)
src=dst/'src'; obj=dst/'build'; old=base/'3c-full/build_ng256_dpi_m0_a0_hier3tail_cp1_cs6'
subprocess.run(['cp','--reflink=auto','-a',str(base/'3c-src'),str(src)],check=True) if not src.exists() else None
subprocess.run(['cp','--reflink=auto','-a',str(old),str(obj)],check=True) if not obj.exists() else None
seq=src/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cseq.sv';cth=src/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth.sv'
original={str(p.relative_to(src)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [seq,cth]}
t=seq.read_text(); obs='''\n`ifndef SYNTHESIS
    always @(posedge sk) if ($test$plusargs("HC_TRACE") && rs_n) begin
        if (take && c_arg[22:20] == K_POST) $display("HCT SEQ_START t=%0t tag=%0d", $time, e_d[6:0]);
        if (run && kind == K_POST && y_take && (ci == 0 || ci == NR-1)) $display("HCT SEQ_Y t=%0t idx=%0d", $time, ci);
        if (run && kind == K_POST && pob_q && (post_ob == 0 || post_ob == NR-1)) $display("HCT SEQ_RETURN t=%0t idx=%0d", $time, post_ob);
        if (d_v && kind == K_POST) $display("HCT SEQ_DONE t=%0t tag=%0d", $time, d_t);
    end
`endif
''';t=t.replace('endmodule',obs+'endmodule',1);seq.write_text(t)
t=cth.read_text();a=t.index('module ot_s81_hc_ctpl #(');b=t.index('endmodule',a);obs='''\n`ifndef SYNTHESIS
    always @(posedge clk) if ($test$plusargs("HC_TRACE") && rst_n && gq == 0 && hq == 0) begin
        if (hp_go) $display("HCT TILE_GO t=%0t path=%m", $time);
        if (hov && (pob == 0 || pob == D/NG-1)) $display("HCT TILE_OUTPUT t=%0t idx=%0d path=%m", $time,pob);
    end
`endif
''';t=t[:b]+obs+t[b:];cth.write_text(t)
(dst/'instrumentation_manifest.json').write_text(json.dumps({'source':'3c62573d5','original':original,'observed':{str(p.relative_to(src)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [seq,cth]},'purpose':'Simulation-only event observation; no synthesizable behavior changed.'},indent=2)+'\n')
cmd=shlex.split((base/'3c-full/build_ng256_dpi_m0_a0_hier3tail_cp1_cs6.log').read_text().splitlines()[0]);cmd=[x.replace(str(base/'3c-src'),str(src)).replace(str(old),str(obj))for x in cmd]
# Mdir in original is an absolute source-qualified output path: explicitly select copied objects.
cmd[cmd.index('-Mdir')+1]=str(obj)
with (dst/'build.log').open('w')as f:
 f.write(shlex.join(cmd)+'\n');f.flush();subprocess.run(cmd,cwd=src,stdout=f,stderr=subprocess.STDOUT,check=True)
exe=obj/'Vtb_s81_hc_master';run=base/'3c-full/runs/golden_L0_L2';
with (dst/'run.log').open('w')as f:subprocess.run([str(exe),'+HC_TRACE'],cwd=run,stdout=f,stderr=subprocess.STDOUT,check=True)
(dst/'DONE').write_text('build and existing production golden vector rc0\n')
