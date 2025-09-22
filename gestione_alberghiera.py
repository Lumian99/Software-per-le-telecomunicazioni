import dash  # framework per creare app web
from dash import dcc, html, Input, Output, State, dash_table, callback
import dash_bootstrap_components as dbc
import pandas as pd  # gestione e manipolazione dati
from datetime import datetime, timedelta
import uuid
import json  # salvare prenotazioni su file json e gestire file locale su os
import os

##############################################
## PARTE OOP (Backend)
#############################################
class Camera:  # classe entity(descrive la prenotazione) richiede parametri in ingresso
    def __init__(self, numero, tipo, capacita,prezzo_notte):  # definisco gli attributi della classe Camera (prezzo, tipologia ...)
        self.numero = numero
        self.tipo = tipo
        self.capacita = capacita
        self._prezzo_notte = prezzo_notte  # attributo privato
        self.disponibile = True

    @property  # decoratore che rende prezzo_notte accessibile come attributo tramite metodo (getter)
    def prezzo_notte(self):  # accedo usando il metodo come fosse un istanza
        return self._prezzo_notte  #################

    def __str__(self):  # metodo stringa senza parametri che restituisce un f string con numero e tipo
        return f"Camera {self.numero} ({self.tipo})"


    @classmethod  # riceve la classe stessa come parametro
    def crea_camera_mock(cls):
        return cls("101", "Singola", 1, 80)  # ritorna una nuova istanza della classe
        # metodo appartenente alla classe ,puo essere direttamente chiamato sulla classe, non serve creare l'istanza


class ServizioAggiuntivo:  # servizi extra, metodo appartenente all'istanza , prima di chiamarlo devo creare istanza
    def __init__(self, nome, prezzo):
        self.nome = nome
        self.prezzo = prezzo

    # metodo statico che non necessita dei dati della classe Camera (gli extra valgono indipendentemente dal tipo, prezzo ecc)
    @staticmethod
    def servizi_disponibili():
        return [
            ServizioAggiuntivo("Colazione", 15),
            ServizioAggiuntivo("Parcheggio", 8),
            ServizioAggiuntivo("SPA", 35),
            ServizioAggiuntivo("WiFi", 5),
            ServizioAggiuntivo("Piscina", 15)
        ]


class Prenotazione:#gestisce le informazioni relative a una singola prenotazione
    def __init__(self, nome, cognome, check_in, check_out, camera, servizi=None, ospiti=1):
        self.id = str(uuid.uuid4())[:8]  # associazione di ogni prenotazione a un id univoco con un codice alfa-numerico
        self.nome = nome
        self.cognome = cognome
        if isinstance(check_in, str):
            self.check_in = datetime.strptime(check_in, "%Y-%m-%d")
        else:
            # Se è già un oggetto date
            self.check_in = datetime.combine(check_in, datetime.min.time())

        if isinstance(check_out, str):
            self.check_out = datetime.strptime(check_out, "%Y-%m-%d")
        else:
            # Se è già un oggetto date
            self.check_out = datetime.combine(check_out, datetime.min.time())
        self.camera = camera
        self.servizi = servizi if servizi else []
        self.ospiti = ospiti

    def __str__(self):
        return f"{self.nome} {self.cognome} - Camera {self.camera.numero}"

    def descrizione(self):
        return f"Prenotazione di {self.nome} {self.cognome} in Camera {self.camera.numero}"

    def calcola_totale(self):
        giorni = (self.check_out - self.check_in).days
        if giorni <= 0:  # Evita prezzi negativi
            return 0
        totale_camera = giorni * self.camera.prezzo_notte
        totale_servizi = sum(s.prezzo for s in self.servizi) * giorni
        return totale_camera + totale_servizi


class PrenotazioneVip(Prenotazione): #classe PrenotazioneVip eredita da classe madre Prenotazione

    # Codice VIP fisso per semplicità
    cod_vip = "VIP2025"
    sconto_percentuale = 20  #20% di sconto

    def __init__(self, nome, cognome, check_in, check_out, camera, servizi=None, ospiti=1, codice_vip=""): #parametri vecchi piu nuovo param codice_vip
        # Chiamiamo il costruttore della classe madre
        super().__init__(nome, cognome, check_in, check_out, camera, servizi, ospiti) #con super posso accedere alla classe madre e ottengo tutti i suoi attributi
        self.codice_vip = codice_vip
        self.is_vip = self._verifica_codice_vip(codice_vip)  #self a dx perchè è un metodo e non una variabile e in ingresso prende il codice vip
        #self.is_vip = self._verifica_codice_vip("VIP2025")  restituisce true se codice corrisponde

    def _verifica_codice_vip(self, codice):
        return codice == self.cod_vip  #return true or false

    def calcola_totale(self):  # OVERRIDE del metodo della classe madre in questo caso calcolo applicando lo sconto

        totale_base = super().calcola_totale()  # Chiama il metodo della classe madre e chiamo metodo calcola_totale()

        if self.is_vip: #se codice corrisponde applico sconto 20%
            sconto = totale_base * (self.sconto_percentuale / 100)
            return totale_base - sconto #dopo aver calcolato nel solito modo applico sconto
        return totale_base

    def descrizione(self):  # OVERRIDE del metodo della classe madre

        desc_base = super().descrizione() #descrizione base prenotazione :Prenotazione di {self.nome} {self.cognome} in Camera {self.camera.numero}
        if self.is_vip:
            return f"{desc_base} [VIP - Sconto {self.sconto_percentuale}%]" #descrizione prenotazione scontata
        return desc_base

    def get_dettagli_sconto(self): #calcolo e mostro le differenti tariffe pre e post scontistica

        if self.is_vip:
            totale_senza_sconto = super().calcola_totale()
            totale_con_sconto = self.calcola_totale()
            sconto_applicato = totale_senza_sconto - totale_con_sconto
            return {
                'totale_originale': totale_senza_sconto,
                'sconto_applicato': sconto_applicato,
                'totale_finale': totale_con_sconto,
                'percentuale_sconto': self.sconto_percentuale
            }
        return None


