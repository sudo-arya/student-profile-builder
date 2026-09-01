from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))


def make_project(destination: Path) -> Path:
    for name in ("templates", "assets"):
        shutil.copytree(ROOT / name, destination / name)
    (destination/"config.yml").write_text("template: basic\noutput_directory: dist\npreview:\n  port: 8000\n",encoding="utf-8")
    return destination
