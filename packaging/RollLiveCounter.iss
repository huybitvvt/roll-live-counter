#define AppVersion "0.1.0"
[Setup]
AppId={{9F09B41C-7FE7-40DF-916A-F3B22D70AB95}
AppName=Roll Live Counter
AppVersion={#AppVersion}
AppPublisher=Roll Live Counter
AppPublisherURL=https://github.com/huybitvvt/roll-live-counter
DefaultDirName={localappdata}\Programs\RollLiveCounter
DefaultGroupName=Roll Live Counter
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir=..\dist\installer
OutputBaseFilename=RollLiveCounter-Setup-{#AppVersion}
Compression=lzma2/fast
SolidCompression=yes
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\RollLiveCounter.exe
LicenseFile=..\LICENSE
CloseApplications=yes
RestartApplications=no
WizardStyle=modern

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: startup; Description: "Start when signing in to Windows"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "..\dist\RollLiveCounter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\HUONG-DAN.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\VALIDATION.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Roll Live Counter"; Filename: "{app}\RollLiveCounter.exe"
Name: "{autodesktop}\Roll Live Counter"; Filename: "{app}\RollLiveCounter.exe"; Tasks: desktopicon
Name: "{userstartup}\Roll Live Counter"; Filename: "{app}\RollLiveCounter.exe"; Tasks: startup

[Run]
Filename: "{app}\RollLiveCounter.exe"; Description: "Open Roll Live Counter"; Flags: nowait postinstall skipifsilent
