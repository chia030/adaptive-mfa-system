# PowerShell script to sample 1,000,000 rows from rba-dataset.csv

# Step 1: Extract the header (first line) and write it to rba-ds-sample.csv
Get-Content -Path .\rba-dataset.csv -TotalCount 1 |
  Set-Content -Path .\rba-ds-sample-2.csv

# Step 2: Read all data rows (skip the header), shuffle them, take 1,000,000, and append to sample
Get-Content -Path .\rba-dataset.csv | Select-Object -Skip 1 `
  | Get-Random -Count 1000000 `
  | Add-Content -Path .\rba-ds-sample-2.csv

# Notes:
# - Run this in the folder containing rba-dataset.csv.
# - Change the –Count value for a different sample size.
