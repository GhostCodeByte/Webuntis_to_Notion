import webuntis
import logging
import requests
from datetime import datetime, timedelta

# Notion API Details
NOTION_API_URL = "https://api.notion.com/v1/pages"
NOTION_TOKEN = "secret_GJJ7dj5b1nUsFA0OYjDXbVk02fCnqgtbbprq90wwYXV"
NOTION_DATABASE_ID = "c807c4e0112a4da794681df458dfeb38"

# Notion API-Endpunkte
headers = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Content-Type': 'application/json',
    'Notion-Version': '2022-06-28'
}

# Aktuelles Datum
heute = datetime.now().date()

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)

# Verbindung zu WebUntis herstellen
sitzung = webuntis.Session(
    server='tritone.webuntis.com',
    username='Darou10e',
    password='Ji34P4Wv',
    school='rotteckgym-freiburg',
    useragent='WebUntis Python API'
)

# Fach-Zuordnung
fach_zuordnung = {
    "m": "Mathe",
    "m-ver2": "Vertiefung",
    "m-ver1": "Vertiefung",
    "d": "Deutsch",
    "bk": "Kunst",
    "mu": "Musik",
    "e1": "Englisch",
    "eth2": "Ethik",
    "it": "IMP",
    "f2": "Französisch",
    "gmk": "Gemeinschaftskunde",
    "g": "Geschichte",
    "sw": "Sport",
    "ch": "Chemie",
    "bio": "Biologie",
    "ph": "Physik"
}

def naechster_montag_und_freitag():
    """Berechnet das Datum des nächsten Montags und Freitags."""
    heute = datetime.today()
    tage_bis_montag = (7 - heute.weekday()) % 7
    naechster_montag = heute + timedelta(days=tage_bis_montag)
    naechster_freitag = naechster_montag + timedelta(days=4)
    return heute, naechster_freitag

def entferne_ueberlappende_stunden(stundenplan):
    """Entfernt überlappende Stunden aus dem Stundenplan."""
    stunden_liste = sorted(stundenplan, key=lambda stunde: (stunde.start.date(), stunde.start.time()))
    nicht_ueberlappender_stundenplan = []
    letzte_ende_zeit = None

    for stunde in stunden_liste:
        if letzte_ende_zeit is None or stunde.start >= letzte_ende_zeit:
            nicht_ueberlappender_stundenplan.append(stunde)
            letzte_ende_zeit = stunde.end

    return nicht_ueberlappender_stundenplan

def kombiniere_aufeinanderfolgende_stunden(stundenplan):
    """Kombiniert aufeinanderfolgende Stunden desselben Fachs."""
    kombinierter_stundenplan = []
    aktuelle_stunde = None

    for stunde in stundenplan:
        if aktuelle_stunde is None:
            aktuelle_stunde = stunde
        else:
            if (stunde.start == aktuelle_stunde.end and 
                [fach.name for fach in stunde.subjects] == [fach.name for fach in aktuelle_stunde.subjects]):
                aktuelle_stunde.end = stunde.end
            else:
                kombinierter_stundenplan.append(aktuelle_stunde)
                aktuelle_stunde = stunde

    if aktuelle_stunde is not None:
        kombinierter_stundenplan.append(aktuelle_stunde)

    return kombinierter_stundenplan

def filtere_unerwuenschte_stunden(stundenplan):
    """Filtert unerwünschte Stunden aus dem Stundenplan."""
    unerwuenschte_faecher = ["M-Werkstatt", "sp-ver", "KLS", "inf_Brücke"]
    return [stunde for stunde in stundenplan if not any(fach.name in unerwuenschte_faecher for fach in stunde.subjects)]

def benenne_faecher_um(stunde):
    """Benennt Fächer in den Stunden um."""
    for fach in stunde.subjects:
        fach.name = fach_zuordnung.get(fach.name, fach.name)
    return stunde

