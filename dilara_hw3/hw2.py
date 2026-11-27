"""Import the untouched HW2 modules without modifying them."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HW2_DIR = Path(__file__).resolve().parents[1] / 'dilara_hw2'
if str(HW2_DIR) not in sys.path:
    sys.path.insert(0, str(HW2_DIR))

import data_adapter  # noqa: E402
import encoder  # noqa: E402
import runtime  # noqa: E402

_STARTER_PATH = HW2_DIR / 'far-trans' / 'starter.py'
_spec = importlib.util.spec_from_file_location('provided_far_trans_starter', _STARTER_PATH)
starter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(starter)

__all__ = ['HW2_DIR', 'data_adapter', 'encoder', 'runtime', 'starter']
