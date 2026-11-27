# Specyfikacja funkcjonalna i techniczna

Data przeglądu źródeł: 2026-11-26. Status: implementacja MVP rozpoczęta po zgodzie właściciela; klient Python, `combined`, oba terminale, wykrywanie CLI i nazwa ShellPilot uzgodnione. Licencja: Apache-2.0.

## 1. Cel i granice

Użytkownik macOS pracujący w interaktywnym Zsh może poprosić o wyjaśnienie lub komendę bez opuszczania bieżącego panelu cmux albo iTerm2. ShellPilot wykorzystuje uwierzytelnienie istniejących lokalnych klientów. Nie instaluje własnego emulatora, nie opakowuje sesji w PTY, nie otwiera dodatkowego panelu, nie żąda klucza API i nie wykonuje propozycji modelu.

Wersja startowa: macOS, Zsh, **oba terminale cmux i iTerm2**. Użycie z Oh My Zsh jest opcjonalne; skrypt Zsh musi działać po `source` bez OMZ. Inne powłoki i terminale są poza MVP. ShellPilot wykrywa lokalne CLI i podaje diagnostykę, jeśli ich brak; nie instaluje Codex CLI ani Claude Code.

## 2. Słownik i pochodzenie kontekstu

`panel_key` oznacza stabilny identyfikator aktywnej powierzchni terminala: dla cmux ID powierzchni, dla iTerm2 `session_id`. Klucz ma prefiks adaptera. Gdy nie da się go potwierdzić, operacja wymagająca kontekstu panelu kończy się błędem; nie pobieramy danych z innego panelu.

`last_command` i `exit_code` pochodzą z hooków Zsh (`preexec`, `precmd`) w tej samej powłoce. `cwd` pochodzi z bieżącego procesu Zsh. `scrollback` to ograniczona próbka tekstu ekranu z adaptera terminala. `output` to wycinek wyniku ostatniego polecenia, jeśli adapter pozwala wyznaczyć granice; w przeciwnym razie ma status `unavailable`. Tekst ekranu ma `stream: combined`, ponieważ nie zachowuje tożsamości stdout/stderr. Pola `stdout`/`stderr` mogą mieć wartość tylko przy potwierdzonym źródle rozdzielonych strumieni; w przeciwnym razie są `null`, nigdy zgadywane.

Konfiguracja limitów (propozycja): maks. 200 linii i 32 KiB scrollback, 16 KiB wyjścia ostatniego polecenia, przycięcie od najstarszych danych; limit po redakcji sekretów i usunięciu sekwencji sterujących. Puste lub niedostępne dane muszą być jawnie oznaczone w zapytaniu.

## 3. Zachowania

Agent jest uruchamiany tylko świadomym wywołaniem `ai` lub widgetu `Ctrl+G`. Hooki Zsh zbierają metadane ostatniego polecenia, lecz nie rozpoczynają sesji agenta. `Ctrl+G` służy wyłącznie do generowania komendy; pozostałe zadania uruchamia się poleceniami `ai`.

| Przypadek | Oczekiwany wynik |
| --- | --- |
| `ai <pytanie>` | Streaming tekstu odpowiedzi w tym samym terminalu; kontekst panelu dołączony po filtracji. Brak pytania pokazuje pomoc. |
| `ai cmd <opis>` | Jedna propozycja polecenia, bez Markdown i bez końcowego Enter, umieszczona w edytowalnym buforze ZLE. Wielowierszowe lub niejednoznaczne odpowiedzi wymagają jawnego błędu albo ręcznego wyboru; nie są wykonywane. |
| `ai fix` | Jeśli ostatni exit code jest niezerowy, wyjaśnienie błędu i opcjonalna propozycja polecenia. Jeżeli brak wiarygodnego ostatniego polecenia lub wyniku, komunikat diagnostyczny bez zgadywania. |
| `ai explain` | Wyjaśnienie ostatniego wyniku z oznaczeniem jakości kontekstu; nie zmienia bufora. |
| `ai new` | Usuwa lokalne powiązanie sesji wybranego backendu z bieżącym panelem, nie usuwa historii klienta agenta. |
| `ai backend ...` | Zmienia backend bieżącego panelu. Każdy backend zachowuje własny identyfikator sesji; zmiana nie miesza historii. |
| `Ctrl+G` | W trybie interaktywnym ZLE używa bieżącego bufora jako opisu, zachowuje go przy anulowaniu lub błędzie; po sukcesie wstawia propozycję bez `accept-line`. |

Polecenia `ai cmd` wywołane jako zwykła komenda Zsh nie mają już aktywnego bufora ZLE. Propozycja: po zakończeniu zwrócić ją przez `print -z`, tak aby pojawiła się w następnym promptcie; widget `Ctrl+G` wstawia bezpośrednio do `BUFFER`. Zachowanie obu dróg musi zostać sprawdzone w interaktywnym Zsh. Nie wolno używać `eval`, `zle accept-line`, dopisywać znaku nowej linii do wstrzykniętego bufora ani wywoływać terminalowego `send_text` do uruchamiania komend.

