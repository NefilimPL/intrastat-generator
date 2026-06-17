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

Samo utworzenie draft release w GitHub UI nie uruchamia GitHub Actions. Aby
zbudowac EXE dla drafta:

1. wypchnij tag, np. `git tag v1.0.3` i `git push origin v1.0.3`, albo
2. uruchom workflow recznie: Actions -> Release -> Run workflow i wpisz
   `release_tag`, np. `v1.0.3`.

Workflow najpierw sprawdza self-hosted runner `Windows`/`X64`. GitHub wymaga
uprawnienia `Administration: read` do API listowania runnerow, dlatego dla
dokladnego fallbacku warto dodac sekret repozytorium `RUNNER_CHECK_TOKEN`
z fine-grained PAT z dostepem `Administration: read`.

Jesli sekret nie jest ustawiony albo API zwroci 403, workflow nie przerywa
release i wybiera self-hosted-first scheduling. Przy aktywnym runnerze build
trafi na self-hosted; przy braku runnera dokladny fallback na `windows-latest`
wymaga `RUNNER_CHECK_TOKEN`.

Publikacja GitHub Release uzywa pliku EXE bezposrednio z joba build. Upload do
Actions artifacts jest opcjonalny i nie blokuje release, szczegolnie na
self-hosted runnerze.

Release jest tworzony jako draft (`draft: true`), zeby EXE byl dodany przed
upublicznieniem. Przy ochronie przed edycja opublikowanych release'ow nalezy
najpierw pozwolic workflow utworzyc lub uzupelnic draft, a dopiero potem
opublikowac go recznie w GitHub.

Do tworzenia draft release i dodawania EXE wystarcza standardowy `GITHUB_TOKEN`
z `contents: write`, o ile ustawienia repozytorium pozwalaja GitHub Actions
zapisywac w repo. Dodatkowy fine-grained PAT jest potrzebny tylko do dokladnego
sprawdzania self-hosted runnerow przez API (`RUNNER_CHECK_TOKEN`).
