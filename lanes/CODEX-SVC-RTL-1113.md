# CODEX SVC RTL takeover 2026-11-08 11:13 PST

Own source: epyc4:/srv/opentallas-scratch3/claude/codex-svc-rtl-1113/repo, branch codex/svc-rtl-1113@65818227fe, origin intel2:/home/ubuntu/OpenTallas. Based on current SVC5 lockstep source af5b7076d8. No POR, merges, tags, deletions or physical runs.

Collected: E5 s81-svc-4/eqatt closing rc=0, 20.6GB peak; default/obs healthy equiv_simple, no rc yet. H16 slice lockstep both seeds clean. H8 both seeds FAIL with bit20 P FIFO underflow on all16 slices, missing second-pass P root beats, zero PV heads8..15. Actual image checker ls/ls_base_h8.json records4096 data differences; schedule windows PASS, score outputs correct. Preserve failed records.

Fix65818227fe: P valid is now emitted on every dimension tile at the static P cycle, inactive SM heads contribute zero. Active-only pbuf readiness fault. Original hsel-gated valid dropped root P in pass1. PIN CYCLES0, no change to per-port rate/payload or compiled calendar; adds inactive-data gating. H16 hsel is constant1 so behavior is unchanged.

Minimal mechanism proof running E4 passes/ unit oth-ubuntu-2530078-1794165639, via canonical Intel2 client2049855; launcher intel2:/srv/opentallas-scratch2/claude/codex-svc-rtl-1113-passes.launch.log. Exact unchanged protected SX master reused after source cmp; new top sends64 sparse P beats over both global-head halves, golden balanced16dim tree; +pdrop=1 recreates old valid gating. No whole-slice qualification from this bench. Initial E4-localhost selector failed hostkey before launch; canonical Intel2→E4 admitted.

SIGNED RT2 source/flags: actual E2 s81ck5/kits/ot_s81c_attn_hcore_rt22m_hx2 config uses CTLA + RST_TIMED, same as current. hcore source sha256ddfa9aa1655c8c794bd618e28e61009663ee3ad958e675c24506318177787d75 exact; tile and tile_lat byte-equal. Whole tile_s diff is only new H8 opt-in wrapper15lines; common head datapath exact. Existing SIGNED view unchanged; new serializer/parent clock/provider-cycle obligation remains.

Next: collect minimal P proof and control, fix if needed; join corrected producer to slice minimum and calibrate actual PIO/PO/PVO/SO edges. Do not qualify H8_CALIBRATED or release physical rows before actual proof/calendar/geometry. RT2 generic Q/replay overlap remains explicitly faulted; SVCv1 pass programme has no overlapping jobs. Earliest QK schedule corner still open. Parent owns compiler/PVSO; sibling SM/H4 work continues independently.

## 11:44 PST progress
ATT identity gate all3 TERMINAL PASS: epyc5 s81-svc-4/eqatt att_default/obs/closing.rc all rc=0. Parent notified, no merges by watcher.

READY canonical codex/svc-rtl-1113@b1275c27ba. Exact production H8 P source factored as combinational helper, existing parent registers/counter retained; H16 original path retained. Actual-source GO/hb/control proof PASS1024 cases (including active missing-row sentinel and inactive empty buffer), oldvalid gating control760 errors. Real SX sparseP numerical PASS64root/1024taps/fault0; oldvalid control32root/512taps/fault0x1000000000. Receipt results/rtl/s81_r5_h8_1108/p_source_1113.json. PIN CYCLES0.

Current nextjoin: epyc2:/srv/opentallas-scratch2/claude/codex-svc-rtl-1113/{repo,join}, one Intel2 launcher2842958,24GB4threads, log intel2:/srv/opentallas-scratch2/claude/codex-svc-rtl-1113-join-e2.launch.log. Exact dated E rows from failed native slice feed actual rs_c P source/SX/Pfold/return/dn topology; ATT and SMS explicit calendar/FIFO/trace doubles, SMT0, no live arithmetic claim. E4 original waiter2705091 canceled while unadmitted (no buildlog/payload) before successor; minimal source staging fewMB, no fullclone. E2 queue now19GB admission vs24 request. No duplicate healthy jobs.

Source GO consumer anchor1448/2489 derives from image1426/2467 plus6+5*depth+gd, Wentry depth0/gd16. Entry qp+jobgate/r1/cs+decode gives hdr1430, counter16 reachesgo_o1447, parentconsumes1448; per-node offsets equal sx_role_off. Also agrees observed firstP-root1798 and secondPOunderflow2897. Anchor is source-derived/inferred, not a new live-GO measurement. Replay will report actual arrival/consumption edges and late-provider120cycle control; whole-slice calendar remains open.

## Replay isolation (11:5x)
E2 first join launch terminal CLI error `-j4` (before RTL), fixed to `-j 4`; second E2 launch NOT RUN root96% guard, no override. Minimal fewMB source moved to supported E5S3. E5 unit2487562-1794167283 ran terminal FAIL: no Pheaders reach attention double, all32 consumption steps underflow. Preserve join/run_late0.log.
Top-only reuse of both compiled masters, unit2639983-1794167580: exact dated provider W seen, actual corrected P source + SX emits64roots, first1798, matching anchor. Real fold/return gives66words at Eentry11 RI, first1802. DNout remains0. Missing stage is entry return injection/broadcast, still being diagnosed, not arithmetic/SX failure. Real minimal source/SX receipts remain PASS.
Current debug job: E5S3 samebase join/pld1, one ENTRY1master with diagnostic `$display` under PJOIN_DEBUG, original ENTRY0 reused. Script join_entrydebug.sh, Intel2 launcher log codex-svc-rtl-1113-entrydebug-e5.launch.log,8GB1thread. Only test diagnostic added in private staged E5 rs.sv, no production behavioral change, no canonical/POR change. Parent notified. Native RT2 earliest QK phase8 corner prepared as runtime +qk_first in own E4 testbench but not launched while Pjoin unresolved.
Canonical branch now7839989633 (adds reusable replay generator/scripts to b1275c27ba); sourcefix remains b127.
