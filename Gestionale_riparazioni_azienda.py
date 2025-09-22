import datetime
import json
import os
from enum import Enum
from typing import List, Dict, Optional


class StatoRiparazione(Enum):
    RICEVUTO = "Ricevuto"
    IN_LAVORAZIONE = "In Lavorazione"
    IN_ATTESA_PEZZI = "In Attesa Pezzi"
    COMPLETATO = "Completato"
    CONSEGNATO = "Consegnato"
    ANNULLATO = "Annullato"


class TipoIntervento(Enum):
    RIPARAZIONE = "Riparazione"
    MANUTENZIONE = "Manutenzione Preventiva"
    SOSTITUZIONE = "Sostituzione Componenti"
    ISPEZIONE = "Ispezione"


class Pezzo:
    def __init__(self, id_pezzo: str, nome: str, modello: str,
                 numero_serie: str, cliente: str):
        self.id_pezzo = id_pezzo
        self.nome = nome
        self.modello = modello
        self.numero_serie = numero_serie
        self.cliente = cliente
        self.data_creazione = datetime.datetime.now()

    def to_dict(self):
        return {
            'id_pezzo': self.id_pezzo,
            'nome': self.nome,
            'modello': self.modello,
            'numero_serie': self.numero_serie,
            'cliente': self.cliente,
            'data_creazione': self.data_creazione.isoformat()
        }


class RichiestaRiparazione:
    def __init__(self, id_richiesta: str, pezzo: Pezzo,
                 descrizione_problema: str, tipo_intervento: TipoIntervento,
                 priorita: str = "Media"):
        self.id_richiesta = id_richiesta
        self.pezzo = pezzo
        self.descrizione_problema = descrizione_problema
        self.tipo_intervento = tipo_intervento
        self.stato = StatoRiparazione.RICEVUTO
        self.priorita = priorita
        self.data_richiesta = datetime.datetime.now()
        self.data_completamento = None
        self.note_tecniche = []
        self.costo_stimato = 0.0
        self.costo_finale = 0.0
        self.tecnico_assegnato = ""

    def aggiungi_nota(self, nota: str, tecnico: str = ""):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.note_tecniche.append({
            'timestamp': timestamp,
            'nota': nota,
            'tecnico': tecnico
        })

    def aggiorna_stato(self, nuovo_stato: StatoRiparazione):
        self.stato = nuovo_stato
        if nuovo_stato == StatoRiparazione.COMPLETATO:
            self.data_completamento = datetime.datetime.now()

    def to_dict(self):
        return {
            'id_richiesta': self.id_richiesta,
            'pezzo': self.pezzo.to_dict(),
            'descrizione_problema': self.descrizione_problema,
            'tipo_intervento': self.tipo_intervento.value,
            'stato': self.stato.value,
            'priorita': self.priorita,
            'data_richiesta': self.data_richiesta.isoformat(),
            'data_completamento': self.data_completamento.isoformat() if self.data_completamento else None,
            'note_tecniche': self.note_tecniche,
            'costo_stimato': self.costo_stimato,
            'costo_finale': self.costo_finale,
            'tecnico_assegnato': self.tecnico_assegnato
        }


