from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from agentic_harness._resource_normalization import (
    NormalizedProcess,
    ResourceNormalizationError,
    matches_resource_pattern,
    normalize_network_origin,
    normalize_artifact,
    normalize_external_service,
    normalize_process,
    normalize_repo_path,
    repo_path_collation_key,
    normalize_repository_ref,
    pattern_is_broader_than,
)

FIXTURES_DIR_NAME = "resource_normalization"
_CONTRACTS_ROOT = Path(__file__).resolve().parents[1] / "contracts"


def _create_directory_escape_link(link: Path, target: Path) -> None:
    if os.name != "nt":
        link.symlink_to(target, target_is_directory=True)
        return
    result = subprocess.run(
        ["cmd.exe", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def _schema_doc(contracts_root: Path) -> dict[str, Any]:
    return json.loads((contracts_root / "resource_normalization.schema.json").read_text(encoding="utf-8"))


def _semantic_types_doc(contracts_root: Path) -> dict[str, Any]:
    return json.loads((contracts_root / "semantic_types.schema.json").read_text(encoding="utf-8"))


def _registry(contracts_root: Path) -> tuple[Registry, dict[str, Any]]:
    rn = _schema_doc(contracts_root)
    sem = _semantic_types_doc(contracts_root)
    registry = Registry().with_resources([(sem["$id"], Resource.from_contents(sem)), (rn["$id"], Resource.from_contents(rn))])
    return registry, rn


def _validator_for(defname: str, contracts_root: Path) -> Draft202012Validator:
    registry, rn = _registry(contracts_root)
    return Draft202012Validator({"$ref": f"{rn['$id']}#/$defs/{defname}"}, registry=registry)


def _load_fixture(contracts_root: Path, name: str) -> list[dict[str, Any]]:
    path = contracts_root / "tests" / FIXTURES_DIR_NAME / name
    return json.loads(path.read_text(encoding="utf-8"))


def _golden_cases(contracts_root: Path) -> list[tuple[str, Any]]:
    return [(c["def"], c["value"]) for c in _load_fixture(contracts_root, "golden.json")]


def _adversarial_cases(contracts_root: Path) -> list[tuple[str, Any]]:
    return [(c["def"], c["value"]) for c in _load_fixture(contracts_root, "adversarial.json")]


# ---------------------------------------------------------------------------
# Contract structural conformance
# ---------------------------------------------------------------------------


def test_schema_is_valid_draft_2020_12(contracts_root: Path) -> None:
    Draft202012Validator.check_schema(_schema_doc(contracts_root))


def test_fixture_files_exist(contracts_root: Path) -> None:
    assert (contracts_root / "tests" / FIXTURES_DIR_NAME / "golden.json").is_file()
    assert (contracts_root / "tests" / FIXTURES_DIR_NAME / "adversarial.json").is_file()


def test_resource_kinds_match_blueprint_9_12_2(contracts_root: Path) -> None:
    import yaml

    doc = yaml.safe_load((contracts_root / "resource_normalization.yaml").read_text(encoding="utf-8"))
    assert doc["resource_kinds"] == ["repo_path", "process", "network_origin", "external_service", "secret", "repository_ref", "artifact"]


def test_repo_path_normalization_steps_match_blueprint_9_12_3(contracts_root: Path) -> None:
    import yaml

    doc = yaml.safe_load((contracts_root / "resource_normalization.yaml").read_text(encoding="utf-8"))
    assert len(doc["repo_path_normalization_steps"]) == 8


@pytest.mark.parametrize("defname,value", _golden_cases(_CONTRACTS_ROOT))
def test_golden_values_validate(defname: str, value: Any, contracts_root: Path) -> None:
    validator = _validator_for(defname, contracts_root)
    errors = sorted(validator.iter_errors(value), key=str)
    assert not errors, f"{defname}: {[e.message for e in errors]}"


@pytest.mark.parametrize("defname,value", _adversarial_cases(_CONTRACTS_ROOT))
def test_adversarial_values_are_rejected(defname: str, value: Any, contracts_root: Path) -> None:
    validator = _validator_for(defname, contracts_root)
    assert not validator.is_valid(value), f"{defname}: {value!r} unexpectedly validated"


# ---------------------------------------------------------------------------
# normalize_repo_path adversarial vectors (10.10.3)
# ---------------------------------------------------------------------------


@pytest.fixture()
def worktree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "src").mkdir()
    (root / "src" / "a.py").write_text("x", encoding="utf-8")
    return root


def test_normalize_repo_path_accepts_a_plain_relative_path(worktree: Path) -> None:
    assert normalize_repo_path("src/a.py", root=worktree) == "src/a.py"


def test_normalize_repo_path_collapses_dot_components(worktree: Path) -> None:
    assert normalize_repo_path("./src/./a.py", root=worktree) == "src/a.py"


def test_normalize_repo_path_rejects_absolute_path(worktree: Path) -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_repo_path("/etc/passwd", root=worktree)


def test_normalize_repo_path_rejects_traversal_escape(worktree: Path) -> None:
    with pytest.raises(ResourceNormalizationError) as excinfo:
        normalize_repo_path("../escape", root=worktree)
    assert excinfo.value.reason_code == "RESOURCE_SCOPE_WIDENING"


def test_normalize_repo_path_allows_dotdot_that_stays_within_root(worktree: Path) -> None:
    (worktree / "b").mkdir()
    assert normalize_repo_path("b/../src/a.py", root=worktree) == "src/a.py"


def test_normalize_repo_path_rejects_windows_drive_form(worktree: Path) -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_repo_path("C:/Windows/System32", root=worktree)


def test_normalize_repo_path_rejects_unc_form(worktree: Path) -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_repo_path("//server/share/file", root=worktree)


def test_normalize_repo_path_rejects_nul_byte(worktree: Path) -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_repo_path("src/\x00evil", root=worktree)


def test_normalize_repo_path_rejects_non_string_input(worktree: Path) -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_repo_path(123, root=worktree)  # type: ignore[arg-type]


def test_normalize_repo_path_rejects_symlink_escape(worktree: Path) -> None:
    escape_target = worktree.parent / "outside"
    escape_target.mkdir()
    (escape_target / "whatever").write_text("outside", encoding="utf-8")
    _create_directory_escape_link(worktree / "link", escape_target)
    with pytest.raises(ResourceNormalizationError) as excinfo:
        normalize_repo_path("link/whatever", root=worktree, exists_hint=True)
    assert excinfo.value.reason_code == "RESOURCE_SCOPE_WIDENING"


def test_normalize_repo_path_creation_target_anchors_to_existing_ancestor(worktree: Path) -> None:
    assert normalize_repo_path("src/new_file.py", root=worktree, exists_hint=False) == "src/new_file.py"


def test_normalize_repo_path_does_not_trust_false_existence_hint_for_symlink(worktree: Path) -> None:
    escape_target = worktree.parent / "outside"
    escape_target.mkdir()
    _create_directory_escape_link(worktree / "link", escape_target)
    with pytest.raises(ResourceNormalizationError):
        normalize_repo_path("link", root=worktree, exists_hint=False)


@pytest.mark.skipif(os.name != "nt", reason="junction vector is Windows-specific")
def test_normalize_repo_path_rejects_windows_junction_escape(worktree: Path, tmp_path: Path) -> None:
    outside = tmp_path / "junction-outside"
    outside.mkdir()
    junction = worktree / "junction"
    result = subprocess.run(
        ["cmd.exe", "/c", "mklink", "/J", str(junction), str(outside)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"Windows junction creation unavailable: {result.stderr or result.stdout}")
    with pytest.raises(ResourceNormalizationError) as excinfo:
        normalize_repo_path("junction/escape.txt", root=worktree, exists_hint=False)
    assert excinfo.value.reason_code == "RESOURCE_SCOPE_WIDENING"


def test_normalize_repo_path_creation_target_rejects_dotdot_suffix(worktree: Path) -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_repo_path("src/../../escape", root=worktree, exists_hint=False)


# ---------------------------------------------------------------------------
# process: PATH shadowing / interpreter ambiguity / environment injection
# ---------------------------------------------------------------------------


def test_normalize_process_accepts_an_absolute_executable() -> None:
    result = normalize_process("/usr/bin/git", ["git", "status"], "/repo")
    assert result.executable == "/usr/bin/git"


def test_normalize_process_canonicalizes_existing_absolute_executable(tmp_path: Path) -> None:
    executable = tmp_path / "bin" / "tool.exe"
    executable.parent.mkdir()
    executable.write_text("tool", encoding="utf-8")
    result = normalize_process(str(executable.parent / ".." / "bin" / "tool.exe"), ["tool"], "/repo")
    assert result.executable == str(executable.resolve())


def test_normalize_process_rejects_existing_absolute_directory(tmp_path: Path) -> None:
    directory = tmp_path / "tool.exe"
    directory.mkdir()
    with pytest.raises(ResourceNormalizationError):
        normalize_process(str(directory), ["tool"], "/repo")


def test_normalize_process_rejects_bare_name_without_path_dirs() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_process("git", ["git"], "/repo")


def test_normalize_process_rejects_relative_path_component() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_process("./git", ["git"], "/repo")


def test_normalize_process_rejects_relative_cwd() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_process("/usr/bin/git", ["git"], "repo")


def test_normalize_process_rejects_nul_in_argv() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_process("/usr/bin/git", ["git\x00status"], "/repo")


def test_normalize_process_resolves_via_explicit_path_dirs_only(tmp_path: Path) -> None:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "tool").write_text("#!/bin/sh\n", encoding="utf-8")
    result = normalize_process("tool", ["tool"], str(tmp_path), path_dirs=[str(bindir)])
    assert result.executable == str((bindir / "tool").resolve())


def test_normalize_process_rejects_directory_path_shadow_candidate(tmp_path: Path) -> None:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "tool").mkdir()
    with pytest.raises(ResourceNormalizationError):
        normalize_process("tool", ["tool"], str(tmp_path), path_dirs=[str(bindir)])


