from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path

from package_release import EXECUTABLE_NAMES, _is_excluded


def verify_release(source_directory: Path, archive_path: Path) -> dict[str, object]:
    source_directory = source_directory.resolve()
    archive_path = archive_path.resolve()
    root_name = f"{source_directory.name}/"
    expected = {
        f"{root_name}{path.relative_to(source_directory).as_posix()}": path.read_bytes()
        for path in source_directory.rglob("*")
        if path.is_file() and not _is_excluded(path.relative_to(source_directory))
    }

    with zipfile.ZipFile(archive_path) as archive:
        archived = {
            name: archive.read(name)
            for name in archive.namelist()
            if not name.endswith("/")
        }
        executable_modes = {
            name: (archive.getinfo(f"{root_name}{name}").external_attr >> 16) & 0o777
            for name in EXECUTABLE_NAMES
        }
        crc_error = archive.testzip()
        root_ok = all(name.startswith(root_name) for name in archive.namelist())

    source_parity = expected == archived
    permissions_ok = all(mode == 0o755 for mode in executable_modes.values())
    if crc_error or not root_ok or not source_parity or not permissions_ok:
        raise RuntimeError(
            "Release verification failed: "
            f"crc_error={crc_error!r}, root_ok={root_ok}, "
            f"source_parity={source_parity}, executable_modes={executable_modes!r}"
        )
    return {
        "archive": str(archive_path),
        "size": archive_path.stat().st_size,
        "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "file_count": len(archived),
        "executable_modes": {name: oct(mode) for name, mode in executable_modes.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the macOS release ZIP")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    for key, value in verify_release(args.source, args.archive).items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
