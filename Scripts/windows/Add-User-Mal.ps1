$user = @{
    Name        = 'Mal'
    FullName    = 'MalDev Lab'
    Description = 'Malware Development Lab User'
}

New-LocalUser @user -NoPassword
Set-LocalUser -Name 'Mal' -PasswordNeverExpires:$true
Add-LocalGroupMember -Group 'Users' -Member 'Mal'
Add-LocalGroupMember -Group 'Administrators' -Member 'Mal'