def test_normalize_process_requires_resolved_script_for_interpreter() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_process("/usr/bin/python3", ["python3", "attack.py"], "/repo")


def test_normalize_process_treats_powershell_as_an_interpreter() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_process("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe", ["powershell.exe", "attack.ps1"], "/repo")


def test_normalize_process_accepts_interpreter_with_resolved_script() -> None:
    result = normalize_process("/usr/bin/python3", ["python3", "run.py"], "/repo", resolved_script="run.py")
    assert result.script == "run.py"


def test_normalize_process_rejects_privileged_env_key_by_default() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_process("/usr/bin/git", ["git"], "/repo", env_keys=["PATH"], allow_privileged_env_keys=False)


def test_normalize_process_allows_privileged_env_key_when_authorized() -> None:
    result = normalize_process("/usr/bin/git", ["git"], "/repo", env_keys=["PATH"], allow_privileged_env_keys=True)
    assert result.env_keys == ("PATH",)


def test_normalize_process_rejects_malformed_env_key_name() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_process("/usr/bin/git", ["git"], "/repo", env_keys=["NOT=VALID"])


# ---------------------------------------------------------------------------
# network_origin: IDNA / trailing dot / default port / IP literal
# ---------------------------------------------------------------------------


def test_normalize_network_origin_materializes_default_https_port() -> None:
    origin = normalize_network_origin("https", "example.com", None)
    assert origin.port == 443


