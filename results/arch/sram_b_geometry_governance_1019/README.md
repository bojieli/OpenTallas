# Governing B geometry distinction

This additive clarification governs dimensions used by the original bc773 B proposal. The original proposal and typed contract remain preserved. No coordinate, geometry, source, engine or qualification changes.

| Family | Actual master SIZE (µm) | Actual master area (µm²) | Proposed outer test-fixture envelope (µm) |
| --- | --- | ---: | --- |
| Qwen32×64 dual-clock | 52.440 × 21.192 | 1111.30848 | 138.840 × 107.592 |
| SC2512×128 single-clock | 216.840 × 43.800 | 9497.592 | 303.240 × 130.200 |

The fixture envelope adds43.2µm clearance on each side,86.4µm per dimension. It is not macro SIZE, macro area, legal parent fit or an installed view. Five SC2 masters cost47487.96µm² before other costs; five independent proposed fixture envelopes occupy197409.24µm² as a separate diagnostic reservation.

The original647-row typed contract had no explicit master-outline field. Its local pin rectangles and west/east corridor coordinates already used the actual master dimensions and origin(43.2,43.2)µm correctly. The annotated typed_terminal_contract.json adds explicit macro_outline_nm and fixture_envelope_nm to every row, preserving every original value and all endpoint NULL/REFUSE fields. geometry_distinction.json records all647 pin/corridor checks and source identity. verify.py independently checks the complete original-versus-annotated relationship.

The original B README called the outer test-fixture envelope “Outline”; that wording must not be used as a macro-area claim. The later real-parent modelb7c6c642a preserves its own earlier9763890 cost-error erratum and uses exact actual master dimensions. No old cost or fit is transferred.

No B/AP/PDN/import/route/LEF/Lib/source/default activation is granted. Actual outside native endpoint/master/site/clock/reset ownership remains unresolved; all existing OBS/core-fit/current/timing holds remain.
