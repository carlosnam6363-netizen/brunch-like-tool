
$wsh = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath('Desktop')

$s1 = $wsh.CreateShortcut("$desktop\브런치 자동 좋아요 (GUI).lnk")
$s1.TargetPath = "C:\Users\user\.gemini\antigravity\scratch\brunch-like-tool\run_gui.bat"
$s1.WorkingDirectory = "C:\Users\user\.gemini\antigravity\scratch\brunch-like-tool"
$s1.IconLocation = "$env:SystemRoot\System32\shell32.dll,43"
$s1.Save()

$s2 = $wsh.CreateShortcut("$desktop\브런치 아침 자동 실행 에이전트.lnk")
$s2.TargetPath = "C:\Users\user\.gemini\antigravity\scratch\brunch-like-tool\run_auto_agent.bat"
$s2.WorkingDirectory = "C:\Users\user\.gemini\antigravity\scratch\brunch-like-tool"
$s2.IconLocation = "$env:SystemRoot\System32\shell32.dll,264"
$s2.Save()

$s3 = $wsh.CreateShortcut("$desktop\브런치 로그인 및 쿠키 등록.lnk")
$s3.TargetPath = "C:\Users\user\.gemini\antigravity\scratch\brunch-like-tool\login.bat"
$s3.WorkingDirectory = "C:\Users\user\.gemini\antigravity\scratch\brunch-like-tool"
$s3.IconLocation = "$env:SystemRoot\System32\shell32.dll,105"
$s3.Save()

$s4 = $wsh.CreateShortcut("$desktop\브런치 쿠키 메모장 직접 입력.lnk")
$s4.TargetPath = "C:\Users\user\.gemini\antigravity\scratch\brunch-like-tool\open_cookie_file.bat"
$s4.WorkingDirectory = "C:\Users\user\.gemini\antigravity\scratch\brunch-like-tool"
$s4.IconLocation = "$env:SystemRoot\System32\notepad.exe,0"
$s4.Save()
