' VBS Launcher for SpotiUp
' This launches Python without showing a console window
' Right-click this file and create a shortcut to pin to taskbar with custom icon

Set oShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Change to the script directory
oShell.CurrentDirectory = scriptDir

' Run Python without showing console (use pythonw.exe)
' 0 = hide window, True = wait for exit
oShell.Run "pythonw.exe main.py", 0, False

Set oShell = Nothing
Set fso = Nothing
