from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from seoultech_lms.auth import auth_state_path
from seoultech_lms.browser import interactive_login

asyncio.run(interactive_login(auth_state_path()))
