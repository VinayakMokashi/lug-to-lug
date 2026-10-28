"""Where the tools read and write outside the repository.

- The **private store** (`../private` by default) holds the photo originals, the
  sheets and the consent records. It is backed up and never committed.
- The **work folder** (`../work` by default) holds what the tools derive from the
  store, such as metadata-stripped copies of the photos. Everything in it can be
  rebuilt from the store, so it isn't backed up. It holds personal data all the same:
  a withdrawal deletes from it too.

Both default to folders next to the repository; LUGTOLUG_PRIVATE_DIR and
LUGTOLUG_WORK_DIR override them.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def private_dir() -> Path:
    return Path(os.environ.get("LUGTOLUG_PRIVATE_DIR") or REPO.parent / "private")


def work_dir() -> Path:
    return Path(os.environ.get("LUGTOLUG_WORK_DIR") or REPO.parent / "work")


def data_dir() -> Path:
    """The repository's data folder: numbers, schemas and manifests, never photos."""
    return REPO / "data"
