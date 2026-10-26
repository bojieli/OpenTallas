#!/usr/bin/env python3
"""KV-TOK 10-26: boot ABI single source + check (tools/qwen_static_kv/boot_abi.py, kv_dieslice/native_host_boot_abi.py).

The dispatcher fixture is the exact word_count / MU-seal text of the staged native dispatcher (codex-kv-land-1026
rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_nc32_face.sv, B48 vehicle4), cut to the lines the check reads; the
loader and the OBSX HOST are the repository files."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/qwen_static_kv'))
sys.path.insert(0, str(ROOT / 'tools/qwen_layerbench/kv_dieslice'))
import boot_abi  # noqa: E402
import native_host_boot_abi as nh  # noqa: E402

FACE = """module qkd_static_kv_boot_dispatch_nc32 #(parameter integer MUT=0,parameter integer DIECFG=0,parameter integer NRST=43,parameter integer LINKCFG=0,parameter integer ESCFG=0,parameter integer DIECAP=0,parameter integer AGES=0,parameter integer SRQ=0,parameter integer RS=24,parameter integer DSTG=0)(
 input wire ck);
 function automatic[10:0]word_count(input[3:0]t);
 case(t)1:word_count=327;2:word_count=181;3:word_count=4;4,5:word_count=192;
 6,7,8,9:word_count=1024;10:word_count=(DIECFG!=0)?11'(32+NRST+1+((DIECAP!=0)?1:0)+((AGES!=0)?19:0)):11'd0;11:word_count=(LINKCFG!=0)?11'd66:11'd0;12:word_count=(ESCFG!=0)?11'd1024:11'd0;13:word_count=(ESCFG!=0)?11'd8:11'd0;default:word_count=0;endcase
 endfunction
endmodule
module qkd_static_kv_boot_dispatch_mu_nc32 #(parameter integer MUT=0,parameter integer DIECFG=0,parameter integer NRST=43,parameter integer LINKCFG=0,parameter integer ESCFG=0,parameter integer DIECAP=0,parameter integer AGES=0,parameter integer MU=1,parameter integer WMUT=0,parameter integer SRQ=0,parameter integer DSTG=0)(
 input wire ck);
 qkd_static_kv_boot_dispatch_nc32 #(.MUT(MUT),.DIECFG(DIECFG),.NRST(NRST),.LINKCFG(LINKCFG),.ESCFG(ESCFG),.DIECAP(DIECAP),.AGES(AGES),.SRQ(SRQ),.DSTG(DSTG))u_disp(.ck(ck));
  wire seal_w=w1&&addr==10'd470;
endmodule
"""
CTL = ("qkd_static_kv_boot_dispatch_mu_nc32 #(.MUT(0), .DIECFG(1), .NRST(43), .LINKCFG(1), .ESCFG(1), .DIECAP(1), "
       ".AGES({a}), .MU(1), .WMUT(0), .SRQ(2), .DSTG(1)) u_boot (.ck(ck));")
C45 = """module qkd_host_root_admission_obsx_bo1_c45 #(parameter integer OBS_NB=1
,parameter integer MU=1, parameter integer D2D_BOOT_ORDER=0, parameter integer REQUIRE_MISSION_START=0)(
 input wire ck);
 qkd_host_rank_services_admission_obsx #(.MU(1),.OBS_NB(OBS_NB)) u_rank(.ck(ck));
endmodule
"""
LOADER = (ROOT / 'rtl/qwen_sys/host_20261013/qkd_host_program_loader_target.sv').read_text()
OBSX = (ROOT / 'rtl/qwen_sys/kv_host_obs_20261019/qkd_host_root_admission_obsx.sv').read_text()


def run(ages_disp, boot_ages, thread=True):
    obsx, c45 = (nh.obsx(OBSX), nh.c45(C45)) if thread else (OBSX, C45)
    lp = nh.loader_params(obsx, c45, {'BOOT_AGES': boot_ages})
    return nh.check_texts(CTL.format(a=ages_disp), FACE, LOADER, lp)


class BootAbi(unittest.TestCase):
    def test_native_pass(self):
        eff, disp, ld, img, errs = run(1, 1)
        self.assertEqual(errs, [])
        self.assertEqual((disp[1], disp[10], ld[1], ld[10], img[1], img[10]), (471, 96, 471, 96, 471, 96))

    def test_asbuilt_legacy_loader_caught(self):
        errs = run(1, 1, thread=False)[-1]       # B33 / B48 as built: loader keeps 327 / 77
        self.assertEqual(errs, ['target 1: dispatcher 471 loader 327 image 471',
                                'target 10: dispatcher 96 loader 77 image 96'])

    def test_missing_boot_ages_caught(self):
        self.assertEqual(run(1, 0)[-1], ['target 10: dispatcher 96 loader 77 image 96'])

    def test_ages0_die_consistent(self):
        self.assertEqual(run(0, 0)[-1], [])
        self.assertEqual(run(0, 1)[-1], ['target 10: dispatcher 77 loader 96 image 77'])

    def test_instance_value_from_dispatcher(self):
        self.assertEqual(nh.dispatcher_ages(CTL.format(a=1)), 1)
        self.assertEqual(nh.host_instance_params('.NL(2), .BOOT_AGES(0)', 1), '.NL(2), .BOOT_AGES(1)')
        self.assertEqual(nh.host_instance_params('.NL(2)', 1), '.NL(2), .BOOT_AGES(1)')

    def test_patches_idempotent_and_default_unchanged(self):
        o = nh.obsx(OBSX)
        self.assertEqual(nh.obsx(o), o)
        self.assertEqual(nh.c45(nh.c45(C45)), nh.c45(C45))
        self.assertEqual(nh.loader_params(o, nh.c45(C45), {}), {'MU': 1, 'AGES': 0})   # default BOOT_AGES 0

    def test_pacing(self):
        # t10 AUTH -> t1 BEGIN: 96 words, no descriptors, +16 fixed, +160 declared link bound
        self.assertEqual(boot_abi.next_begin_min(1000, 96, 0), 1000 + 96 + 16 + 160)

    def test_evaluator(self):
        self.assertEqual(boot_abi.sv_eval("(A!=0)?11'(32+N+1):11'd0", dict(A=1, N=43)), 76)
        self.assertEqual(boot_abi.sv_eval("(A!=0)?11'(32+N+1):11'd0", dict(A=0, N=43)), 0)
        with self.assertRaises(ValueError):
            boot_abi.sv_eval('X+1', {})


if __name__ == '__main__':
    unittest.main()
