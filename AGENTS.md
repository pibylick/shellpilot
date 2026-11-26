# Wskazówki dla współtwórców i agentów

Projekt jest obecnie wyłącznie specyfikacją. **Nie implementuj produktu przed zatwierdzeniem przez właściciela** [SPECIFICATION.md](SPECIFICATION.md), [ARCHITECTURE.md](ARCHITECTURE.md) i zakresu [ROADMAP.md](ROADMAP.md). Instrukcje użytkownika w rozmowie mają pierwszeństwo przed tym dokumentem.

## Niezmienne założenia produktu

- macOS + interaktywny Zsh; Oh My Zsh opcjonalny, cmux i iTerm2 jako odrębne adaptery.
- Bez wrappera PTY, dodatkowych paneli, dodatkowych kluczy API i automatycznego wykonywania poleceń.
- Do komunikacji z CLI używaj zdarzeń JSON; nie parsuj tekstowego UI ani renderowanego stdout terminala jako protokołu agenta.
- Komendy modelu trafiają tylko do edytowalnego bufora ZLE. Nie używaj `eval`, `accept-line` ani terminalowego wysyłania Enter.
- Nie obiecuj oddzielnych stdout/stderr, jeśli źródło dostarcza tylko połączony ekran.
- Ograniczenia narzędzi i maskowanie kontekstu wymagają testów negatywnych; sam prompt nie jest kontrolą bezpieczeństwa.

## Praca w repozytorium

- Decyzje wymagające wyboru architektury zapisuj w `docs/adr` ze statusem i uzasadnieniem.
- Weryfikuj zmienne szczegóły CLI i API w dokumentacji źródłowej; zapisuj datę sprawdzenia.
- Dodawaj testy dla rzeczywistych granic protokołu i integracji, nie dla samej obecności plików.
- Nie wysyłaj kodu ani repozytorium do zdalnej usługi bez upoważnienia. Nie kopiuj poświadczeń użytkownika.
- Nie dodawaj licencji ani nie ogłaszaj gotowości open source przed decyzją właściciela o licencji i nazwie.