class SistemaGestioneRiparazioni:
    def __init__(self, file_dati: str = "riparazioni.json"):
        self.file_dati = file_dati
        self.richieste: Dict[str, RichiestaRiparazione] = {}
        self.pezzi: Dict[str, Pezzo] = {}
        self.carica_dati()

    def carica_dati(self):
        """Carica i dati dal file JSON"""
        if os.path.exists(self.file_dati):
            try:
                with open(self.file_dati, 'r', encoding='utf-8') as f:
                    dati = json.load(f)

                # Ricostruisce gli oggetti dai dati salvati
                for id_richiesta, dati_richiesta in dati.get('richieste', {}).items():
                    # Ricostruisce il pezzo
                    dati_pezzo = dati_richiesta['pezzo']
                    pezzo = Pezzo(
                        dati_pezzo['id_pezzo'],
                        dati_pezzo['nome'],
                        dati_pezzo['modello'],
                        dati_pezzo['numero_serie'],
                        dati_pezzo['cliente']
                    )

                    # Ricostruisce la richiesta
                    richiesta = RichiestaRiparazione(
                        id_richiesta,
                        pezzo,
                        dati_richiesta['descrizione_problema'],
                        TipoIntervento(dati_richiesta['tipo_intervento'])
                    )

                    # Ripristina i dati aggiuntivi
                    richiesta.stato = StatoRiparazione(dati_richiesta['stato'])
                    richiesta.priorita = dati_richiesta['priorita']
                    richiesta.data_richiesta = datetime.datetime.fromisoformat(dati_richiesta['data_richiesta'])
                    if dati_richiesta['data_completamento']:
                        richiesta.data_completamento = datetime.datetime.fromisoformat(
                            dati_richiesta['data_completamento'])
                    richiesta.note_tecniche = dati_richiesta['note_tecniche']
                    richiesta.costo_stimato = dati_richiesta['costo_stimato']
                    richiesta.costo_finale = dati_richiesta['costo_finale']
                    richiesta.tecnico_assegnato = dati_richiesta['tecnico_assegnato']

                    self.richieste[id_richiesta] = richiesta
                    self.pezzi[pezzo.id_pezzo] = pezzo

            except Exception as e:
                print(f"Errore nel caricamento dei dati: {e}")

    def salva_dati(self):
        """Salva i dati nel file JSON"""
        try:
            dati = {
                'richieste': {id_req: req.to_dict() for id_req, req in self.richieste.items()}
            }
            with open(self.file_dati, 'w', encoding='utf-8') as f:
                json.dump(dati, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Errore nel salvataggio dei dati: {e}")

    def genera_id_richiesta(self) -> str:
        """Genera un ID univoco per la richiesta"""
        today = datetime.datetime.now().strftime("%Y%m%d")
        counter = len([r for r in self.richieste.keys() if r.startswith(f"RIP{today}")]) + 1
        return f"RIP{today}{counter:03d}"

    def genera_id_pezzo(self) -> str:
        """Genera un ID univoco per il pezzo"""
        today = datetime.datetime.now().strftime("%Y%m%d")
        counter = len([p for p in self.pezzi.keys() if p.startswith(f"PZ{today}")]) + 1
        return f"PZ{today}{counter:03d}"

    def crea_richiesta_riparazione(self, nome_pezzo: str, modello: str,
                                   numero_serie: str, cliente: str,
                                   descrizione_problema: str, tipo_intervento: TipoIntervento,
                                   priorita: str = "Media") -> str:
        """Crea una nuova richiesta di riparazione"""

        # Crea il pezzo
        id_pezzo = self.genera_id_pezzo()
        pezzo = Pezzo(id_pezzo, nome_pezzo, modello, numero_serie, cliente)

        # Crea la richiesta
        id_richiesta = self.genera_id_richiesta()
        richiesta = RichiestaRiparazione(id_richiesta, pezzo, descrizione_problema,
                                         tipo_intervento, priorita)

        # Salva nella memoria
        self.pezzi[id_pezzo] = pezzo
        self.richieste[id_richiesta] = richiesta

        # Salva su file
        self.salva_dati()

        return id_richiesta

    def cerca_richieste(self, termine_ricerca: str = "",
                        stato: Optional[StatoRiparazione] = None,
                        cliente: str = "", tipo: Optional[TipoIntervento] = None) -> List[RichiestaRiparazione]:
        """Cerca richieste di riparazione con diversi criteri"""

        risultati = []

        for richiesta in self.richieste.values():
            match = True

            # Filtra per termine di ricerca
            if termine_ricerca:
                termine = termine_ricerca.lower()
                if not (termine in richiesta.id_richiesta.lower() or
                        termine in richiesta.pezzo.nome.lower() or
                        termine in richiesta.pezzo.modello.lower() or
                        termine in richiesta.pezzo.numero_serie.lower() or
                        termine in richiesta.descrizione_problema.lower()):
                    match = False

            # Filtra per stato
            if stato and richiesta.stato != stato:
                match = False

            # Filtra per cliente
            if cliente and cliente.lower() not in richiesta.pezzo.cliente.lower():
                match = False

            # Filtra per tipo intervento
            if tipo and richiesta.tipo_intervento != tipo:
                match = False

            if match:
                risultati.append(richiesta)

        # Ordina per data di richiesta (più recenti prima)
        risultati.sort(key=lambda r: r.data_richiesta, reverse=True)
        return risultati

    def aggiorna_richiesta(self, id_richiesta: str, **kwargs) -> bool:
        """Aggiorna i dati di una richiesta"""
        if id_richiesta not in self.richieste:
            return False

        richiesta = self.richieste[id_richiesta]

        if 'stato' in kwargs:
            richiesta.aggiorna_stato(kwargs['stato'])
        if 'tecnico_assegnato' in kwargs:
            richiesta.tecnico_assegnato = kwargs['tecnico_assegnato']
        if 'costo_stimato' in kwargs:
            richiesta.costo_stimato = float(kwargs['costo_stimato'])
        if 'costo_finale' in kwargs:
            richiesta.costo_finale = float(kwargs['costo_finale'])
        if 'nota' in kwargs:
            tecnico = kwargs.get('tecnico_nota', '')
            richiesta.aggiungi_nota(kwargs['nota'], tecnico)

        self.salva_dati()
        return True

    def stampa_richiesta(self, richiesta: RichiestaRiparazione):
        """Stampa i dettagli di una richiesta in formato leggibile"""
        print(f"\n{'=' * 60}")
        print(f"ID RICHIESTA: {richiesta.id_richiesta}")
        print(f"{'=' * 60}")
        print(f"PEZZO:")
        print(f"  - ID: {richiesta.pezzo.id_pezzo}")
        print(f"  - Nome: {richiesta.pezzo.nome}")
        print(f"  - Modello: {richiesta.pezzo.modello}")
        print(f"  - S/N: {richiesta.pezzo.numero_serie}")
        print(f"  - Cliente: {richiesta.pezzo.cliente}")
        print(f"\nDETTAGLI RIPARAZIONE:")
        print(f"  - Tipo: {richiesta.tipo_intervento.value}")
        print(f"  - Stato: {richiesta.stato.value}")
        print(f"  - Priorità: {richiesta.priorita}")
        print(f"  - Tecnico: {richiesta.tecnico_assegnato or 'Non assegnato'}")
        print(f"  - Data richiesta: {richiesta.data_richiesta.strftime('%Y-%m-%d %H:%M')}")
        if richiesta.data_completamento:
            print(f"  - Data completamento: {richiesta.data_completamento.strftime('%Y-%m-%d %H:%M')}")
        print(f"  - Costo stimato: €{richiesta.costo_stimato:.2f}")
        if richiesta.costo_finale > 0:
            print(f"  - Costo finale: €{richiesta.costo_finale:.2f}")
        print(f"\nDESCRIZIONE PROBLEMA:")
        print(f"  {richiesta.descrizione_problema}")

        if richiesta.note_tecniche:
            print(f"\nNOTE TECNICHE:")
            for nota in richiesta.note_tecniche:
                tecnico_info = f" - {nota['tecnico']}" if nota['tecnico'] else ""
                print(f"  [{nota['timestamp']}]{tecnico_info}")
                print(f"    {nota['nota']}")


def menu_principale():
    sistema = SistemaGestioneRiparazioni()

    while True:
        print(f"\n{'=' * 60}")
        print("🔧 SISTEMA GESTIONE RIPARAZIONI")
        print(f"{'=' * 60}")
        print("1. Crea nuova richiesta di riparazione")
        print("2. Cerca richieste")
        print("3. Visualizza tutte le richieste")
        print("4. Aggiorna richiesta")
        print("5. Statistiche")
        print("0. Esci")
        print(f"{'=' * 60}")

        scelta = input("Seleziona un'opzione: ").strip()

        if scelta == "1":
            crea_nuova_richiesta(sistema)
        elif scelta == "2":
            cerca_richieste_menu(sistema)
        elif scelta == "3":
            visualizza_tutte_richieste(sistema)
        elif scelta == "4":
            aggiorna_richiesta_menu(sistema)
        elif scelta == "5":
            mostra_statistiche(sistema)
        elif scelta == "0":
            print("Arrivederci!")
            break
        else:
            print("Opzione non valida!")


def crea_nuova_richiesta(sistema: SistemaGestioneRiparazioni):
    print(f"\n{'=' * 40}")
    print("📝 NUOVA RICHIESTA DI RIPARAZIONE")
    print(f"{'=' * 40}")

    nome_pezzo = input("Nome del pezzo: ").strip()
    modello = input("Modello: ").strip()
    numero_serie = input("Numero di serie: ").strip()
    cliente = input("Cliente: ").strip()
    descrizione = input("Descrizione del problema: ").strip()

    print("\nTipi di intervento disponibili:")
    for i, tipo in enumerate(TipoIntervento, 1):
        print(f"{i}. {tipo.value}")

    while True:
        try:
            scelta_tipo = int(input("Seleziona tipo intervento (1-4): "))
            if 1 <= scelta_tipo <= 4:
                tipo_intervento = list(TipoIntervento)[scelta_tipo - 1]
                break
            else:
                print("Scelta non valida!")
        except ValueError:
            print("Inserisci un numero!")

    print("\nPriorità: 1. Bassa, 2. Media, 3. Alta, 4. Urgente")
    priorita_map = {"1": "Bassa", "2": "Media", "3": "Alta", "4": "Urgente"}
    scelta_priorita = input("Priorità (default Media): ").strip()
    priorita = priorita_map.get(scelta_priorita, "Media")

    id_richiesta = sistema.crea_richiesta_riparazione(
        nome_pezzo, modello, numero_serie, cliente,
        descrizione, tipo_intervento, priorita
    )

    print(f"\n✅ Richiesta creata con successo!")
    print(f"ID Richiesta: {id_richiesta}")


def cerca_richieste_menu(sistema: SistemaGestioneRiparazioni):
    print(f"\n{'=' * 40}")
    print("🔍 RICERCA RICHIESTE")
    print(f"{'=' * 40}")

    termine = input("Termine di ricerca (ID, nome pezzo, modello, S/N): ").strip()
    cliente = input("Cliente (opzionale): ").strip()

    print("\nFiltra per stato (opzionale):")
    print("0. Tutti")
    for i, stato in enumerate(StatoRiparazione, 1):
        print(f"{i}. {stato.value}")

    stato_filtro = None
    scelta_stato = input("Seleziona stato (default tutti): ").strip()
    if scelta_stato.isdigit() and 1 <= int(scelta_stato) <= len(StatoRiparazione):
        stato_filtro = list(StatoRiparazione)[int(scelta_stato) - 1]

    risultati = sistema.cerca_richieste(termine, stato_filtro, cliente)

    if not risultati:
        print("\n❌ Nessuna richiesta trovata con i criteri specificati.")
        return

    print(f"\n📋 Trovate {len(risultati)} richieste:")
    for i, richiesta in enumerate(risultati, 1):
        print(f"\n{i}. {richiesta.id_richiesta} - {richiesta.pezzo.nome} ({richiesta.stato.value})")
        print(f"   Cliente: {richiesta.pezzo.cliente}")
        print(f"   Data: {richiesta.data_richiesta.strftime('%Y-%m-%d')}")

    scelta = input(f"\nVuoi visualizzare una richiesta specifica? (1-{len(risultati)}, N per no): ").strip()
    if scelta.isdigit() and 1 <= int(scelta) <= len(risultati):
        sistema.stampa_richiesta(risultati[int(scelta) - 1])


def visualizza_tutte_richieste(sistema: SistemaGestioneRiparazioni):
    if not sistema.richieste:
        print("\n❌ Nessuna richiesta presente nel sistema.")
        return

    richieste = list(sistema.richieste.values())
    richieste.sort(key=lambda r: r.data_richiesta, reverse=True)

    print(f"\n📋 TUTTE LE RICHIESTE ({len(richieste)} totali)")
    print(f"{'=' * 80}")

    for i, richiesta in enumerate(richieste, 1):
        stato_icon = "✅" if richiesta.stato == StatoRiparazione.COMPLETATO else "🔧"
        print(f"{i:2d}. {stato_icon} {richiesta.id_richiesta} - {richiesta.pezzo.nome}")
        print(f"     Cliente: {richiesta.pezzo.cliente} | Stato: {richiesta.stato.value}")
        print(f"     Data: {richiesta.data_richiesta.strftime('%Y-%m-%d %H:%M')}")
        if richiesta.tecnico_assegnato:
            print(f"     Tecnico: {richiesta.tecnico_assegnato}")

    scelta = input(f"\nVuoi visualizzare una richiesta specifica? (1-{len(richieste)}, N per no): ").strip()
    if scelta.isdigit() and 1 <= int(scelta) <= len(richieste):
        sistema.stampa_richiesta(richieste[int(scelta) - 1])


def aggiorna_richiesta_menu(sistema: SistemaGestioneRiparazioni):
    print(f"\n{'=' * 40}")
    print("✏️ AGGIORNA RICHIESTA")
    print(f"{'=' * 40}")

    id_richiesta = input("ID Richiesta da aggiornare: ").strip().upper()

    if id_richiesta not in sistema.richieste:
        print("❌ ID Richiesta non trovato!")
        return

    richiesta = sistema.richieste[id_richiesta]
    print(f"\nRichiesta corrente: {richiesta.pezzo.nome} - {richiesta.stato.value}")

    print("\nCosa vuoi aggiornare?")
    print("1. Stato")
    print("2. Tecnico assegnato")
    print("3. Costo stimato")
    print("4. Costo finale")
    print("5. Aggiungi nota tecnica")
    print("0. Annulla")

    scelta = input("Seleziona opzione: ").strip()

    if scelta == "1":
        print("\nStati disponibili:")
        for i, stato in enumerate(StatoRiparazione, 1):
            print(f"{i}. {stato.value}")

        while True:
            try:
                scelta_stato = int(input("Seleziona nuovo stato: "))
                if 1 <= scelta_stato <= len(StatoRiparazione):
                    nuovo_stato = list(StatoRiparazione)[scelta_stato - 1]
                    sistema.aggiorna_richiesta(id_richiesta, stato=nuovo_stato)
                    print(f"✅ Stato aggiornato a: {nuovo_stato.value}")
                    break
                else:
                    print("Scelta non valida!")
            except ValueError:
                print("Inserisci un numero!")

    elif scelta == "2":
        tecnico = input("Nome tecnico: ").strip()
        sistema.aggiorna_richiesta(id_richiesta, tecnico_assegnato=tecnico)
        print(f"✅ Tecnico assegnato: {tecnico}")

    elif scelta == "3":
        try:
            costo = float(input("Costo stimato (€): "))
            sistema.aggiorna_richiesta(id_richiesta, costo_stimato=costo)
            print(f"✅ Costo stimato aggiornato: €{costo:.2f}")
        except ValueError:
            print("❌ Valore non valido!")

    elif scelta == "4":
        try:
            costo = float(input("Costo finale (€): "))
            sistema.aggiorna_richiesta(id_richiesta, costo_finale=costo)
            print(f"✅ Costo finale aggiornato: €{costo:.2f}")
        except ValueError:
            print("❌ Valore non valido!")

    elif scelta == "5":
        nota = input("Nota tecnica: ").strip()
        tecnico = input("Nome tecnico (opzionale): ").strip()
        sistema.aggiorna_richiesta(id_richiesta, nota=nota, tecnico_nota=tecnico)
        print("✅ Nota aggiunta!")


def mostra_statistiche(sistema: SistemaGestioneRiparazioni):
    if not sistema.richieste:
        print("\n❌ Nessuna richiesta presente per generare statistiche.")
        return

    print(f"\n{'=' * 50}")
    print("📊 STATISTICHE SISTEMA")
    print(f"{'=' * 50}")

    # Conteggio per stato
    stati_count = {}
    for richiesta in sistema.richieste.values():
        stato = richiesta.stato.value
        stati_count[stato] = stati_count.get(stato, 0) + 1

    print("RICHIESTE PER STATO:")
    for stato, count in stati_count.items():
        print(f"  📍 {stato}: {count}")

    # Conteggio per tipo intervento
    tipi_count = {}
    for richiesta in sistema.richieste.values():
        tipo = richiesta.tipo_intervento.value
        tipi_count[tipo] = tipi_count.get(tipo, 0) + 1

    print("\nRICHIESTE PER TIPO INTERVENTO:")
    for tipo, count in tipi_count.items():
        print(f"  🔧 {tipo}: {count}")

    # Statistiche sui costi
    costi_finali = [r.costo_finale for r in sistema.richieste.values() if r.costo_finale > 0]
    if costi_finali:
        print(f"\nSTATISTICHE COSTI:")
        print(f"  💰 Costo medio: €{sum(costi_finali) / len(costi_finali):.2f}")
        print(f"  💰 Costo totale: €{sum(costi_finali):.2f}")
        print(f"  📊 Riparazioni fatturate: {len(costi_finali)}")

    print(f"\nTOTALE RICHIESTE: {len(sistema.richieste)}")


if __name__ == "__main__":
    menu_principale()