# Fantacalcio Co-Pilot — Roma Non Perdona (versione Streamlit)

Versione in Python/Streamlit dell'app di supporto all'asta del fantacalcio,
con i dati reali delle Quotazioni ufficiali 2026/27 già caricati (517 calciatori)
e le 9 squadre rivali della lega "Fanta Logista 26-27".

## Avvio

1. Assicurati di avere Python 3.9+ installato.
2. Nella cartella del progetto:
   ```
   pip install -r requirements.txt
   streamlit run app.py
   ```
3. Si aprirà automaticamente il browser su `http://localhost:8501`.

## Funzionalità

- **La mia rosa**: dashboard con crediti spesi/rimanenti, slot per ruolo,
  media punti attesa (con modificatore difesa) e calciatori acquistati.
- **Listone**: tabella filtrabile per ruolo, squadra, tier e nome; selezionando
  un calciatore puoi assegnarlo a "Roma Non Perdona" con il prezzo pagato,
  oppure segnarlo come comprato da un rivale.
- **Rivali**: aggiorna i crediti spesi da ciascuna delle 9 squadre avversarie.
- **Aggiorna Quotazioni**: carica un nuovo file "Quotazioni_Fantacalcio" ufficiale
  (.xlsx, stesso formato Fantacalcio.it) per aggiornare Qt.A/FVM/tier di tutti i
  calciatori, mantenendo rose e prezzi già assegnati. Usalo alla chiusura del
  mercato (1° settembre 2026) o a ogni nuova pubblicazione del listone.

## Persistenza dei dati

Ogni modifica (acquisti, budget rivali, aggiornamento quotazioni) viene salvata
automaticamente in `data/state.json`. Se elimini quel file, o premi
"Azzera asta" nella sidebar, l'app riparte dai dati iniziali in
`data/players_seed.json` e `data/rivals_seed.json`.

## Rigenerare i dati da un nuovo file Quotazioni da zero

Preferisci farlo direttamente dal tab **Aggiorna Quotazioni** dell'app. In
alternativa, sostituisci `data/players_seed.json` e cancella `data/state.json`.
