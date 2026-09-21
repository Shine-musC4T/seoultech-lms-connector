import importlib.util
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "package_release.py"
SPEC = importlib.util.spec_from_file_location("package_release", SCRIPT_PATH)
assert SPEC and SPEC.loader
package_release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package_release)


class PackageReleaseTests(unittest.TestCase):
    def test_zip_preserves_mac_executable_permissions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "release"
            source.mkdir()
            (source / "install.sh").write_text("#!/bin/bash\n", encoding="utf-8")
            (source / "README.md").write_text("hello\n", encoding="utf-8")
            media = source / "docs" / "media"
            media.mkdir(parents=True)
            (media / "large-demo.mp4").write_bytes(b"not for release")
            build = source / "build" / "lib"
            build.mkdir(parents=True)
            (build / "generated.py").write_text("generated\n", encoding="utf-8")
            egg_info = source / "src" / "example.egg-info"
            egg_info.mkdir(parents=True)
            (egg_info / "PKG-INFO").write_text("generated\n", encoding="utf-8")
            output = root / "release.zip"

            package_release.build_release(source, output)

            with zipfile.ZipFile(output) as archive:
                install = archive.getinfo("release/install.sh")
                readme = archive.getinfo("release/README.md")
                self.assertNotIn("release/docs/media/large-demo.mp4", archive.namelist())
                self.assertNotIn("release/build/lib/generated.py", archive.namelist())
                self.assertNotIn("release/src/example.egg-info/PKG-INFO", archive.namelist())
                install_mode = (install.external_attr >> 16) & 0xFFFF
                readme_mode = (readme.external_attr >> 16) & 0xFFFF
                self.assertTrue(install_mode & stat.S_IXUSR)
                self.assertFalse(readme_mode & stat.S_IXUSR)


if __name__ == "__main__":
    unittest.main()