class Albergo:  # classe madre che gestisce i vari parametri e file di salvataggio
    def __init__(self, nome):
        self.nome = nome  # nome albergo
        self.camere = []
        self.prenotazioni = []
        self.servizi = ServizioAggiuntivo.servizi_disponibili()
        self.file_dati = "gestione_alberghiera.json"
        self._crea_camere()  # creazione camere di diverso tipo
        self.carica_dati()  # Carica dati esistenti

    def _crea_camere(self):
        # Camere singole
        for i in range(101, 105):
            self.camere.append(Camera(str(i), "Singola", 1, 80))

        # Camere doppie
        for i in range(201, 205):
            self.camere.append(Camera(str(i), "Doppia", 2, 120))

        # Suite
        for i in range(301, 303):
            self.camere.append(Camera(str(i), "Suite", 4, 200))

    def elimina_prenotazione(self, prenotazione_id):  # verifica corrispondenza id ed elimina prenotazione

        for i, prenotazione in enumerate(self.prenotazioni):
            if prenotazione.id == prenotazione_id:
                self.prenotazioni.pop(i)  # cancella prenotazione i
                self.salva_dati()
                return True
        return False

    def trova_prenotazione(self, prenotazione_id):  # ricerca prenotazione in base all'id(per evitare omonimi)

        for prenotazione in self.prenotazioni:
            if prenotazione.id == prenotazione_id:
                return prenotazione
        return None

    def modifica_prenotazione(self, prenotazione_id, nuovi_dati):  # Modifica una prenotazione esistente

        prenotazione = self.trova_prenotazione(prenotazione_id)
        if not prenotazione:
            return False

        # Aggiorna i campi modificati
        if 'nome' in nuovi_dati:  # controllo nel diz se la chiave 'nome' è presente, in tal caso aggiorno con i nuovi dati
            prenotazione.nome = nuovi_dati['nome']
        if 'cognome' in nuovi_dati:
            prenotazione.cognome = nuovi_dati['cognome']
        if 'check_in' in nuovi_dati:
            prenotazione.check_in = datetime.combine(nuovi_dati['check_in'],datetime.min.time())  # creo una data combinata a orario 00:00
        if 'check_out' in nuovi_dati:
            prenotazione.check_out = datetime.combine(nuovi_dati['check_out'], datetime.min.time())
        if 'ospiti' in nuovi_dati:
            prenotazione.ospiti = nuovi_dati['ospiti']
        if 'servizi' in nuovi_dati:
            prenotazione.servizi = nuovi_dati['servizi']

        self.salva_dati()
        return True

    def salva_dati(self):  # salva prenotazioni in database json

        try:
            data = {
                "prenotazioni": [],  # diz con chiave "prenotazioni" che accede a una lista di dic"
                # "ultimo_aggiornamento": datetime.now().isoformat() #########
            }

            for p in self.prenotazioni:
                prenotazione_data = {
                    "id": p.id,
                    "nome": p.nome,
                    "cognome": p.cognome,
                    "check_in": p.check_in.isoformat(),  # formato ISO per file json
                    "check_out": p.check_out.isoformat(),
                    "camera_numero": p.camera.numero,
                    "camera_tipo": p.camera.tipo,
                    "camera_capacita": p.camera.capacita,
                    "camera_prezzo": p.camera.prezzo_notte,
                    "ospiti": p.ospiti,
                    "servizi": [{"nome": s.nome, "prezzo": s.prezzo} for s in p.servizi],
                    "is_vip": isinstance(p, PrenotazioneVip),#se p è istanza della classe Prenotazionevip
                    #prenotazione_vip = PrenotazioneVip("Luigi", "Verdi", "01/01/2025", "02/01/2025", camera, codice_vip="VIP2025") --> TRUE
                    "codice_vip": getattr(p, 'codice_vip', ''), #se p è PrenotazioneVip prendo l'attributo codice_vip (codice sconto )se no una str vuota
                    "vip_valid": getattr(p, 'is_vip', False) #se p è PrenotazioneVip prendo l'attributo is_vip (true) se no una str vuota
                }
                data["prenotazioni"].append(prenotazione_data)

            with open(self.file_dati, 'w',
                      encoding='utf-8') as f:  # apro file (f) in modalità scrittura con enable caratteri speciali
                json.dump(data, f, indent=2, ensure_ascii=False)  # scrivo i dati present in "data" su file "f"

            print(f" Dati salvati in {self.file_dati}")

        except Exception as e:
            print(f" Errore nel salvataggio: {e}")

    def carica_dati(self):

        try:
            if not os.path.exists(
                    self.file_dati):  # verifica che file json sia prensente nel os, nel caso non esista lo crea
                print(f" File {self.file_dati} non trovato, imposto nuovo database")
                return

            with open(self.file_dati, 'r', encoding='utf-8') as f:  # apro file json in mod lettura
                data = json.load(f)

            self.prenotazioni = []  # definisco nuova lista vuota prenotazioni prima di sovrascrivere da file json

            for p_data in data.get("prenotazioni",
                                   []):  # cerco nel diz data la chiave "prenotazioni se non esiste return lista vuota "
                # dizionario.get(chiave, valore_di_default)
                # Ricostruisce la camera
                camera = None
                for c in self.camere:
                    if c.numero == p_data[
                        "camera_numero"]:  # i dati salvati in json sono del tipo "camera_numero": 101, quindi quando
                        # devo verificare la loro presenza confronto il dato con le varie istanze di camera
                        camera = c
                        break

                if not camera:
                    # Se la camera non esiste più, la ricreo
                    camera = Camera(
                        p_data["camera_numero"],
                        p_data["camera_tipo"],
                        p_data["camera_capacita"],
                        p_data["camera_prezzo"]
                    )

                # Ricostruisce i servizi
                servizi = []
                for s_data in p_data.get("servizi", []):
                    servizi.append(ServizioAggiuntivo(s_data["nome"], s_data["prezzo"]))

                # NUOVO: Controlla se è una prenotazione VIP
                if p_data.get("is_vip", False):
                    prenotazione = PrenotazioneVip(
                        nome=p_data["nome"],
                        cognome=p_data["cognome"],
                        check_in=datetime.fromisoformat(p_data["check_in"]),
                        # ritorno a formato standard date-time orario da stringa ISO
                        check_out=datetime.fromisoformat(p_data["check_out"]),
                        camera=camera,
                        servizi=servizi,
                        ospiti=p_data["ospiti"],
                        codice_vip=p_data.get("codice_vip", "")
                    )
                else:
                    # Prenotazione normale
                    prenotazione = Prenotazione(
                        nome=p_data["nome"],
                        cognome=p_data["cognome"],
                        check_in=datetime.fromisoformat(p_data["check_in"]),
                        check_out=datetime.fromisoformat(p_data["check_out"]),
                        camera=camera,
                        servizi=servizi,
                        ospiti=p_data["ospiti"]
                    )
                prenotazione.id = p_data["id"]  # Mantieni l'ID originale

                self.prenotazioni.append(prenotazione)

            print(
                f" Caricate {len(self.prenotazioni)} prenotazioni da {self.file_dati}")  # info del numero di prenotazioni caricate

        except Exception as e:  # eccezione nominata con lettera e
            print(f" Errore nel caricamento: {e}")
            print("Partendo con dati vuoti...")
            self.prenotazioni = []

    def aggiungi_prenotazione(self, prenotazione):
        self.prenotazioni.append(prenotazione)
        self.salva_dati()  # Salva automaticamente dopo ogni aggiunta
        return prenotazione

    def trova_camere_disponibili(self, check_in, check_out):
        try:
            ci = datetime.strptime(check_in,
                                   "%Y-%m-%d")  # converto stringa in formato datetime che mi interessa [giorno-mese-anno]
            co = datetime.strptime(check_out, "%Y-%m-%d")
        except ValueError:
            return []

        camere_disponibili = []
        for camera in self.camere:
            disponibile = True
            for prenotazione in self.prenotazioni:
                if prenotazione.camera == camera:
                    if (
                            ci < prenotazione.check_out and co > prenotazione.check_in):  # controllo sovrapposizione di date
                        disponibile = False
                        break
            if disponibile:
                camere_disponibili.append(camera)  # se disponibile aggiungo camera
        return camere_disponibili

    def calcola_incasso(self, inizio=None, fine=None):
        totale = 0
        for prenotazione in self.prenotazioni:
            try:
                # solo la parte della data (no orario)
                inizio_dt = None
                fine_dt = None
                # non mi serve l'orario per calcolare gli incassi
                if inizio:
                    inizio_clean = str(inizio).split('T')[0]  # 2025-08-21T15:30:00" split in due parti separate dalla T e poi prendo elem [0] cioe data
                    inizio_dt = datetime.strptime(inizio_clean, "%Y-%m-%d")

                if fine:
                    fine_clean = str(fine).split('T')[0]
                    fine_dt = datetime.strptime(fine_clean, "%Y-%m-%d")

                # Controlla se la prenotazione rientra nel periodo
                if (not inizio_dt or prenotazione.check_in >= inizio_dt) and (not fine_dt or prenotazione.check_out <= fine_dt):
                    totale += prenotazione.calcola_totale()

            except (ValueError, AttributeError) as e:
                # In caso di errore di parsing, salta questa prenotazione
                print(f"Errore parsing date per prenotazione {prenotazione.id}: {e}")
                continue

        return totale

    def calcola_ricavo_netto(self, inizio=None, fine=None, costi_gestione_giornalieri=None):

        incasso_lordo = self.calcola_incasso(inizio, fine)  # Calcola incasso lordo

        # Calcola giorni del periodo
        try:
            if inizio and fine:
                inizio_clean = str(inizio).split('T')[0] # 2025-08-21T15:30:00" split in due parti separate dalla T e poi prendo elem [0] cioe data
                fine_clean = str(fine).split('T')[0]
                inizio_dt = datetime.strptime(inizio_clean, "%Y-%m-%d")
                fine_dt = datetime.strptime(fine_clean, "%Y-%m-%d")
                giorni = (fine_dt - inizio_dt).days + 1
            else:
                giorni = 1
        except:
            giorni = 1

        costi_totali = (costi_gestione_giornalieri or 0) * giorni  # Calcola costi totali
        ricavo_netto = incasso_lordo - costi_totali  # Calcola ricavo netto

        return {
            'incasso': incasso_lordo,
            'costi': costi_totali,
            'ricavo_netto': ricavo_netto,
            'giorni': giorni,
            'margine_percentuale': (ricavo_netto / incasso_lordo * 100) if incasso_lordo > 0 else 0
        }  # ritorno valori calcolati di incassi

    def conta_camere_per_tipo(self, check_in, check_out, num_ospiti=1):

        camere_disponibili = self.trova_camere_disponibili(check_in, check_out)
        camere_filtrate = [c for c in camere_disponibili if
                           c.capacita >= num_ospiti]  # counter c caricato in camere filtrate per ogni camera valida

        # Conta per tipo
        conteggio = {}  # diz {tipo_camera: numero_disponibili}
        for camera in camere_filtrate:
            if camera.tipo not in conteggio:  # controlla se la chiave cameratipo è presente in conteggio
                conteggio[camera.tipo] = 0  # se non c'e il contatore conteggio[1/2/4] = 0
            conteggio[camera.tipo] += 1  # incrementa contatore conteggio

        return conteggio  # es: {'singola': 1, 'doppia': 2, 'suite': 1}

    def trova_camere_con_dettagli(self, check_in, check_out, num_ospiti=1):

        try:
            ci = datetime.strptime(check_in, "%Y-%m-%d")
            co = datetime.strptime(check_out, "%Y-%m-%d")
        except ValueError:
            return []  # lista vuota

        # Ottieni conteggio camere per tipo
        conteggio_tipi = self.conta_camere_per_tipo(check_in, check_out, num_ospiti)

        risultati = []

        for camera in self.camere:
            if camera.capacita < num_ospiti:
                # Camera troppo piccola, stampo messaggio
                risultati.append({
                    'camera': camera,
                    'disponibile': False,
                    'motivo': f'capacità insufficiente (max {camera.capacita} ospiti)',
                    'conteggio_tipo': 0
                })
                continue

            # Controlla conflitti con prenotazioni esistenti
            conflitti = []
            for prenotazione in self.prenotazioni:
                if prenotazione.camera == camera:
                    if (ci < prenotazione.check_out and co > prenotazione.check_in):
                        conflitti.append(prenotazione)  # riga 220 per info su dati PRENOTAZIONE,

            if not conflitti:
                # Camera completamente libera
                risultati.append({
                    'camera': camera,
                    'disponibile': True,
                    'motivo': 'disponibile',
                    'conteggio_tipo': conteggio_tipi.get(camera.tipo, 0)
                    # conteggio_tipi = {'singola': 2, 'doppia': 3, 'suite': 1}. camera.tipo(singola,doppia..) o 0
                })
            else:
                # Camera occupata, trova quando si libera
                pros_libera = max(p.check_out for p in
                                  conflitti)  # estraggo dalla lista conflitti tutti i check_out es[30/04, 12/05] e ne prendo il max
                risultati.append({
                    'camera': camera,
                    'disponibile': False,
                    'motivo': f'occupata fino al {pros_libera.strftime("%d-%m-%Y")}, libera dal {(pros_libera).strftime("%d-%m-%Y")}',
                    'conteggio_tipo': 0
                })

        return risultati

    def verifica_disponibilita_per_modifica(self, prenotazione_da_modificare, nuova_check_in,
                                            nuova_check_out):  # IMPORTANTE!!!

        try:
            # Se sono stringhe, le parsiamo prima ,isistance controlla un oggetto se è di un tipo definito da user
            if isinstance(nuova_check_in, str): #nuova_check_in è di tipo str ? se si converto in datatime
                nuova_check_in = datetime.strptime(nuova_check_in, "%Y-%m-%d").date()
            elif isinstance(nuova_check_in, datetime):
                nuova_check_in = nuova_check_in.date()

            if isinstance(nuova_check_out, str):
                nuova_check_out = datetime.strptime(nuova_check_out, "%Y-%m-%d").date()
            elif isinstance(nuova_check_out, datetime):
                nuova_check_out = nuova_check_out.date()

            # Ora combiniamo con l'orario 00:00
            ci = datetime.combine(nuova_check_in, datetime.min.time())
            co = datetime.combine(nuova_check_out, datetime.min.time())

        except (ValueError, TypeError):
            return False, "Date non valide"

        if ci >= co:
            return False, "La data di check-out deve essere successiva al check-in"

        camera = prenotazione_da_modificare.camera  # riga 207

        # Controlla conflitti con altre prenotazioni (escludendo quella che stiamo modificando)
        for prenotazione in self.prenotazioni:
            if prenotazione.id == prenotazione_da_modificare.id:
                continue  # Salta la prenotazione che stiamo modificando

            if prenotazione.camera == camera:
                if (ci < prenotazione.check_out and co > prenotazione.check_in):
                    return False, f"Camera occupata da {prenotazione.nome} {prenotazione.cognome} dal {prenotazione.check_in.strftime('%d-%m-%Y')} al {prenotazione.check_out.strftime('%d-%m-%Y')}"

        return True, "Camera disponibile"

