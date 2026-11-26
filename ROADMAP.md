# Roadmap, MVP i strategia testów — projekt

Status: do dalszego uzgodnienia po przeglądzie [SPECIFICATION.md](SPECIFICATION.md) i [ARCHITECTURE.md](ARCHITECTURE.md). Klient Python, `combined`, oba terminale, wykrywanie CLI i nazwa ShellPilot uzgodnione. Zadania poniżej nie oznaczają rozpoczętej implementacji.

## MVP — zakres częściowo uzgodniony

1. Cienka wtyczka Zsh działająca przez `source` i jako zewnętrzna wtyczka Oh My Zsh; `ai`, `ai cmd`, `ai fix`, `ai explain`, `ai new`, `ai backend`, `Ctrl+G`.
2. Klient Python uruchamiany na żądanie, bez daemona, z wersjonowanym NDJSON i streamingiem tekstu w bieżącym terminalu.
3. Dwa backendy korzystające z lokalnych logowań: Claude Code stream-json i Codex App Server lub `exec --json`, po przejściu testów blokady narzędzi.
4. Osobne adaptery cmux i iTerm2 już w MVP; panel ID, ograniczony scrollback, metadane z hooków Zsh; jawna degradacja przy braku API.
5. Osobne sesje dla `(panel, backend)`, bez globalnego `--last`; atomowy lokalny zapis tylko identyfikatorów i ustawień.
6. Ograniczanie i maskowanie kontekstu, brak automatycznego wykonania, propozycje wyłącznie w edytowalnym buforze.
7. Instalacja/odinstalowanie bez naruszania innych hooków i mapowań. Wykrywanie zainstalowanych Codex CLI i Claude Code oraz diagnostyka braku; bez instalacji tych klientów. `ai doctor` pozostaje propozycją pomocniczego polecenia.

Uzgodniony zakres MVP dostarcza `combined` terminal output. Oddzielne `stdout` i `stderr` mają status `unavailable`, dopóki nie istnieje źródło, które je wiarygodnie rozdziela.

## Backlog po MVP

- Opcjonalna, świadomie włączana rejestracja osobnych stdout/stderr z analizą wpływu na TTY, potoki i programy interaktywne; nie wolno jej włączyć domyślnie.
- Pomiar i ewentualna migracja klienta do Go/Rust, jeśli start P95 lub dystrybucja Pythona nie spełnią ustalonych celów.
- Inne terminale, selekcja własnego fragmentu scrollback, podgląd danych przed wysłaniem, własne wzorce redakcji.
- Rozszerzony format odpowiedzi komend, historia propozycji, telemetria wyłącznie po świadomej zgodzie.
- Pakowanie Homebrew i automatyczne testy na macOS po ustaleniu minimalnych wersji.

## Kryteria akceptacji MVP

| ID | Sprawdzalny warunek |
| --- | --- |
| A1 | Na macOS interaktywny Zsh ładuje plugin z OMZ i przez `source`; ponowne ładowanie nie powiela hooków ani mapowań. |
| A2 | `ai` dla Claude i Codex wyświetla pierwszą dostępną deltę przed zakończeniem tury, bez surowego JSON; błąd protokołu ma czytelny status. |
| A3 | Dwa panele jednego terminala i dwa backendy tworzą cztery niezależne mapowania; wznowienie po restarcie powłoki trafia do właściwej sesji. |
| A4 | `ai fix` używa ostatniego polecenia i exit code z tej samej powłoki; przy niepewnym output pokazuje brak danych. |
| A5 | cmux i iTerm2 odczytują tylko panel wywołujący; przy odmowie dostępu lub braku API klient nie pobiera danych z innego panelu. |
| A6 | `ai cmd` i `Ctrl+G` wstawiają jednowierszową propozycję do ZLE; Enter nie jest generowany; anulowanie i błąd zachowują poprzedni bufor. |
| A7 | Testy negatywne pokazują, że wywołane CLI nie może uruchomić narzędzia shell, zapisać pliku ani użyć skonfigurowanego MCP. Backend, którego nie da się ograniczyć, jest odrzucany. |
| A8 | Typowe sekrety, URL z hasłem oraz sekwencje ANSI/OSC nie pojawiają się w danych przekazanych do mock backendu; limity rozmiaru są egzekwowane. |
| A9 | `Ctrl+C` przerywa backend i pozostawia panel z działającą powłoką; nie zapisuje uszkodzonej sesji. |
| A10 | Instalacja nie wymaga dodatkowego klucza API, wrappera PTY ani panelu; testy instalacji i odinstalowania zachowują istniejący `.zshrc`. |

Wartości liczbowe czasu do pierwszej delty, RSS i minimalne wersje pozostają do ustalenia po prototypie pomiarowym; nie są w tym dokumencie pozorowane jako spełnione.

## Strategia testów

- **Parsery protokołów:** zapisane, zanonimizowane fixture NDJSON z obiema wersjami klientów; delty, final result, przerwanie, błąd, nieznany event, zdarzenie narzędzia, rozcięte wejście, błędny JSON, EOF bez `done`.
- **Wtyczka Zsh:** testy w interaktywnym Zsh z pseudo-terminalem użytym wyłącznie przez test runner, bez zmiany architektury produktu; `preexec`/`precmd`, status, konflikt `Ctrl+G`, keymap emacs/vi, `print -z`, zachowanie bufora i idempotencja.
- **Adaptery:** mock Socket API cmux oraz mock iTerm2 Python API dla limitów, błędów, tożsamości panelu, braku uprawnień i scrollback po przepełnieniu; szczególny test błędnej nazwy parametru ID powierzchni cmux i braku fallbacku do aktywnego obcego okna.
- **Bezpieczeństwo:** podmieniony proces agenta rejestruje dokładny prompt po filtracji; testy sekretów i sekwencji sterujących. Żywe testy obu CLI sprawdzają brak tool calls i efektów ubocznych w temp dir, z ustawieniami użytkownika/MCP próbującymi je przywrócić.
- **Sesje:** restart procesu, dwa panele, dwa backendy, `ai new`, uszkodzony plik stanu, równoczesne wywołania i przerwanie podczas zapisu.
- **Integracja na macOS:** najnowsze wspierane cmux/iTerm2 oraz obie architektury CPU, ręczne scenariusze SSH, program pełnoekranowy, wyczyszczony scrollback i różne motywy promptu. Macierz wersji powstaje po zatwierdzeniu minimów.
- **Wydajność:** mierzyć medianę/P95 czasu startu klienta, czasu do pierwszej delty, odczytu kontekstu, szczytowego RSS oraz rozmiar instalacji. Oddzielić opóźnienie lokalne od czasu odpowiedzi modelu.

## Kolejność prac po zatwierdzeniu

1. Próby wykonalności: ograniczenie narzędzi obu CLI, tożsamość panelu, odczyt output, zachowanie ZLE. Wyniki mogą zmienić ADR.
2. Kontrakt NDJSON i parsery obu backendów z fixture.
3. Adaptery i kontekst z redakcją.
4. Stan sesji i komendy klienta.
5. Wtyczka Zsh, instalacja i integracja.
6. Testy macOS, pomiary, dokumentacja wydania.
