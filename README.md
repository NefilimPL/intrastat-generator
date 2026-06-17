# Generator INTRASTAT XLSX

Desktop/CLI generator plikow XLSX do importu INTRASTAT.

## Uruchomienie lokalne

```powershell
python -m pip install -e .
python -m intrastat_generator
```

## Tryb CLI

```powershell
python -m intrastat_generator --input intrastat.xml --tariff Taryfa\taryfa.txt --no-gui
```

## Release EXE

Release jest tworzony z tagow `v*`, np. `v3.4.0`.
Artefakt ma nazwe `Intrastat-Generator_<tag>_Windows_x64.exe`.

Workflow najpierw sprawdza self-hosted runner `Windows`/`X64`. GitHub wymaga
uprawnienia `Administration: read` do API listowania runnerow, dlatego dla
dokladnego fallbacku warto dodac sekret repozytorium `RUNNER_CHECK_TOKEN`
z fine-grained PAT z dostepem `Administration: read`.

Jesli sekret nie jest ustawiony albo API zwroci 403, workflow nie przerywa
release i wybiera self-hosted-first scheduling. Przy aktywnym runnerze build
trafi na self-hosted; przy braku runnera dokladny fallback na `windows-latest`
wymaga `RUNNER_CHECK_TOKEN`.
