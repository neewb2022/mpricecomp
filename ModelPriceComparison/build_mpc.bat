%CD%\env1\Scripts\create-version-file.exe file_version_info.yml --outfile file_version_info.txt
%CD%\env1\Scripts\pyinstaller.exe --onefile --version-file=file_version_info.txt -i icon.png --workpath %temp% --name mpricecomp main.py