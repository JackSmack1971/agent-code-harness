#!/usr/bin/env python3
from __future__ import annotations
import ast, sys, tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
errors=[]
required=[ROOT/'AGENTS.md', ROOT/'.codex/config.toml', ROOT/'.codex/README.md', ROOT/'.codex/CONVERSION.md', ROOT/'.codex/references/runtime-observation-contract.md', ROOT/'.codex/references/execution-binding-v1.md', ROOT/'scripts/check_chronos.ps1']
for p in required:
    if not p.is_file(): errors.append(f'missing required file: {p.relative_to(ROOT)}')
try:
    tomllib.loads((ROOT/'.codex/config.toml').read_text(encoding='utf-8'))
except Exception as e: errors.append(f'invalid TOML .codex/config.toml: {e}')
for p in sorted((ROOT/'.codex/agents').glob('*.toml')):
    try:
        d=tomllib.loads(p.read_text(encoding='utf-8'))
        for k in ('name','description','developer_instructions'):
            if not d.get(k): errors.append(f'{p}: missing {k}')
    except Exception as e: errors.append(f'invalid agent TOML {p}: {e}')
for p in sorted((ROOT/'.codex/hooks').glob('*.py')):
    try: ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
    except Exception as e: errors.append(f'invalid Python {p}: {e}')
for skill in sorted((ROOT/'.agents/skills').glob('*/SKILL.md')):
    text=skill.read_text(encoding='utf-8')
    if not text.startswith('---\n') or '\nname:' not in text or '\ndescription:' not in text:
        errors.append(f'invalid portable skill frontmatter: {skill}')
    for forbidden in ('disable-model-invocation:', 'user-invocable:', 'context:', 'agent:'):
        if forbidden in text.split('---',2)[1]: errors.append(f'Claude-only field {forbidden} remains in {skill}')
    if not (skill.parent/'agents/openai.yaml').is_file(): errors.append(f'missing openai.yaml: {skill.parent}')

# Chronos/runtime-observation integration invariants.
chronos_contract = ROOT/'.codex/references/runtime-observation-contract.md'
binding_contract = ROOT/'.codex/references/execution-binding-v1.md'
phase_registry = ROOT/'.codex/references/phase-registry.md'
if chronos_contract.is_file():
    ct = chronos_contract.read_text(encoding='utf-8')
    for phrase in ('observed', 'partial', 'unsupported', 'does not authorize', 'execution-binding-v1.md', 'CHRONOS_NATIVE', 'CHRONOS_OBSERVATION', 'CHRONOS_SUPERVISION', 'recurrenceEligible=true', 'host_verification_required'):
        if phrase not in ct:
            errors.append(f'runtime observation contract missing required semantic: {phrase}')

chronos_preflight = ROOT/'scripts/check_chronos.ps1'
if chronos_preflight.is_file():
    cp = chronos_preflight.read_text(encoding='utf-8')
    for phrase in ('chronos-capability-preflight/v1', "'-Action','install-status'", "'-SupervisionAction','status'", "'-Action','heartbeat'", 'host_verification_required', 'recurrence_eligible_native'):
        if phrase not in cp:
            errors.append(f'Chronos preflight missing required semantic: {phrase}')
    for forbidden in ('plugin add', 'marketplace add', 'initialize', 'create recurrence', 'trust hooks'):
        if forbidden in cp.lower() and forbidden not in ('create recurrence', 'trust hooks'):
            errors.append(f'Chronos preflight may contain a mutating operation marker: {forbidden}')

if binding_contract.is_file():
    bt = binding_contract.read_text(encoding='utf-8')
    for phrase in ('execution_id', 'candidate_identity', 'skill_digest', 'agent_config_digest', 'provider_generation'):
        if phrase not in bt:
            errors.append(f'ExecutionBinding contract missing required semantic: {phrase}')
if phase_registry.is_file():
    pt = phase_registry.read_text(encoding='utf-8')
    for phrase in ('ExecutionBinding', 'Chronos', 'runtime-observation provenance'):
        if phrase not in pt:
            errors.append(f'phase registry missing runtime-observation integration marker: {phrase}')
config_text = (ROOT/'.codex/config.toml').read_text(encoding='utf-8') if (ROOT/'.codex/config.toml').is_file() else ''
if 'chronos' in config_text.lower():
    errors.append('Chronos must remain an independently installed plugin; do not embed it in .codex/config.toml')
for hook in sorted((ROOT/'.codex/hooks').glob('*')):
    if hook.is_file() and 'chronos' in hook.read_text(encoding='utf-8', errors='ignore').lower():
        errors.append(f'Chronos integration leaked into project hook implementation: {hook.relative_to(ROOT)}')

for p in list((ROOT/'.codex/agents').glob('*.toml')) + list((ROOT/'.codex/hooks').glob('*.py')) + list((ROOT/'.agents/skills').glob('*/SKILL.md')) + [ROOT/'AGENTS.md', ROOT/'.codex/config.toml']:
    if not p.is_file(): continue
    txt=p.read_text(encoding='utf-8')
    if '.claude/' in txt or 'CLAUDE_PROJECT_DIR' in txt:
        errors.append(f'Claude runtime/path reference remains in active artifact: {p.relative_to(ROOT)}')
if errors:
    print('CONTROL PLANE VALIDATION: FAIL')
    for e in errors: print(' -',e)
    sys.exit(1)
print('CONTROL PLANE VALIDATION: PASS')
print('agents:', len(list((ROOT/'.codex/agents').glob('*.toml'))))
print('skills:', len(list((ROOT/'.agents/skills').glob('*/SKILL.md'))))
print('hooks:', len(list((ROOT/'.codex/hooks').glob('*.py'))))
print('path policies:', len(list((ROOT/'.codex/references/path-policies').glob('*.md'))))