################################################################################################################################################################
############################################## TERMINE PARTE OOP ################################################################################################
################################################################################################################################################################

# INIZIALIZZAZIONE APP

albergo = Albergo("Albergo Software")
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)#dash e bootstrap per creare un sito in CSS e HTML
app.title = "Albergo Software"

########################################################
## LAYOUT WEB APP
########################################################
app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Albergo Software", className="text-center my-4"))), #my-4 è il margine verticale da sopra e sotto

    dbc.Tabs([ #creo gruppo di schede cliccabili (3 tab)
        dbc.Tab(label="Nuova Prenotazione", tab_id="tab-nuova"),#label è il testo fisso, tab_id identificatore scheda attivabile con i callback
        dbc.Tab(label="Prenotazioni Esistenti", tab_id="tab-lista"),
        dbc.Tab(label="Statistiche", tab_id="tab-stat")
    ], id="tabs", active_tab="tab-nuova"),#id="tabs" → ID del componente Tabs, per collegarlo ai callback

 # html.Div contenitore inizalmente vuoto, quando si attiva il callback di uno dei 3 tab
    html.Div(id="tab-content", className="p-4") #pannello dove appare il contenuto delle tab,
], fluid=True) #per adattarsi alla dim dello schermo
 #p-4 padding per rendere il layout piu centrato e non attaccato ai bordi

