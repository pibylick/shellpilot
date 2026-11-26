# ShellPilot

**Status: projekt specyfikacji, bez implementacji; wybór Python i zakres wyjścia MVP uzgodnione.** ShellPilot ma dodać pomoc AI do istniejącej sesji Zsh w cmux lub iTerm2 na macOS. Odpowiedzi pojawią się w terminalu, a proponowane polecenia trafią do edytowalnego bufora ZLE. Uruchomienie polecenia pozostanie decyzją użytkownika.

Projekt zakłada użycie lokalnie zainstalowanych i zalogowanych klientów Codex CLI i Claude Code. ShellPilot nie wymaga osobnych kluczy API, nie zastępuje emulatora terminala, nie tworzy panelu i nie opakowuje powłoki w PTY.

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

## Uzgodnione ograniczenia i otwarte decyzje

- Ekran/scrollback terminala zawiera połączony obraz wyjścia. API cmux i iTerm2 nie daje ogólnej gwarancji osobnych bajtów stdout i stderr dla dowolnego wcześniej uruchomionego programu. Uzgodniony zakres MVP jawnie oznacza takie wyjście jako `combined`; osobne strumienie są osobnym, warunkowym tematem, bo ich przechwytywanie mogłoby zmienić semantykę poleceń.
- Gwarancja „agent nie wykonuje poleceń” wymaga twardego ograniczenia dostępnych narzędzi, sprawdzonego dla obsługiwanych wersji klientów. Sam tekst instrukcji dla modelu nie wystarcza.
- Zakres pierwszego wydania, wersje minimalne klientów, sposób instalacji i licencja wymagają decyzji przed implementacją. Nazwa ShellPilot jest robocza; przed publikacją potrzebna będzie kontrola nazwy.

## Bieżący etap

Repozytorium zawiera wyłącznie dokumenty. Nie ma instalatora, wtyczki ani działającego polecenia `ai`. Nie skonfigurowano zdalnego repozytorium.