Streaming oznacza przyrostową prezentację odpowiedzi po zdarzeniach JSON, z obsługą przerwania `Ctrl+C`, bez renderowania surowego JSON lub zdarzeń narzędzi. Gdy backend kończy się błędem lub sesja jest niekompletna, interfejs pokazuje status i nie zapisuje błędnego identyfikatora sesji.

## 4. Kontrakt wewnętrzny (propozycja)

Wtyczka wywołuje niezależnego klienta `shellpilot`. Backend komunikuje się wyłącznie przez zdarzenia JSON. Domyślne wyjście klienta to NDJSON: `text_delta`, `command_candidate`, `session`, `backend`, `doctor`, `error`, `done`. Każdy rekord ma `schema_version: 1`, `request_id` i `type`; `done` zawiera `ok` oraz powód zakończenia, także przy błędzie. Zsh używa trybów prezentacyjnych `--format text` i `--format candidate`, aby przekazać sam tekst do terminala lub zwalidowaną jednowierszową komendę do ZLE. Te tryby nie parsują tekstowego interfejsu agentów. stderr procesu służy wyłącznie diagnostyce klienta.

Kontekst przekazywany backendowi ma pola `panel_key`, `cwd`, `last_command`, `exit_code`, `scrollback`, `last_output`, `stdout`, `stderr`, `availability` oraz zakresy/źródła danych. Pola tekstowe są danymi niezaufanymi. Sekrety są maskowane przed utworzeniem zapytania; użytkownik otrzymuje ostrzeżenie, gdy filtr mógł pominąć poufny materiał. Samo maskowanie wzorcami nie gwarantuje wykrycia wszystkich sekretów.

## 5. Bezpieczeństwo i prywatność

- Zakaz wykonania przez agenta to własność konfiguracji uruchomienia, nie samego promptu. Dla Claude Code należy ograniczyć wbudowane narzędzia (`--tools ""`) i wykluczyć MCP; dla Codex należy potwierdzić na obsługiwanej wersji skuteczne wyłączenie narzędzi i tryb odczytu, albo odmówić uruchomienia. Ustawienia użytkownika nie mogą przywrócić narzędzi.
- Kontekst jest zbierany dopiero po świadomym wywołaniu `ai`; brak ciągłego zapisu pełnego wyjścia. Lokalnie utrwalane są tylko identyfikatory sesji, backend i ustawienia, z uprawnieniami właściciela. Prompt i scrollback nie trafiają do logów ShellPilot.
- Filtr przed wysłaniem: usuwanie ANSI/OSC i znaków sterujących, limity rozmiaru, maskowanie wzorców tokenów/kluczy/URL z poświadczeniami, opcjonalne wykluczenie całego kontekstu. Prompt injection w wyjściu poleceń jest traktowany jako dane; nie może zmienić uprawnień klienta.
- `Ctrl+C` kończy klienta i potomny proces backendu. Identyfikator sesji zapisywany jest atomowo dopiero po potwierdzeniu poprawnej odpowiedzi protokołu.
- Brak obietnicy „zero wycieku”: sekret w niestandardowym formacie może ominąć maskowanie. Wymagany test z przykładowymi sekretami i jawny opis ograniczenia w README wydania.

## 6. Otwarte decyzje

Uzgodniono: MVP przyjmuje `combined` i jawne `null` dla rozdzielonych strumieni. Bez PTY wrappera lub ingerencji w uruchamianie poleceń nie można odzyskać osobnych stdout/stderr ze scrollback dowolnej sesji.

Uzgodniono również: oba terminale od pierwszego wydania, tylko wykrywanie lokalnych CLI oraz nazwa ShellPilot (`shellpilot` jako nazwa repozytorium).

1. Minimalne wersje macOS/Zsh/klientów: do ustalenia po próbach na rzeczywistym macOS.
2. Dalszy rozwój kontraktu NDJSON i polityka kolizji `Ctrl+G`: do doprecyzowania przed stabilnym wydaniem.

## 7. Źródła

- [Claude Code CLI](https://code.claude.com/docs/en/cli-reference), [programmatic streaming](https://code.claude.com/docs/en/headless).
- [Codex CLI](https://developers.openai.com/codex/cli/reference), [Codex App Server](https://developers.openai.com/codex/app-server).
- [cmux CLI i Socket API](https://cmux.com/docs/api).
- [iTerm2 Python API Session](https://iterm2.com/python-api/session.html), [Shell Integration](https://iterm2.com/documentation-shell-integration.html).
- [Zsh Line Editor](https://zsh.sourceforge.io/Doc/Release/Zsh-Line-Editor.html), [hooki Zsh](https://zsh.sourceforge.io/Doc/Release/Functions.html), [zewnętrzne wtyczki Oh My Zsh](https://github.com/ohmyzsh/ohmyzsh/wiki/External-plugins).
