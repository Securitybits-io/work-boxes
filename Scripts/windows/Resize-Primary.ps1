#Get the partition sizes.
$size = (Get-PartitionSupportedSize -DriveLetter 'C')

#Resize to the maximum size.
Resize-Partition -DriveLetter 'C' -Size $size.SizeMax