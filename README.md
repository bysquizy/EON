# EON Local

EON is a private, local-first personal AI assistant for Windows. This repository
contains **v0.0.1**, an early command-line proof of concept rather than a finished
Windows agent.

## Principles

- Local model inference via Ollama (127.0.0.1 only in EON's source).
- No Google/Gemini API, paid AI service or remote model dependency.
- No autonomous shell, file-editing or desktop permissions in this prototype.
- Personal memory and secret storage are **not implemented yet**.
- Future risky actions will require explicit, one-time user approval.

## Requirements

Windows 11, Python 3.10+, Ollama for Windows and a downloaded local model.
Download Ollama from https://ollama.com/download/windows .

Configure the following **user environment variables** on Windows and restart
Ollama fully:

- OLLAMA_NO_CLOUD = 1
- OLLAMA_HOST = 127.0.0.1:11434

Important: this disables Ollama cloud inference but does **not** prove that
all supporting software can never make other network requests. Initial model
downloads and software installation require internet.

## Install and run

1. Download or clone this repository.
2. Install Ollama.
3. Run this command once to download the default local model:
   ollama pull qwen3:4b-instruct
4. Run baslat.bat on Windows, or run:
   py -3 eon.py

For a lighter model, download qwen3:1.7b and run:
py -3 eon.py --model qwen3:1.7b

## Commands

- /yardim — help
- /durum — session information
- /hesap 2*(3+5) — safe arithmetic evaluator
- /temizle — clear in-process chat memory
- /cikis — exit

The current session history is held in RAM; EON does not intentionally write
messages to a database. Operating system and Ollama logs/caches are outside
this prototype's guarantees. Don't feed confidential personal files yet.

## Tests

Run: py -3 -m unittest discover -s tests -v

Eight Python unit tests have been run successfully during development.
**Real Ollama inference has not been verified on the user's Windows PC.**

## Roadmap

- v0.0.2: approval state machine and carefully scoped tools
- v0.0.3: encrypted, editable local memory
- v0.1: minimal React UI and stable Windows MVP
- Later: offline voice, wake word, project spaces and permissioned computer use

Design basis: EON technical architecture v1.2.1 (November 19, 2026),
updated to remove all cloud AI model dependencies.
