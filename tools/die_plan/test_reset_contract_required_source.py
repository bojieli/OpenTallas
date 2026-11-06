"""Exercise the actual factory reset branch without building a physical kit."""
import ast
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

import kit_reset_contract as K


def actual_factory_branch():
    path = Path(__file__).resolve().parents[2] / "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py"
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "component_cycles"):
            return compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                           str(path), "exec")
    raise AssertionError("factory reset branch not found")


def execute_branch(root, cycles, release_eligible=False):
    env = dict(component_cycles=cycles, source_profile=dict(release_eligible=release_eligible),
               kd=root, design="ot_svgr_own", json=json,
               kit_reset_contract=SimpleNamespace(stage=K.stage, DIE_CONTRACT={"hbm": root/"missing.json"}))
    exec(actual_factory_branch(), env)
    return env


class RequiredResetSourceTest(unittest.TestCase):
    def test_missing_ordinary_source_refuses_optional_behavior_preserved(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNone(K.stage(root, "listed_core", root/"missing.json"))
            with self.assertRaisesRegex(SystemExit, "required canonical die reset contract is missing"):
                execute_branch(root, None)
            self.assertEqual(list(root.iterdir()), [])

    def test_present_unlisted_module_gains_no_reset_contract(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/"contract.json"
            source.write_text(json.dumps(dict(modules=["other"])))
            self.assertIsNone(K.stage(root, "new_helper", source, required_source=True))
            self.assertFalse((root/"reset_contract.json").exists())

    def test_present_listed_source_stages_same_proven_window(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source, kit = root/"source", root/"kit"
            (source/"reset_contract").mkdir(parents=True)
            kit.mkdir()
            receipt = b"HOLD64 PASS assert 66; HOLD8 mutant CAUGHT\n"
            (source/"reset_contract/receipt.txt").write_bytes(receipt)
            contract = dict(schema="opentallas.reset_contract.v1", die="hbm", edges=64,
                            modules=["listed_core"], proof=dict(verdict="PASS", assert_edges=66,
                            mutant="CAUGHT", receipt="reset_contract/receipt.txt",
                            receipt_sha256=hashlib.sha256(receipt).hexdigest()))
            path = source/"reset_contract.json"
            path.write_text(json.dumps(contract))
            result = K.stage(kit, "listed_core", path, required_source=True)
            self.assertEqual(result["edges"], 64)
            import lec
            self.assertEqual(lec.reset_contract_gate(kit, "listed_core", environ={})["used"], 64)

    def test_explicit_component_proof_remains_nonrelease_native4(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            env = execute_branch(root, 4)
            self.assertIsNone(env["reset_contract"])
            result = json.loads((root/"component_proof_reset.json").read_text())
            self.assertEqual(result["cycles"], 4)
            self.assertIs(result["release_eligible"], False)
            self.assertIs(result["die_contract_staged"], False)
            self.assertFalse((root/"reset_contract.json").exists())

    def test_invalid_component_exception_refuses(self):
        for cycles, eligible in [(4, True), (True, False), (8, False)]:
            with self.subTest(cycles=cycles, eligible=eligible), TemporaryDirectory() as directory:
                root = Path(directory)
                with self.assertRaisesRegex(ValueError, "explicitly nonrelease"):
                    execute_branch(root, cycles, eligible)
                self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
