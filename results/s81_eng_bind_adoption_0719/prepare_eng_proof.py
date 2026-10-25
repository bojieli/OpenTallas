from pathlib import Path
import re,subprocess,shutil
w=Path('/srv/opentallas-scratch2/claude/wt/codex-s81-bindadopt-0719');r=Path('/srv/opentallas-scratch2/claude/codex-s81-bindadopt-0719/proof');r.mkdir(parents=True,exist_ok=True)
script=Path('/srv/opentallas-scratch2/claude/wt/tok-ds-bind178/tools/s81_dv/eng_rr/run_eng_rr.sh').read_text();fs=re.search(r'F=\((.*?)\)\n',script,re.S).group(1).split()
fs+=['rtl/dsrom_sys/engram/static_lookup_1015/ot_s81_engram_hash_n32_layer.sv','rtl/dsrom_sys/engram/static_lookup_1015/dsfd_engram_lkp_ra640_hx.sv','rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr_split.sv']
for f in fs:
 p=r/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','-C','/home/ubuntu/OpenTallas','show','main:'+f]))
eng='rtl/dsrom_sys/s81_dv/eng/dsdv_eng_rr.sv';boot=Path('/srv/opentallas-scratch2/claude/wt/tok-ds-bind178/'+eng).read_text();(r/eng).write_text(re.sub(r'module dsdv_eng_rr\s*#','module reference_eng_rr #',boot))
generated=Path('/srv/opentallas-scratch2/claude/codex-s81-bindadopt-0719/dsdv_eng_rr.sv').read_text();i=generated.index('module dsdv_eng_rr #(');generated=generated[i:].replace('localparam integer SPLIT_MUT = 0;','localparam integer SPLIT_MUT = `ADOPT_MUT;');(r/'adopted.sv').write_text(generated)
t=r/fs[-4] if False else r/'rtl/dsrom_sys/s81_dv/eng/test/tb_dsdv_eng_rr.sv';s=t.read_text()
extra='''
    wire [275:0]boot_vi = (cyc==50) ? ((276'(8'hE6)<<42)|(276'd1<<41)|(276'(RANK)<<39)|(276'd1<<38)|(276'd1<<37)|276'd1) : vi_s;
    wire [42:0]ar,br;wire[275:0]as_,an,bs,bn;wire af,bf;
    reference_eng_rr #(.PCBASE(PCBASE)) refboot(.ck(ck),.rst_n(rst),.f_ks(f_ks),.rco(ar),.pci(pci_h),.vi_s(boot_vi),.vi_n(vi_n),.vo_s(as_),.vo_n(an),.fault(af));
    dsdv_eng_rr #(.PCBASE(PCBASE)) hardboot(.ck(ck),.rst_n(rst),.f_ks(f_ks),.rco(br),.pci(pci_h),.vi_s(boot_vi),.vi_n(vi_n),.vo_s(bs),.vo_n(bn),.fault(bf));
    integer adopt_cycles=0;
    always @(negedge ck)if(rst&&cyc>100)begin
        adopt_cycles=adopt_cycles+1;
        if(ar!==br||as_!==bs||an!==bn||af!==bf)$fatal(1,"ADOPT_LOCKSTEP cyc%0d rco%0d S%0d N%0d fault%0d",cyc,ar!==br,as_!==bs,an!==bn,af!==bf);
    end
'''
s=s.replace('    // ------------------------------------------------------------------ taps, chains, controllers, PHY',extra+'\n    // ------------------------------------------------------------------ taps, chains, controllers, PHY');s=s.replace('        // ------------------------------------------------------------------ verdict','        $display("ADOPT_LOCKSTEP_PASS cycles %0d",adopt_cycles);\n        // ------------------------------------------------------------------ verdict');t.write_text(s)
shutil.copytree('/srv/opentallas-scratch2/claude/s81-cores3/bench/split_base/rom',r/'rom',dirs_exist_ok=True)
(r/'files.txt').write_text(' '.join(fs+['adopted.sv']))
