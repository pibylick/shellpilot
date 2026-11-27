# ShellPilot

**Status: wersja rozwojowa; integracja na macOS wymaga potwierdzenia.** ShellPilot dodaje pomoc AI do istniejącej sesji Zsh w cmux lub iTerm2 na macOS. Odpowiedzi pojawiają się w terminalu, a proponowane polecenia trafiają do edytowalnego bufora ZLE. Uruchomienie polecenia pozostaje decyzją użytkownika.

Projekt zakłada wykrywanie lokalnie zainstalowanych i zalogowanych klientów Codex CLI i Claude Code, bez ich instalowania. ShellPilot nie wymaga osobnych kluczy API, nie zastępuje emulatora terminala, nie tworzy panelu i nie opakowuje powłoki w PTY.

## Planowany interfejs

| Polecenie | Działanie |
| --- | --- |
| `ai <pytanie>` | Rozmowa z kontekstem bieżącego panelu. |
| `ai cmd <opis>` | Propozycja polecenia do edycji w ZLE. |
| `ai fix` | Wyjaśnienie ostatniego niepowodzenia i ewentualna propozycja poprawki. |
| `ai explain` | Wyjaśnienie ostatniego wyniku. |
| `ai new` | Nowa sesja wybranego backendu dla bieżącego panelu. |
| `ai backend codex\|claude` | Wybór backendu dla bieżącego panelu. |
| `Ctrl+G` | Zamiana tekstu w buforze ZLE w propozycję polecenia. |

Szczegóły interfejsu i przypadki błędów opisuje [SPECIFICATION.md](SPECIFICATION.md). [ARCHITECTURE.md](ARCHITECTURE.md) zawiera analizę protokołów, bezpieczeństwa i wyboru języka. [ROADMAP.md](ROADMAP.md) definiuje MVP, backlog, kryteria akceptacji i testy. Decyzje architektoniczne mają trafiać do [docs/adr](docs/adr).

Agent uruchamia się wyłącznie po wywołaniu `ai` albo skrótu `Ctrl+G`. Skrót służy do generowania komendy z tekstu w buforze ZLE; rozmowa, analiza błędu i wyjaśnienie wyniku używają poleceń `ai`.

## Instalacja z lokalnego checkoutu

Wymagane: macOS, Zsh, Python 3.10+ oraz zainstalowany i zalogowany `codex` lub `claude` w `PATH`. ShellPilot nie instaluje tych klientów. W iTerm2 włącz Python API; dla cmux włącz dostęp do lokalnego socketu dla procesów uruchomionych w cmux.

```zsh
cd /ścieżka/do/shellpilot
python3 -m venv .venv
.venv/bin/pip install -e '.[iterm2]'
export SHELLPILOT_BIN="$PWD/.venv/bin/shellpilot"
source "$PWD/shellpilot.plugin.zsh"
ai doctor
```

Dla samego cmux wystarczy `.venv/bin/pip install -e .`; pakiet `iterm2` jest wymagany tylko dla adaptera iTerm2. Aby ładować wtyczkę przy każdym uruchomieniu Zsh, dodaj `SHELLPILOT_BIN` oraz `source /bezwzględna/ścieżka/do/shellpilot.plugin.zsh` do `~/.zshrc`. W Oh My Zsh można zamiast tego dodać symlink checkoutu w `$ZSH_CUSTOM/plugins/shellpilot` i umieścić `shellpilot` na liście `plugins` przed załadowaniem OMZ. W obu wariantach `SHELLPILOT_BIN` musi wskazywać skrypt z utworzonego środowiska Python.

`ai doctor` sprawdza dostępność klientów i zmiennych identyfikujących terminal; nie wykonuje zapytań do modeli. Codex jest domyślnym backendem dla nowego panelu. Użyj `ai backend claude`, aby go zmienić. `ai new` odłącza zapisany identyfikator sesji bieżącego backendu w bieżącym panelu.

## Uzgodnione ograniczenia i otwarte decyzje

- Ekran/scrollback terminala zawiera połączony obraz wyjścia. API cmux i iTerm2 nie daje ogólnej gwarancji osobnych bajtów stdout i stderr dla dowolnego wcześniej uruchomionego programu. Uzgodniony zakres MVP jawnie oznacza takie wyjście jako `combined`; osobne strumienie są osobnym, warunkowym tematem, bo ich przechwytywanie mogłoby zmienić semantykę poleceń.
- Gwarancja „agent nie wykonuje poleceń” wymaga twardego ograniczenia dostępnych narzędzi, sprawdzonego dla obsługiwanych wersji klientów. Sam tekst instrukcji dla modelu nie wystarcza.
- Minimalne wersje macOS i klientów oraz zgodność flag ograniczających narzędzia wymagają testu na rzeczywistym macOS. Nazwa produktu to ShellPilot, a repozytorium `shellpilot`.

## Bieżący etap

Kod i testy działają na Linuxie z atrapami cmux/Claude/Codex; nie przeprowadzono jeszcze testu obu rzeczywistych terminali na macOS. Codex CLI w tym środowisku nie mógł zainicjalizować własnego katalogu stanu z powodu systemu plików tylko do odczytu. Zdarzenia `codex exec --json` są wypisywane przy ich nadejściu; ta ścieżka może dawać mniej płynny streaming niż delty Claude Code. Wynik ostatniego polecenia pochodzi ze scrollback i ma oznaczenie `combined`; osobne stdout/stderr nie są odzyskiwane. Maskowanie sekretów jest oparte na wzorcach i nie wykryje wszystkich możliwych formatów.

Licencja: [Apache-2.0](LICENSE).
