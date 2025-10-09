from __future__ import annotations

import asyncio

from main import amain

if __name__ == "__main__":
    # Delegates to main's entrypoint; provide default DEMO prompt via input if not passed
    asyncio.run(amain())
