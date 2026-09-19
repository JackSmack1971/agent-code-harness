[CmdletBinding()]
param(
    [switch]$HostTaskSurfaceAvailable,
    [switch]$HostAutomationSurfaceAvailable,
    [switch]$HostTaskSurfaceUnavailable,
    [switch]$HostAutomationSurfaceUnavailable
)

$ErrorActionPreference = 'Stop'

function Invoke-ChronosReadOnly {
    param([string[]]$Arguments)
    try {
        $cmd = Get-Command chronos.cmd -ErrorAction Stop
        $output = & $cmd.Source @Arguments 2>&1 | Out-String
        return [pscustomobject]@{ ok = ($LASTEXITCODE -eq 0); output = $output.Trim() }
    }
    catch {
        return [pscustomobject]@{ ok = $false; output = $_.Exception.Message }
    }
}

function Get-JsonObjectFromText {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $null }
    $start = $Text.IndexOf('{')
    $end = $Text.LastIndexOf('}')
    if ($start -lt 0 -or $end -le $start) { return $null }
    try { return ($Text.Substring($start, $end - $start + 1) | ConvertFrom-Json) }
    catch { return $null }
}

function Find-TextSignal {
    param([string]$Text, [string[]]$Patterns)
    foreach ($pattern in $Patterns) {
        if ($Text -match $pattern) { return $true }
    }
    return $false
}

$command = Get-Command chronos.cmd -ErrorAction SilentlyContinue
if (-not $command) {
    [pscustomobject]@{
        schema = 'chronos-capability-preflight/v1'
        provider = 'chronos'
        native = 'unavailable'
        observation = 'unavailable'
        supervision = 'unavailable'
        hook_execution = 'unknown'
        heartbeat_coverage = 'unsupported'
        host_task_surface = 'unknown'
        host_automation_surface = 'unknown'
        notes = @('chronos.cmd was not found on PATH; no installation or trust action was attempted')
    } | ConvertTo-Json -Depth 5
    exit 0
}

$install = Invoke-ChronosReadOnly @('-Action','install-status')
$supervise = Invoke-ChronosReadOnly @('-Action','supervise','-SupervisionAction','status')
$heartbeat = Invoke-ChronosReadOnly @('-Action','heartbeat')

$combined = @($install.output, $supervise.output, $heartbeat.output) -join "`n"
$superviseJson = Get-JsonObjectFromText $supervise.output
$heartbeatJson = Get-JsonObjectFromText $heartbeat.output

$nativeState = if ($install.ok -or $supervise.ok -or $heartbeat.ok) { 'available' } else { 'degraded' }

$hookObserved = Find-TextSignal $combined @(
    'hookExecutionObservation["''=: ]+observed',
    '"hookExecutionObservation"\s*:\s*"observed"',
    'hookRuns["''=: ]+[1-9][0-9]*',
    '"hookRuns"\s*:\s*[1-9][0-9]*'
)
$hookConfigured = Find-TextSignal $combined @('hook.*trusted','hook.*active','hook.*configured')

$observedCoverage = Find-TextSignal $heartbeat.output @(
    'coverageObserved["''=: ]+[1-9][0-9]*',
    '"coverageObserved"\s*:\s*[1-9][0-9]*',
    '"observed"'
)
$partialCoverage = Find-TextSignal $heartbeat.output @(
    'coveragePartial["''=: ]+[1-9][0-9]*',
    '"coveragePartial"\s*:\s*[1-9][0-9]*',
    '"partial"'
)
$unsupportedEight = Find-TextSignal $heartbeat.output @(
    'coverageUnsupported["''=: ]+8',
    '"coverageUnsupported"\s*:\s*8'
)

if ($observedCoverage) { $observationState = 'available'; $coverageState = 'observed' }
elseif ($partialCoverage -or $hookObserved) { $observationState = 'partial'; $coverageState = 'partial' }
elseif ($nativeState -eq 'available') { $observationState = 'unsupported'; $coverageState = if ($unsupportedEight) { 'unsupported' } else { 'unknown' } }
else { $observationState = 'unavailable'; $coverageState = 'unsupported' }

$taskSurface = 'unknown'
if ($HostTaskSurfaceAvailable) { $taskSurface = 'available' }
elseif ($HostTaskSurfaceUnavailable) { $taskSurface = 'unavailable' }

$automationSurface = 'unknown'
if ($HostAutomationSurfaceAvailable) { $automationSurface = 'available' }
elseif ($HostAutomationSurfaceUnavailable) { $automationSurface = 'unavailable' }

if ($taskSurface -eq 'available' -and $automationSurface -eq 'available') {
    $supervisionState = 'host_verification_required'
}
elseif ($taskSurface -eq 'unavailable' -or $automationSurface -eq 'unavailable') {
    $supervisionState = 'unavailable'
}
else {
    $supervisionState = 'host_verification_required'
}

$recurrenceEligible = Find-TextSignal $supervise.output @(
    'recurrenceEligible["''=: ]+true',
    '"recurrenceEligible"\s*:\s*true'
)

$notes = @()
$notes += 'Read-only preflight only: no plugin install, hook trust, Governor initialization, recurrence creation, or task mutation was attempted.'
if ($recurrenceEligible) {
    $notes += 'Native recurrenceEligible=true was observed; this is necessary but is not proof that the Codex host exposes task/automation surfaces or that exactly one Governor recurrence exists.'
}
if ($hookConfigured -and -not $hookObserved) {
    $notes += 'Hooks appear configured/trusted, but execution was not observed; configuration is not execution evidence.'
}
if ($supervisionState -eq 'host_verification_required') {
    $notes += 'Full supervision requires host-side proof of task inventory plus exactly one active Governor recurrence and zero worker recurrences.'
}

[pscustomobject]@{
    schema = 'chronos-capability-preflight/v1'
    provider = 'chronos'
    native = $nativeState
    observation = $observationState
    supervision = $supervisionState
    hook_execution = if ($hookObserved) { 'observed' } elseif ($hookConfigured) { 'not_observed' } else { 'unknown' }
    heartbeat_coverage = $coverageState
    host_task_surface = $taskSurface
    host_automation_surface = $automationSurface
    recurrence_eligible_native = [bool]$recurrenceEligible
    notes = $notes
} | ConvertTo-Json -Depth 6
