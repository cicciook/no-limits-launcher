# No Limits Launcher

Launcher Minecraft desktop multipiattaforma, in sviluppo, indipendente da Nuovo Ordine.

## Prototipo attuale
- Interfaccia desktop PySide6 per Windows, Linux e macOS
- Ricerca modpack tramite API pubblica Modrinth
- Registro locale per istanze Minecraft indipendenti
- Modulo di autenticazione Microsoft portato da Nuovo Ordine (Device Code, Xbox Live, XSTS, profilo Minecraft e refresh token)
- Provider CurseForge predisposto, ma non ancora implementato: richiede API key autorizzata

## Avvio da sorgente
Richiede Python 3.11+.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -e .
python -m nolimits
```

## Da completare
- Collegare il login Microsoft all'interfaccia e configurare il Client ID pubblico dell'app
- Installazione modpack e risoluzione loader/librerie
- Avvio del gioco e gestione Java
- Integrazione CurseForge tramite API autorizzata
- Client Android separato: non condivide il runtime Java desktop

Non inserire password Microsoft o client secret nel repository. Il Client ID è un identificativo pubblico dell'applicazione.
