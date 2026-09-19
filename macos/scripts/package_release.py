from __future__ import annotations

import argparse
import stat
import zipfile
from pathlib import Path, PurePosixPath


EXECUTABLE_NAMES = {
    "install.sh",
    "uninstall.sh",
    "install.command",
    "uninstall.command",
}
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
ZIP_TIMESTAMP = (2026, 9, 19, 0, 0, 0)


def _is_excluded(path: Path) -> bool:
    if len(path.parts) >= 2 and path.parts[:2] == ("docs", "media"):
        return True
    return bool(EXCLUDED_PARTS.intersection(path.parts)) or path.suffix in EXCLUDED_SUFFIXES


def _zip_info(archive_name: str, *, directory: bool, executable: bool = False) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(archive_name, ZIP_TIMESTAMP)
    info.create_system = 3
    permissions = 0o755 if directory or executable else 0o644
    file_type = stat.S_IFDIR if directory else stat.S_IFREG
    info.external_attr = (file_type | permissions) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def build_release(source_directory: Path, output_path: Path) -> Path:
    source_directory = source_directory.resolve()
    output_path = output_path.resolve()
    if not source_directory.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_directory}")
    if output_path == source_directory or source_directory in output_path.parents:
        raise ValueError("Output ZIP must be outside the release source directory")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    root_name = source_directory.name

    with zipfile.ZipFile(
        temporary,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        archive.writestr(_zip_info(f"{root_name}/", directory=True), b"")
        for path in sorted(source_directory.rglob("*")):
            relative = path.relative_to(source_directory)
            if _is_excluded(relative):
                continue
            archive_name = str(PurePosixPath(root_name, *relative.parts))
            if path.is_dir():
                archive.writestr(_zip_info(f"{archive_name}/", directory=True), b"")
                continue
            archive.writestr(
                _zip_info(
                    archive_name,
                    directory=False,
                    executable=path.name in EXECUTABLE_NAMES,
                ),
                path.read_bytes(),
            )

    temporary.replace(output_path)
    return output_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the macOS release ZIP")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    print(build_release(args.source, args.output))


if __name__ == "__main__":
    main()
