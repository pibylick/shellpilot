# ShellPilot

**Status: projekt specyfikacji, bez implementacji; główne granice MVP uzgodnione.** ShellPilot ma dodać pomoc AI do istniejącej sesji Zsh w cmux lub iTerm2 na macOS. Odpowiedzi pojawią się w terminalu, a proponowane polecenia trafią do edytowalnego bufora ZLE. Uruchomienie polecenia pozostanie decyzją użytkownika.

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

## Uzgodnione ograniczenia i otwarte decyzje

- Ekran/scrollback terminala zawiera połączony obraz wyjścia. API cmux i iTerm2 nie daje ogólnej gwarancji osobnych bajtów stdout i stderr dla dowolnego wcześniej uruchomionego programu. Uzgodniony zakres MVP jawnie oznacza takie wyjście jako `combined`; osobne strumienie są osobnym, warunkowym tematem, bo ich przechwytywanie mogłoby zmienić semantykę poleceń.
- Gwarancja „agent nie wykonuje poleceń” wymaga twardego ograniczenia dostępnych narzędzi, sprawdzonego dla obsługiwanych wersji klientów. Sam tekst instrukcji dla modelu nie wystarcza.
- Licencja, minimalne wersje macOS/Zsh/klientów i szczegóły instalacji wymagają dalszej decyzji lub weryfikacji technicznej. Nazwa produktu to ShellPilot, a proponowana nazwa repozytorium to `shellpilot`; przed publikacją potrzebna będzie kontrola kolizji nazwy.

## Bieżący etap

Repozytorium zawiera wyłącznie dokumenty. Nie ma instalatora, wtyczki ani działającego polecenia `ai`. Nie skonfigurowano zdalnego repozytorium.
