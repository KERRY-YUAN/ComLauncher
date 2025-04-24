@echo off
REM Set console to UTF-8 Code Page
chcp 65001 > nul
setlocal enabledelayedexpansion

REM --- Configuration ---
set "output_file=子文件列表_List.md"
set "script_name=%~nx0"
set "root_dir_name="
for %%F in ("%cd%") do set "root_dir_name=%%~nxF"

REM Directories and files to exclude (case-insensitive comparison)
REM Add more directories like node_modules, __pycache__ if needed
set "exclude_dirs=.git venv"
set "exclude_files=%script_name% %output_file%"

REM File extensions to include in the content section
set "content_extensions=*.txt *.json *.py *.vbs *.bat *.md"
REM --- End Configuration ---

REM Initialize Output File
(
    echo @@@@文件夹架构：
    echo ```
    echo %root_dir_name%/
) > "%output_file%"

REM Start the recursive directory processing
call :ProcessDirectory "%cd%" ""

REM Close the tree structure code block
>> "%output_file%" echo ```

REM --- Task 2: Add File Contents (Recursive) ---
(
    echo.
    echo @@@@文件内容：
    echo.
) >> "%output_file%"

REM Iterate recursively through specified file types
for /r "%cd%" %%G in (%content_extensions%) do (
    set "file_path=%%~fG"
    set "file_name=%%~nxG"
    set "is_excluded_file=0"
    set "is_in_excluded_dir=0"

    REM Check if the file itself is excluded
    for %%E in (%exclude_files%) do (
        if /i "!file_name!"=="%%E" (
            set "is_excluded_file=1"
        )
    )

    REM Check if the file is within an excluded directory path
    for %%D in (%exclude_dirs%) do (
        echo "!file_path!" | findstr /i /c:"\\%%~D\\" > nul
        if !errorlevel! equ 0 (
            set "is_in_excluded_dir=1"
        )
         REM Check if it's directly inside an excluded dir at the root
        echo "!file_path!" | findstr /i /c:"%cd%\%%~D\\!file_name!" > nul
         if !errorlevel! equ 0 (
             set "is_in_excluded_dir=1"
         )
    )

    REM If not excluded, add its content
    if !is_excluded_file! equ 0 if !is_in_excluded_dir! equ 0 (
        (
            echo.
            echo @@@@ File: !file_name! (Relative Path: !file_path:%cd%\=!)
            echo ```
            REM Use type command, handle potential errors reading file
            type "!file_path!" 2>nul || echo [Error reading file: !file_path!]
            echo ```
            echo.
        ) >> "%output_file%"
    )
)

echo.
echo Script finished. Output generated in "%output_file%"
endlocal
exit /b

REM --- Recursive Function to Process Directories ---
:ProcessDirectory <CurrentPath> <Prefix>
setlocal enabledelayedexpansion
set "current_path=%~1"
set "prefix=%~2"

REM Use temporary files to store directory and file lists for sorting and last-item detection
set "temp_list_file=%temp%\dir_list_%random%.txt"
del "%temp_list_file%" 2>nul

REM List items (Dirs first AD, then Files A-D) in the current directory
REM Exclude specified dirs/files during listing if possible, or filter after
(
    for /f "delims=" %%I in ('dir "%current_path%" /ad /b 2^>nul') do (
        set "item_name=%%I"
        set "is_excluded=0"
        for %%D in (%exclude_dirs%) do (
            if /i "!item_name!"=="%%~D" set "is_excluded=1"
        )
        if !is_excluded! equ 0 echo D:!item_name!
    )
    for /f "delims=" %%I in ('dir "%current_path%" /a-d /b 2^>nul') do (
        set "item_name=%%I"
        set "is_excluded=0"
        for %%F in (%exclude_files%) do (
            if /i "!item_name!"=="%%~F" set "is_excluded=1"
        )
        if !is_excluded! equ 0 echo F:!item_name!
    )
) > "%temp_list_file%"

REM Count the total number of items in the temp file
set "item_count=0"
for /f %%C in ('find /c /v "" "%temp_list_file%"') do set /a item_count=%%C 2>nul
if not defined item_count set item_count=0

REM Process the items from the temp file
set "current_item_index=0"
for /f "tokens=1,* delims=:" %%T in ('type "%temp_list_file%"') do (
    set /a current_item_index+=1
    set "item_type=%%T"
    set "item_name=%%U"

    REM Determine connector and next prefix based on whether it's the last item
    set "connector=├─"
    set "next_prefix=│   "
    if !current_item_index! equ !item_count! (
        set "connector=└─"
        set "next_prefix=    "
    )

    REM Output the line to the main output file
    if "!item_type!"=="D" (
        echo %prefix%!connector! !item_name!/ >> "%output_file%"
        REM Recursive call for subdirectory
        call :ProcessDirectory "%current_path%\!item_name!" "%prefix%!next_prefix!"
    ) else if "!item_type!"=="F" (
        echo %prefix%!connector! !item_name! >> "%output_file%"
    )
)

REM Clean up temporary file
del "%temp_list_file%" 2>nul

endlocal
exit /b