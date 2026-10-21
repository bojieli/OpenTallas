#!/usr/bin/env bash
# TOK-FUNC-HBM (10-21): ONE command for the HBM d4g release die functional token pass (HBM-DeepSeek TOK.HDS + HBM-Qwen
# TOK.HQ, single user): assemble the die RTL -> SW quadrant slice -> per-layer + chained replays -> build -> run -> report.
#
#   MODE=source (default, grade "RTL-functional (source assembly)"):
#     CONTRACT = the release die's source contract (pre-relay: relays are physical) at SRC_REV; the l12 bank-latency
#     layer (tools/hbm_die_v16/d4g_layers/l12_banklat.py of SRC_REV) is applied so every fixed-latency VM client gets
#     its compiler budget (pads fill the short lanes: the static schedule is the one the post-relay die runs), then
#     contract_die_v.py emits die.v.  OVERLAY="path[@rev] ..." replaces bundle files by another revision's (pending RTL
#     the release source needs; default: main's per-bank RD_LAT x-load ctlx, which l12 requires).
#   MODE=netlist (rerun at die closure, grade "die-netlist"): DIE_V=<GEN die.v of record> CONTRACT=<its contract>
#     SRC_REV=<its source rev>; no l12 (already in the GEN contract), no overlay unless given.
#
#   env: OUT (local work dir) SRC_REV CONTRACT [DIE_V] [L12_OVERLAY] [OVERLAY] [REPLAYS] [MEM=256] [JOBS=48]
#        [STAGE_HOSTS="ot-gold1 ot-gold2"] (data staged there; ot-run unpinned picks among hosts that have it)
#        [RUN=1] (0 = assemble + emit only)
#   Emission: DS L0/L2/L14 (layer_images, fixtures FIX_DS=<dir with L00 L02 L14>) and Qwen L0 + L0->L1 chain ranks 0/5
#   (qwen_layer_images emit, operands QOP=<dir with operands_{L0,chain}.npz>), SU native READ/WRITE_RETURN read from
#   the contract's su_SW0 (the die's own parameters).  Writes OUT/report.json (+ OUT/log/*).
set -u -o pipefail
T=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$T/../.." && pwd)
REPO=${REPO:-/home/ubuntu/OpenTallas}
MODE=${MODE:-source}
OUT=${OUT:?OUT}; SRC_REV=${SRC_REV:?SRC_REV}; CONTRACT=${CONTRACT:?CONTRACT}
FIX_DS=${FIX_DS:?FIX_DS (dir with L00 L02 L14 fixtures: records.json operands.npz images/)}
QOP=${QOP:?QOP (dir with operands_L0.npz operands_chain.npz from qwen_layer_images snap)}
MEM=${MEM:-256}; JOBS=${JOBS:-48}; RUN=${RUN:-1}
STAGE_HOSTS=${STAGE_HOSTS:-"ot-gold1 ot-gold2"}
OVERLAY=${OVERLAY-"rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2.sv@origin/main"}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
TAG=${TAG:-$(basename "$OUT")}
REMOTE=${REMOTE:-/srv/opentallas-scratch/claude/tok-func-hbm/$TAG}
mkdir -p "$OUT/log"; L=$OUT/log
say() { echo "$(date -Is) $*" | tee -a "$L/summary.log"; }
SRCWT=$OUT/srcwt                       # read-only export of SRC_REV tools (l12 / contract_die_v / functional bind)
if [ ! -d "$SRCWT/tools/hbm_die_v16" ]; then
  mkdir -p "$SRCWT"; git -C "$REPO" archive "$SRC_REV" tools/hbm_die_v16 tools/die_port_bind.py results/arch/hbm_die_d4g/gen0/die.v.pads.json | tar -x -C "$SRCWT" || exit 2
fi
say "TOK_FUNC_HBM mode=$MODE src=$SRC_REV contract=$CONTRACT ($(sha256sum "$CONTRACT" | cut -c1-16)) tools=$(git -C "$ROOT" rev-parse --short=9 HEAD)"

# 1. die RTL assembly ------------------------------------------------------------------------------------------------
if [ "$MODE" = source ]; then
  L12O=${L12_OVERLAY:-results/arch/hbm_die_d4g/gen2e4r11_1020/l12_budget_r11.json}
  OVA=(); if [ -n "$L12O" ]; then git -C "$REPO" show "$SRC_REV:$L12O" > "$OUT/l12_overlay.json" 2>/dev/null || cp "$L12O" "$OUT/l12_overlay.json"; OVA=(--budget-overlay "$OUT/l12_overlay.json"); fi
  (cd "$SRCWT" && python3 tools/hbm_die_v16/d4g_layers/l12_banklat.py "$CONTRACT" "$OUT/contract_func.json" --report "$OUT/l12.json" "${OVA[@]}") > "$L/l12.log" 2>&1 \
    || { say "L12_FAIL"; tail -5 "$L/l12.log"; exit 3; }
  say "$(tail -1 "$L/l12.log")"
  FC=$OUT/contract_func.json
  (cd "$SRCWT" && python3 tools/hbm_die_v16/contract_die_v.py emit "$FC" "$OUT/die.v") > "$L/die_v.log" 2>&1 || { say DIE_V_FAIL; exit 3; }
  (cd "$SRCWT" && python3 tools/hbm_die_v16/d4g_functional_bind.py "$FC" --report "$OUT/functional_bind.json") > "$L/functional_bind.log" 2>&1
  say "$(tail -1 "$L/functional_bind.log")"
  grep -q "^FUNCTIONAL_BIND PASS" "$L/functional_bind.log" || exit 3
  DIEV=$OUT/die.v