########################################################
## LAYOUT PRIMA TAB (NUOVA PRENOTAZIONE)
########################################################
def nuova_prenotazione_layout():
    # Crea opzioni con prezzi visibili per i servizi aggiuntivi
    servizi_opzioni = [
        {"label": f"{s.nome} - €{s.prezzo}/giorno", "value": s.nome}
        for s in albergo.servizi
    ]

    # PARTE RELATIVA A INSERIMENTO NOME E COGNOME
    return dbc.Card([ #card visualizzabile nella prima tab prenotazioni
        dbc.CardHeader("Nuova Prenotazione"),
        dbc.CardBody([
            dbc.Row([# griglia responsiva per gestire 12 colonne per ogni riga e adattarsi in automatico
                dbc.Col(dbc.Input(id="nome", placeholder="Nome", type="text"), md=6),# input di testo "nome" largo 6/12 colonne
                dbc.Col(dbc.Input(id="cognome", placeholder="Cognome", type="text"), md=6)
            ], className="mb-3"),#margine inf per separare i vari componenti testuali

            dbc.Row([ #PARTE RELATIVA A SELEZIONE DATA
                dbc.Col(dcc.DatePickerSingle(id="check-in", display_format='DD-MM-YYYY', date=datetime.today().date(),first_day_of_week=1),md=4),
                dbc.Col(dcc.DatePickerSingle(id="check-out", display_format='DD-MM-YYYY',date=(datetime.today() + timedelta(days=1)).date(), first_day_of_week=1),md=4),
                dbc.Col(dbc.Input(id="ospiti", type="number", min=1, value=1), md=4)#selettore ospiti incrementabile di 1 fino a 4
            ], className="mb-3"),
            #seleziona data check in e check out, DatePickerSingle genera un calendario pop-up cliccabile

            dbc.Row([ #PARTE RELATIVA A PULSANTE CODICE VIP
                dbc.Col([
                    dbc.Label("Codice VIP (opzionale)"),
                    dbc.Input(id="codice-vip", placeholder="Inserisci codice VIP per sconto 20%", type="text"),
                    html.Small("Suggerimento: prova 'VIP2025'", className="text-muted")], md=12)], className="mb-3"),#className applica stili CSS , in questo caso ho un testo piu trasparente

            dbc.Row([#PARTE RELATIVA A SERVIZI AGGIUNTIVI E VERIFICA DISPONIBILITA PRENOTAZ.
                dbc.Col([
                    dbc.Label("Servizi aggiuntivi (prezzi al giorno)"),
                    dcc.Dropdown(id="servizi", options=servizi_opzioni, multi=True)], md=8),#menu a tendina in cui si puo selez. piu scelte
                dbc.Col(dbc.Button("Verifica Disponibilità", id="btn-disponibilita", color="primary"), md=4)
            ], className="mb-3"),

            # Anteprima costo servizi selezionati
            html.Div(id="anteprima-servizi", className="mb-3"),#creo contenitore dei servizi
            html.Div(id="camere-disponibili", className="mb-3"), #pagina in cui compariranno camere vuote dopo callback
            dbc.Select(id="selezione-camera", options=[], style={"display": "none"}),#menu a tendina inizialmente vuoto,le camere sono disp dopo verifica disponibilita
            dbc.Button("Conferma Prenotazione", id="btn-conferma", color="success", disabled=True),#pulsante conferma inizialmente disattivo
            html.Div(id="output-conferma", className="mt-3")#messaggio dinamico di corretta/errata prenotazione
        ])
    ])

########################################################
## LAYOUT SECONDA TAB (PRENOTAZIONI ESISTENTI)
########################################################
def lista_prenotazioni_layout():
    if not albergo.prenotazioni:
        return dbc.Alert(
            "Nessuna prenotazione trovata. Le prenotazioni vengono salvate automaticamente in 'gestione_alberghiera.json'",
            color="info")

    # Crea DataFrame con pulsanti
    prenotazioni_data = []
    for p in albergo.prenotazioni:
        status_vip = ""
        totale = p.calcola_totale()

        if isinstance(p, PrenotazioneVip) and p.is_vip: #verifica se prenotazione è tipo vip
            dettagli = p.get_dettagli_sconto() #se l’oggetto p è di tipo PrenotazioneVip e p di tipo vip chiama un metodo dell’oggetto PrenotazioneVip per ottenere i dettagli dello sconto
            status_vip = f" (-€{dettagli['sconto_applicato']:.0f})" # es (-50€)

        prenotazioni_data.append({
            "ID": p.id[:8],
            "Cliente": f"{p.nome} {p.cognome}",
            "Camera": p.camera.numero,
            "Tipo": p.camera.tipo,
            "Check-in": p.check_in.strftime("%d-%m-%Y"),
            "Check-out": p.check_out.strftime("%d-%m-%Y"),
            "Ospiti": p.ospiti,
            "Servizi": len(p.servizi),
            "Status": "VIP" if isinstance(p, PrenotazioneVip) and p.is_vip else "Standard",
            "Totale": f"€{totale}{status_vip}",
            "Azioni": p.id  # ID completo [vecchia implementazione quando avevo id a 16 cifre]  aggiunto qui solo per uso interno
        })

    return dbc.Card([#PARTE RELATIVA A TESTO PRENOTAZIONI ESISTENTI
        dbc.CardHeader(f"Prenotazioni Esistenti ({len(albergo.prenotazioni)} totali)"),
        dbc.CardBody([

            # Tabella prenotazioni
            dash_table.DataTable(
                id='tabella-prenotazioni',
                columns=[{"name": col, "id": col} for col in prenotazioni_data[0].keys() if col != "Azioni"],# prendo elementi [0] per creare struttura gli altri pren sono uguali
                #prende le chiavi da prenotazione:["ID", "Cliente", "Camera", "Azioni"] esclusa azione
                data=[{k: v for k, v in row.items() if k != "Azioni"} for row in prenotazioni_data],# prende i dati delle prenotazioni pronti per essere visualizzati nella tabella, escludendo  "Azioni"
                filter_action='native', #possibilità di filtraggio
                page_action='native',
                page_size=10, #10 righe per pagina
                style_table={'overflowX': 'auto'}, #adatta tabella a schermo
                style_cell={'textAlign': 'left', 'padding': '10px'},#allineamento testo e distanza da i bordi
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                row_selectable='single',  # Permette selezione singola riga
                selected_rows=[]
            ),

            html.Hr(),

            # Pulsanti azioni
            dbc.Row([
                dbc.Col([
                    dbc.Button(" Modifica Selezionata", id="btn-modifica", color="warning", className="me-2"),
                    dbc.Button(" Elimina Selezionata", id="btn-elimina", color="danger"),
                ], md=6),
                dbc.Col([
                    html.Div(id="info-selezione", className="text-muted")
                ], md=6)
            ], className="mt-3"),

            # Area messaggi
            html.Div(id="messaggio-azioni", className="mt-3"),

            # Modal per modifica (nascosto inizialmente)
            dbc.Modal([
                dbc.ModalHeader("Modifica Prenotazione"),
                dbc.ModalBody(id="modal-body-modifica"),
                dbc.ModalFooter([
                    dbc.Button("Annulla", id="btn-annulla-modifica", color="secondary"),
                    dbc.Button("Salva Modifiche", id="btn-salva-modifica", color="primary")
                ])
            ], id="modal-modifica", is_open=False, size="lg")
        ])
    ])

