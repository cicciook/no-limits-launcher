# No Limits Launcher

Launcher Minecraft desktop multipiattaforma, in sviluppo, indipendente da Nuovo Ordine.

## Prototipo attuale
- Interfaccia desktop scura blu/neon con navigazione laterale ispirata al concept grafico
- Ricerca modpack tramite API pubblica Modrinth
- Download e installazione del formato Modrinth .mrpack in cartelle isolate
- Avvio delle istanze .mrpack con account Microsoft collegato
- Registro locale per istanze Minecraft indipendenti
- Login Microsoft Device Code Flow portato da Nuovo Ordine, con Xbox Live, XSTS, profilo Minecraft, ripristino sessione e logout
- Refresh token nel portachiavi di sistema con namespace separato dal vecchio launcher
- Il portachiavi usa un namespace separato: non sovrascrive i token di Nuovo Ordine
- Provider CurseForge predisposto ma non ancora implementato: richiede API key autorizzata
- **Importa** (come su Prism): trascina o scegli un file, oppure incolla un link. Riconosce dal contenuto dello ZIP i modpack Modrinth (`.mrpack`), CurseForge (`.zip`) e Prism/MultiMC (`.zip`, con RAM, argomenti JVM e note)
- **Modifica istanza**: nome, icona, note, versione di Minecraft e mod loader, RAM, Java, argomenti JVM, risoluzione, e gestione di mod / resource pack / shader (attiva, disattiva, aggiungi, rimuovi). Inoltre duplica, apri cartella ed elimina
- Le impostazioni dell'istanza (RAM, Java, argomenti, risoluzione) vengono applicate all'avvio
- Nota CurseForge: le mod si scaricano senza API key dal sito, quindi alcune possono essere saltate (le elenca a fine import). Con una chiave autorizzata in `NOLIMITS_CURSEFORGE_API_KEY` il download passa dall'API ufficiale

## Avvio da sorgente
Python 3.11+:
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -e .
python -m nolimits
```

## Test
```bash
python tests/test_core.py
```
Verificano riconoscimento dei formati, import, estrazione sicura e opzioni di avvio senza rete né Minecraft (le librerie esterne sono simulate).

## Login Microsoft
Apri Account, inserisci il Client ID pubblico (Application/Client ID) dell'app Microsoft registrata per account personali, abilita il flusso client pubblico/device code in Microsoft Entra e premi Accedi. Il Client ID non era presente nel file di configurazione pubblico di Nuovo Ordine, quindi va inserito qui o impostato in NO_LIMITS_MSA_CLIENT_ID. Non inserire client secret o password nel launcher. Il Client ID può essere fornito anche tramite variabile d'ambiente `NO_LIMITS_MSA_CLIENT_ID`.

## Da completare
- Ripristino automatico sessione tramite refresh token all'avvio e logout
- Migliorare selezione versioni e gestione aggiornamenti modpack
- Installazione e gestione completa dei modpack CurseForge
- Avvio del gioco e gestione Java
- Integrazione CurseForge tramite API autorizzata
- Client Android separato: non condivide il runtime Java desktop
