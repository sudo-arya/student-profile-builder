from pathlib import Path
import json

root = Path(__file__).parent
data = json.loads((root / "generated" / "profile-data.json").read_text(encoding="utf-8"))
output = root / "build-output"
output.mkdir()
(output / "index.html").write_text(
    "<!doctype html><meta charset=utf-8><title>External example</title><h1>" +
    data["profile"]["name"].replace("&", "&amp;").replace("<", "&lt;") + "</h1>", encoding="utf-8")