########################################################
## LAYOUT TERZA TAB (STATISTICHE,INCASSI E RICAVI)
########################################################
def statistiche_layout():
    return dbc.Card([
        dbc.CardHeader("Statistiche, Incassi e Ricavi"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(dcc.DatePickerRange(
                    id='date-range',
                    display_format='DD-MM-YYYY',
                    min_date_allowed=datetime(2025, 8, 1),
                    max_date_allowed=datetime(2025, 12, 31),
                    start_date=datetime.today() - timedelta(days=30),
                    end_date=datetime.today(),
                    first_day_of_week=1
                ), md=6),
                dbc.Col([
                    dbc.Label("Costi gestione giornalieri (€)"),
                    dbc.Input(id="costi-gestione", type="number", min=0, value=150, step=10) #simulatore costi gestione e ricavi in un periodo
                ], md=3),
                dbc.Col(dbc.Button("Calcola Ricavi", id="btn-calcola", color="primary", className="mt-4"), md=3)
            ], className="mb-3"),

            # Risultati finanziari
            html.Div(id="risultato-calcolo", className="mb-4"), #contenitore dinamico

            html.Hr(),#linea di separazione

            # Statistiche camere e servizi LISTA STATICA
            dbc.Row([
                dbc.Col([
                    html.H5(" Riepilogo Camere"),
                    html.Div(id="riepilogo-camere")
                ], md=6),
                dbc.Col([
                    html.H5(" Listino Servizi"),
                    html.Div([
                        dbc.ListGroup([
                            dbc.ListGroupItem([
                                html.Strong(f"{servizio.nome}: "),
                                f"€{servizio.prezzo}/giorno"
                            ]) for servizio in albergo.servizi
                        ])
                    ])
                ], md=6)
            ])
        ])
    ])


########################################################
## CALLBACKS
########################################################
# Callback per gestire i tab
@app.callback( # decoratore che collega funzione a componenti dell'interfaccia
    Output("tab-content", "children"), #Output: contenuto di "tab-content" viene aggiornato con il nuovo layout
    [Input("tabs", "active_tab")] #Quando la proprietà active_tab del componente con id tabs cambia, esegui questa funzione"
    #L'utente clicca su "Nuova Prenotazione" -> active_tab diventa "tab-nuova"
    #L'utente clicca su "Prenotazioni Esistenti" -> active_tab diventa "tab-lista"
    #L'utente clicca su "Statistiche" -> active_tab diventa "tab-stat"
)
def render_tab_content(active_tab): #funzione che riceve quale tab è attiva
    if active_tab == "tab-nuova":
        return nuova_prenotazione_layout() #restituisce layout della prima tab
    elif active_tab == "tab-lista":
        return lista_prenotazioni_layout() #restituisce layout della seconda tab
    elif active_tab == "tab-stat":
        return statistiche_layout() #restituisce layout della terza tab
    return html.P("Seleziona una scheda") #messaggio di default


# Callback per verificare disponibilità delle camere
@app.callback(
    [Output("camere-disponibili", "children"), # aggiorna contenuto di camere disponibili
     Output("btn-conferma", "disabled")], #disabilita pulsante conferma
    [Input("btn-disponibilita", "n_clicks")],
    [State("check-in", "date"), #stato attuale del campo check-in
     State("check-out", "date"),
     State("ospiti", "value")]
)
def verifica_disponibilita(n_clicks, check_in, check_out, ospiti):
    if not n_clicks:
        return "", True

    if not check_in or not check_out or not ospiti: #validazione campi obbligatori
        return dbc.Alert("Compila tutti i campi prima di verificare la disponibilità", color="warning"), True #messaggio di avviso

    #ottenere info complete su ogni camera
    dettagli_camere = albergo.trova_camere_con_dettagli(check_in, check_out, ospiti)

    #Separa camere disponibili da quelle non disponibili
    camere_disponibili = [d for d in dettagli_camere if d['disponibile']]
    camere_non_disponibili = [d for d in dettagli_camere if not d['disponibile']]

    if camere_disponibili:

        options = []
        for idx, dettaglio in enumerate(camere_disponibili): #idx indice e dettaglio camera
            camera = dettaglio['camera'] #estrae oggetto camera dal dizionario dettaglio
            conteggio = dettaglio['conteggio_tipo'] #numero di camere dello stesso tipo disponibili

            #Crea etichetta descrittiva con tutte le info della camera
            label = f"{camera.tipo} - Camera {camera.numero} - €{camera.prezzo_notte}/notte - max {camera.capacita} ospiti - ({camera.tipo}e disponibili: {conteggio})"
            #Usa l'ID univoco della camera invece dell'indice per evitare errori
            options.append({"label": label, "value": camera.numero})


        messaggio_parti = [f" Trovate {len(camere_disponibili)} camere disponibili"] #DISPONIBILITA CAMERE

        if camere_non_disponibili:#messaggio camere non disponibili
            messaggio_parti.append("\n X Camere non disponibili:")
            for dettaglio in camere_non_disponibili:
                camera = dettaglio['camera']
                messaggio_parti.append(f" {camera.tipo} (Camera {camera.numero}): {dettaglio['motivo']}") #STAMPA CAMERA NON DISPONIBILE E DATA

        messaggio_completo = "\n".join(messaggio_parti) # unisce lista stringhe con join in un unica stringa

        return [
            dbc.Alert(messaggio_completo, color="success", style={"white-space": "pre-line"}), #stampa su app lista con camere disponibili e non
            dbc.Select(id="selezione-camera", options=options, placeholder="Seleziona una camera") #selezione camera tra le disponibili
        ], False #per usare bottone conferma

    else:
        # Nessuna camera disponibile
        messaggio_parti = [" Nessuna camera disponibile per il periodo richiesto:"]

        for dettaglio in camere_non_disponibili:
            camera = dettaglio['camera']
            messaggio_parti.append(f" {camera.tipo} (Camera {camera.numero}): {dettaglio['motivo']}")

        messaggio_completo = "\n".join(messaggio_parti)#lista camere non disponbili, non si potra proseguire con la prenotazione

        return dbc.Alert(messaggio_completo, color="danger", style={"white-space": "pre-line"}), True # True = pulsante disabilitato


