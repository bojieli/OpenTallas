#!/usr/bin/env python3
"""KV die HBM3E refresh calendar (Q-KVSYS-DIE 2026-10-15, compiler request: "provide the real refresh schedule; it is
modelled as zero today").  A STATIC schedule: every refresh command is at a compiler-known time, nothing is postponed or
pulled in at run time, so the KV static calendar can place its reads around the windows.

Timing (JESD238 HBM3, the project's HBM model rtl/dsrom_sys/c8/ot_hdc_v41x_idx_hbm_c8.sv / Ramulator 2 72427a1, 16 Gb dies,
8-high, normal temperature): tREFI 3.9 us, all-bank tRFC 350 ns, per-bank tRFCpb 200 ns, 32 banks per pseudo-channel
(2 SID x 4 bank groups x 4 banks), tREFIpb = tREFI / 32 = 121.875 ns, tRREFD 8 ns.  Core clock 1.2 GHz (833.333 ps).

Policy (recommended, REFpb): per pseudo-channel p (0..127 = stack * 32 + pc), bank b is refreshed at
    t(n, b, p) = n * tREFI + b * tREFIpb + phase(p),   phase(p) = (p % 32) * tREFIpb / 32
blocking that bank for tRFCpb (~1.64 of 32 banks busy at any time); the other 31 serve.  The KV static calendar must not
issue an ACT/RD to (p, b) inside [t, t + tRFCpb) and keeps tRREFD around each REFpb.  Alternative (REFab): the whole
pseudo-channel blocked tRFC every tREFI at phase(p) * 32 -- 8.97 % of each channel's time.

    python3 tools/qwen_kv_die/hbm_refresh_calendar.py --out FILE.json
"""
import argparse, json
from pathlib import Path

CORE_PS = 1e6 / 1200.0
T = dict(tREFI_ps=3_900_000, tRFC_ab_ps=350_000, tRFC_pb_ps=200_000, banks_per_pc=32, tRREFD_ps=8_000)


# What the die's HBM controller RTL ACTUALLY does (rtl/qwen_sys/emb_hbm_20261008/ot_hbm_r14_stream_pc_srow.sv defaults,
# instantiated by rtl/physical/ot_qwen_ctrl_pc_head.sv): REF_MODE 1 (REFpb), HBM controller clock 1.024 ns, tREFIpb 118
# cycles (120.8 ns <= 121.875: never late), tRFCpb 196, tRREFD 8, REF_PHASE(pc) = (PHASE + pc*118/32) % 118, refresh issued
# on the due cycle (never postponed; PULLIN 0); the BANK is chosen LEAD cycles ahead (closed, not needed within tRFCpb +
# tRCD), so the compiler sees a fixed TIME table and a guaranteed non-conflicting bank.
RTL = dict(file='rtl/qwen_sys/emb_hbm_20261008/ot_hbm_r14_stream_pc_srow.sv', head='rtl/physical/ot_qwen_ctrl_pc_head.sv',
           hbm_clk_ps=1024, REF_MODE=1, T_REFIPB=118, T_RFCPB=196, T_RREFD=8, T_REFI=3808, T_RFC=342)


def rtl_calendar():
    c = RTL['hbm_clk_ps']
    pcs = [dict(pc=k, REF_PHASE_hbm_cycles=(k * 118) // 32 % 118, first_refpb_ps=((k * 118) // 32 % 118) * c) for k in range(32)]
    return dict(source=RTL, period_ps=RTL['T_REFIPB'] * c, period_core_cycles=round(RTL['T_REFIPB'] * c / CORE_PS, 3),
                bank_busy_ps=RTL['T_RFCPB'] * c, rrefd_ps=RTL['T_RREFD'] * c,
                act_slot_loss_upper_bound=round(RTL['T_RREFD'] / RTL['T_REFIPB'], 4),
                per_stack_pc_phases=pcs,
                compiler_rule=('per PC: one REFpb at REF_PHASE + n*118 HBM cycles; for tRREFD (8 cycles) around it no ACT; one bank '
                               'out of 32 busy tRFCpb (196), chosen by the controller outside the stream\'s current and next two '
                               'sets -> RD continuity is kept; model the 8-cycle ACT gap per 118 cycles (<= 6.8 % ACT slots)'))


def calendar():
    refipb = T['tREFI_ps'] / T['banks_per_pc']
    pcs = []
    for p in range(128):
        ph = (p % 32) * refipb / 32
        pcs.append(dict(pc=p, stack=('WS', 'WN', 'ES', 'EN')[p // 32], phase_ps=round(ph, 3),
                        phase_core_cycles=round(ph / CORE_PS, 3)))
    return dict(schema='opentallas.qwen-kvsys-hbm-refresh-calendar.v1', status='STATIC SCHEDULE (no run-time postpone / pull-in)',
                timing=dict(T, tREFIpb_ps=refipb, source='JESD238 HBM3 16 Gb 8-high (project HBM model / Ramulator 2 72427a1)'),
                core_clock_ps=CORE_PS,
                policy_recommended=dict(kind='REFpb round-robin', command_time='n*tREFI + b*tREFIpb + phase(p)',
                    bank_busy_ps=T['tRFC_pb_ps'], busy_banks_avg=round(T['tRFC_pb_ps'] / refipb, 3),
                    in_core_cycles=dict(tREFI=round(T['tREFI_ps'] / CORE_PS, 3), tREFIpb=round(refipb / CORE_PS, 3),
                                        tRFCpb=round(T['tRFC_pb_ps'] / CORE_PS, 3), tRREFD=round(T['tRREFD_ps'] / CORE_PS, 3)),
                    calendar_rule='no ACT/RD to (pc, bank) in [t, t + tRFCpb); tRREFD between a REFpb and an ACT/REFpb of another bank'),
                policy_alternative=dict(kind='REFab staggered', command_time='n*tREFI + 32*phase(p)', pc_blocked_ps=T['tRFC_ab_ps'],
                    duty=round(T['tRFC_ab_ps'] / T['tREFI_ps'], 4),
                    in_core_cycles=dict(tREFI=round(T['tREFI_ps'] / CORE_PS, 3), tRFC=round(T['tRFC_ab_ps'] / CORE_PS, 3))),
                pseudo_channels=pcs,
                as_implemented=rtl_calendar(),
                owner_split='HBM controller (qkd_ctrl_pc) issues REFpb from this table (strap phase per PC); compiler (Q-VMWB kv_calendar.py) places KV reads around the windows')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    rec = calendar()
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ('policy_recommended',)})[:600])


if __name__ == '__main__':
    main()
