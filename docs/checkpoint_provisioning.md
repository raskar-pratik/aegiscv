# Offline trusted encoder provisioning

Expected local path: `local_state/imports/checkpoints/resnet18.pth`. No checkpoint is supplied or downloaded by Veyra. Provide an authentic ResNet18 state dictionary compatible with torchvision's standard 1000-class architecture. Obtain provenance and an expected SHA-256 through your approved independent provisioning process; a locally calculated checksum alone does not establish authenticity or pretraining.

```powershell
Get-FileHash -Algorithm SHA256 local_state/imports/checkpoints/resnet18.pth
python scripts/validate_checkpoint.py local_state/imports/checkpoints/resnet18.pth --expected-sha256 YOUR_TRUSTED_DIGEST
$env:AEGISCV_ENCODER='resnet18'
$env:AEGISCV_ENCODER_WEIGHTS=(Resolve-Path local_state/imports/checkpoints/resnet18.pth).Path
$env:AEGISCV_ENCODER_SHA256='YOUR_TRUSTED_DIGEST'
python run.py
```

Validation checks SHA-256 before loading and strict state-dictionary compatibility. Construction uses `weights=None`; loading uses `weights_only=True`, CPU and evaluation mode. Preprocessing is recorded in encoder capability. Missing/incompatible/mismatched weights cause explicit handcrafted FALLBACK during scans. Use `AEGISCV_ENCODER=handcrafted` to explicitly select the baseline. API-supplied paths remain confined to imports; environment configuration is controlled by the local operator.

The report records encoder ID/version, checkpoint SHA-256, combined encoder/config hash, capability and whether an independently supplied checksum was pinned. No claim that checkpoint compatibility establishes semantic quality. Run the benchmark again after provisioning; profiles are encoder-specific and must not be reused across encoders.
