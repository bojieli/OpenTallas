# Actual six-ingress BK fragment candidate (not adopted)

The selected PORTFIX178 BK contains `dsdv_idx_vmux6`, not the generic four-input mux. Its old bit0 mask drops q/BF16 continuation fragments whose literal payload bit0 is zero. A two-bit countdown per ingress preserves the four-fragment occupancy independently from payload. Collision detection now counts occupancy as well. All literal bits, public pins, clocks, resets and cycle counts remain unchanged.

7.11 impact approved by root COORD for candidate preparation: +12 reset FFs / clock sinks and two reset loads on each existing ingress reset region; no added pipeline stage, interface, clock/reset domain, outline or cycle. The selected BK source is `physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_l20s.sv`. Re-sign the affected BK physical view and its containing views before adoption; no canonical source/plan or physical claim follows from this component qualification.

Actual six-input focused gate on epyc2, unit oth-ubuntu-2163187-1793564766: 3389 checks, 768 literal fragments across all six ingress legs. Original source loses192 fragments. All-zero continuation collision sets the candidate fault and escapes the original; wrong-payload control is caught. Existing two-edge mux latency is preserved.

Full selected BK overlay on intel1, unit oth-ubuntu-1138304-1793565159, `/srv/opentallas-scratch2/claude/codex-ds-norm-1101/bk_transit_fragment6_v2`: north128/128 at6edges and south128/128 at3edges, errors0 at833ps; phase mutation fails. Only the actual vmux6 body was replaced in the baseline selected source. This qualifies literal transit, not global token completion or physical timing.

Earlier four-input patch was not selected by this BK. Its successful focused test, its ineffective full-BK failure (96/128 north), and original failure are preserved as history; the generic four-input RTL is restored. Initial impact.md describes that superseded8FF attempt. This README records the final12FF candidate scope. No failed run was overwritten.
