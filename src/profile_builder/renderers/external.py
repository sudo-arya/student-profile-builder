from pathlib import Path
from typing import Any
import json
import os
import shutil
import subprocess
import tempfile
from ..template_manifest import TemplateManifest
from ..utils import BuilderError


class ExternalBuildRenderer:
    def build(self, template: TemplateManifest, context: dict[str, Any], output: Path) -> None:
        missing = [name for name in template.executables if shutil.which(name) is None]
        command = list(template.build.command)
        executable = command[0]
        if executable == "{python}":
            import sys
            command[0] = sys.executable
        elif shutil.which(executable) is None:
            missing.insert(0, executable)
        if missing:
            unique = ", ".join(dict.fromkeys(missing))
            raise BuilderError(f'Cannot build template "{template.name}".\n\nRequired executable not found: {unique}\n'
                               "Install it and try again, or choose another template.")
        with tempfile.TemporaryDirectory(prefix="profile-builder-") as temporary:
            work = Path(temporary) / "template"
            shutil.copytree(template.directory, work, ignore=shutil.ignore_patterns("node_modules", ".git"))
            data_file = work / template.build.data_file
            data_file.parent.mkdir(parents=True, exist_ok=True)
            data_file.write_text(json.dumps(context, indent=2, ensure_ascii=False), encoding="utf-8")
            env = {key: value for key, value in os.environ.items() if not any(secret in key.upper() for secret in ("PASSWORD", "TOKEN", "SECRET", "KEY"))}
            result = subprocess.run(command, cwd=work, shell=False, text=True, capture_output=True, env=env)
            if result.returncode:
                diagnostic = (result.stdout + result.stderr).strip()[-4000:]
                raise BuilderError(f"Template build failed.\n\nTemplate: {template.name}\nCommand: {' '.join(command)}\n"
                                   f"Exit code: {result.returncode}\n\nBuild output:\n{diagnostic}")
            built = work / template.build.output_directory
            if not built.is_dir():
                raise BuilderError(f'Unable to build template "{template.name}".\n\nTemplate build output was not found: '
                                   f"{template.build.output_directory}\nCheck build.output_directory.")
            shutil.copytree(built, output, dirs_exist_ok=True)
