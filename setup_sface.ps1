$ErrorActionPreference = "Stop"

$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$modelDir = Join-Path $base "face_model"
$model = Join-Path $modelDir "face_recognition_sface_2021dec.onnx"

New-Item -ItemType Directory -Force -Path $modelDir | Out-Null

if (Test-Path $model) {
    Write-Host "[OK] Model SFace sudah ada:"
    Write-Host $model
    exit 0
}

$url = "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

Write-Host "[INFO] Download model SFace..."
Write-Host $url

Invoke-WebRequest `
    -Uri $url `
    -OutFile $model

if (!(Test-Path $model)) {
    throw "Model SFace gagal dibuat."
}

$size = (Get-Item $model).Length

if ($size -lt 30000000) {
    Remove-Item $model -Force
    throw "File model terlalu kecil / download tidak valid. Size=$size bytes"
}

Write-Host "[SUCCESS] Model SFace siap."
Write-Host "Path : $model"
Write-Host "Size : $size bytes"
