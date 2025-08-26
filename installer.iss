; Inno Setup Script for AI Attendance
; Compile with Inno Setup (ISCC.exe) after building the EXE with PyInstaller

#define MyAppName "AI Attendance"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Your Company"
#define MyAppExeName "AI-Attendance.exe"
#define MyAppDistDir "dist"

[Setup]
AppId={{B3F114F7-0D3E-4F55-9E0A-7E2C2F53B3E1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=AI-Attendance-Installer
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#MyAppDistDir}\\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Include data directory if needed (uncomment if you ship pre-seeded data)
; Source: "data\\*"; DestDir: "{app}\\data"; Flags: ignoreversion recursesubdirs createallsubdirs
; Include docs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent


