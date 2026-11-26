# Architektura i analiza techniczna — propozycja

Stan źródeł: 2026-11-26. Decyzje nie są jeszcze zatwierdzone.

## Przepływ

```text
Zsh / OMZ (ai, widget ZLE, preexec/precmd)
  ├─ identyfikator panelu + ostatnie polecenie + exit code + cwd
  └─ klient shellpilot (oddzielny proces, NDJSON)
       ├─ redakcja / limity / normalizacja kontekstu
       ├─ adapter cmux (CLI lub Socket API)
       ├─ adapter iTerm2 (mały most Python API)
       ├─ rejestr sesji per panel i backend
       ├─ adapter Claude Code (stream-json)
       └─ adapter Codex (app-server lub exec --json)
           ↓
       text_delta do terminala / command_candidate do ZLE
```

Wtyczka Zsh jest cienka: obsługuje hooki, wybór panelu, wywołanie klienta i edycję bufora. Klient odpowiada za protokoły, stan, filtrowanie i błędy. Bez daemona w MVP. Identyfikatory sesji są indeksowane parą `(adapter:panel_id, backend)`, z oddzielną wartością wybranego backendu per panel. Trzeba sprawdzić cykl życia ID po zamknięciu/odtworzeniu panelu, aby uniknąć przypadkowego wznowienia cudzej sesji.

## Co potwierdzają interfejsy

