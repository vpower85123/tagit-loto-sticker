; TAG!T Sticker App - Inno Setup Script
; Kostenloser Installer

#define MyAppName "TAG!T Sticker"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Ihr Unternehmen"
#define MyAppURL "https://www.example.com"
#define MyAppExeName "TAG!T_Sticker.exe"

[Setup]
; Grundeinstellungen
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Output-Einstellungen
OutputDir=..\installer\output
OutputBaseFilename=TAGIT_Setup_{#MyAppVersion}
; Kompression
Compression=lzma2/ultra64
SolidCompression=yes
; Darstellung
SetupIconFile=..\assets\icons\app_icon.ico
WizardStyle=modern
; Windows-Version
MinVersion=10.0

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Hauptanwendung (PyInstaller Output)
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Konfigurationsdateien
Source: "..\config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs
; Fonts
Source: "..\fonts\*"; DestDir: "{app}\fonts"; Flags: ignoreversion recursesubdirs createallsubdirs
; Symbole
Source: "..\symbols\*"; DestDir: "{app}\symbols"; Flags: ignoreversion recursesubdirs createallsubdirs
; Assets
Source: "..\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
// Prüfen ob bereits installiert
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
end;

// Nach Installation aufräumen
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Hier können Sie zusätzliche Aktionen ausführen
  end;
end;