def test_normalize_network_origin_default_and_explicit_port_normalize_identically() -> None:
    a = normalize_network_origin("https", "example.com", None)
    b = normalize_network_origin("https", "example.com", 443)
    assert (a.host_ascii, a.port) == (b.host_ascii, b.port)


def test_normalize_network_origin_lowercases_scheme_and_host() -> None:
    origin = normalize_network_origin("HTTPS", "Example.COM", None)
    assert origin.scheme == "https"
    assert origin.host_ascii == "example.com"


def test_normalize_network_origin_strips_single_trailing_dot() -> None:
    a = normalize_network_origin("https", "example.com.", None)
    b = normalize_network_origin("https", "example.com", None)
    assert a.host_ascii == b.host_ascii


def test_normalize_network_origin_rejects_multiple_trailing_dots() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_network_origin("https", "example.com..", None)


def test_normalize_network_origin_encodes_idna_hostname() -> None:
    origin = normalize_network_origin("https", "münchen.example", None)
    assert origin.host_ascii.startswith("xn--")


def test_normalize_network_origin_ipv4_literal_does_not_equal_hostname() -> None:
    ip = normalize_network_origin("https", "93.184.216.34", None)
    host = normalize_network_origin("https", "example.com", None)
    assert ip.is_ip_literal is True
    assert host.is_ip_literal is False
    assert ip.host_ascii != host.host_ascii


def test_normalize_network_origin_ipv6_literal() -> None:
    origin = normalize_network_origin("https", "[2001:db8::1]", None)
    assert origin.is_ip_literal is True


def test_normalize_network_origin_rejects_ipv6_zone_identifier() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_network_origin("https", "[fe80::1%25eth0]", None)


def test_normalize_network_origin_canonicalizes_ipv6_spelling() -> None:
    a = normalize_network_origin("https", "[2001:0db8:0:0:0:0:0:1]", None)
    b = normalize_network_origin("https", "[2001:db8::1]", None)
    assert a.host_ascii == b.host_ascii


def test_normalize_network_origin_rejects_unknown_scheme() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_network_origin("ftp", "example.com", None)


def test_redirect_is_a_distinct_network_origin_resource() -> None:
    first = normalize_network_origin("https", "api.example.com", None)
    redirected = normalize_network_origin("https", "cdn.example.com", None)
    assert (first.scheme, first.host_ascii, first.port) != (redirected.scheme, redirected.host_ascii, redirected.port)


def test_normalize_network_origin_rejects_out_of_range_port() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_network_origin("https", "example.com", 70000)


def test_normalize_network_origin_rejects_non_string_host() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_network_origin("https", 123, None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# repository_ref: git argv-option-injection defense
# ---------------------------------------------------------------------------


def test_normalize_repository_ref_rejects_option_like_ref_name() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_repository_ref("repo", "BRANCH", "--upload-pack=evil")


def test_normalize_repository_ref_accepts_ordinary_branch_name() -> None:
    ref = normalize_repository_ref("repo", "BRANCH", "feature/x")
    assert ref.ref_name_or_oid == "feature/x"


def test_normalize_artifact_accepts_contract_identity_formats() -> None:
    artifact = normalize_artifact("harness.tool_output", "018f1e2e-0000-7000-8000-000000000000", None, "text/plain")
    assert artifact.artifact_id is not None
    digest = normalize_artifact("harness.tool_output", None, "sha256:" + "a" * 64, None)
    assert digest.digest == "sha256:" + "a" * 64


def test_normalize_artifact_rejects_non_contract_identity_formats() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_artifact("ns", "artifact-1", None, None)
    with pytest.raises(ResourceNormalizationError):
        normalize_artifact("ns", None, "not-a-digest", None)
    with pytest.raises(ResourceNormalizationError):
        normalize_artifact("ns", "018f1e2e-0000-7000-8000-000000000000", None, "")


def test_normalize_external_service_rejects_empty_account_scope() -> None:
    with pytest.raises(ResourceNormalizationError):
        normalize_external_service("provider", "read", "", "records/1")


# ---------------------------------------------------------------------------
# resource-pattern grammar and broadening (10.10.1)
# ---------------------------------------------------------------------------


def test_matches_resource_pattern_exact() -> None:
    assert matches_resource_pattern(kind="repo_path", match="EXACT", value="src/a.py", normalized_key="src/a.py", pattern_kind="repo_path")
    assert not matches_resource_pattern(kind="repo_path", match="EXACT", value="src/a.py", normalized_key="src/b.py", pattern_kind="repo_path")


def test_matches_resource_pattern_prefix() -> None:
    assert matches_resource_pattern(kind="repo_path", match="PREFIX", value="src/", normalized_key="src/a.py", pattern_kind="repo_path")
    assert not matches_resource_pattern(kind="repo_path", match="PREFIX", value="src/", normalized_key="lib/a.py", pattern_kind="repo_path")


def test_matches_resource_pattern_prefix_supports_contract_hierarchical_kinds() -> None:
    assert matches_resource_pattern(kind="artifact", match="PREFIX", value="build/", normalized_key="build/output.bin", pattern_kind="artifact")
    assert matches_resource_pattern(kind="external_service", match="PREFIX", value="records/", normalized_key="records/item/1", pattern_kind="external_service")


def test_matches_resource_pattern_glob_double_star_crosses_separators() -> None:
    assert matches_resource_pattern(kind="repo_path", match="GLOB", value="src/**/*.py", normalized_key="src/a/b/c.py", pattern_kind="repo_path")


def test_matches_resource_pattern_glob_single_star_does_not_cross_separators() -> None:
    assert not matches_resource_pattern(kind="repo_path", match="GLOB", value="src/*.py", normalized_key="src/a/b.py", pattern_kind="repo_path")


def test_matches_resource_pattern_prefix_rejected_for_non_hierarchical_kind() -> None:
    with pytest.raises(ResourceNormalizationError):
        matches_resource_pattern(kind="network_origin", match="PREFIX", value="https://", normalized_key="https://example.com:443", pattern_kind="network_origin")


def test_pattern_is_broader_than_rejects_widened_prefix_scope() -> None:
    narrower = {"kind": "repo_path", "match": "PREFIX", "value": "src/agentic_harness/"}
    broader = {"kind": "repo_path", "match": "PREFIX", "value": "src/"}
    assert pattern_is_broader_than(narrower, broader)
    assert not pattern_is_broader_than(broader, narrower)


def test_pattern_is_broader_than_rejects_cross_kind_comparison() -> None:
    a = {"kind": "repo_path", "match": "EXACT", "value": "src/a.py"}
    b = {"kind": "secret", "match": "EXACT", "value": "x"}
    assert not pattern_is_broader_than(a, b)


def test_case_insensitive_path_collation_exposes_case_fold_collision() -> None:
    assert repo_path_collation_key("Src/Readme.md", case_sensitive=False) == repo_path_collation_key("src/README.md", case_sensitive=False)
