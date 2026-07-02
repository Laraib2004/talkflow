' WhisprLocal background launcher
' Starts the voice-dictation app hidden, at below-normal CPU priority,
' with the transcription engine capped to 2 threads to stay light on RAM/CPU.
Option Explicit

Dim sh, py, workdir, cmd
Set sh = CreateObject("WScript.Shell")

py      = "C:\Users\larai\OneDrive\Dokumente\TalkFlow\whisprlocal\whisprlocal\.venv\Scripts\pythonw.exe"
workdir = "C:\Users\larai\OneDrive\Dokumente\TalkFlow\whisprlocal"

sh.CurrentDirectory = workdir

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