else
  FC=$CONTRACT; DIEV=${DIE_V:?DIE_V (GEN die.v) for MODE=netlist}
fi
python3 "$T/die_filelist.py" --contract "$FC" --repo "$REPO" --rev "$SRC_REV" --out "$OUT/fl" > "$L/filelist.log" 2>&1; say "$(tail -1 "$L/filelist.log")"
VIEWS=${VIEWS:-}; VA=(); [ -n "$VIEWS" ] && VA=(--views "$VIEWS")
python3 "$T/make_bundle.py" --fl "$OUT/fl" --repo "$REPO" --rev "$SRC_REV" --die "$DIEV" --wt "$ROOT" --out "$OUT/bundle" "${VA[@]}" > "$L/bundle.log" 2>&1 || { say BUNDLE_FAIL; exit 3; }
for o in $OVERLAY; do f=${o%@*}; r=${o#*@}; [ "$r" = "$o" ] && r=origin/main
  git -C "$REPO" show "$r:$f" > "$OUT/bundle/$f" || { say "OVERLAY_FAIL $o"; exit 3; }
  say "OVERLAY $f <- $r $(git -C "$REPO" rev-parse --short=9 "$r")"; done
cp "$T/check_slice_run.py" "$OUT/bundle/"

# 2. SW quadrant slice (input pads/relays pulled in: the die's own lane latency in front of the slice) --------------
RLX=${RELAY_RE:-'^(l12p_|rf\d+_)'}
python3 "$T/cut_slice.py" --die "$DIEV" --contract "$FC" --set sw --with-relays "$RLX" --out "$OUT/bundle/slice" > "$L/cut.log" 2>&1 || { say CUT_FAIL; exit 3; }
say "$(grep -m1 '^SLICE' "$L/cut.log")"

# 3. replays (compiler of record on the die's own SU timing) ----------------------------------------------------------
read RR WR < <(python3 -c "import json,sys; p=json.load(open(sys.argv[1]))['instances']['su_SW0']['params']; print(p['READ_RETURN'], p['WRITE_RETURN'])" "$FC")
say "SU native timing READ_RETURN=$RR WRITE_RETURN=$WR (contract su_SW0)"
B=$OUT/bundle/slice/boundary.json; RJ=$OUT/rj; mkdir -p "$RJ"
for LL in 00 02 14; do l=$((10#$LL))
  (cd "$ROOT" && python3 tools/hbm_layer_vehicle/layer_images.py --design ds --layer $l --programme "$FIX_DS/L$LL/images/ds_v41_1M_L${LL}_per_die.json" \
     --fixtures "$FIX_DS/L$LL" --boundary "$B" --native-read-return $RR --native-write-return $WR --out "$OUT/emit/ds_l$l") > "$L/emit_ds_l$l.log" 2>&1 \
    && cp "$OUT/emit/ds_l$l/replay.json" "$RJ/ds_l$l.json"; say "EMIT ds_l$l $(tail -c 260 "$L/emit_ds_l$l.log" | tr -d '\n')"
done
for st in L0 chain; do
  (cd "$ROOT" && python3 tools/hbm_layer_vehicle/qwen_layer_images.py emit --stage $st --ranks 0,5 --boundary "$B" --operands "$QOP/operands_$st.npz" \
     --native-read-return $RR --native-write-return $WR --out "$OUT/qemit") > "$L/emit_qw_$st.log" 2>&1
  for r in 0 5; do [ -f "$OUT/qemit/$st/r$r/replay.json" ] && cp "$OUT/qemit/$st/r$r/replay.json" "$RJ/qw_${st,,}_r$r.json"; done
  say "EMIT qw_$st $(grep -o '"counts": {[^}]*}' "$L/emit_qw_$st.log" | head -1)"
done
REPLAYS=${REPLAYS:-$(cd "$RJ" && ls *.json | sed 's/\.json$//' | tr '\n' ' ')}
NEV=$(python3 -c "import json,sys; print(max(16, 1 + max(sum(e['k']!='M' for e in json.load(open(f))['events']) for f in sys.argv[1:])))" $(for n in $REPLAYS; do echo "$RJ/$n.json"; done))
python3 "$T/gen_slice_tb.py" --boundary "$B" --out "$OUT/bundle/slice" --nev "$NEV" $(for n in $REPLAYS; do echo --replay "$RJ/$n.json"; done) > "$L/tb.log" 2>&1 || { say TB_FAIL; cat "$L/tb.log"; exit 3; }
say "$(tail -1 "$L/tb.log")"
[ "$RUN" = 1 ] || { say "ASSEMBLED (RUN=0)"; exit 0; }

# 4. stage + build + run (fleet, unpinned) ---------------------------------------------------------------------------
for h in $STAGE_HOSTS; do timeout 600 ssh "$h" "mkdir -p $REMOTE" && timeout 1800 rsync -a --delete "$OUT/bundle/" "$h:$REMOTE/" && say "STAGED $h:$REMOTE"; done
/home/ubuntu/bin/ot-run --mem "$MEM" --threads "$JOBS" --disk 200 --dir "$REMOTE" -- env SRC="$REMOTE" OUT="$REMOTE/out" JOBS="$JOBS" BUILD_ONLY=1 bash run_slice_vehicle.sh > "$L/build.log" 2>&1
BRC=$?; H=$(grep -o 'RAN on [a-z0-9-]*' "$L/build.log" | tail -1 | awk '{print $3}'); say "BUILD rc=$BRC host=$H"
[ -n "$H" ] && timeout 120 ssh "$H" "test -x $REMOTE/out/obj/Vtb_hbm_slice" || { say NO_BINARY; exit 4; }
for n in $REPLAYS; do
  # --dir = the build's obj dir: it exists only on the build host, so the unpinned run lands where the binary is
  ( /home/ubuntu/bin/ot-run --mem "${RUN_MEM:-64}" --threads 1 --dir "$REMOTE/out/obj" -- bash -c "cd $REMOTE && mkdir -p out_$n && /usr/bin/time -v -o out_$n/run.time out/obj/Vtb_hbm_slice +verilator+rand+reset+0 +REPLAY=slice/replay/$n > out_$n/run.log 2>&1; echo RUN_RC=\$?; python3 check_slice_run.py --replay slice/replay/$n --run-log out_$n/run.log --out out_$n/acceptance.json >/dev/null 2>&1; grep -E '^SLICE_(SUMMARY|PASS|FAIL)' out_$n/run.log | tail -2" > "$L/rpl_$n.log" 2>&1 || true
    say "RUN $n $(tr '\n' ' ' < "$L/rpl_$n.log")" ) &
  sleep 2
done
wait
for n in $REPLAYS; do timeout 300 rsync -a "$H:$REMOTE/out_$n/" "$OUT/runs/$n/" 2>/dev/null; done
python3 - "$OUT" "$MODE" "$SRC_REV" "$CONTRACT" $REPLAYS <<'PY'
import json, re, sys, hashlib
from pathlib import Path
out, mode, rev, contract, names = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:]
rows = {}
for n in names:
    rj = json.loads((out / "rj" / f"{n}.json").read_text())
    log = out / "runs" / n / "run.log"; t = log.read_text(errors="replace") if log.exists() else ""
    m = re.search(r"SLICE_SUMMARY drives=(\d+) checks=(\d+) fails=(\d+) rec_commit_ok=(\d+) rec_fail=(\d+) stream_edges=(\d+) serial_edges=(\d+)", t)
    v = "PASS" if re.search(r"^SLICE_PASS", t, re.M) else ("FAIL" if t else "NO_RUN")
    rows[n] = dict(verdict=v, scope=rj.get("scope", "component_probe"), priced_layer_cycles=rj.get("priced_layer_cycles"),
                   t0_serial=rj.get("t0_serial"), events=len(rj["events"]),
                   **({k: int(x) for k, x in zip(["drives", "checks", "fails", "rec_commit_ok", "rec_fail", "stream_edges", "serial_edges"], m.groups())} if m else {}))
grade = "RTL-functional (source assembly)" if mode == "source" else "die-netlist"
rep = dict(schema="opentallas.tok_func_hbm.v1", grade=grade, src_rev=rev, contract=contract,
           contract_sha256=hashlib.sha256(Path(contract).read_bytes()).hexdigest(), replays=rows,
           note="SW quadrant slice replays: SU-programme records emitted by the compiler of record; other units are "
                "format_open in layer_images v1 (see emit/*/manifest.json counts) -> component probes, not full-layer tokens")
(out / "report.json").write_text(json.dumps(rep, indent=1))
print("REPORT", json.dumps({k: (r["verdict"], r.get("serial_edges")) for k, r in rows.items()}))
PY
say "DONE $(tail -1 "$L/summary.log" >/dev/null; echo report=$OUT/report.json)"
