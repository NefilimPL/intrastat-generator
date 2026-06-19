# Generator INTRASTAT XLSX

[![Testy i release](https://github.com/NefilimPL/intrastat-generator/actions/workflows/release.yml/badge.svg)](https://github.com/NefilimPL/intrastat-generator/actions/workflows/release.yml)
[![Latest release](https://img.shields.io/github/v/release/NefilimPL/intrastat-generator?label=release&sort=semver)](https://github.com/NefilimPL/intrastat-generator/releases/latest)
[![License: MIT](https://img.shields.io/github/license/NefilimPL/intrastat-generator)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)

Desktop/CLI generator plikow XLSX do przygotowania danych INTRASTAT.

## Do czego sluzy

Program pomaga przygotowac arkusz XLSX z pozycjami do zgloszen INTRASTAT na
podstawie plikow XML z deklaracji lub systemu Subiekt. Wczytuje dane towarowe,
slowniki XML oraz taryfe CN, a potem generuje plik XLSX z kolumnami potrzebnymi
do dalszej kontroli i importu/przepisania danych do procesu zgloszenia.

INTRASTAT to sprawozdawczosc dotyczaca obrotu towarowego z krajami Unii
Europejskiej. Oficjalne informacje, formularze i program do elektronicznych
zgloszen INTRASTAT publikuje GUS:
https://stat.gov.pl/badania-statystyczne/sprawozdawczosc/intrastat/elektroniczne-zgloszenia-intrastat/

Ten projekt nie zastepuje oficjalnego systemu GUS. Jego zadaniem jest
przyspieszenie przygotowania i weryfikacji danych przed zlozeniem zgloszenia w
oficjalnym narzedziu.

## Informacje o projekcie

- Nazwa pakietu: `intrastat-generator`
- Aplikacja: Generator INTRASTAT XLSX
- Opis: Generator XLSX INTRASTAT
- Autorzy: NefilimPL and contributors
- Licencja: MIT
- Repozytorium: https://github.com/NefilimPL/intrastat-generator

Repozytorium prywatne jest traktowane w GUI jako niedostepne publicznie. Po
upublicznieniu ten sam adres bedzie otwierany z ikony GitHub w GUI i bedzie
uzywany do sprawdzania publicznych release.

## GUI

GUI pokazuje ikone aplikacji z `Icon/icon.png` oraz ikone GitHub z
`Icon/github.png`. Ikona GitHub jest klikalna: dla publicznego repozytorium
otwiera strone repo, a dla prywatnego lub niedostepnego repo pokazuje komunikat.

Przycisk `Info` pokazuje podstawowe informacje o projekcie, aktualna wersje,
status repozytorium, status aktualizacji i ostatnio pobrany plik aktualizacji.

## Aktualizacje

Aplikacja sprawdza publiczne GitHub API:

- `repos/NefilimPL/intrastat-generator` do wykrycia, czy repozytorium jest
  publiczne;
- `repos/NefilimPL/intrastat-generator/releases/latest` do wykrycia najnowszego
  release.

Przycisk `Update` jest widoczny tylko wtedy, gdy publiczny release jest nowszy
od aktualnej wersji i zawiera plik `.exe` dla Windows. Klikniecie pobiera EXE do
folderu `aktualizacje` obok uruchomionego programu. Aplikacja nie podmienia
samej siebie w locie; po pobraniu trzeba zamknac aktualny program i uruchomic
pobrany plik.

## Uruchomienie lokalne

```powershell
python -m pip install -e .
python -m intrastat_generator
```

## Tryb CLI

```powershell
python -m intrastat_generator --input intrastat.xml --tariff Taryfa/taryfa.txt --no-gui
```

## Release EXE

Release jest tworzony z tagow `v*`, np. `v3.4.0`.
Artefakt ma nazwe `Intrastat-Generator_<tag>-<branch>_Windows_x64.exe`.
Build EXE uzywa `Icon/icon.ico` jako ikony pliku oraz bundluje folder `Icon`,
zeby GUI mialo ikony takze po skopiowaniu pojedynczego EXE do innego folderu.

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

Workflow tylko dodaje plik EXE do release. Nie wlacza automatycznego
`generate_release_notes`, zeby nie nadpisywac ani nie dublowac recznie wpisanego
opisu release, w tym automatycznego fragmentu `Full Changelog`.

Do tworzenia draft release i dodawania EXE wystarcza standardowy `GITHUB_TOKEN`
z `contents: write`, o ile ustawienia repozytorium pozwalaja GitHub Actions
zapisywac w repo. Dodatkowy fine-grained PAT jest potrzebny tylko do dokladnego
sprawdzania self-hosted runnerow przez API (`RUNNER_CHECK_TOKEN`).

## Licencja

MIT. Szczegoly sa w pliku [LICENSE](LICENSE).