# Callback per confermare la prenotazione
@app.callback(
    Output("output-conferma", "children"), #area dove compare messaggio di conferma
    [Input("btn-conferma", "n_clicks")],
    [State("nome", "value"), #tutti i dati  vengono presi come State (stato attuale)
     State("cognome", "value"),
     State("check-in", "date"),
     State("check-out", "date"),
     State("ospiti", "value"),
     State("servizi", "value"), #lista servizi selezionati
     State("selezione-camera", "value"), #numero camera selezionata
     State("codice-vip", "value")]  #codice sconto inserito dall'utente
)
def conferma_prenotazione(n_clicks, nome, cognome, check_in, check_out, ospiti, servizi_selez, numero_camera,
                          codice_vip):
    if not n_clicks or numero_camera is None:
        return ""

    # Trova camera corrispondente al numero selezionato
    camera_selezionata = None
    for camera in albergo.camere:
        if camera.numero == numero_camera: # confronto numero camera
            camera_selezionata = camera
            break

    if not camera_selezionata: # gestione errore camera non trovata
        return dbc.Alert("Errore: camera non trovata", color="danger")

    # Converte nomi servizi selezionati in oggetti ServizioAggiuntivo
    servizi = [s for s in albergo.servizi if s.nome in servizi_selez] if servizi_selez else []
    #Se il suo nome è nella lista scelta dall’utente (servizi_selez), allora lo includo nella nuova lista servizi.

    # Controlla se c'è un codice VIP valido
    if codice_vip and codice_vip.strip(): # strip() rimuove spazi vuoti
        # Crea PrenotazioneVip con tutti i parametri
        prenotazione = PrenotazioneVip(
            nome=nome,
            cognome=cognome,
            check_in=check_in,
            check_out=check_out,
            camera=camera_selezionata,
            servizi=servizi,
            ospiti=ospiti,
            codice_vip=codice_vip.strip()
        )

        if prenotazione.is_vip:

            dettagli_sconto = prenotazione.get_dettagli_sconto() #metodo che calcola importi sconto
            albergo.aggiungi_prenotazione(prenotazione) # salva prenotazione

            # Messaggio di successo con dettagli dello sconto applicato
            return dbc.Alert([
                html.H5("Prenotazione VIP confermata!", className="alert-heading"),
                html.P(f"Totale originale: €{dettagli_sconto['totale_originale']:.2f}"),
                html.P(
                    f"Sconto VIP ({dettagli_sconto['percentuale_sconto']}%): -€{dettagli_sconto['sconto_applicato']:.2f}",
                    className="text-success"),
                html.P(f"Totale finale: €{dettagli_sconto['totale_finale']:.2f}",
                       className="fw-bold"),
                html.Hr(), #linea orizzontale separatrice
                html.P("Dati salvati automaticamente", className="mb-0")
            ], color="success")
        else:
            #Codice non valido - crea prenotazione normale invece di VIP
            prenotazione_normale = Prenotazione(
                nome=nome,
                cognome=cognome,
                check_in=check_in,
                check_out=check_out,
                camera=camera_selezionata,
                servizi=servizi,
                ospiti=ospiti
            )
            albergo.aggiungi_prenotazione(prenotazione_normale)

            #Avviso che il codice VIP non è valido
            return dbc.Alert([
                html.H5("Codice VIP non valido", className="alert-heading"),
                html.P("Prenotazione creata senza sconto"),
                html.P(f"Totale: €{prenotazione_normale.calcola_totale()}"),
                html.Hr(),
                html.P("Dati salvati automaticamente", className="mb-0")
            ], color="warning")
    else:
        # Nessun codice VIP inserito - prenotazione standard
        prenotazione = Prenotazione(
            nome=nome,
            cognome=cognome,
            check_in=check_in,
            check_out=check_out,
            camera=camera_selezionata,
            servizi=servizi,
            ospiti=ospiti
        )

        albergo.aggiungi_prenotazione(prenotazione)
        return dbc.Alert([
            html.H5("Prenotazione confermata!", className="alert-heading"),
            html.P(f"Totale: €{prenotazione.calcola_totale()}"),
            html.Hr(),
            html.P("Dati salvati automaticamente", className="mb-0")
        ], color="success")

# Callback per calcolo ricavi e riepilogo camere
@app.callback(
    [Output("risultato-calcolo", "children"), #risultati finanziari
     Output("riepilogo-camere", "children")], #riepilogo tipologie camere
    [Input("btn-calcola", "n_clicks")], #pulsante calcola
    [State("date-range", "start_date"), # date per periodo di analisi
     State("date-range", "end_date"),
     State("costi-gestione", "value")] # stima costi per calcolo ricavi
)
def calcola_ricavo_completo(n_clicks, start_date, end_date, costi_gestione):
    if not n_clicks:
        risultato_msg = dbc.Alert("Imposta le date e i costi, poi clicca 'Calcola Ricavi'", color="info")
    else:
        # Usa il metodo della classe Albergo per calcolare ricavi netti
        risultati = albergo.calcola_ricavo_netto(start_date, end_date, costi_gestione)

        #Crea risultati organizzati in 4 colonne
        risultato_msg = dbc.Card([
            dbc.CardBody([
                dbc.Row([ #griglia responsive con 4 colonne uguali
                    dbc.Col([
                        html.H6(" Incasso Lordo"), # intestazione piccola
                        html.H4(f"€{risultati['incasso']:.2f}", className="text-success") #verde
                    ], md=3), # 3/12 colonne
                    dbc.Col([
                        html.H6(" Costi Gestione"),
                        html.H4(f"€{risultati['costi']:.2f}", className="text-warning"), # arancione
                        html.Small(f"({risultati['giorni']} giorni × €{costi_gestione or 0}/giorno)") # dettaglio calcolo
                    ], md=3),
                    dbc.Col([
                        html.H6(" Ricavo Netto"),
                        # Colore condizionale: verde se positivo, rosso se negativo
                        html.H4(f"€{risultati['ricavo_netto']:.2f}",
                                className="text-success" if risultati['ricavo_netto'] >= 0 else "text-danger")
                    ], md=3),
                    dbc.Col([
                        html.H6(" Margine"),
                        html.H4(f"{risultati['margine_percentuale']:.1f}%",
                                className="text-info") # blu
                    ], md=3)
                ])
            ])
        ], color="light") #sfondo grigio chiaro

    # Statistiche camere raggruppate per tipo (parte sempre eseguita)
    camere_per_tipo = {} #diz
    for camera in albergo.camere:
        if camera.tipo not in camere_per_tipo: #se tipo non esiste nel dizionario
            camere_per_tipo[camera.tipo] = [] #crea lista vuota
        camere_per_tipo[camera.tipo].append(camera) #aggiunge camera alla lista del suo tipo

    #Crea lista di elementi Bootstrap per ogni tipo di camera
    riepilogo_items = []
    for tipo, camere_lista in camere_per_tipo.items(): #itera su coppie chiave-valore
        prezzo = camere_lista[0].prezzo_notte #tutte le camere dello stesso tipo hanno stesso prezzo
        riepilogo_items.append(
            dbc.ListGroupItem([
                html.Strong(f"{tipo}: "), #nome tipo in grassetto
                f"{len(camere_lista)} camere disponibili - €{prezzo}/notte" #count e prezzo
            ])
        )

    riepilogo = dbc.ListGroup(riepilogo_items) # componente lista tipologie di camere

    return risultato_msg, riepilogo


# Callback per gestire selezione righe nella tabella prenotazioni
@app.callback(
    [Output("info-selezione", "children"),
     Output("btn-modifica", "disabled"), #pulsante modifica
     Output("btn-elimina", "disabled")], #pulsante elimina
    [Input("tabella-prenotazioni", "selected_rows")]
)
def aggiorna_selezione(selected_rows): #MODIFICA O ELIMINA prenotazione
    if not selected_rows:
        return "Seleziona una prenotazione per modificarla o eliminarla", True, True #pulsanti disabilitati

    row_index = selected_rows[0] #indice della riga selezionata (lista con un elemento)
    prenotazione = albergo.prenotazioni[row_index] #oggetto prenotazione corrispondente
    info = f"Selezionata: {prenotazione.nome} {prenotazione.cognome} - Camera {prenotazione.camera.numero}"

    return info, False, False #


# Callback per eliminare prenotazione selezionata
@app.callback(
    [Output("messaggio-azioni", "children"), #area messaggi di conferma/errore
     Output("tabella-prenotazioni", "data")], #aggiorna dati tabella dopo eliminazione
    [Input("btn-elimina", "n_clicks")], #click pulsante elimina
    [State("tabella-prenotazioni", "selected_rows")] #riga attualmente selezionata
)
def elimina_prenotazione(n_clicks, selected_rows):
    if not n_clicks or not selected_rows:
        # Aggiorna comunque i dati della tabella anche se non c'è stata eliminazione
        prenotazioni_data = []
        for p in albergo.prenotazioni: # ricostruisce dati tabella da zero
            status_vip = ""
            totale = p.calcola_totale()

            # Controlla se è prenotazione VIP per aggiungere info sconto
            if isinstance(p, PrenotazioneVip) and p.is_vip:
                dettagli = p.get_dettagli_sconto()
                status_vip = f" (-€{dettagli['sconto_applicato']:.0f})" # sconto arrotondato

            # Crea dizionario con tutti i dati per una riga della tabella
            prenotazioni_data.append({
                "ID": p.id[:8],
                "Cliente": f"{p.nome} {p.cognome}",
                "Camera": p.camera.numero,
                "Tipo": p.camera.tipo,
                "Check-in": p.check_in.strftime("%d-%m-%Y"),
                "Check-out": p.check_out.strftime("%d-%m-%Y"),
                "Ospiti": p.ospiti,
                "Servizi": len(p.servizi), #numero di servizi aggiunti
                "Status": "VIP" if isinstance(p, PrenotazioneVip) and p.is_vip else "Standard",
                "Totale": f"€{totale}{status_vip}" #prezzo con eventuale indicazione sconto
            })
        return "", prenotazioni_data #messaggio vuoto e dati aggiornati

    #Procedura di eliminazione vera e propria
    row_index = selected_rows[0]
    prenotazione = albergo.prenotazioni[row_index]
    prenotazione_id = prenotazione.id #ID univoco per eliminazione sicura
    cliente = f"{prenotazione.nome} {prenotazione.cognome}" #nome per messaggio

    #Chiama metodo di eliminazione della classe Albergo
    if albergo.elimina_prenotazione(prenotazione_id):
        messaggio = dbc.Alert(f" Prenotazione di {cliente} eliminata con successo", color="success")
    else:
        messaggio = dbc.Alert(" Errore durante l'eliminazione", color="danger")

    #Ricostruisce dati tabella dopo eliminazione (stesso codice di sopra)
    prenotazioni_data = []
    for p in albergo.prenotazioni:
        status_vip = ""
        totale = p.calcola_totale()

        if isinstance(p, PrenotazioneVip) and p.is_vip:
            dettagli = p.get_dettagli_sconto()
            status_vip = f" (-€{dettagli['sconto_applicato']:.0f})"

        prenotazioni_data.append({
            "ID": p.id[:8],
            "Cliente": f"{p.nome} {p.cognome}",
            "Camera": p.camera.numero,
            "Tipo": p.camera.tipo,
            "Check-in": p.check_in.strftime("%d-%m-%Y"),
            "Check-out": p.check_out.strftime("%d-%m-%Y"),
            "Ospiti": p.ospiti,
            "Servizi": len(p.servizi),
            "Status": "VIP" if isinstance(p, PrenotazioneVip) and p.is_vip else "Standard",
            "Totale": f"€{totale}{status_vip}"
        })

    return messaggio, prenotazioni_data


