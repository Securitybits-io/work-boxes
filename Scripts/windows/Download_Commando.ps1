$url = "https://github.com/mandiant/commando-vm/archive/refs/heads/main.zip"
$dest = "C:\tmp\commando-vm.zip"

Invoke-WebRequest -Uri $url -OutFile $dest

Expand-Archive -Path c:\tmp\commando-vm.zip -DestinationPath c:\tmp\