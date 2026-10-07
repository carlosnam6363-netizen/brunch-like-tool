"""
Create desktop shortcuts for Brunch Like Tool
"""
import os
import sys

def create_shortcuts():
    try:
        import win32com.client
    except ImportError:
        # Fallback to WScript.Shell via powershell or python script
        pass

    desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
    base_dir = os.path.dirname(os.path.abspath(__file__))

    gui_bat = os.path.join(base_dir, "run_gui.bat")
    agent_bat = os.path.join(base_dir, "run_auto_agent.bat")
    login_bat = os.path.join(base_dir, "login.bat")
    cookie_bat = os.path.join(base_dir, "open_cookie_file.bat")

    ps_script = f"""
$wsh = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath('Desktop')

$s1 = $wsh.CreateShortcut("$desktop\\브런치 자동 좋아요 (GUI).lnk")
$s1.TargetPath = "{gui_bat}"
$s1.WorkingDirectory = "{base_dir}"
$s1.IconLocation = "$env:SystemRoot\\System32\\shell32.dll,43"
$s1.Save()

$s2 = $wsh.CreateShortcut("$desktop\\브런치 아침 자동 실행 에이전트.lnk")
$s2.TargetPath = "{agent_bat}"
$s2.WorkingDirectory = "{base_dir}"
$s2.IconLocation = "$env:SystemRoot\\System32\\shell32.dll,264"
$s2.Save()

$s3 = $wsh.CreateShortcut("$desktop\\브런치 로그인 및 쿠키 등록.lnk")
$s3.TargetPath = "{login_bat}"
$s3.WorkingDirectory = "{base_dir}"
$s3.IconLocation = "$env:SystemRoot\\System32\\shell32.dll,105"
$s3.Save()

$s4 = $wsh.CreateShortcut("$desktop\\브런치 쿠키 메모장 직접 입력.lnk")
$s4.TargetPath = "{cookie_bat}"
$s4.WorkingDirectory = "{base_dir}"
$s4.IconLocation = "$env:SystemRoot\\System32\\notepad.exe,0"
$s4.Save()
"""
    # Write as UTF-8 with BOM
    ps_path = os.path.join(base_dir, "create_shortcut.ps1")
    with open(ps_path, "w", encoding="utf-8-sig") as f:
        f.write(ps_script)

    os.system(f'powershell -ExecutionPolicy Bypass -File "{ps_path}"')
    print("Desktop shortcuts created successfully.")

if __name__ == "__main__":
    create_shortcuts()