# Callback per aprire/chiudere finestra di modifica
@app.callback(
    [Output("modal-modifica", "is_open"), #controlla visibilità
     Output("modal-body-modifica", "children")], #contenuto del corpo
    [Input("btn-modifica", "n_clicks"), #apertura mod
     Input("btn-annulla-modifica", "n_clicks")], #chiusura
    [State("tabella-prenotazioni", "selected_rows"), #riga selezionata
     State("modal-modifica", "is_open")] #stato attuale
)
def gestisci_modal_modifica(n_clicks_modifica, n_clicks_annulla, selected_rows, is_open):
    ctx = dash.callback_context #contesto per identificare quale componente ha attivato il callback
    if not ctx.triggered: #se callback non è stato attivato da nessun componente
        return False, []

    #Estrae l'ID del componente che ha causato il callback
    button_id = ctx.triggered[0]["prop_id"].split(".")[0] # es: "btn-modifica.n_clicks" -> "btn-modifica"

    if button_id == "btn-modifica" and n_clicks_modifica and selected_rows:
        row_index = selected_rows[0]
        prenotazione = albergo.prenotazioni[row_index]

        #Crea opzioni per servizi con nomi dei servizi disponibili
        servizi_opzioni = [{"label": s.nome, "value": s.nome} for s in albergo.servizi]
        servizi_selezionati = [s.nome for s in prenotazione.servizi] #servizi già selezionati

        # Costruisce form di modifica pre-compilato con dati attuali
        modal_content = [
            dbc.Row([
                dbc.Col([
                    dbc.Label("Nome"),
                    dbc.Input(id="edit-nome", value=prenotazione.nome) # campo pre-compilato
                ], md=6),
                dbc.Col([
                    dbc.Label("Cognome"),
                    dbc.Input(id="edit-cognome", value=prenotazione.cognome)
                ], md=6)
            ], className="mb-3"),

            dbc.Row([
                dbc.Col([
                    dbc.Label("Check-in"),
                    dcc.DatePickerSingle( #calendario per selezione data
                        id="edit-check-in",
                        date=prenotazione.check_in.date(), #data attuale come default
                        display_format='DD-MM-YYYY',
                        first_day_of_week=1
                    )
                ], md=4),
                dbc.Col([
                    dbc.Label("Check-out"),
                    dcc.DatePickerSingle(
                        id="edit-check-out",
                        date=prenotazione.check_out.date(),
                        display_format='DD-MM-YYYY',
                        first_day_of_week=1
                    )
                ], md=4),
                dbc.Col([
                    dbc.Label("Ospiti"),
                    dbc.Input(id="edit-ospiti", type="number", min=1, value=prenotazione.ospiti)
                ], md=4)
            ], className="mb-3"),

            dbc.Row([
                dbc.Col([
                    dbc.Label("Servizi aggiuntivi"),
                    dcc.Dropdown(
                        id="edit-servizi",
                        options=servizi_opzioni,
                        multi=True, # permette selezione multipla
                        value=servizi_selezionati # servizi già selezionati
                    )
                ])
            ], className="mb-3"),

            html.Hr(), # linea separatrice
            html.P(f"Camera attuale: {prenotazione.camera.numero} ({prenotazione.camera.tipo})",
                   className="text-muted"), # testo grigio
            html.Small("Nota: per cambiare camera, elimina questa prenotazione e creane una nuova",
                       className="text-muted")
        ]

        return True, modal_content

    elif button_id == "btn-annulla-modifica": #se cliccato pulsante annulla
        return False, [] #chiuso

    return is_open, [] #mantiene stato attuale


# Callback per salvare le modifiche alla prenotazione
@app.callback(
    [Output("messaggio-azioni", "children", allow_duplicate=True), # messaggio risultato operazione
     Output("modal-modifica", "is_open", allow_duplicate=True)], # chiude schermata dopo salvataggio
    [Input("btn-salva-modifica", "n_clicks")], #salva
    [State("tabella-prenotazioni", "selected_rows"), #prenotazione da modificare
     State("edit-nome", "value"), #tutti i nuovi valori dal form di modifica
     State("edit-cognome", "value"),
     State("edit-check-in", "date"),
     State("edit-check-out", "date"),
     State("edit-ospiti", "value"),
     State("edit-servizi", "value")], #lista nomi servizi selezionati
    prevent_initial_call=True #evita esecuzione al caricamento pagina
)
def salva_modifiche(n_clicks, selected_rows, nome, cognome, check_in, check_out, ospiti, servizi_nomi):
    if not n_clicks or not selected_rows:
        return "", False

    row_index = selected_rows[0]
    prenotazione = albergo.prenotazioni[row_index]

    #Validazione campi obbligatori
    if not nome or not cognome or not check_in or not check_out:
        return dbc.Alert(" Compila tutti i campi obbligatori", color="danger"), True # mantiene modale aperto

    #Conversione e validazione date
    try:
        check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
        check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()
    except:
        return dbc.Alert(" Date non valide", color="danger"), True

    # Verifica disponibilità camera per il nuovo periodo (evita conflitti)
    disponibile, motivo = albergo.verifica_disponibilita_per_modifica(
        prenotazione, check_in_date, check_out_date
    )

    if not disponibile: # se camera non disponibile nel nuovo periodo
        return dbc.Alert(f" Impossibile modificare: {motivo}", color="danger"), True

    #Verifica che numero ospiti non superi capacità camera
    if ospiti > prenotazione.camera.capacita:
        return dbc.Alert(f" Troppi ospiti per questa camera (max {prenotazione.camera.capacita})",
                         color="danger"), True

    #Ricostruisce lista oggetti servizi da lista nomi
    servizi = [s for s in albergo.servizi if s.nome in servizi_nomi] if servizi_nomi else []

    #Crea dizionario con nuovi dati (chiave stringa: valore)
    nuovi_dati = {
        'nome': nome,
        'cognome': cognome,
        'check_in': check_in_date,
        'check_out': check_out_date,
        'ospiti': ospiti,
        'servizi': servizi
    }

    #Chiama metodo di modifica della classe Albergo
    if albergo.modifica_prenotazione(prenotazione.id, nuovi_dati):
        return dbc.Alert(" Prenotazione modificata con successo", color="success"), False # chiude modale
    else:
        return dbc.Alert(" Errore durante la modifica", color="danger"), True # mantiene modale aperto


#Callback per anteprima costi servizi in tempo reale
@app.callback(
    Output("anteprima-servizi", "children"), #area anteprima sotto selezione servizi
    [Input("servizi", "value"), #attiva quando cambiano servizi selezionati
     Input("check-in", "date"), #attiva quando cambia data check-in
     Input("check-out", "date")] #attiva quando cambia data check-out
)
def aggiorna_anteprima_servizi(servizi_selezionati, check_in, check_out):
    if not servizi_selezionati or not check_in or not check_out:
        return "" #nessuna anteprima

    try:
        #Calcola numero di giorni soggiorno
        ci = datetime.strptime(check_in, "%Y-%m-%d")
        co = datetime.strptime(check_out, "%Y-%m-%d")
        giorni = (co - ci).days
        if giorni <= 0: # periodo non valido
            return dbc.Alert("Le date non sono valide", color="warning")

    except: # errore nel parsing date
        return ""

    # Trova oggetti servizio corrispondenti ai nomi selezionati
    servizi = [s for s in albergo.servizi if s.nome in servizi_selezionati]
    costo_totale_servizi = sum(s.prezzo for s in servizi) * giorni #costo totale tutti i servizi per tutti i giorni

    if servizi:
        dettagli = [] #lista stringhe con dettaglio costo per servizio
        for servizio in servizi:
            costo_servizio = servizio.prezzo * giorni #costo singolo servizio per periodo
            dettagli.append(f" {servizio.nome}: €{servizio.prezzo} × {giorni} giorni = €{costo_servizio}")

        #Crea contenuto anteprima con dettaglio calcoli
        contenuto = [
            html.H6(" Anteprima costi servizi:"),
            html.P("\n".join(dettagli), style={"white-space": "pre-line", "margin": "0"}), #rispetta newline
            html.Hr(style={"margin": "0.5rem 0"}),
            html.Strong(f"Totale servizi: €{costo_totale_servizi}") #totale in grassetto
        ]

        return dbc.Alert(contenuto, color="info") #riquadro blu informativo

    return "" #nessun servizio selezionato


############################################
## AVVIO APPLICAZIONE
############################################
if __name__ == '__main__':
    app.run(debug=True)  # development toolbar di Dash (modalità debug per verifare corretto funzionamento)
