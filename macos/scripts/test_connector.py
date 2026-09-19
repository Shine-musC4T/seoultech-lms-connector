from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from seoultech_lms.client import SeoultechLMSClient


async def main() -> None:
    async with SeoultechLMSClient(ROOT) as client:
        for name, operation in (("courses", client.get_courses), ("notices", client.get_notices), ("assignments", client.get_assignments)):
            try:
                result = await operation()
                print(f"{name}: OK ({len(result)} items)")
            except Exception as exc:
                print(f"{name}: {type(exc).__name__}: {exc}")


asyncio.run(main())
