import json
from pathlib import Path
from types import SimpleNamespace

import bootstrap


def test_python_version_requirement():
    assert bootstrap.python_supported((3,11,0))
    assert bootstrap.python_supported((3,14,0))
    assert not bootstrap.python_supported((3,10,9))


def test_virtual_environment_python_paths(tmp_path):
    assert bootstrap.venv_python(tmp_path,"nt") == tmp_path/".venv"/"Scripts"/"python.exe"
    assert bootstrap.venv_python(tmp_path,"posix") == tmp_path/".venv"/"bin"/"python"


def test_dependency_fingerprint_changes_with_requirements_and_python(tmp_path):
    (tmp_path/"requirements.txt").write_text("one\n",encoding="utf-8")
    first=bootstrap.dependency_fingerprint(tmp_path,(3,11,0))
    (tmp_path/"requirements.txt").write_text("two\n",encoding="utf-8")
    assert bootstrap.dependency_fingerprint(tmp_path,(3,11,0)) != first
    assert bootstrap.dependency_fingerprint(tmp_path,(3,12,0)) != bootstrap.dependency_fingerprint(tmp_path,(3,11,0))


def test_unchanged_dependencies_skip_pip(tmp_path,monkeypatch):
    (tmp_path/"requirements.txt").write_text("demo==1\n",encoding="utf-8")
    environment=tmp_path/".venv"; environment.mkdir()
    fingerprint=bootstrap.dependency_fingerprint(tmp_path)
    (environment/bootstrap.STATE_FILE).write_text(json.dumps({"fingerprint":fingerprint}),encoding="utf-8")
    monkeypatch.setattr(bootstrap,"run",lambda *_args,**_kwargs: (_ for _ in ()).throw(AssertionError("pip must not run")))
    assert bootstrap.ensure_dependencies(tmp_path,Path("venv-python")) is False


def test_changed_dependencies_use_only_venv_python(tmp_path,monkeypatch):
    (tmp_path/"requirements.txt").write_text("demo==1\n",encoding="utf-8"); (tmp_path/".venv").mkdir()
    calls=[]
    monkeypatch.setattr(bootstrap,"run",lambda args,*_a,**_k: calls.append(args) or SimpleNamespace(returncode=0))
    python=Path("project-venv-python")
    assert bootstrap.ensure_dependencies(tmp_path,python) is True
    assert calls == [[str(python),"-m","pip","install","-r",str(tmp_path/"requirements.txt")]]


def test_existing_valid_environment_is_reused(tmp_path,monkeypatch):
    python=bootstrap.venv_python(tmp_path); python.parent.mkdir(parents=True); python.write_text("",encoding="utf-8")
    monkeypatch.setattr(bootstrap,"environment_works",lambda *_:True)
    monkeypatch.setattr(bootstrap.subprocess,"run",lambda *_a,**_k:SimpleNamespace(returncode=0))
    monkeypatch.setattr(bootstrap.venv.EnvBuilder,"create",lambda *_:(_ for _ in ()).throw(AssertionError("must reuse")))
    assert bootstrap.ensure_environment(tmp_path) == python


def test_optional_tools_never_block_core():
    assert bootstrap.optional_tools(lambda _name:None) == {"ssh":False,"scp":False,"git":False,"gh":False}


def test_recreation_decline_preserves_environment(tmp_path):
    environment=tmp_path/".venv"; environment.mkdir(); marker=environment/"keep.txt"; marker.write_text("keep")
    assert not bootstrap.recreate_environment(tmp_path,input_fn=lambda _prompt:"n")
    assert marker.is_file()
