[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string] $TimeZoneId,

    [Parameter(Mandatory)]
    [ValidatePattern('^[a-zA-Z]{2,3}(?:-[a-zA-Z]{2})?$')]
    [string] $LanguageTag
)

Set-StrictMode -Version Latest
$ProgressPreference = 'SilentlyContinue'
$ErrorActionPreference = 'Stop'

if ((Get-TimeZone).Id -ne $TimeZoneId) {
    Write-Output "Setting Windows timezone to '$TimeZoneId'."
    Set-TimeZone -Id $TimeZoneId
}

$currentLanguages = @(Get-WinUserLanguageList)
if ($currentLanguages.Count -ne 1 -or $currentLanguages[0].LanguageTag -ne $LanguageTag) {
    Write-Output "Setting Windows user language to '$LanguageTag'."
    Set-WinUserLanguageList -LanguageList $LanguageTag -Force
}

if ((Get-Culture).Name -ne $LanguageTag) {
    Write-Output "Setting Windows culture to '$LanguageTag'."
    Set-Culture -CultureInfo $LanguageTag
}

Set-ItemProperty -Path 'HKCU:\Control Panel\Desktop' -Name DragFullWindows -Value 1
Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced' -Name Hidden -Value 1
Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced' -Name ShowSuperHidden -Value 1
Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced' -Name HideFileExt -Value 0
