# ADR 0001: Granice wtyczki i wybór klienta

Status: **częściowo zaakceptowane** — Python i `combined` w MVP uzgodnione; reszta architektury pozostaje projektem.
Data: 2026-11-26

## Kontekst

ShellPilot ma działać w Zsh bez zmiany terminala i bez wrappera PTY. Integracja iTerm2 ma oficjalną bibliotekę Python; cmux ma CLI i Unix socket. Oba backendy dostarczają strukturalne zdarzenia JSON, ale różnią się sesjami i uprawnieniami.

## Propozycja

Cienka wtyczka Zsh zbiera metadane powłoki i edytuje ZLE. Osobny klient Python odpowiada za oba adaptery terminala, oba backendy, redakcję i stan sesji. Komunikacja wewnętrzna to wersjonowany NDJSON. Nie ma daemona.

Codex App Server jest preferowaną ścieżką, jeśli test potwierdzi pełną blokadę narzędzi przy istniejącym lokalnym logowaniu; `codex exec --json` jest wariantem porównawczym. Claude Code używa `stream-json`. Wydanie nie może deklarować osobnych stdout/stderr na podstawie scrollback.

## Alternatywy

- Go lub Rust jako główny klient zmniejszają zależności instalacji i czas startu, ale wymagają mostu Python do oficjalnego iTerm2 API albo utrzymywania własnego protokołu.
- TypeScript ułatwia obsługę zdarzeń, lecz wymaga runtime i również mostu iTerm2.
- Wrapper PTY dałby pełniejszy zapis wyniku, ale narusza podstawowy warunek produktu.

## Konsekwencje i warunki zmiany

Python wymaga kontrolowanego sposobu instalacji i pomiaru opóźnienia. Jeśli P95 lub dystrybucja okażą się nieakceptowalne, wracamy do wyboru języka. Jeśli żadna konfiguracja Codex CLI nie zagwarantuje braku autonomicznych narzędzi, backend pozostaje wyłączony do rozwiązania tego problemu. Zakres MVP dla oddzielnych strumieni jest uzgodniony: `combined` z jawną niedostępnością stdout/stderr. Ewentualne przechwytywanie osobnych strumieni wymaga odrębnej decyzji i ADR.