| Obszar | Potwierdzona możliwość | Ograniczenie / wniosek dla projektu |
| --- | --- | --- |
| Claude Code | `claude -p --input-format stream-json --output-format stream-json --verbose`, delty przy `--include-partial-messages`; `--resume <id>`; `--tools ""` ogranicza wbudowane narzędzia. [CLI](https://code.claude.com/docs/en/cli-reference), [streaming](https://code.claude.com/docs/en/headless) | Trzeba parsować typ zdarzenia i `result`, nie wycinać tekstu z TUI. `--tools` nie blokuje samych MCP, więc wymagane odcięcie MCP i test negatywny. Nie zakładać, że każda linia stdout jest deltą tekstu. |
| Codex CLI | `codex exec --json` emituje JSONL, `codex exec resume <id>` wznawia sesję. [CLI](https://developers.openai.com/codex/cli/reference) | `exec` uruchamia nowy proces na turę. `--json` opisuje zdarzenia, nie gwarantuje przyrostowych tokenów w każdym wydaniu. `resume --last` nie nadaje się do izolacji paneli. Konfiguracja narzędzi wymaga testu wersji. |
| Codex App Server | Dwukierunkowy protokół JSON-RPC/JSONL: `initialize` → `initialized` → `thread/start`/`thread/resume` → `turn/start`, zdarzenia `item/agentMessage/delta`, `turn/completed`. [Dokumentacja](https://developers.openai.com/codex/app-server) | Najlepsza ścieżka do streamingu i sesji. Klient musi obsłużyć żądania serwera i jawnie odmówić uruchomienia narzędzi; wymagana weryfikacja, czy da się zapewnić ścisły brak side effects przy dostępnej konfiguracji. |
| cmux | CLI i lokalny Unix socket z JSON `method`/`params`, `--json`, ID powierzchni z `CMUX_SURFACE_ID`; `read-screen` / `surface.read_text` opisuje też repozytorium cmux. [API](https://cmux.com/docs/api), [kontrakt CLI](https://github.com/manaflow-ai/cmux/blob/main/docs/cli-contract.md) | Socket może być wyłączony lub ograniczony do procesów potomnych cmux. Wyłącznie odczyt przypisanej powierzchni. Zrzut ekranu nie rozdziela stdout/stderr. Udokumentowano przypadki, gdy niepoprawny parametr celu odczytywał aktywną powierzchnię: wymagany test właściwego panelu i odmowa przy niepewnym adresowaniu. [Zgłoszenie cmux](https://github.com/manaflow-ai/cmux/issues/12937) |
| iTerm2 | Python API: `session_id`, `async_get_line_info`, `async_get_contents`, `async_get_screen_contents`; zalecana transakcja dla spójnego odczytu historii. [Session](https://iterm2.com/python-api/session.html) | API wymaga włączonego dostępu/zgody. Shell Integration pomaga śledzić polecenia i CWD, lecz nie stanowi gwarancji rozdzielenia strumieni. Adapter nie używa `async_send_text` do komend. |
| Zsh / OMZ | `zle -N`, `bindkey`, `BUFFER`/`LBUFFER`, `print -z`; `preexec`/`precmd`; zewnętrzna wtyczka OMZ może być ładowana z katalogu custom. [ZLE](https://zsh.sourceforge.io/Doc/Release/Zsh-Line-Editor.html), [funkcje](https://zsh.sourceforge.io/Doc/Release/Functions.html), [OMZ](https://github.com/ohmyzsh/ohmyzsh/wiki/External-plugins) | Hooki trzeba dodawać bez nadpisywania istniejących. `precmd` musi przechwycić `$?` przed innymi czynnościami; widget musi zachować bufor przy błędzie i działać w keymapach emacs/vi. Skrót `Ctrl+G` może kolidować z lokalnym mapowaniem. |

## Wybór klienta

| Język | Opóźnienie i dystrybucja | JSON stream i utrzymanie | Ocena |
| --- | --- | --- | --- |
| Python | Start interpretera i `venv` zwiększają koszt oraz instalację; na macOS interpreter może wymagać osobnego dostarczenia. | Standardowe `asyncio`/`json`, oficjalny pakiet iTerm2; jeden język dla obu adapterów. | **Propozycja MVP**: najszybsze sprawdzenie trudnych integracji, bez mostu międzyjęzykowego. |
| Go | Mały koszt startu, jeden binarny artefakt per architektura. | Prosty NDJSON i procesy; iTerm2 wymaga mostu Python lub własnej implementacji jego protokołu. | Dobra alternatywa po stabilizacji kontraktu. |
| Rust | Mały koszt startu, jeden artefakt, kontrola pamięci. | Solidne biblioteki, większy nakład pracy; iTerm2 dalej wymaga mostu. | Sensowny przy twardym celu dystrybucji jednego pliku. |
| TypeScript | Runtime Node i pakiety powiększają instalację; koszt startu zależy od sposobu pakowania. | Wygodne zdarzenia i JSON, lecz iTerm2 wymaga mostu Python. | Dobre dla zespołu TS, słabsze dla lekkiej instalacji na macOS. |

Opóźnienie odpowiedzi dominuje zwykle start agenta i sieć; to hipoteza do zmierzenia, nie wynik benchmarku. Przed wyborem produkcyjnym mierzymy medianę/P95 startu klienta, czas do pierwszej delty, RSS, czas adaptera i zachowanie po wznowieniu na Intel i Apple Silicon. Python pozostaje propozycją, dopóki te pomiary i sposób instalacji nie zostaną zatwierdzone.

## Protokół i sesje

1. Zsh rozpoznaje `panel_key` i zbiera lokalne metadane. Jeśli brak jednoznacznego panelu, `ai fix`/`explain` nie sięgają do aktywnego okna na ślepo.
2. Adapter pobiera ograniczony wycinek tekstu, oznacza źródło i dostępność. Redaktor usuwa sekwencje sterujące, przycina, maskuje sekrety. Nie zapisuje surowego wyniku na dysk.
3. Backend otrzymuje wyłącznie jawnie zbudowane dane. Parser sprawdza schemat zdarzeń i dopuszcza do renderera jedynie tekst odpowiedzi; linie z nieznanych zdarzeń są ignorowane lub zgłaszane jako błąd protokołu.
4. `command_candidate` jest niezaufanym tekstem. Klient usuwa obramowanie Markdown, odrzuca wielowierszowe/control characters i limity; Zsh wstawia go do edycji, nigdy do wykonania.
5. Sesję zapisujemy po poprawnym zakończeniu. `ai new` usuwa tylko mapowanie dla wybranego backendu i panelu. Brak sesji powoduje utworzenie nowej, nie wznowienie „ostatniej globalnej”.

Wybór Codex: preferować App Server po potwierdzeniu blokady narzędzi i zgodności z lokalnym `codex login`; `exec --json` pozostaje wariantem prostszym operacyjnie i ścieżką porównawczą. Nie proponujemy importu tokenów ani konfiguracji osobnego OAuth, ponieważ cel zakłada istniejące lokalne logowanie. Każdy fallback musi spełniać ten sam test braku wykonywania narzędzi.

## Ryzyka i bramki wykonalności

**Rozdzielne stdout/stderr.** Terminal renderuje połączony strumień; hooki Zsh znają tekst polecenia i status, lecz nie oryginalne deskryptory procesu potomnego. Przechwytywanie przez przekierowanie, `tee`, koproces lub PTY zmienia zachowanie poleceń, TTY i potoków. Bez takiej ingerencji nie obiecujemy wiernych strumieni dla arbitralnych poleceń. Wymaganie wymaga decyzji zakresowej.

**Zakaz autonomicznego wykonania.** Read-only sandbox sam w sobie nie oznacza „bez wykonania” i może nie chronić sekretów w czytelnym katalogu. Dla każdego wspieranego wydania klienta testujemy próbę wywołania narzędzia oraz odmowę lub brak możliwości. Jeśli nie da się tego wykazać, backend pozostaje niedostępny. Nie polegamy wyłącznie na instrukcji modelu.

**Granice ostatniego wyniku.** Scrollback może zostać wyczyszczony, nadpisany, pochodzić z programu pełnoekranowego lub komendy w SSH. Adapter zwraca `unavailable` zamiast udawać kompletny zapis.

**Subskrypcja i regulaminy.** ShellPilot wywołuje niezmodyfikowane lokalne CLI użytkownika; zgodność planu, limitów i logowania należy sprawdzić przy wydaniu. Nie czyta plików poświadczeń. [Claude Code legal](https://code.claude.com/docs/en/legal-and-compliance), [Codex jako platforma](https://developers.openai.com/blog/codex-as-a-platform).

## Porównanie istniejących projektów

| Projekt | Co potwierdza / czego można się nauczyć | Różnica względem ShellPilot |
| --- | --- | --- |
| [myk-org/claude-shell](https://github.com/myk-org/claude-shell) | Wtyczka OMZ i widgety ZLE, opcjonalny Kitty scrollback. | Jeden backend, funkcje scrollback związane z Kitty; ShellPilot planuje cmux/iTerm2 i jawny JSON stream. |
| [powowbox/codex-shell-assistant](https://github.com/powowbox/codex-shell-assistant) | Zsh bez obowiązkowego OMZ, Codex z istniejącym logowaniem, iTerm2 Python API i edytowalna komenda. Szczególnie przydatny wzór kontroli tożsamości panelu i testów instalatora. | Głównie Codex+iTerm2; ShellPilot planuje dwa backendy, cmux i sesje per panel. |
| [fluffypony/nsh](https://github.com/fluffypony/nsh) | Bogaty kontekst i historia z lokalnym stanem. | Używa wrappera PTY i osobnej infrastruktury, sprzecznych z założeniem lekkiej wtyczki. |
| [Deltik/shell-ai](https://github.com/Deltik/shell-ai) | Rust CLI, streaming, integracje powłok i obydwa lokalne CLI; pokazuje, że blokada narzędzi wymaga jawnych flag. | Szerszy produkt wielu providerów; ShellPilot skupia się na kontekście panelu i niezależnych sesjach. |

Wykorzystanie pomysłów nie oznacza kopiowania kodu. Licencje i zakres ewentualnego zapożyczenia należy sprawdzić przed implementacją.
