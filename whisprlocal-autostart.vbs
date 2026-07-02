' WhisprLocal background launcher (portable)
' Starts the voice-dictation app hidden, at below-normal CPU priority, with the
' transcription engine capped to 2 threads to stay light on RAM/CPU.
'
' Path-independent: it locates itself, so the project folder can live anywhere
' and be named anything. It expects a virtualenv at ".venv" next to this script
' (create one per machine: `python -m venv .venv` then `pip install -e .`).
' If no venv is found it falls back to a "pythonw" on the system PATH.
Option Explicit

Dim sh, fso, scriptDir, py, cmd
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Folder this .vbs lives in = project root
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Prefer the project's own venv; fall back to whatever pythonw is on PATH
py = fso.BuildPath(scriptDir, ".venv\Scripts\pythonw.exe")
If Not fso.FileExists(py) Then py = "pythonw.exe"

sh.CurrentDirectory = scriptDir

' single-instance guard: bail out if whisprlocal is already running
Dim wmi, procs, proc, running
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
Set procs = wmi.ExecQuery("SELECT ProcessId, CommandLine FROM Win32_Process WHERE Name = 'pythonw.exe'")
running = False
For Each proc In procs
    If Not IsNull(proc.CommandLine) Then
        If InStr(proc.CommandLine, "whisprlocal") > 0 Then running = True
    End If
Next
If running Then WScript.Quit

' set thread cap, then start pythonw detached (/b = no window) at below-normal priority
cmd = "cmd /c set OMP_NUM_THREADS=2&& start """" /b /belownormal """ & py & """ -m whisprlocal"

' 0 = hidden window, False = don't wait
sh.Run cmd, 0, False