def erstelle_notion_seite(fachname, startzeit, endzeit):
    """Erstellt eine Seite in Notion."""
    daten = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "title": {"title": [{"text": {"content": fachname}}]},
            "Date": {"date": {"start": startzeit.isoformat(), "end": endzeit.isoformat() if endzeit else None}},
            "Kategorie": {"select": {"name": "Stundenplan"}}
        }
    }

    response = requests.post(NOTION_API_URL, json=daten, headers=headers)
    if response.status_code == 200:
        logging.info(f"Notion-Seite erfolgreich erstellt für {fachname} ({startzeit} - {endzeit})")
    else:
        logging.error(f"Fehler beim Erstellen der Notion-Seite: {response.status_code} - {response.text}")

def get_stundenplan_pages():
    """Abrufen von Seiten mit der Kategorie 'Stundenplan'."""
    url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'
    query = {"filter": {"property": "Kategorie", "select": {"equals": "Stundenplan"}}}
    response = requests.post(url, headers=headers, json=query)
    if response.status_code == 200:
        return response.json().get('results', [])
    else:
        print('Fehler beim Abrufen der Seiten:', response.status_code, response.text)
        return []

def delete_page(page_id):
    """Löschen einer Seite nach ID."""
    url = f'https://api.notion.com/v1/blocks/{page_id}'
    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        print(f'Seite {page_id} erfolgreich gelöscht.')
    else:
        print(f'Fehler beim Löschen der Seite {page_id}:', response.status_code, response.text)

def delete_old_stundenplan_pages():
    """Löschen alter Stundenplanseiten in Notion."""
    pages = get_stundenplan_pages()
    for page in pages:
        page_date_str = page['properties']['Date']['date']['start']
        page_date = datetime.fromisoformat(page_date_str).date()
        if page_date > heute:
            delete_page(page['id'])

# Hauptteil des Skripts
delete_old_stundenplan_pages()
try:
    sitzung.login()
    logging.info("Anmeldung erfolgreich")

    alle_klassen = sitzung.klassen()
    logging.info(f"Anzahl der abgerufenen Klassen: {len(alle_klassen)}")

    klassen_name = '10e'
    gefilterte_klassen = [klasse for klasse in alle_klassen if klasse.name == klassen_name]

    if gefilterte_klassen:
        klasse = gefilterte_klassen[0]
        logging.info(f"Klasse '{klassen_name}' gefunden")
        
        start_datum, end_datum = naechster_montag_und_freitag()
        
        stundenplan = sitzung.timetable(klasse=klasse, start=start_datum, end=end_datum)
        
        gefilterter_stundenplan = filtere_unerwuenschte_stunden(stundenplan)
        
        umbenannter_stundenplan = [benenne_faecher_um(stunde) for stunde in gefilterter_stundenplan]
        
        nicht_ueberlappender_stundenplan = entferne_ueberlappende_stunden(umbenannter_stundenplan)
        
        kombinierter_stundenplan = kombiniere_aufeinanderfolgende_stunden(nicht_ueberlappender_stundenplan)
        
        for stunde in kombinierter_stundenplan:
            fach_namen = ', '.join([fach.name for fach in stunde.subjects])
            print(f"{stunde.start} - {stunde.end}: {fach_namen}")
            erstelle_notion_seite(fach_namen, stunde.start, stunde.end)
    else:
        logging.warning(f"Klasse '{klassen_name}' nicht gefunden")

except webuntis.errors.AuthError:
    logging.error("Authentifizierungsfehler: Überprüfe die Anmeldedaten")
except webuntis.errors.RemoteError as e:
    logging.error(f"RemoteError: {e.message}")  # Keine Attribute 'code' und 'message' verwenden
except Exception as e:
    logging.error(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
finally:
    try:
        sitzung.logout()
        logging.info("Abmeldung erfolgreich")
    except KeyError:
        logging.warning("Abmeldung fehlgeschlagen: Kein gültiges jsessionid gefunden")
