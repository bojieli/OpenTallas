import json, unittest
import kit_wave as K


class BlockIgnore(unittest.TestCase):
    def test_option_reaches_probe_and_strips_only_named_keys(self):
        self.assertIn('a.get("block_ignore")', K.PROBE_PLAN)
        src = K.PROBE_PLAN
        i = src.index('for dotted in a.get("block_ignore")'); j = src.index('ids = identities(p, a["plan"], mode)')
        body = "\n".join(line[4:] for line in src[i - 4:j].splitlines())
        pt = {"x": {"clock": {"tap_model": "f", "taps": [1]}, "reset": {"obstacle_model": "l"}}}
        exec(body, {"a": {"block_ignore": ["clock.tap_model", "reset.obstacle_model"]}, "pt": pt})
        self.assertEqual(pt, {"x": {"clock": {"taps": [1]}}})


if __name__ == "__main__":
    unittest.main()
