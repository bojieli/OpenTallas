"""S81-ROMCAP (10-20): ROM capacity of the p4l(-MU) release die vs the content a stage holds, per frame-field layout.
Arithmetic only (no RTL): frame census from the emitted frame RTL + the p4l plan; word sizes from the element
(ot_v41_rom_elem_w10: NB 2 macros of 8192 x 274 = 256 data bits/word; FP8 32 el/word, FP4 64 el/word); cfg7 bank
limit from xs_place.write_images (4 rows a phase, 4096 rows -> 1,024 phases a frame programme).
    python3 capacity.py <worktree> <out.json>"""
import json, math, re, subprocess, sys
from pathlib import Path
WT = Path(sys.argv[1])
plan = json.loads((WT / 'results/arch/s81_dv_1016/p4l/plan.json').read_text())
H9 = 2695.68
fr = [b for b in plan['blocks'] if b['kind'] == 'frame']
n9 = sum(1 for b in fr if abs(b['h'] - H9) < 1); n10 = len(fr) - n9
def census(master):
    t = subprocess.check_output(['git', '-C', str(WT), 'show', f'HEAD:rtl/dsrom_sys/s81_dv/frame/{master}.sv'], text=True)
    q = len(re.findall(r'^\s*ot_v41_rom_elem_q_qxpq_w10 #', t, re.M)); bf = len(re.findall(r'^\s*dsfd_bf_front_(?:static|roots) #', t, re.M))
    return q, bf
q9, bf9 = census('col_h9'); q10, bf10 = census('col_h10')
WPP = 2 * 8192                        # words a q pair (NB 2 macros x 8192 words, PP = 2 x 4096 banks a macro)
qpairs = n9 * q9 + n10 * q10
cap12 = qpairs * WPP; cap10 = len(fr) * 10 * WPP
wfp4 = lambda r, k: r * k / 64; wfp8 = lambda r, k: r * k / 32
EXP = wfp4(576, 5120) * 2 + wfp4(1280, 2304)                 # one routed expert, rank quarter (w1 + w3 + w2)
DENSE = {'L0': wfp8(448, 5120) + wfp8(8192, 1280) + wfp8(5120, 2048) + wfp8(1152, 5120) + wfp8(1280, 2304)}
DENSE['L2'] = DENSE['L0'] + wfp8(4096, 1280)                  # + indexer wq_b (compressor / weights_proj are BF / small)
DENSE['L14'] = DENSE['L2'] + wfp8(6400, 6144)                 # + Engram wkv
NEXP = 40 * 384                                               # routed experts a rank (40 MoE layers x 384)
PH = dict(current=dict(gu=4, down=3), gu_merge=dict(gu=3, down=3), k2=dict(gu=2, down=2), k3=dict(gu=1, down=1))
DENSE_PH = 60                                                 # a_proj 1 + wq_b 11 + wo_b 4 + shared 4+3 + wo_a 12 + router 5 + idx/cmp/eng ~20
out = dict(frames=len(fr), col_h9=n9, col_h10=n10, q_per_frame=[q9, q10], bf_per_frame=[bf9, bf10], q_pairs=qpairs,
           words_per_q_pair=WPP, q_words_12=cap12, q_words_10=cap10, frame_words_12=12 * WPP, frame_words_10=10 * WPP,
           expert_words=EXP, dense_words=DENSE, rank_experts=NEXP, cases={})
for stages in (110, 97):
    E = NEXP / stages
    case = dict(experts_per_die=round(E, 1))
    for kind, dw in (('attention_stage_L0', DENSE['L0']), ('attention_stage_L14', DENSE['L14']), ('expert_only', 0.0)):
        need = E * EXP + dw
        case[kind] = dict(need_words=round(need), fill_10=round(need / cap10, 3), fill_12=round(need / cap12, 3),
                          free_frames_10=round((cap10 - need) / (10 * WPP), 1), free_frames_12=round((cap12 - need) / (12 * WPP), 1),
                          emax_10=math.floor((cap10 - dw) / EXP), emax_12=math.floor((cap12 - dw) / EXP))
    case['cfg7_phases'] = {k: dict(phases=round(E * (v['gu'] + v['down']) + DENSE_PH), fits_1024=E * (v['gu'] + v['down']) + DENSE_PH <= 1024,
                                   emax=math.floor((1024 - DENSE_PH) / (v['gu'] + v['down']))) for k, v in PH.items()}
    out['cases'][f'{stages}_stages'] = case
Path(sys.argv[2]).write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps(out, indent=1))
