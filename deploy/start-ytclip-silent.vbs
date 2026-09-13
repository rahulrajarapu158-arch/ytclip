Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "wsl -d Ubuntu -e bash -c 'source /home/hermes/.bashrc && systemctl --user start ytclip 2>/dev/null || true'", 0, False
