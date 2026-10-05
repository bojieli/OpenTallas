1M field-spine sensitivity, conditional analytical output only

Executed source af7e729f6 on EPYC2 with existing dsrom_recovery_field.py sensitivity and read-only dsrom_1m_allmeasured.compose. Terminal exit 0. Added edge is 0.833333 ns in the 1.2 GHz streaming domain. Debit is phase_count * extra_cycles for each actual measured die, before the parallel die maximum. Wire is charged once per node. All added phase edges are exposed conservatively; no guessed overlap or .9 GHz SU charge. Existing AR and six-position MTP composition rules are retained.

Baseline replay: AR 1612.7 tok/s, MTP 4462.1 tok/s. Baseline and historical REJECT/PQ SS/FF failures remain unchanged. Points are not measurements of redesigned hardware and confer no adoption, timing, energy or full-token exactness credit.

| Added 1.2 GHz cycles per phase | AR tok/s | MTP tok/s | AR gain vs baseline | MTP gain vs baseline |
|---:|---:|---:|---:|---:|
| 0 | 1943.1 | 5211.0 | 20.49% | 16.78% |
| 2 | 1940.2 | 5204.5 | 20.31% | 16.64% |
| 4 | 1937.2 | 5197.9 | 20.12% | 16.49% |
| 6 | 1934.3 | 5191.4 | 19.94% | 16.34% |
| 8 | 1931.4 | 5184.9 | 19.76% | 16.20% |

Retained plan /srv/opentallas-scratch/codex/epicurus-field-phase-matched-20261005-r1/planv/plan.json SHA256 6b9ceaa0296e376bb9fdc28e2d7041435614afca415dc9674aaabcc16dbba5a4 matches field_pq.json. Historical measurement covers layers 0/1/2/3/20/21/24, 153 plan phases, S81 R93 BF520. Full40 graph uses the existing representative field_rep mapping; it is not full40 native measurement or canonical BF519 placement requalification. Original measurement source hashes are retained; new corrected-leaf gate PASS does not retroactively qualify historical field arithmetic. JSON carries baseline input/source hashes, mapped-node count, measured spine issue rule and every representative per-die phase debit.

Remote source snapshot /srv/opentallas/repos/noether-spine-sensitivity-af7e729f6 and output /srv/opentallas-scratch/codex/noether-field-spine-sensitivity-af7e729f6-r1 retained. Local result is deliberately outside levers/ so shared adopted-lever enumeration is unchanged. No spine/PQ/full-die route or native build was launched.
