#!/usr/bin/env python3
"""Exact gate of the main-hidden row path to the DSpark primary die (mtp-dsbind 2026-10-10):
3 x ot_dsrom_mtp_hrow_tx -> stations -> dsfd_mtp_hrow (row store) <- dsfd_mtp_seed_launch (seed client).

    python3 tools/mtp_hrow_gate.py --out <dir> [--record <json>] [--only pos|mut]

Bench rtl/dsrom_sys/mtp/tb_mtp_hrow.sv (iverilog, real SRAM macro models).  Cases:
  pos_steady  two users; prefill, rejection (epoch +1: squashed rows re-land under the new epoch), all-accepted steps:
              every x beat equals the issued row version's beat
  pos_late    the descriptor arrives BEFORE the re-verified rows (the store holds the squashed old-epoch rows): the
              read must wait for the new version
  neg_drop    one part of a committed row lost: the row is never served (seed waits), the ring wrap is flagged
              (store fault[0]) -- PASS when rejected exactly so
Mutants (must FAIL): OT_HROW_MUT_NOEPOCH on pos_late (serves the stale squashed row), OT_HROW_MUT_NOPART on neg_drop
(serves a row with a missing part).
"""
import argparse, json, re, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = ['rtl/dsrom_sys/mtp/ot_dsrom_mtp_hrow.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_mtp_hrow_bank.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_mtp_seed_launch.sv',
       'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv',
       'rtl/dsrom_sys/mtp/rtt/ot_dsrom_mtp_rstsync.sv',
       'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v',
       'rtl/dsrom_sys/mtp/tb_mtp_hrow.sv']
POS = ['pos_steady', 'pos_late', 'neg_drop']
MUT = [('OT_HROW_MUT_NOEPOCH', 'pos_late'), ('OT_HROW_MUT_NOPART', 'neg_drop')]


TILES = False   # --tiles: the bench runs on the two-level tile composition dsfd_mtp_hrow_tc
HARD_RELAYS = False
UT_STAGES = 1
DISTRIBUTED_RESET = False
UTURN = False   # --uturn (with --tiles): the die composition dsfd_mtp_hrow_td (tc + one die relay on the U-turn hop)
HALF_BANKS = False   # --half-banks (with --uturn): every bank = two dsfd_mtp_hrow_cbh half tiles (dsfd_mtp_hrow_cbp)
TILE_SRC = 'rtl/dsrom_sys/mtp/ot_dsrom_mtp_hrow_tiles.sv'   # --tile-src: another tiles file (e.g. a mixed-commit pair)


def build(out, d=None):
    exe = out / ('sim' + ('_' + d if d else '') + ('_tiles' if TILES else '') + ('_uturn' if UTURN else '') + ('_half' if HALF_BANKS else ''))
    src = SRC + (['rtl/dsrom_sys/s81_ph/relays/dsfd_die_relays.sv'] if HARD_RELAYS else []) + ([TILE_SRC] if TILES else []) + (['rtl/dsrom_sys/mtp/ot_dsrom_mtp_hrow_die.sv'] if UTURN else []) + (['rtl/dsrom_sys/mtp/ot_dsrom_mtp_hrow_cbh.sv'] if HALF_BANKS else [])
    subprocess.run(['iverilog', '-g2012', '-o', str(exe), '-s', 'tb_mtp_hrow'] + (['-D' + d] if d else [])
                   + (['-DOT_HROW_HARD_RELAYS'] if HARD_RELAYS else []) + (['-DOT_HROW_UT=' + str(UT_STAGES)] if UTURN else []) + (['-DOT_HROW_DISTRIBUTED_RST'] if DISTRIBUTED_RESET else []) + (['-DOT_HROW_TILES'] if TILES else []) + (['-DOT_HROW_DIE'] if UTURN else []) + (['-DOT_HROW_HALF_BANKS'] if HALF_BANKS else [])
                   + [str(s) if Path(s).is_absolute() else str(ROOT / s) for s in src], check=True)
    return exe


