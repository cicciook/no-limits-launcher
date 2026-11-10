# No Limits Launcher

Launcher Minecraft desktop multipiattaforma, in sviluppo, indipendente da Nuovo Ordine.

## Prototipo attuale
- Interfaccia desktop scura blu/neon con navigazione laterale ispirata al concept grafico
- Ricerca modpack tramite API pubblica Modrinth
- Registro locale per istanze Minecraft indipendenti
- Login Microsoft Device Code Flow portato da Nuovo Ordine, con Xbox Live, XSTS, profilo Minecraft, ripristino sessione e logout
- Refresh token nel portachiavi di sistema con namespace separato dal vecchio launcher
- Il portachiavi usa un namespace separato: non sovrascrive i token di Nuovo Ordine
- Provider CurseForge predisposto ma non ancora implementato: richiede API key autorizzata

## Avvio da sorgente
Python 3.11+:
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -e .
python -m nolimits
```

## Login Microsoft
Apri Account, inserisci il Client ID pubblico (Application/Client ID) dell'app Microsoft registrata per account personali, abilita il flusso client pubblico/device code in Microsoft Entra e premi Accedi. Il Client ID non era presente nel file di configurazione pubblico di Nuovo Ordine, quindi va inserito qui o impostato in NO_LIMITS_MSA_CLIENT_ID. Non inserire client secret o password nel launcher. Il Client ID può essere fornito anche tramite variabile d'ambiente `NO_LIMITS_MSA_CLIENT_ID`.

## Da completare
- Ripristino automatico sessione tramite refresh token all'avvio e logout
- Installazione modpack e risoluzione loader/librerie
- Avvio del gioco e gestione Java
- Integrazione CurseForge tramite API autorizzata
- Client Android separato: non condivide il runtime Java desktop
