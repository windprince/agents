$javaPath = "C:\Users\psharmak\OneDrive - Amgen\psharmak\agents\CRO_file_analysis\java\XcoreXsftpX240X9175"
$classPath = "C:\Users\psharmak\OneDrive - Amgen\psharmak\agents\CRO_file_analysis\class"

# Get all file names (without extension) from both folders
$javaFiles = Get-ChildItem -Path $javaPath -File | Select-Object -ExpandProperty BaseName
$classFiles = Get-ChildItem -Path $classPath -File | Select-Object -ExpandProperty BaseName

# Find files in java not in class
$inJavaNotClass = $javaFiles | Where-Object { $_ -notin $classFiles }
# Find files in class not in java
$inClassNotJava = $classFiles | Where-Object { $_ -notin $javaFiles }

Write-Host "Files in JAVA but not in CLASS:"
$inJavaNotClass

Write-Host "`nFiles in CLASS but not in JAVA:"
$inClassNotJava