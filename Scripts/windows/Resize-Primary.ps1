[CmdletBinding()]
param(
    [ValidatePattern('^[a-zA-Z]$')]
    [string] $DriveLetter = 'C'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$partition = Get-Partition -DriveLetter $DriveLetter
$supportedSize = Get-PartitionSupportedSize -DriveLetter $DriveLetter

if ($partition.Size -ge $supportedSize.SizeMax) {
    Write-Output "Partition ${DriveLetter}: already uses the maximum supported size."
    return
}

Write-Output "Expanding partition ${DriveLetter}: to $($supportedSize.SizeMax) bytes."
Resize-Partition -DriveLetter $DriveLetter -Size $supportedSize.SizeMax
