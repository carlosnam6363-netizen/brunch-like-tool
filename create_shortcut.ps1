$wsh = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath('Desktop')
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $currentDir) {
    $currentDir = (Get-Location).Path
}

$shortcutPath = Join-Path $desktop "브런치 자동 좋아요 (GUI).lnk"
$targetBat = Join-Path $currentDir "run_gui.bat"

$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetBat
$shortcut.WorkingDirectory = $currentDir
$shortcut.Description = "브런치 연재글 자동 좋아요 도구 (최신 동기화)"
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,43"
$shortcut.Save()

Write-Host "바탕화면에 바로가기 생성이 완료되었습니다: $shortcutPath" -ForegroundColor Green