def run(exe, case):
    r = subprocess.run(['vvp', '-n', str(exe), f'+CASE={case}'], capture_output=True, text=True, timeout=7200)
    m = re.search(r'HROW_RESULT (.*)', r.stdout)
    rec = dict(case=case, rc=r.returncode, line=m.group(1) if m else None,
               errors=[l for l in r.stdout.splitlines() if l.startswith('HROW_ERR')][:10])
    if m:
        rec.update(dict(re.findall(r'(\w+)=(\S+)', m.group(1))))
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--only', choices=['pos', 'mut'])
    ap.add_argument('--record', type=Path)
    ap.add_argument('--tiles', action='store_true', help='run on the two-level tile composition (dsfd_mtp_hrow_tc)')
    ap.add_argument('--uturn', action='store_true', help='with --tiles: the die composition dsfd_mtp_hrow_td (U-turn relay)')
    ap.add_argument('--hard-relays', action='store_true', help='with --uturn: exact fixed relay hard masters')
    ap.add_argument('--ut-stages', type=int, default=1, help='die U-turn relay stages; production default remains one')
    ap.add_argument('--distributed-reset', action='store_true', help='local reset synchronizers for each hard relay')
    ap.add_argument('--half-banks', action='store_true', help='with --uturn: banks as two dsfd_mtp_hrow_cbh half tiles')
    ap.add_argument('--tile-src', help='tiles source file instead of ot_dsrom_mtp_hrow_tiles.sv (a mixed-commit pair)')
    a = ap.parse_args()
    global TILES, UTURN, TILE_SRC, HARD_RELAYS, UT_STAGES, DISTRIBUTED_RESET, HALF_BANKS
    HALF_BANKS = a.half_banks
    if HALF_BANKS and not a.uturn: ap.error('--half-banks requires --uturn')
    TILES = a.tiles or a.uturn
    UTURN = a.uturn
    HARD_RELAYS = a.hard_relays
    UT_STAGES = a.ut_stages
    DISTRIBUTED_RESET = a.distributed_reset
    if UT_STAGES < 1: ap.error("--ut-stages must be positive")
    if DISTRIBUTED_RESET and not HARD_RELAYS: ap.error("--distributed-reset requires --hard-relays")
    if HARD_RELAYS and not UTURN: ap.error("--hard-relays requires --uturn")
    if a.tile_src:
        TILE_SRC = a.tile_src
    a.out.mkdir(parents=True, exist_ok=True)
    rec = dict(schema='opentallas.mtp-hrow-gate.v1', sources=SRC, tiles=TILES, uturn=UTURN, tile_src=TILE_SRC if TILES else None, hard_relays=HARD_RELAYS, half_banks=HALF_BANKS, ut_stages=UT_STAGES, distributed_reset=DISTRIBUTED_RESET,
               cases=[], mutants=[])
    ok = mut_ok = True
    if a.only != 'mut':
        exe = build(a.out)
        for c in POS:
            r = run(exe, c); rec['cases'].append(r); ok &= r.get('result') == 'PASS'
            print(c, r.get('result'), r.get('cyc'), r.get('store_fault'), flush=True)
    if a.only != 'pos':
        for d, c in MUT:
            r = run(build(a.out, d), c); r['define'] = d; rec['mutants'].append(r); mut_ok &= r.get('result') == 'FAIL'
            print(d, c, r.get('result'), flush=True)
    rec['verdict'] = dict(positives_and_rejections=ok if a.only != 'mut' else None,
                          mutants_fail=mut_ok if a.only != 'pos' else None)
    if a.record:
        a.record.parent.mkdir(parents=True, exist_ok=True)
        a.record.write_text(json.dumps(rec, indent=1) + '\n')
    if a.only == 'mut':
        print('HROW_MUTANTS ' + ('FAIL_AS_REQUIRED' if mut_ok else 'NOT_DISCRIMINATING'))
        return 1 if mut_ok else 0
    print(f'HROW_GATE {"PASS" if ok and mut_ok else "FAIL"} positives={sum(1 for x in rec["cases"] if x.get("result") == "PASS")}')
    return 0 if ok and mut_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
