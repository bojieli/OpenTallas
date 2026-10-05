"""Immutable identities and product bounds for the Qwen3-8B target."""

from __future__ import annotations

from pathlib import Path


MODEL_ID = "qwen3-8b"
MODEL_NAME = "Qwen3-8B"
REPOSITORY = "Qwen/Qwen3-8B"
REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
CONFIG_SHA256 = "f7c4eadfbbf522470667b797a3c89be2524832d2d599797248dc304fff447c30"
# The checked-in mirror differs from the upstream file only by the repository's
# required final newline. The official source contract still pins CONFIG_SHA256.
LOCAL_CONFIG_SHA256 = "deaa300e5384a480c2cafd0db33cba0da89db8eeeb8ddc2b584b89bd46d52ffb"
INDEX_SHA256 = "f9fdbcb91c23971c13ec5d5f2573d2349e8f61f2f049371ec699281748fdb1bc"
OFFICIAL_CHECKPOINT_LOCK_ID = (
    "fa32932d73c1f605a69db3a803f1f25ef5b022a98cc3c6b5fe42b7f7af024e2a"
)
OFFICIAL_TENSOR_CONTENT_SHA256 = (
    "41273c7db035ea2fed66b23ea7a294a05463f897f71f2cca11237118c9141402"
)
TOKENIZER_SHA256 = "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4"
TOKENIZER_CONFIG_SHA256 = (
    "d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101"
)
TRANSFORMERS_VERSION = "4.51.0"
TRANSFORMERS_MODEL_SOURCE_SHA256 = (
    "704c914530530a1acb0b443add1f520404e3ac2c28c0ab7e16f80f86cfe8ccb2"
)
TRANSFORMERS_MODULAR_SOURCE_SHA256 = (
    "959460177639c3743496bc015f5cfdfd9f722171688b541852f3630b469cec56"
)
TRANSFORMERS_CONFIG_SOURCE_SHA256 = (
    "87f0d17326c44f2dfe1bfc329faf9201ab4b19a89ad555da085b4cc81461b201"
)

TARGET_CONTEXT_TOKENS = 8_000
#: One source-current Qwen session must hold the mandatory 8,000-token prompt
#: and all 256 tokens in its frozen decode budget.  The older 8,192-position
#: physical campaign remains a separate retained boundary fixture.
SESSION_CONTEXT_CAPACITY = 8_256
#: Frozen token-row association for both Qwen ABI 3.0 storage targets.  Keeping
#: the ROM and HBM schedules on the same 512-row block makes their executed
#: numeric associations directly comparable under amendment A7.
TOKEN_BLOCK_ROWS = 512
TENSOR_COUNT = 399
PAYLOAD_BYTES = 16_381_470_720
PARAMETER_COUNT = 8_190_735_360
LAYER_COUNT = 36
TENSORS_PER_LAYER = 11

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "compiler" / "qwen3"
MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / MODEL_ID
DEFAULT_CONFIG = MODEL_DIR / "config.json"
DEFAULT_SOURCE = MODEL_DIR / "checkpoint_source.json"
DEFAULT_REFERENCE_SOURCES = MODEL_DIR / "reference_sources.json"
