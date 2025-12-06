from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify
import csv
import os
import io
import json
from datetime import datetime, date, timedelta
from urllib.parse import quote
from werkzeug.utils import secure_filename
import requests
import pandas as pd

app = Flask(__name__)
# Usa la secret key da variabile d'ambiente o una di default per sviluppo
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Crea la cartella uploads se non esiste
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# File JSON per salvare l'anagrafica
ANAGRAFICA_JSON = 'anagrafica.json'

# File JSON per configurazione OData
ODATA_CONFIG_JSON = 'odata_config.json'

# Cache rimossa - usiamo solo file JSON nella cartella uploads

# Inizializza i file JSON se non esistono
def init_json_files():
    """Inizializza i file JSON se non esistono"""
    # Inizializza odata_config.json se non esiste
    if not os.path.exists(ODATA_CONFIG_JSON):
        app.logger.info(f"File {ODATA_CONFIG_JSON} non trovato, creazione con valori di default")
        default_config = {
            'odata_url': 'https://voiapp.fr',
            'odata_endpoint': 'michelinpal/odata/DMX',
            'requires_auth': True,
            'auth_type': 'basic',
            'auth_username': 'API',
            'auth_password': 'IPA',
            'auth_token': '',
            'date_field': 'LaunchDate',
            'site_field': 'SiteName'
        }
        try:
            with open(ODATA_CONFIG_JSON, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            app.logger.info(f"File {ODATA_CONFIG_JSON} creato con successo")
        except Exception as e:
            app.logger.error(f"Impossibile creare {ODATA_CONFIG_JSON}: {e}")
    else:
        app.logger.info(f"File {ODATA_CONFIG_JSON} trovato, caricamento configurazione")
        try:
            with open(ODATA_CONFIG_JSON, 'r', encoding='utf-8') as f:
                config = json.load(f)
            app.logger.info(f"Configurazione OData caricata: URL={config.get('odata_url')}, Endpoint={config.get('odata_endpoint')}, Username={config.get('auth_username')}")
        except Exception as e:
            app.logger.error(f"Errore nel caricamento {ODATA_CONFIG_JSON}: {e}")
    
    # Cache rimossa - non più necessaria

# Inizializza i file JSON all'avvio
init_json_files()

# Variabile globale per memorizzare l'anagrafica
anagrafica_data = None
anagrafica_filename = None


def load_anagrafica(filepath, update_mode=False):
    """Carica l'anagrafica articoli dal file CSV e salva in JSON
    
    Args:
        filepath: percorso del file CSV
        update_mode: se True, aggiorna/merge con l'anagrafica esistente invece di sostituirla
    """
    global anagrafica_data
    
    # Se non è in modalità update, inizializza il dizionario
    if not update_mode:
        anagrafica_data = {}
    elif anagrafica_data is None:
        anagrafica_data = {}
    
    new_items = 0
    updated_items = 0
    
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        # Rileva il delimitatore
        first_line = f.readline()
        delimiter = ';' if ';' in first_line else ','
        f.seek(0)
        
        reader = csv.reader(f, delimiter=delimiter)
        next(reader)  # Salta l'header
        
        for row in reader:
            if len(row) >= 4:
                # Colonna C (ITM_0) è l'indice 2, Colonna D (COD_0) è l'indice 3
                itm_code = row[2].strip().strip('"').upper()
                cod_code = row[3].strip().strip('"')
                # Salva solo se abbiamo sia il codice che il valore di sostituzione (non vuoto)
                if itm_code and cod_code and cod_code.strip():
                    if itm_code in anagrafica_data:
                        updated_items += 1
                    else:
                        new_items += 1
                    anagrafica_data[itm_code] = cod_code
    
    # Salva l'anagrafica in JSON
    save_anagrafica_json()
    
    return len(anagrafica_data), new_items, updated_items


def save_anagrafica_json():
    """Salva l'anagrafica in un file JSON"""
    global anagrafica_data
    if anagrafica_data:
        with open(ANAGRAFICA_JSON, 'w', encoding='utf-8') as f:
            json.dump(anagrafica_data, f, ensure_ascii=False, indent=2)


def load_anagrafica_json():
    """Carica l'anagrafica dal file JSON se esiste"""
    global anagrafica_data
    if os.path.exists(ANAGRAFICA_JSON):
        try:
            with open(ANAGRAFICA_JSON, 'r', encoding='utf-8') as f:
                anagrafica_data = json.load(f)
            return len(anagrafica_data)
        except Exception as e:
            print(f"Errore nel caricamento dell'anagrafica da JSON: {e}")
            anagrafica_data = None
            return 0
    return 0


def transform_article_code(code):
    """Trasforma il codice articolo secondo le regole specificate"""
    if not code or not isinstance(code, str):
        return code
    
    code = code.strip()
    code_lower = code.lower()
    
    # so_12345 -> cso_12345 (case insensitive)
    if code_lower.startswith('so_'):
        code = 'c' + code
    
    # id_ -> rimuovere id_ (case insensitive)
    elif code_lower.startswith('id_'):
        code = code[3:]
    
    # ig_ -> rimuovere ig_ (case insensitive)
    elif code_lower.startswith('ig_'):
        code = code[3:]
    
    # ar_ -> rimuovere ar_ (case insensitive)
    elif code_lower.startswith('ar_'):
        code = code[3:]
    
    # fg_ -> rimuovere fg_ (case insensitive)
    elif code_lower.startswith('fg_'):
        code = code[3:]
    
    return code


def process_csv_file(input_filepath, output_filepath):
    """Processa il file CSV applicando le trasformazioni"""
    global anagrafica_data
    
    if anagrafica_data is None:
        raise ValueError("Anagrafica non caricata. Carica prima l'anagrafica articoli.")
    
    # Rileva il delimitatore
    with open(input_filepath, 'r', encoding='utf-8-sig') as f:
        first_line = f.readline()
        delimiter = ';' if ';' in first_line else ','
    
    rows_processed = 0
    rows_transformed = 0
    missing_codes = set()  # Set per raccogliere i codici mancanti (senza duplicati)
    
    with open(input_filepath, 'r', encoding='utf-8-sig') as infile, \
         open(output_filepath, 'w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.reader(infile, delimiter=delimiter)
        writer = csv.writer(outfile, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
        
        # Leggi e scrivi l'header
        header = next(reader)
        writer.writerow(header)
        
        # Trova l'indice della colonna ARTICLE (N)
        try:
            article_col_index = header.index('ARTICLE')
        except ValueError:
            # Prova a cercare senza case sensitivity
            article_col_index = next((i for i, col in enumerate(header) if col.upper() == 'ARTICLE'), None)
            if article_col_index is None:
                raise ValueError("Colonna 'ARTICLE' non trovata nel file CSV")
        
        # Processa ogni riga
        for row in reader:
            if len(row) > article_col_index:
                original_code = row[article_col_index].strip() if row[article_col_index] else ''
                
                if original_code:
                    # Applica le trasformazioni
                    transformed_code = transform_article_code(original_code)
                    
                    # Se il codice inizia con cso_, cerca nell'anagrafica
                    if transformed_code and transformed_code.lower().startswith('cso_'):
                        # Normalizza in maiuscolo per la ricerca
                        search_code = transformed_code.upper()
                        # Cerca nella colonna C (ITM_0) dell'anagrafica
                        if search_code in anagrafica_data:
                            # Sostituisci con il valore della colonna D (COD_0)
                            replacement = anagrafica_data[search_code]
                            if replacement and replacement.strip():  # Verifica che il valore non sia vuoto
                                transformed_code = replacement.strip()
                                rows_transformed += 1
                        else:
                            # Codice non trovato nell'anagrafica
                            missing_codes.add(search_code)
                    
                    row[article_col_index] = transformed_code
                else:
                    # Mantieni il valore originale se vuoto
                    row[article_col_index] = original_code
                
                rows_processed += 1
            
            writer.writerow(row)
    
    return rows_processed, rows_transformed, list(missing_codes)


@app.route('/')
def index():
    """Pagina principale"""
    global anagrafica_data, anagrafica_filename
    
    # Carica l'anagrafica da JSON se esiste e non è già caricata
    if anagrafica_data is None:
        count = load_anagrafica_json()
        if count > 0:
            anagrafica_filename = "anagrafica.json (caricata automaticamente)"
    
    return render_template('index.html', anagrafica_loaded=anagrafica_data is not None, 
                         anagrafica_filename=anagrafica_filename)


@app.route('/view_anagrafica')
def view_anagrafica():
    """Pagina per visualizzare l'anagrafica con paginazione e ricerca"""
    global anagrafica_data
    
    if anagrafica_data is None:
        flash('Anagrafica non caricata', 'error')
        return redirect(url_for('index'))
    
    # Parametri di paginazione
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search_query = request.args.get('search', '').strip().upper()
    
    # Filtra per ricerca se presente
    if search_query:
        filtered_items = [(k, v) for k, v in anagrafica_data.items() 
                         if search_query in k.upper() or search_query in str(v).upper()]
    else:
        filtered_items = list(anagrafica_data.items())
    
    # Ordina
    filtered_items = sorted(filtered_items)
    
    total_count = len(filtered_items)
    
    # Calcola paginazione
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    items_list = filtered_items[start_idx:end_idx]
    
    return render_template('view_anagrafica.html', 
                         items=items_list, 
                         total_count=total_count,
                         showing_count=len(items_list),
                         page=page,
                         total_pages=total_pages,
                         per_page=per_page,
                         search_query=search_query)


@app.route('/upload_anagrafica', methods=['POST'])
def upload_anagrafica():
    """Endpoint per caricare l'anagrafica articoli"""
    global anagrafica_data, anagrafica_filename
    
    if 'file' not in request.files:
        flash('Nessun file selezionato', 'error')
        return redirect(request.referrer or url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('Nessun file selezionato', 'error')
        return redirect(request.referrer or url_for('index'))
    
    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Controlla se è un update o un nuovo caricamento
            update_mode = request.form.get('update_mode') == 'true' or anagrafica_data is not None
            total_count, new_items, updated_items = load_anagrafica(filepath, update_mode=update_mode)
            anagrafica_filename = filename
            
            if update_mode:
                flash(f'Anagrafica aggiornata! Totale: {total_count} articoli ({new_items} nuovi, {updated_items} aggiornati).', 'success')
            else:
                flash(f'Anagrafica caricata con successo! {total_count} articoli memorizzati.', 'success')
        except Exception as e:
            flash(f'Errore nel caricamento dell\'anagrafica: {str(e)}', 'error')
    else:
        flash('File non valido. Carica un file CSV.', 'error')
    
    return redirect(request.referrer or url_for('index'))


@app.route('/upload_transform', methods=['POST'])
def upload_transform():
    """Endpoint per caricare e trasformare il file CSV"""
    global anagrafica_data
    
    if anagrafica_data is None:
        flash('Carica prima l\'anagrafica articoli!', 'error')
        return redirect(url_for('index'))
    
    if 'file' not in request.files:
        flash('Nessun file selezionato', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('Nessun file selezionato', 'error')
        return redirect(url_for('index'))
    
    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        input_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_filepath)
        
        try:
            # Crea il nome del file di output
            base_name = os.path.splitext(filename)[0]
            output_filename = f"{base_name}_trasformato.csv"
            output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
            
            # Processa il file
            rows_processed, rows_transformed, missing_codes = process_csv_file(input_filepath, output_filepath)
            
            # Se ci sono codici mancanti, mostra una pagina con popup invece di scaricare direttamente
            if missing_codes:
                return render_template('transform_result.html', 
                                     output_filename=output_filename,
                                     rows_processed=rows_processed,
                                     rows_transformed=rows_transformed,
                                     missing_codes=sorted(missing_codes),
                                     missing_count=len(missing_codes))
            
            # Se non ci sono codici mancanti, scarica direttamente
            flash(f'File trasformato con successo! {rows_processed} righe processate, {rows_transformed} codici cso_* sostituiti.', 'success')
            return send_file(
                output_filepath,
                as_attachment=True,
                download_name=output_filename,
                mimetype='text/csv'
            )
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Errore nella trasformazione: {error_details}")  # Debug
            flash(f'Errore nella trasformazione: {str(e)}', 'error')
            return redirect(url_for('index'))
    else:
        flash('File non valido. Carica un file CSV.', 'error')
    
    return redirect(url_for('index'))


@app.route('/download_file/<filename>')
def download_file(filename):
    """Endpoint per scaricare il file trasformato"""
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename, mimetype='text/csv')
    else:
        flash('File non trovato', 'error')
        return redirect(url_for('index'))


def load_odata_config():
    """Carica la configurazione OData da JSON"""
    default_config = {
        'odata_url': 'https://voiapp.fr',
        'odata_endpoint': 'michelinpal/odata/DMX',  # Endpoint trovato nel VBA
        'requires_auth': True,  # Abilitato di default
        'auth_type': 'basic',  # Basic Auth di default
        'auth_username': 'API',  # Nome utente API (impostato di default)
        'auth_password': 'IPA',  # Password API (impostato di default)
        'auth_token': '',  # Per altri tipi di auth
        'date_field': 'LaunchDate',
        'site_field': 'SiteName'  # Cambiato da 'Site' a 'SiteName' come nel VBA
    }
    
    if os.path.exists(ODATA_CONFIG_JSON):
        try:
            with open(ODATA_CONFIG_JSON, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Merge con default per valori mancanti
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
        except Exception as e:
            print(f"Errore nel caricamento config OData: {e}")
    
    return default_config


def save_odata_config(config):
    """Salva la configurazione OData in JSON"""
    try:
        with open(ODATA_CONFIG_JSON, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Errore nel salvataggio config OData: {e}")
        return False


def get_json_extraction(date_str, site='TST - EDC Torino'):
    """Recupera un'estrazione dal file JSON più recente per quella data"""
    uploads_dir = app.config['UPLOAD_FOLDER']
    if not os.path.exists(uploads_dir):
        return None
    
    # Cerca file JSON che iniziano con "estrazione_" e contengono la data
    date_pattern = date_str.replace('-', '')
    matching_files = []
    
    for filename in os.listdir(uploads_dir):
        if filename.startswith('estrazione_') and filename.endswith('.json'):
            # Estrai la data dal nome file (formato: estrazione_YYYYMMDD_timestamp.json)
            if date_pattern in filename:
                filepath = os.path.join(uploads_dir, filename)
                try:
                    mtime = os.path.getmtime(filepath)
                    matching_files.append((filepath, mtime, filename))
                except:
                    continue
    
    # Ordina per data di modifica (più recente prima)
    if matching_files:
        matching_files.sort(key=lambda x: x[1], reverse=True)
        # Carica il file più recente
        filepath, _, filename = matching_files[0]
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                # Verifica che contenga i dati analizzati
                if 'data' in json_data or 'statistics' in json_data:
                    app.logger.info(f"Trovato JSON per {date_str}: {filename}")
                    return json_data
        except Exception as e:
            app.logger.warning(f"Errore nel caricamento JSON {filename}: {e}")
    
    return None


def save_json_extraction(date_str, site, analysis_result):
    """Salva un'estrazione come file JSON nella cartella uploads"""
    try:
        uploads_dir = app.config['UPLOAD_FOLDER']
        app.logger.info(f"Tentativo di salvataggio JSON in: {uploads_dir} (path assoluto: {os.path.abspath(uploads_dir)})")
        
        # Crea la directory se non esiste
        try:
            os.makedirs(uploads_dir, exist_ok=True)
            app.logger.info(f"Directory uploads creata/verificata: {uploads_dir}")
        except Exception as e:
            app.logger.error(f"Errore nella creazione directory {uploads_dir}: {e}")
            return None
        
        # Verifica permessi di scrittura
        if not os.access(uploads_dir, os.W_OK):
            app.logger.error(f"Directory {uploads_dir} non ha permessi di scrittura")
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        date_pattern = date_str.replace('-', '')
        filename = f"estrazione_{date_pattern}_{timestamp}.json"
        filepath = os.path.join(uploads_dir, filename)
        
        app.logger.info(f"Salvataggio file JSON: {filepath}")
        
        # Salva i dati analizzati
        json_data = {
            'date': date_str,
            'site': site,
            'extraction_date': datetime.now().isoformat(),
            'count': analysis_result.get('count', 0),
            **analysis_result  # Include tutte le statistiche e dettagli
        }
        
        # Prova a salvare
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # Verifica che il file sia stato creato
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            app.logger.info(f"Estrazione salvata in JSON: {filename} (dimensione: {file_size} bytes)")
            return filename
        else:
            app.logger.error(f"File {filename} non creato dopo il salvataggio")
            return None
            
    except PermissionError as e:
        app.logger.error(f"Errore di permessi nel salvataggio JSON: {e}")
        return None
    except Exception as e:
        import traceback
        app.logger.error(f"Errore nel salvataggio JSON: {e}\n{traceback.format_exc()}")
        return None


@app.route('/estrazione_dati')
def estrazione_dati():
    """Pagina per l'estrazione dati con calendario"""
    config = load_odata_config()
    return render_template('estrazione_dati.html', odata_config=config)


@app.route('/calendario_estrazione')
def calendario_estrazione():
    """Pagina calendario per estrazione automatica"""
    return render_template('calendario_estrazione.html')


@app.route('/config_odata')
def config_odata():
    """Pagina per configurare OData"""
    config = load_odata_config()
    return render_template('config_odata.html', config=config)


@app.route('/api/save_odata_config', methods=['POST'])
def save_odata_config_api():
    """API per salvare la configurazione OData"""
    try:
        data = request.get_json()
        config = {
            'odata_url': data.get('odata_url', 'https://voiapp.fr'),
            'odata_endpoint': data.get('odata_endpoint', 'michelinpal/odata/DMX'),
            'requires_auth': data.get('requires_auth', True),
            'auth_type': data.get('auth_type', 'basic'),
            'auth_username': data.get('auth_username', ''),
            'auth_password': data.get('auth_password', ''),
            'auth_token': data.get('auth_token', ''),
            'date_field': data.get('date_field', 'LaunchDate'),
            'site_field': data.get('site_field', 'SiteName')
        }
        
        if save_odata_config(config):
            return jsonify({'success': True, 'message': 'Configurazione salvata con successo'})
        else:
            return jsonify({'error': 'Errore nel salvataggio'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/estrai_dati', methods=['POST'])
def estrai_dati():
    """API endpoint per estrarre dati da OData con filtro data"""
    try:
        data = request.get_json()
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        site = data.get('site', '')
        date_field = data.get('date_field', 'LaunchDate')
        
        if not date_debut or not date_fin:
            return jsonify({'error': 'Date di inizio e fine sono obbligatorie'}), 400
        
        # Converti le date
        try:
            date_start = datetime.strptime(date_debut, '%Y-%m-%d').date()
            date_end = datetime.strptime(date_fin, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato data non valido. Usa YYYY-MM-DD'}), 400
        
        # Carica configurazione OData
        config = load_odata_config()
        # URL corretto trovato nel codice VBA: https://voiapp.fr/michelinpal/odata/DMX
        odata_base_url = config.get('odata_url', 'https://voiapp.fr')
        odata_endpoint = config.get('odata_endpoint', 'michelinpal/odata/DMX')
        date_field = config.get('date_field', 'LaunchDate')
        site_field = config.get('site_field', 'SiteName')  # Cambiato da 'Site' a 'SiteName'
        
        # Costruisci URL completo
        if odata_endpoint:
            odata_url = f"{odata_base_url.rstrip('/')}/{odata_endpoint.lstrip('/')}"
        else:
            odata_url = f"{odata_base_url.rstrip('/')}/michelinpal/odata/DMX"
        
        # Costruisci il filtro OData seguendo la logica del codice VBA
        # Il VBA usa: day(LaunchDate) ge X and day(LaunchDate) le Y and month(LaunchDate) eq Z
        # Per Torino (TST), usa SiteName eq 'TST'
        
        # Estrai sito (per Torino: "TST - EDC Torino" -> "TST")
        site_code = ''
        if site and site != '' and site != 'Tous':
            # Estrai il codice sito (primi 3 caratteri prima di "-")
            if '-' in site:
                site_code = site.split('-')[0].strip()
            else:
                site_code = site[:3].strip()
        
        # Costruisci filtro come nel VBA
        # Formato VBA: day(LaunchDate) ge X and day(LaunchDate) le Y and month(LaunchDate) eq Z
        day_start = date_start.day
        day_end = date_end.day
        month = date_start.month
        year = date_start.year
        
        filters = []
        
        # Filtro sito
        if site_code:
            filters.append(f"{site_field} eq '{site_code}'")
        
        # Filtro data - usa la stessa logica del VBA
        if date_start == date_end:
            # Stesso giorno: day(LaunchDate) eq X and month(LaunchDate) eq Y and year(LaunchDate) eq Z
            filters.append(f"day({date_field}) eq {day_start} and month({date_field}) eq {month} and year({date_field}) eq {year}")
        elif date_start.month == date_end.month:
            # Stesso mese: day(LaunchDate) ge X and day(LaunchDate) le Y and month(LaunchDate) eq Z
            filters.append(f"day({date_field}) ge {day_start} and day({date_field}) le {day_end} and month({date_field}) eq {month}")
        else:
            # Mesi diversi: usa range con date
            date_start_str = date_start.strftime('%Y-%m-%dT00:00:00Z')
            date_end_str = date_end.strftime('%Y-%m-%dT23:59:59Z')
            filters.append(f"{date_field} ge {date_start_str} and {date_field} le {date_end_str}")
        
        filter_query = ' and '.join(filters)
        
        # Campi da selezionare (come nel VBA)
        detail_col = "Id,Route,ShipTo,CustomerName,CustomerAddress,CustomerPostCode,CustomerCity,PAYS,CAI,ItemDescription,SiteName,Weight,LaunchDate,Carrier,CarrierMode,Reservation,InvRem,PalletId,PalletScanDate,TransportPalletId,TransportPalletScanDate,LoadingId,LoadingDate,REF,LoadingPosition,GROUPE,Quantity,CustomerRef,EXPDLVDAT,CAC,REF_CLIENT,ADD,YDMXId"
        
        # IMPORTANTE: Power Query OData.Feed() non è la stessa cosa di una chiamata HTTP diretta
        # Power Query negozia automaticamente il formato e l'endpoint corretto
        # Per chiamate HTTP dirette, potremmo aver bisogno di un endpoint specifico
        
        # Costruisci URL - prova diverse varianti
        # Costruisci URL seguendo esattamente il formato del VBA
        # VBA usa: https://voiapp.fr/michelinpal/odata/DMX?$filter=...&$orderby=LaunchDate&$select=...
        filter_encoded = quote(filter_query)
        select_encoded = quote(detail_col)
        
        # URL completo come nel VBA (con %24 invece di $ per encoding)
        full_url = f"{odata_url}?$filter={filter_encoded}&$orderby={date_field}&$select={select_encoded}"
        
        print(f"URL OData costruito (come VBA): {full_url}")
        
        # Fai la richiesta
        try:
            # Aggiungi logging per debug
            print(f"Tentativo di connessione a: {full_url}")
            
            # Headers per OData (come Power Query)
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            # Preparazione autenticazione
            auth = None
            requires_auth = config.get('requires_auth', True)  # Default True
            
            if requires_auth:
                auth_type = config.get('auth_type', 'basic')
                auth_username = config.get('auth_username', '').strip()
                auth_password = config.get('auth_password', '').strip()
                auth_token = config.get('auth_token', '').strip()
                
                if auth_type == 'basic':
                    if not auth_username or not auth_password:
                        return jsonify({
                            'error': 'Credenziali API mancanti',
                            'message': 'Le credenziali API (username e password) non sono configurate.',
                            'hint': 'Vai su /config_odata e inserisci Nome Utente API e Password API nella sezione Autenticazione',
                            'action': 'config_required'
                        }), 401
                    
                    # Usa Basic Auth con requests.auth
                    from requests.auth import HTTPBasicAuth
                    auth = HTTPBasicAuth(auth_username, auth_password)
                    print(f"Usando Basic Auth con username: {auth_username}")
                elif auth_type == 'bearer':
                    if not auth_token:
                        return jsonify({
                            'error': 'Token Bearer mancante',
                            'message': 'Il Bearer Token non è configurato.',
                            'hint': 'Vai su /config_odata e inserisci il Bearer Token',
                            'action': 'config_required'
                        }), 401
                    headers['Authorization'] = f'Bearer {auth_token}'
                elif auth_type == 'api_key':
                    if not auth_token:
                        return jsonify({
                            'error': 'API Key mancante',
                            'message': 'L\'API Key non è configurata.',
                            'hint': 'Vai su /config_odata e inserisci l\'API Key',
                            'action': 'config_required'
                        }), 401
                    headers['X-API-Key'] = auth_token
            else:
                # Se requires_auth è False ma il server richiede autenticazione
                print("ATTENZIONE: Autenticazione disabilitata ma il server potrebbe richiederla")
            
            print(f"Richiesta a: {full_url}")
            print(f"Headers: {headers}")
            if auth:
                print("Autenticazione: Basic Auth abilitata")
            
            # Timeout ridotto a 15 secondi per evitare timeout del worker
            response = requests.get(full_url, headers=headers, auth=auth, timeout=15, allow_redirects=True)
            
            print(f"Status code: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            
            # Se la risposta non è OK
            if response.status_code != 200:
                error_msg = f"Errore HTTP {response.status_code}"
                
                # Gestione specifica per 401 (Unauthorized)
                if response.status_code == 401:
                    try:
                        error_json = response.json()
                        if 'odata.error' in error_json:
                            odata_error = error_json['odata.error'].get('message', {})
                            error_value = odata_error.get('value', 'Authorization denied')
                            error_msg = f"Errore di autenticazione (401): {error_value}"
                    except:
                        error_msg = "Errore di autenticazione (401): Authorization has been denied for this request"
                    
                    # Verifica se le credenziali sono configurate
                    auth_configured = False
                    if config.get('requires_auth'):
                        auth_type = config.get('auth_type', 'basic')
                        if auth_type == 'basic':
                            auth_configured = bool(config.get('auth_username') and config.get('auth_password'))
                        else:
                            auth_configured = bool(config.get('auth_token'))
                    
                    hint_msg = 'Errore di autenticazione. '
                    if not auth_configured:
                        hint_msg += 'Le credenziali non sono configurate. Vai su /config_odata e inserisci Username e Password API.'
                    else:
                        hint_msg += 'Verifica: 1) Username e Password API sono corretti, 2) Le credenziali hanno i permessi per accedere a questo endpoint, 3) Le credenziali non sono scadute'
                    
                    return jsonify({
                        'error': error_msg,
                        'message': 'Le credenziali fornite non sono valide o non hanno i permessi necessari.',
                        'url_tried': full_url,
                        'status_code': 401,
                        'hint': hint_msg,
                        'credentials_configured': auth_configured
                    }), 401
                
                # Altri errori
                if response.text:
                    error_msg += f": {response.text[:500]}"
                return jsonify({
                    'error': error_msg,
                    'url_tried': full_url,
                    'status_code': response.status_code,
                    'hint': 'Verifica la configurazione OData. URL corretto: https://voiapp.fr/michelinpal/odata/DMX'
                }), response.status_code
            
            print(f"Response preview (first 500 chars): {response.text[:500]}")
            
            # Prova a parsare come JSON
            try:
                data_json = response.json()
                print(f"Dati ricevuti (tipo): {type(data_json)}")
                if isinstance(data_json, dict):
                    print(f"Chiavi nel JSON: {list(data_json.keys())[:10]}")
                
                # Se è un feed OData, estrai i valori
                if 'value' in data_json:
                    records = data_json['value']
                elif isinstance(data_json, list):
                    records = data_json
                else:
                    records = [data_json]
                
                # Converti in DataFrame per facilità di gestione
                if not records:
                    # Crea un DataFrame vuoto con le colonne standard se non ci sono dati
                    df = pd.DataFrame(columns=['Id', 'Route', 'ShipTo', 'CustomerName', 'CustomerAddress', 
                                               'CustomerPostCode', 'CustomerCity', 'PAYS', 'CAI', 'ItemDescription',
                                               'SiteName', 'Weight', 'LaunchDate', 'Carrier', 'CarrierMode',
                                               'Reservation', 'InvRem', 'PalletId', 'PalletScanDate', 
                                               'TransportPalletId', 'TransportPalletScanDate', 'LoadingId',
                                               'LoadingDate', 'REF', 'LoadingPosition', 'GROUPE', 'Quantity',
                                               'CustomerRef', 'EXPDLVDAT', 'CAC', 'REF_CLIENT', 'ADD', 'YDMXId'])
                else:
                    df = pd.DataFrame(records)
                
                # Salva come CSV (come "Voiteq Data DMX" nel VBA)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"Voiteq_Data_DMX_{date_start.strftime('%Y%m%d')}_{date_end.strftime('%Y%m%d')}_{timestamp}.csv"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                df.to_csv(filepath, index=False, encoding='utf-8-sig', sep=';')
                
                if len(records) == 0:
                    return jsonify({
                        'success': True,
                        'filename': filename,
                        'count': 0,
                        'message': 'Nessun dato trovato per le date selezionate. File vuoto creato.',
                        'warning': True
                    })
                
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'count': len(records),
                    'message': f'Estratti {len(records)} record con successo'
                })
                
            except ValueError as ve:
                # Se non è JSON, potrebbe essere XML o altro formato
                print(f"Errore parsing JSON: {ve}")
                print(f"Content-Type: {response.headers.get('Content-Type')}")
                print(f"Response (first 1000 chars): {response.text[:1000]}")
                
                # Salva come file raw per analisi
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"estrazione_{date_start.strftime('%Y%m%d')}_{date_end.strftime('%Y%m%d')}_{timestamp}.txt"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'count': 0,
                    'message': 'Dati estratti (formato non JSON, salvato come file raw). Controlla il file per vedere il formato della risposta.',
                    'warning': 'La risposta non è in formato JSON. Potrebbe essere necessario modificare l\'endpoint OData.'
                })
                
        except requests.exceptions.RequestException as e:
            error_detail = str(e)
            print(f"Errore richiesta: {error_detail}")
            return jsonify({
                'error': f'Errore nella connessione a OData: {error_detail}',
                'url_tried': full_url,
                'hint': 'Verifica: 1) URL corretto, 2) Connessione internet, 3) Endpoint OData specifico necessario'
            }), 500
        
    except Exception as e:
        return jsonify({'error': f'Errore durante l\'estrazione: {str(e)}'}), 500


@app.route('/api/download_estrazione/<filename>')
def download_estrazione(filename):
    """Endpoint per scaricare il file estratto"""
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    else:
        return jsonify({'error': 'File non trovato'}), 404


@app.route('/api/estrai_dati_json', methods=['POST'])
def estrai_dati_json():
    """API endpoint per estrarre dati e salvarli in JSON (per calendario)"""
    try:
        data = request.get_json()
        date_str = data.get('date')
        site = data.get('site', 'TST - EDC Torino')
        
        if not date_str:
            return jsonify({'error': 'Data non specificata'}), 400
        
        # Usa la stessa data per inizio e fine
        date_debut = date_str
        date_fin = date_str
        date_field = 'LaunchDate'
        
        # Converti le date
        try:
            date_start = datetime.strptime(date_debut, '%Y-%m-%d').date()
            date_end = datetime.strptime(date_fin, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato data non valido. Usa YYYY-MM-DD'}), 400
        
        # Carica configurazione OData
        config = load_odata_config()
        odata_base_url = config.get('odata_url', 'https://voiapp.fr')
        odata_endpoint = config.get('odata_endpoint', 'michelinpal/odata/DMX')
        date_field = config.get('date_field', date_field)
        site_field = config.get('site_field', 'SiteName')
        
        # Costruisci URL completo
        if odata_endpoint:
            odata_url = f"{odata_base_url.rstrip('/')}/{odata_endpoint.lstrip('/')}"
        else:
            odata_url = f"{odata_base_url.rstrip('/')}/michelinpal/odata/DMX"
        
        # Estrai sito (per Torino: "TST - EDC Torino" -> "TST")
        site_code = ''
        if site and site != '' and site != 'Tous':
            if '-' in site:
                site_code = site.split('-')[0].strip()
            else:
                site_code = site[:3].strip()
        
        # Costruisci filtro come nel VBA (stesso giorno)
        day_start = date_start.day
        month = date_start.month
        year = date_start.year
        
        filters = []
        if site_code:
            filters.append(f"{site_field} eq '{site_code}'")
        
        # Filtro data: stesso giorno
        filters.append(f"day({date_field}) eq {day_start} and month({date_field}) eq {month} and year({date_field}) eq {year}")
        
        filter_query = ' and '.join(filters)
        
        # Campi da selezionare
        detail_col = "Id,Route,ShipTo,CustomerName,CustomerAddress,CustomerPostCode,CustomerCity,PAYS,CAI,ItemDescription,SiteName,Weight,LaunchDate,Carrier,CarrierMode,Reservation,InvRem,PalletId,PalletScanDate,TransportPalletId,TransportPalletScanDate,LoadingId,LoadingDate,REF,LoadingPosition,GROUPE,Quantity,CustomerRef,EXPDLVDAT,CAC,REF_CLIENT,ADD,YDMXId"
        
        # Costruisci URL
        filter_encoded = quote(filter_query)
        select_encoded = quote(detail_col)
        full_url = f"{odata_url}?$filter={filter_encoded}&$orderby={date_field}&$select={select_encoded}"
        
        print(f"URL OData per JSON: {full_url}")
        
        # Headers per OData
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Autenticazione
        auth = None
        if config.get('requires_auth'):
            auth_type = config.get('auth_type', 'basic')
            auth_username = config.get('auth_username', '').strip()
            auth_password = config.get('auth_password', '').strip()
            
            if auth_type == 'basic' and auth_username and auth_password:
                from requests.auth import HTTPBasicAuth
                auth = HTTPBasicAuth(auth_username, auth_password)
        
        # Fai la richiesta
        response = requests.get(full_url, headers=headers, auth=auth, timeout=30, allow_redirects=True)
        
        if response.status_code != 200:
            error_msg = f"Errore HTTP {response.status_code}"
            if response.text:
                error_msg += f": {response.text[:500]}"
            return jsonify({'error': error_msg}), response.status_code
        
        # Parsa JSON
        try:
            data_json = response.json()
            
            # Estrai i valori
            if 'value' in data_json:
                records = data_json['value']
            elif isinstance(data_json, list):
                records = data_json
            else:
                records = [data_json]
            
            # Salva come JSON
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"estrazione_{date_start.strftime('%Y%m%d')}_{timestamp}.json"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Salva i dati in JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'date': date_str,
                    'site': site,
                    'extraction_date': datetime.now().isoformat(),
                    'count': len(records),
                    'data': records
                }, f, ensure_ascii=False, indent=2)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'count': len(records),
                'date': date_str,  # Aggiungi la data nel formato YYYY-MM-DD
                'message': f'Dati estratti e salvati in JSON: {len(records)} record'
            })
            
        except ValueError as e:
            return jsonify({'error': f'Errore nel parsing della risposta: {str(e)}'}), 500
        
    except Exception as e:
        import traceback
        print(f"Errore estrazione JSON: {traceback.format_exc()}")
        return jsonify({'error': f'Errore durante l\'estrazione: {str(e)}'}), 500


@app.route('/api/list_extractions')
def list_extractions():
    """Lista tutte le estrazioni JSON salvate nella cartella uploads"""
    try:
        extractions = []
        uploads_dir = app.config['UPLOAD_FOLDER']
        
        if os.path.exists(uploads_dir):
            # Raggruppa per data (prendi solo il file più recente per ogni data)
            date_files = {}
            for filename in os.listdir(uploads_dir):
                if filename.startswith('estrazione_') and filename.endswith('.json'):
                    filepath = os.path.join(uploads_dir, filename)
                    try:
                        mtime = os.path.getmtime(filepath)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            date_str = data.get('date', 'N/A')
                            if date_str != 'N/A':
                                # Se abbiamo già un file per questa data, prendi il più recente
                                if date_str not in date_files or mtime > date_files[date_str][1]:
                                    date_files[date_str] = (filename, mtime, data)
                    except Exception as e:
                        app.logger.warning(f"Errore nel leggere {filename}: {e}")
            
            # Crea la lista delle estrazioni
            for date_str, (filename, mtime, data) in date_files.items():
                extractions.append({
                    'filename': filename,
                    'date': date_str,
                    'site': data.get('site', 'N/A'),
                    'count': data.get('count', 0),
                    'extraction_date': data.get('extraction_date', 'N/A')
                })
        
        # Ordina per data di estrazione (più recente prima)
        extractions.sort(key=lambda x: x.get('extraction_date', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'extractions': extractions,
            'total': len(extractions)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/estrazioni')
def estrazioni():
    """Pagina per visualizzare tutte le estrazioni salvate"""
    return render_template('estrazioni.html')


@app.route('/api/download_json/<filename>')
def download_json(filename):
    """Endpoint per scaricare il file JSON estratto dalla cartella uploads"""
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename, mimetype='application/json')
    else:
        return jsonify({'error': 'File non trovato'}), 404


@app.route('/api/view_json/<filename>')
def view_json(filename):
    """Endpoint per visualizzare il file JSON in formato leggibile dalla cartella uploads"""
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        except Exception as e:
            return jsonify({'error': f'Errore nel leggere il file: {str(e)}'}), 500
    else:
        return jsonify({'error': 'File non trovato'}), 404


def analyze_odata_data(records):
    """
    Analizza i dati OData e restituisce i dati aggregati per giro (simile ad analyze_excel)
    """
    try:
        if not records:
            return {
                'success': True,
                'analysis': {},
                'details': {},
                'accessori_details': {},
                'crossdock_details': {},
                'clienti_per_giro': {},
                'product_search': {},
                'product_descriptions': {},
                'dates': [],
                'statistics': {
                    'totali': {
                        'totale_pezzi': 0,
                        'pezzi_checkati': 0,
                        'pezzi_da_checkare': 0,
                        'pezzi_accessori': 0,
                        'pezzi_crossdock': 0,
                        'totale_giri': 0,
                        'giri_completati': 0,
                        'giri_non_completati': 0,
                        'percentuale_completamento': 0,
                        'percentuale_completamento_giri': 0
                    },
                    'per_giro': [],
                    'per_cc': []
                }
            }
        
        # Converti i record in DataFrame per facilitare l'analisi
        df = pd.DataFrame(records)
        
        # DEBUG: Stampa i campi disponibili per trovare la destinazione
        if len(df) > 0:
            app.logger.info(f"Campi disponibili nel DataFrame: {list(df.columns)}")
            # Cerca un esempio di record con dati
            sample_row = df.iloc[0]
            for col in df.columns:
                val = sample_row[col]
                if pd.notna(val) and str(val).strip() != '':
                    val_str = str(val).upper()
                    if 'SICILIA' in val_str or 'DEST' in col.upper() or 'LOAD' in col.upper() or 'SHIP' in col.upper() or 'CARRIER' in col.upper() or 'GROUPE' in col.upper():
                        app.logger.info(f"Campo potenzialmente rilevante per destinazione: {col} = {val}")
        
        # Mappa i campi OData alle colonne Excel
        # Route -> Route (colonna B)
        # CAI -> CAI (colonna I, codice prodotto)
        # InvRem -> InvRem (colonna T, check)
        # CustomerName -> CustomerName (colonna D, cliente)
        # ItemDescription -> ItemDescription (colonna J, descrizione)
        # LoadingPosition -> LoadingPosition (destinazione)
        # ADD -> ADD (colonna AF, ubicazione) - CORRETTO: era REF ma deve essere ADD
        # LaunchDate -> LaunchDate (colonna AL, data)
        
        # Estrai i dati - usa accesso diretto alle colonne con gestione errori
        # Gestisci i casi in cui le colonne potrebbero non esistere o essere vuote
        df['route'] = df['Route'].fillna('') if 'Route' in df.columns else pd.Series([''] * len(df))
        df['cliente'] = df['CustomerName'].fillna('') if 'CustomerName' in df.columns else pd.Series([''] * len(df))
        df['codice_prodotto_originale'] = df['CAI'].fillna('') if 'CAI' in df.columns else pd.Series([''] * len(df))
        df['descrizione'] = df['ItemDescription'].fillna('') if 'ItemDescription' in df.columns else pd.Series([''] * len(df))
        df['check'] = df['InvRem'].fillna('') if 'InvRem' in df.columns else pd.Series([''] * len(df))
        # Funzione helper per verificare se un valore è numerico (non usarlo come destinazione)
        def is_numeric_value(val):
            """Verifica se un valore è puramente numerico"""
            if pd.isna(val) or val == '':
                return True
            val_str = str(val).strip()
            # Se è solo numeri, è numerico
            if val_str.isdigit():
                return True
            # Se è un numero decimale
            try:
                float(val_str)
                return True
            except ValueError:
                pass
            # Se contiene solo numeri e caratteri comuni di ID (es. "12345", "ID123")
            if len(val_str) > 0 and all(c.isdigit() or c in ['-', '_', '.'] for c in val_str.replace(' ', '')):
                # Se ha più di 5 caratteri e sono tutti numeri, probabilmente è un ID
                if len(val_str.replace('-', '').replace('_', '').replace('.', '')) > 5:
                    return True
            return False
        
        # Usa LoadingName come destinazione (viene dal merge con la tabella Loadings)
        # LoadingName rappresenta la destinazione della tournée, non del cliente
        # Ottimizzato: usa operazioni vettorizzate invece di loop
        df['destinazione'] = ''
        
        if 'LoadingName' in df.columns:
            # Filtra LoadingName: solo valori non numerici e non vuoti
            loading_names = df['LoadingName'].fillna('').astype(str).str.strip()
            # Applica filtro numerico in modo vettorizzato
            mask_valid = loading_names.apply(lambda x: x != '' and not is_numeric_value(x))
            df.loc[mask_valid, 'destinazione'] = loading_names[mask_valid]
        
        # Per le righe senza destinazione, cerca nelle altre righe dello stesso Route
        if 'Route' in df.columns:
            # Raggruppa per Route e trova la prima destinazione valida per ogni Route
            route_destinations = df[df['destinazione'] != ''].groupby('Route')['destinazione'].first()
            
            # Applica la destinazione trovata a tutte le righe dello stesso Route che non hanno destinazione
            for route, dest in route_destinations.items():
                mask = (df['Route'] == route) & (df['destinazione'] == '')
                df.loc[mask, 'destinazione'] = dest
        
        # DEBUG: Stampa un esempio di destinazione trovata
        if len(df) > 0 and df['destinazione'].notna().any():
            sample_dest = df[df['destinazione'].notna() & (df['destinazione'] != '')]['destinazione'].iloc[0]
            app.logger.info(f"Esempio di destinazione trovata: {sample_dest}")
        df['ubicazione'] = df['ADD'].fillna('') if 'ADD' in df.columns else pd.Series([''] * len(df))
        df['data'] = pd.to_datetime(df['LaunchDate'], errors='coerce') if 'LaunchDate' in df.columns else pd.Series([None] * len(df))
        
        # Trasforma ubicazione "1" in "CROSSDOCK"
        def transform_ubicazione(ubicazione):
            if pd.isna(ubicazione):
                return ''
            ubicazione_str = str(ubicazione).strip()
            if ubicazione_str == '1' or ubicazione_str == '1.0':
                return 'CROSSDOCK'
            return ubicazione_str
        
        df['ubicazione'] = df['ubicazione'].apply(transform_ubicazione)
        
        # Identifica accessori (ubicazione che inizia con "LX")
        def is_accessorio(ubicazione):
            if pd.isna(ubicazione):
                return False
            ubicazione_str = str(ubicazione).strip().upper()
            return ubicazione_str.startswith('LX')
        
        df['is_accessorio'] = df['ubicazione'].apply(is_accessorio)
        
        # Identifica crossdock (ubicazione = "CROSSDOCK")
        def is_crossdock(ubicazione):
            if pd.isna(ubicazione):
                return False
            ubicazione_str = str(ubicazione).strip().upper()
            return ubicazione_str == 'CROSSDOCK'
        
        df['is_crossdock'] = df['ubicazione'].apply(is_crossdock)
        
        # Trasforma i codici CAI secondo le regole e calcola CC
        def transform_cai_and_cc(row):
            codice_originale = row['codice_prodotto_originale']
            if pd.isna(codice_originale):
                return pd.Series({'codice_prodotto': '', 'cc': 'MICHELIN'})
            
            codice_str = str(codice_originale).strip().upper()
            
            # Trasforma il codice
            if codice_str.startswith('IG'):
                codice_trasformato = 'T' + str(row['codice_prodotto_originale']).strip()
                cc = 'EUROMASTER'
            elif codice_str.startswith('AR'):
                codice_trasformato = 'Y' + str(row['codice_prodotto_originale']).strip()
                cc = 'EUROMASTER'
            elif codice_str.startswith('FG'):
                codice_trasformato = 'B' + str(row['codice_prodotto_originale']).strip()
                cc = 'EUROMASTER'
            elif codice_str.startswith('SO'):
                codice_trasformato = 'C' + str(row['codice_prodotto_originale']).strip()
                cc = 'CAMSO'
            else:
                codice_trasformato = str(row['codice_prodotto_originale']).strip()
                cc = 'MICHELIN'
            
            return pd.Series({'codice_prodotto': codice_trasformato, 'cc': cc})
        
        # Applica trasformazione
        df[['codice_prodotto', 'cc']] = df.apply(transform_cai_and_cc, axis=1)
        
        # Converti la data in formato stringa (YYYY-MM-DD)
        def parse_date(date_val):
            if pd.isna(date_val):
                return None
            try:
                if isinstance(date_val, str):
                    date_val = pd.to_datetime(date_val)
                return date_val.strftime('%Y-%m-%d')
            except:
                return None
        
        df['data_str'] = df['data'].apply(parse_date)
        
        # Converti check in booleano (True se valorizzato, False altrimenti)
        df['is_checked'] = (~df['is_accessorio']) & (~df['is_crossdock']) & df['check'].notna() & (df['check'].astype(str).str.strip() != '')
        
        # Rimuovi righe con route vuoto
        df = df[df['route'].notna()]
        
        # Analisi per giro
        analysis = {}
        details = {}
        accessori_details = {}
        crossdock_details = {}
        clienti_per_giro = {}
        
        for route in df['route'].unique():
            route_df = df[df['route'] == route]
            
            totale_pezzi = len(route_df)
            pezzi_accessori = route_df['is_accessorio'].sum()
            pezzi_crossdock = route_df['is_crossdock'].sum()
            pezzi_non_accessori_crossdock = totale_pezzi - pezzi_accessori - pezzi_crossdock
            # I pezzi checkati sono solo quelli NON accessori e NON crossdock che hanno il check
            # is_checked già esclude accessori e crossdock, quindi possiamo usare direttamente sum()
            pezzi_checkati = route_df['is_checked'].sum()
            pezzi_da_checkare = pezzi_non_accessori_crossdock - pezzi_checkati
            
            # Dettagli dei pezzi non checkati
            non_checkati = route_df[(~route_df['is_checked']) & (~route_df['is_accessorio']) & (~route_df['is_crossdock'])].copy()
            dettagli_non_checkati = []
            
            # Dettagli degli accessori
            accessori = route_df[route_df['is_accessorio']].copy()
            dettagli_accessori = []
            
            # Dettagli del crossdock
            crossdock = route_df[route_df['is_crossdock']].copy()
            dettagli_crossdock = []
            
            for idx, row in non_checkati.iterrows():
                dettagli_non_checkati.append({
                    'codice_prodotto': str(row['codice_prodotto']) if pd.notna(row['codice_prodotto']) else '',
                    'cliente': str(row['cliente']) if pd.notna(row['cliente']) else '',
                    'descrizione': str(row['descrizione']) if pd.notna(row['descrizione']) else '',
                    'ubicazione': str(row['ubicazione']) if pd.notna(row['ubicazione']) else '',
                    'cc': str(row['cc']) if pd.notna(row['cc']) else 'MICHELIN',
                })
            
            for idx, row in accessori.iterrows():
                dettagli_accessori.append({
                    'codice_prodotto': str(row['codice_prodotto']) if pd.notna(row['codice_prodotto']) else '',
                    'cliente': str(row['cliente']) if pd.notna(row['cliente']) else '',
                    'descrizione': str(row['descrizione']) if pd.notna(row['descrizione']) else '',
                    'ubicazione': str(row['ubicazione']) if pd.notna(row['ubicazione']) else '',
                    'cc': str(row['cc']) if pd.notna(row['cc']) else 'MICHELIN',
                })
            
            for idx, row in crossdock.iterrows():
                dettagli_crossdock.append({
                    'codice_prodotto': str(row['codice_prodotto']) if pd.notna(row['codice_prodotto']) else '',
                    'cliente': str(row['cliente']) if pd.notna(row['cliente']) else '',
                    'descrizione': str(row['descrizione']) if pd.notna(row['descrizione']) else '',
                    'ubicazione': str(row['ubicazione']) if pd.notna(row['ubicazione']) else '',
                    'cc': str(row['cc']) if pd.notna(row['cc']) else 'MICHELIN',
                })
            
            # Prendi la destinazione - cerca in tutte le righe del giro per trovare un valore non vuoto
            destinazione = ''
            if len(route_df) > 0:
                # Cerca la prima destinazione non vuota nel giro
                for idx, row in route_df.iterrows():
                    dest_val = row.get('destinazione', '') if 'destinazione' in row else row.get('LoadingPosition', '') if 'LoadingPosition' in row else ''
                    if dest_val and pd.notna(dest_val) and str(dest_val).strip() != '' and str(dest_val).strip().lower() != 'nan':
                        destinazione = str(dest_val).strip()
                        break
            
            analysis[route] = {
                'totale_pezzi': int(totale_pezzi),
                'pezzi_checkati': int(pezzi_checkati),
                'pezzi_da_checkare': int(pezzi_da_checkare),
                'pezzi_accessori': int(pezzi_accessori),
                'pezzi_crossdock': int(pezzi_crossdock),
                'destinazione': destinazione
            }
            
            details[route] = dettagli_non_checkati
            accessori_details[route] = dettagli_accessori
            crossdock_details[route] = dettagli_crossdock
            
            # Lista clienti per giro
            route_df_for_clienti = df[df['route'] == route]
            clienti_unici_list = route_df_for_clienti['cliente'].dropna().unique().tolist()
            clienti_unici_list = [str(c).strip() for c in clienti_unici_list if str(c).strip()]
            clienti_per_giro[route] = sorted(clienti_unici_list)
        
        # Crea un indice per la ricerca per codice prodotto
        product_search = {}
        product_descriptions = {}
        for idx, row in df.iterrows():
            codice = str(row['codice_prodotto']) if pd.notna(row['codice_prodotto']) else ''
            descrizione = str(row['descrizione']) if pd.notna(row['descrizione']) else ''
            if codice and not row['is_checked']:
                route = str(row['route'])
                if codice not in product_search:
                    product_search[codice] = {}
                if route not in product_search[codice]:
                    product_search[codice][route] = 0
                product_search[codice][route] += 1
                if codice not in product_descriptions and descrizione:
                    product_descriptions[codice] = descrizione
        
        # Calcola statistiche totali
        totale_pezzi_globali = len(df)
        totale_pezzi_accessori = df['is_accessorio'].sum()
        totale_pezzi_crossdock = df['is_crossdock'].sum()
        totale_pezzi_non_accessori_crossdock = totale_pezzi_globali - totale_pezzi_accessori - totale_pezzi_crossdock
        totale_pezzi_checkati = df['is_checked'].sum()
        totale_pezzi_da_checkare = totale_pezzi_non_accessori_crossdock - totale_pezzi_checkati
        totale_giri = len(df['route'].unique())
        
        # Calcola giri completati
        giri_completati = 0
        giri_non_completati = 0
        for route, data in analysis.items():
            if data['totale_pezzi'] > 0:
                if data['pezzi_da_checkare'] == 0:
                    giri_completati += 1
                else:
                    giri_non_completati += 1
            else:
                giri_non_completati += 1
        
        percentuale_completamento_giri = round((giri_completati / totale_giri * 100) if totale_giri > 0 else 0, 2)
        
        # Calcola statistiche per Centro di Costo (CC)
        stats_per_cc = {}
        for idx, row in df.iterrows():
            cc = row['cc']
            if cc not in stats_per_cc:
                stats_per_cc[cc] = {
                    'totale_pezzi': 0,
                    'pezzi_checkati': 0,
                    'pezzi_da_checkare': 0,
                    'pezzi_accessori': 0,
                    'pezzi_crossdock': 0
                }
            stats_per_cc[cc]['totale_pezzi'] += 1
            if row['is_accessorio']:
                stats_per_cc[cc]['pezzi_accessori'] += 1
            elif row['is_crossdock']:
                stats_per_cc[cc]['pezzi_crossdock'] += 1
            elif row['is_checked']:
                stats_per_cc[cc]['pezzi_checkati'] += 1
            else:
                stats_per_cc[cc]['pezzi_da_checkare'] += 1
        
        # Converti in lista per il JSON
        stats_cc_list = []
        for cc, stats in stats_per_cc.items():
            # La percentuale è calcolata su tutti i pezzi totali, non escludendo accessori e crossdock
            stats_cc_list.append({
                'cc': cc,
                'totale_pezzi': int(stats['totale_pezzi']),
                'pezzi_checkati': int(stats['pezzi_checkati']),
                'pezzi_da_checkare': int(stats['pezzi_da_checkare']),
                'pezzi_accessori': int(stats['pezzi_accessori']),
                'pezzi_crossdock': int(stats['pezzi_crossdock']),
                'percentuale': round((stats['pezzi_checkati'] / stats['totale_pezzi'] * 100) if stats['totale_pezzi'] > 0 else 0, 2)
            })
        
        # Statistiche per giri
        stats_per_giro = []
        for route, data in analysis.items():
            pezzi_non_accessori_crossdock = data['totale_pezzi'] - data.get('pezzi_accessori', 0) - data.get('pezzi_crossdock', 0)
            
            route_df_for_cc = df[df['route'] == route]
            cc_set = set()
            for idx, row in route_df_for_cc.iterrows():
                cc = str(row['cc']) if pd.notna(row['cc']) else 'MICHELIN'
                cc_set.add(cc)
            
            cc_list = sorted(list(cc_set)) if cc_set else ['MICHELIN']
            
            route_df_for_clienti = df[df['route'] == route]
            clienti_unici_list = route_df_for_clienti['cliente'].dropna().unique().tolist()
            clienti_unici_list = [str(c).strip() for c in clienti_unici_list if str(c).strip()]
            clienti_unici = len(clienti_unici_list)
            
            # Calcola la percentuale di completamento
            # La percentuale è: (pezzi checkati / pezzi totali) * 100
            # Su tutti i pezzi, non escludendo accessori e crossdock
            totale = int(data['totale_pezzi'])
            checkati = int(data['pezzi_checkati'])
            
            if totale > 0 and checkati >= 0:
                # Calcola la percentuale come float
                percentuale = float(checkati) / float(totale) * 100.0
                percentuale = round(percentuale, 2)
                # Assicurati che la percentuale sia tra 0 e 100
                percentuale = max(0.0, min(percentuale, 100.0))
            else:
                percentuale = 0.0
            
            # DEBUG: Log per verificare il calcolo per route HI e KH
            if route == 'HI' or route == 'KH':
                app.logger.info(f"Route {route} - totale={totale}, checkati={checkati}, percentuale_calcolata={percentuale}, tipo={type(percentuale)}")
                # Verifica se la percentuale è sospetta (es. 16% invece di 6.16%)
                expected_percent = (checkati / totale * 100) if totale > 0 else 0
                if abs(percentuale - expected_percent) > 1:
                    app.logger.warning(f"Route {route} - Percentuale sospetta! Calcolata: {percentuale}%, Attesa: {expected_percent}%")
            
            stats_per_giro.append({
                'route': route,
                'destinazione': data['destinazione'],
                'cc': cc_list,
                'totale': data['totale_pezzi'],
                'checkati': data['pezzi_checkati'],
                'da_checkare': data['pezzi_da_checkare'],
                'pezzi_accessori': data.get('pezzi_accessori', 0),
                'pezzi_crossdock': data.get('pezzi_crossdock', 0),
                'clienti': int(clienti_unici),
                'percentuale': percentuale
            })
        
        # Estrai le date uniche
        dates = sorted([d for d in df['data_str'].dropna().unique() if d])
        
        return {
            'success': True,
            'analysis': analysis,
            'details': details,
            'accessori_details': accessori_details,
            'crossdock_details': crossdock_details,
            'clienti_per_giro': clienti_per_giro,
            'product_search': product_search,
            'product_descriptions': product_descriptions,
            'dates': dates,
            'statistics': {
                'totali': {
                    'totale_pezzi': int(totale_pezzi_globali),
                    'pezzi_checkati': int(totale_pezzi_checkati),
                    'pezzi_da_checkare': int(totale_pezzi_da_checkare),
                    'pezzi_accessori': int(totale_pezzi_accessori),
                    'pezzi_crossdock': int(totale_pezzi_crossdock),
                    'totale_giri': int(totale_giri),
                    'giri_completati': int(giri_completati),
                    'giri_non_completati': int(giri_non_completati),
                    'percentuale_completamento': round((totale_pezzi_checkati / totale_pezzi_globali * 100) if totale_pezzi_globali > 0 else 0, 2),
                    'percentuale_completamento_giri': percentuale_completamento_giri
                },
                'per_giro': stats_per_giro,
                'per_cc': stats_cc_list
            }
        }
    
    except Exception as e:
        import traceback
        print(f"Errore analisi OData: {traceback.format_exc()}")
        return {
            'success': False,
            'error': str(e)
        }


@app.route('/api/estrai_e_analizza', methods=['POST'])
def estrai_e_analizza():
    """API endpoint per estrarre dati OData, analizzarli e restituirli (senza salvare JSON)
    Usa la cache se l'API non restituisce dati (es. per date oltre 7 giorni)"""
    try:
        data = request.get_json()
        date_str = data.get('date')
        site = data.get('site', 'TST - EDC Torino')
        
        if not date_str:
            return jsonify({'error': 'Data non specificata'}), 400
        
        # Usa la stessa data per inizio e fine
        date_debut = date_str
        date_fin = date_str
        date_field = 'LaunchDate'
        
        # Converti le date
        try:
            date_start = datetime.strptime(date_debut, '%Y-%m-%d').date()
            date_end = datetime.strptime(date_fin, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato data non valido. Usa YYYY-MM-DD'}), 400
        
        # Controlla se esiste un JSON salvato per questa data (come fallback)
        json_data = get_json_extraction(date_str, site)
        if json_data:
            app.logger.info(f"Trovato JSON salvato per {date_str}")
        
        # Carica configurazione OData
        config = load_odata_config()
        odata_base_url = config.get('odata_url', 'https://voiapp.fr')
        odata_endpoint = config.get('odata_endpoint', 'michelinpal/odata/DMX')
        date_field = config.get('date_field', date_field)
        site_field = config.get('site_field', 'SiteName')
        
        # Costruisci URL completo
        if odata_endpoint:
            odata_url = f"{odata_base_url.rstrip('/')}/{odata_endpoint.lstrip('/')}"
        else:
            odata_url = f"{odata_base_url.rstrip('/')}/michelinpal/odata/DMX"
        
        # Estrai sito (per Torino: "TST - EDC Torino" -> "TST")
        site_code = ''
        if site and site != '' and site != 'Tous':
            if '-' in site:
                site_code = site.split('-')[0].strip()
            else:
                site_code = site[:3].strip()
        
        # Costruisci filtro come nel VBA (stesso giorno)
        day_start = date_start.day
        month = date_start.month
        year = date_start.year
        
        filters = []
        if site_code:
            filters.append(f"{site_field} eq '{site_code}'")
        
        # Filtro data: stesso giorno
        filters.append(f"day({date_field}) eq {day_start} and month({date_field}) eq {month} and year({date_field}) eq {year}")
        
        filter_query = ' and '.join(filters)
        
        # Campi da selezionare
        detail_col = "Id,Route,ShipTo,CustomerName,CustomerAddress,CustomerPostCode,CustomerCity,PAYS,CAI,ItemDescription,SiteName,Weight,LaunchDate,Carrier,CarrierMode,Reservation,InvRem,PalletId,PalletScanDate,TransportPalletId,TransportPalletScanDate,LoadingId,LoadingDate,REF,LoadingPosition,GROUPE,Quantity,CustomerRef,EXPDLVDAT,CAC,REF_CLIENT,ADD,YDMXId"
        
        # Costruisci URL
        filter_encoded = quote(filter_query)
        select_encoded = quote(detail_col)
        full_url = f"{odata_url}?$filter={filter_encoded}&$orderby={date_field}&$select={select_encoded}"
        
        # Headers per OData
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Autenticazione
        auth = None
        if config.get('requires_auth'):
            auth_type = config.get('auth_type', 'basic')
            auth_username = config.get('auth_username', '').strip()
            auth_password = config.get('auth_password', '').strip()
            
            if auth_type == 'basic' and auth_username and auth_password:
                from requests.auth import HTTPBasicAuth
                auth = HTTPBasicAuth(auth_username, auth_password)
        
        # Fai la richiesta all'API
        response = requests.get(full_url, headers=headers, auth=auth, timeout=30, allow_redirects=True)
        
        api_has_data = False
        records = []
        
        if response.status_code == 200:
            # Parsa JSON solo se la risposta è OK
            try:
                data_json = response.json()
                
                # Estrai i valori
                if 'value' in data_json:
                    records = data_json['value']
                elif isinstance(data_json, list):
                    records = data_json
                else:
                    records = [data_json]
                
                # Se ci sono record, l'API ha restituito dati
                if records and len(records) > 0:
                    api_has_data = True
            except ValueError:
                # Errore nel parsing JSON
                pass
        
        # Se l'API non ha restituito dati, usa JSON salvato se disponibile
        if not api_has_data:
            if json_data:
                app.logger.info(f"API non ha restituito dati per {date_str}, uso JSON salvato")
                result = json_data.copy()
                result['from_json'] = True
                result['api_available'] = False
                return jsonify(result)
            else:
                # Nessun dato dall'API e nessun JSON disponibile
                if response.status_code != 200:
                    error_msg = f"Errore HTTP {response.status_code}"
                    if response.text:
                        error_msg += f": {response.text[:500]}"
                    app.logger.warning(f"Errore API e nessun JSON disponibile per {date_str}: {error_msg}")
                    return jsonify({
                        'error': error_msg,
                        'from_json': False,
                        'json_available': False,
                        'message': 'Nessun dato disponibile dall\'API e nessuna estrazione precedente salvata per questa data.'
                    }), response.status_code
                else:
                    app.logger.info(f"API restituita vuota per {date_str}, nessun JSON disponibile")
                    return jsonify({
                        'error': 'Nessun dato disponibile per questa data',
                        'from_json': False,
                        'json_available': False,
                        'count': 0,
                        'message': 'L\'API non ha restituito dati per questa data e non esiste una estrazione precedente salvata.'
                    }), 404
        
        # Se arriviamo qui, l'API ha restituito dati - continua con l'elaborazione normale
        # Carica anche i dati dalla tabella Loadings per ottenere LoadingName
        loadings_dict = {}
        try:
                loadings_url = f"{odata_base_url.rstrip('/')}/michelinpal/odata/Loadings"
                app.logger.info(f"Caricamento Loadings da: {loadings_url}")
                loadings_response = requests.get(loadings_url, headers=headers, auth=auth, timeout=30, allow_redirects=True)
                app.logger.info(f"Risposta Loadings: status={loadings_response.status_code}")
                if loadings_response.status_code == 200:
                    loadings_json = loadings_response.json()
                    loadings_records = loadings_json.get('value', []) if 'value' in loadings_json else (loadings_json if isinstance(loadings_json, list) else [])
                    
                    # Crea un dizionario: LoadingId -> LoadingName
                    # Dalla formula VBA: VLOOKUP(V2;'Voiteq Data Loadings'!A:I;2;FALSE)
                    # Quindi colonna A è LoadingId, colonna B è LoadingName
                    # Ma dalla riga 309 del VBA, LoadingName viene calcolato come concatenazione di A2 ed E2
                    for loading in loadings_records:
                        if isinstance(loading, dict):
                            loading_id = None
                            loading_name = None
                            
                            # Cerca LoadingId - potrebbe essere in vari campi
                            if 'LoadingId' in loading:
                                loading_id = loading['LoadingId']
                            elif 'Id' in loading:
                                loading_id = loading['Id']
                            elif len(loading) > 0:
                                # Prendi il primo campo come LoadingId (colonna A)
                                first_key = list(loading.keys())[0]
                                loading_id = loading[first_key]
                            
                            # Cerca LoadingName - prima cerca un campo esplicito
                            if 'LoadingName' in loading:
                                loading_name = loading['LoadingName']
                            elif 'Name' in loading:
                                loading_name = loading['Name']
                            elif len(loading) > 1:
                                # Prendi il secondo campo (colonna B) come LoadingName
                                keys_list = list(loading.keys())
                                if len(keys_list) > 1:
                                    second_key = keys_list[1]
                                    loading_name = loading[second_key]
                                    
                                    # Cerca anche un campo che contiene "Name" nel nome
                                    for key in loading.keys():
                                        if 'name' in key.lower() and key.lower() not in ['loadingid', 'id']:
                                            loading_name = loading[key]
                                            break
                            
                            # Se non abbiamo LoadingName ma abbiamo LoadingId e altri campi,
                            # prova a costruirlo come nel VBA (concatenazione di A ed E)
                            if loading_id is not None and not loading_name:
                                keys_list = list(loading.keys())
                                if len(keys_list) >= 5:
                                    # Prova a concatenare il primo e il quinto campo (A ed E)
                                    first_val = str(loading[keys_list[0]]) if keys_list[0] in loading and pd.notna(loading[keys_list[0]]) else ''
                                    fifth_val = str(loading[keys_list[4]]) if len(keys_list) > 4 and keys_list[4] in loading and pd.notna(loading[keys_list[4]]) else ''
                                    if first_val or fifth_val:
                                        loading_name = f"{first_val}{fifth_val}".strip()
                            
                            # Se ancora non abbiamo LoadingName, prova tutti i campi che potrebbero contenere un nome
                            if loading_id is not None and not loading_name:
                                for key, value in loading.items():
                                    if value and pd.notna(value):
                                        val_str = str(value).strip()
                                        # Se il valore contiene lettere e non è solo numeri, potrebbe essere un nome
                                        if val_str and not val_str.isdigit() and any(c.isalpha() for c in val_str):
                                            # Evita campi che sono chiaramente ID o date
                                            if key.lower() not in ['id', 'loadingid', 'date', 'loadingdate', 'chatstartdat', 'chaenddate']:
                                                loading_name = val_str
                                                break
                            
                            if loading_id is not None and loading_name:
                                loadings_dict[str(loading_id)] = str(loading_name).strip()
        except Exception as e:
            app.logger.warning(f"Errore nel caricamento dei Loadings (continuerò senza): {str(e)}")
        
        # Aggiungi LoadingName ai record DMX usando LoadingId
        matched_count = 0
        unmatched_count = 0
        for record in records:
            if isinstance(record, dict):
                if 'LoadingId' in record and record['LoadingId']:
                    loading_id = str(record['LoadingId']).strip()
                    if loading_id in loadings_dict:
                        record['LoadingName'] = loadings_dict[loading_id]
                        matched_count += 1
                    else:
                        record['LoadingName'] = ''
                        unmatched_count += 1
                else:
                    record['LoadingName'] = ''
                    unmatched_count += 1
        
        # Analizza i dati (come analyze_excel)
        analysis_result = analyze_odata_data(records)
        
        if not analysis_result.get('success'):
            return jsonify(analysis_result), 500
        
        # Aggiungi informazioni aggiuntive
        analysis_result['date'] = date_str
        analysis_result['site'] = site
        analysis_result['extraction_date'] = datetime.now().isoformat()
        analysis_result['count'] = len(records)
        analysis_result['from_json'] = False
        analysis_result['api_available'] = True
        
        # Salva SEMPRE in JSON per mantenere lo storico
        saved_filename = save_json_extraction(date_str, site, analysis_result)
        if saved_filename:
            analysis_result['saved_filename'] = saved_filename
        
        return jsonify(analysis_result)
        
    except Exception as e:
        import traceback
        print(f"Errore estrazione e analisi: {traceback.format_exc()}")
        return jsonify({'error': f'Errore durante l\'estrazione: {str(e)}'}), 500


@app.route('/risultati/<date_str>')
def risultati(date_str):
    """Pagina a tutto schermo per visualizzare i risultati analizzati per una data specifica
    Fa chiamata OData diretta con timeout breve, usa cache come fallback"""
    try:
        app.logger.info(f"Inizio estrazione risultati per data: {date_str}")
        
        # Estrai e analizza i dati per la data specificata
        site = 'TST - EDC Torino'
        date_field = 'LaunchDate'
        
        # Converti la data
        try:
            date_start = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Formato data non valido', 'error')
            return redirect(url_for('calendario_estrazione'))
        
        # Controlla se esiste un JSON salvato per questa data (come fallback)
        json_data = get_json_extraction(date_str, site)
        
        # Carica configurazione OData
        config = load_odata_config()
        odata_base_url = config.get('odata_url', 'https://voiapp.fr')
        odata_endpoint = config.get('odata_endpoint', 'michelinpal/odata/DMX')
        date_field = config.get('date_field', date_field)
        site_field = config.get('site_field', 'SiteName')
        
        # Costruisci URL completo
        if odata_endpoint:
            odata_url = f"{odata_base_url.rstrip('/')}/{odata_endpoint.lstrip('/')}"
        else:
            odata_url = f"{odata_base_url.rstrip('/')}/michelinpal/odata/DMX"
        
        # Estrai sito (per Torino: "TST - EDC Torino" -> "TST")
        site_code = ''
        if site and site != '' and site != 'Tous':
            if '-' in site:
                site_code = site.split('-')[0].strip()
            else:
                site_code = site[:3].strip()
        
        # Costruisci filtro come nel VBA (stesso giorno)
        day_start = date_start.day
        month = date_start.month
        year = date_start.year
        
        filters = []
        if site_code:
            filters.append(f"{site_field} eq '{site_code}'")
        
        # Filtro data: stesso giorno
        filters.append(f"day({date_field}) eq {day_start} and month({date_field}) eq {month} and year({date_field}) eq {year}")
        
        filter_query = ' and '.join(filters)
        
        # Campi da selezionare
        detail_col = "Id,Route,ShipTo,CustomerName,CustomerAddress,CustomerPostCode,CustomerCity,PAYS,CAI,ItemDescription,SiteName,Weight,LaunchDate,Carrier,CarrierMode,Reservation,InvRem,PalletId,PalletScanDate,TransportPalletId,TransportPalletScanDate,LoadingId,LoadingDate,REF,LoadingPosition,GROUPE,Quantity,CustomerRef,EXPDLVDAT,CAC,REF_CLIENT,ADD,YDMXId"
        
        # Costruisci URL
        filter_encoded = quote(filter_query)
        select_encoded = quote(detail_col)
        full_url = f"{odata_url}?$filter={filter_encoded}&$orderby={date_field}&$select={select_encoded}"
        
        app.logger.info(f"URL OData: {full_url}")
        
        # Headers per OData
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Autenticazione
        auth = None
        if config.get('requires_auth'):
            auth_type = config.get('auth_type', 'basic')
            auth_username = config.get('auth_username', '').strip()
            auth_password = config.get('auth_password', '').strip()
            
            if auth_type == 'basic' and auth_username and auth_password:
                from requests.auth import HTTPBasicAuth
                auth = HTTPBasicAuth(auth_username, auth_password)
                app.logger.info(f"Autenticazione configurata: username={auth_username}")
        
        # Fai la richiesta DMX con timeout molto breve (10 secondi)
        records = []
        try:
            app.logger.info(f"Inizio richiesta OData per {date_str} (timeout 10s)")
            app.logger.info(f"URL completo: {full_url}")
            app.logger.info(f"Auth configurata: {auth is not None}")
            
            response = requests.get(full_url, headers=headers, auth=auth, timeout=10, allow_redirects=True)
            app.logger.info(f"Risposta OData ricevuta: status={response.status_code}, size={len(response.content) if response.content else 0} bytes")
            
            if response.status_code == 200:
                data_json = response.json()
                if 'value' in data_json:
                    records = data_json['value']
                elif isinstance(data_json, list):
                    records = data_json
                else:
                    records = [data_json]
                app.logger.info(f"API ha restituito {len(records)} record per {date_str}")
        except requests.exceptions.Timeout:
            app.logger.warning(f"Timeout OData per {date_str}, uso JSON salvato se disponibile")
            if json_data:
                result = json_data.copy()
                result['from_json'] = True
                result['api_available'] = False
                result['error'] = 'Timeout nella richiesta OData, dati dal JSON salvato'
                return render_template('risultati.html', data=result)
            else:
                error_data = {
                    'success': False,
                    'error': 'Timeout nella richiesta OData. Riprova più tardi o estrai i dati dal calendario.',
                    'date': date_str,
                    'statistics': {
                        'totali': {
                            'totale_pezzi': 0,
                            'pezzi_checkati': 0,
                            'pezzi_da_checkare': 0,
                            'pezzi_accessori': 0,
                            'pezzi_crossdock': 0,
                            'totale_giri': 0,
                            'giri_completati': 0,
                            'giri_non_completati': 0,
                            'percentuale_completamento': 0,
                            'percentuale_completamento_giri': 0
                        },
                        'per_giro': [],
                        'per_cc': []
                    },
                    'details': {},
                    'accessori_details': {},
                    'crossdock_details': {},
                    'clienti_per_giro': {},
                    'product_search': {},
                    'product_descriptions': {}
                }
                return render_template('risultati.html', data=error_data)
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Errore OData per {date_str}: {e}")
            if json_data:
                result = json_data.copy()
                result['from_json'] = True
                result['api_available'] = False
                result['error'] = f'Errore OData: {str(e)}, dati dal JSON salvato'
                return render_template('risultati.html', data=result)
            else:
                error_data = {
                    'success': False,
                    'error': f'Errore di connessione OData: {str(e)}',
                    'date': date_str,
                    'statistics': {
                        'totali': {
                            'totale_pezzi': 0,
                            'pezzi_checkati': 0,
                            'pezzi_da_checkare': 0,
                            'pezzi_accessori': 0,
                            'pezzi_crossdock': 0,
                            'totale_giri': 0,
                            'giri_completati': 0,
                            'giri_non_completati': 0,
                            'percentuale_completamento': 0,
                            'percentuale_completamento_giri': 0
                        },
                        'per_giro': [],
                        'per_cc': []
                    },
                    'details': {},
                    'accessori_details': {},
                    'crossdock_details': {},
                    'clienti_per_giro': {},
                    'product_search': {},
                    'product_descriptions': {}
                }
                return render_template('risultati.html', data=error_data)
        
        # Se non ci sono record, usa JSON salvato se disponibile
        if not records or len(records) == 0:
            app.logger.warning(f"Nessun record dall'API per {date_str}")
            if json_data:
                result = json_data.copy()
                result['from_json'] = True
                result['api_available'] = False
                result['error'] = 'Nessun dato dall\'API per questa data, dati dal JSON salvato'
                return render_template('risultati.html', data=result)
            else:
                error_data = {
                    'success': False,
                    'error': 'Nessun dato disponibile per questa data dall\'API OData.',
                    'date': date_str,
                    'statistics': {
                        'totali': {
                            'totale_pezzi': 0,
                            'pezzi_checkati': 0,
                            'pezzi_da_checkare': 0,
                            'pezzi_accessori': 0,
                            'pezzi_crossdock': 0,
                            'totale_giri': 0,
                            'giri_completati': 0,
                            'giri_non_completati': 0,
                            'percentuale_completamento': 0,
                            'percentuale_completamento_giri': 0
                        },
                        'per_giro': [],
                        'per_cc': []
                    },
                    'details': {},
                    'accessori_details': {},
                    'crossdock_details': {},
                    'clienti_per_giro': {},
                    'product_search': {},
                    'product_descriptions': {}
                }
                return render_template('risultati.html', data=error_data)
        
        # Carica Loadings per LoadingName (con timeout breve)
        loadings_dict = {}
        try:
            loadings_url = f"{odata_base_url.rstrip('/')}/michelinpal/odata/Loadings"
            loadings_response = requests.get(loadings_url, headers=headers, auth=auth, timeout=10, allow_redirects=True)
            if loadings_response.status_code == 200:
                loadings_json = loadings_response.json()
                loadings_records = loadings_json.get('value', []) if 'value' in loadings_json else (loadings_json if isinstance(loadings_json, list) else [])
                
                for loading in loadings_records:
                    if isinstance(loading, dict):
                        loading_id = None
                        loading_name = None
                        
                        if 'LoadingId' in loading:
                            loading_id = loading['LoadingId']
                        elif 'Id' in loading:
                            loading_id = loading['Id']
                        elif len(loading) > 0:
                            loading_id = loading[list(loading.keys())[0]]
                        
                        if 'LoadingName' in loading:
                            loading_name = loading['LoadingName']
                        elif 'Name' in loading:
                            loading_name = loading['Name']
                        elif len(loading) > 1:
                            keys_list = list(loading.keys())
                            if len(keys_list) > 1:
                                loading_name = loading[keys_list[1]]
                                for key in loading.keys():
                                    if 'name' in key.lower() and key.lower() not in ['loadingid', 'id']:
                                        loading_name = loading[key]
                                        break
                        
                        if loading_id is not None and loading_name:
                            loadings_dict[str(loading_id)] = str(loading_name).strip()
        except Exception as e:
            app.logger.warning(f"Errore caricamento Loadings (continuerò senza): {str(e)}")
        
        # Aggiungi LoadingName ai record
        for record in records:
            if isinstance(record, dict) and 'LoadingId' in record and record['LoadingId']:
                loading_id = str(record['LoadingId']).strip()
                record['LoadingName'] = loadings_dict.get(loading_id, '')
        
        # Analizza i dati
        app.logger.info(f"Analisi di {len(records)} record per {date_str}")
        analysis_result = analyze_odata_data(records)
        
        if not analysis_result.get('success'):
            app.logger.error(f"Errore nell'analisi per {date_str}: {analysis_result.get('error')}")
            if json_data:
                result = json_data.copy()
                result['from_json'] = True
                result['api_available'] = False
                result['error'] = f"Errore nell'analisi, dati dal JSON salvato"
                return render_template('risultati.html', data=result)
            else:
                error_data = {
                    'success': False,
                    'error': f"Errore nell'analisi: {analysis_result.get('error', 'Errore sconosciuto')}",
                    'date': date_str,
                    'statistics': {
                        'totali': {
                            'totale_pezzi': 0,
                            'pezzi_checkati': 0,
                            'pezzi_da_checkare': 0,
                            'pezzi_accessori': 0,
                            'pezzi_crossdock': 0,
                            'totale_giri': 0,
                            'giri_completati': 0,
                            'giri_non_completati': 0,
                            'percentuale_completamento': 0,
                            'percentuale_completamento_giri': 0
                        },
                        'per_giro': [],
                        'per_cc': []
                    },
                    'details': {},
                    'accessori_details': {},
                    'crossdock_details': {},
                    'clienti_per_giro': {},
                    'product_search': {},
                    'product_descriptions': {}
                }
                return render_template('risultati.html', data=error_data)
        
        # Aggiungi informazioni e salva SEMPRE in JSON
        analysis_result['date'] = date_str
        analysis_result['site'] = site
        analysis_result['extraction_date'] = datetime.now().isoformat()
        analysis_result['count'] = len(records)
        analysis_result['from_json'] = False
        analysis_result['api_available'] = True
        
        # Salva SEMPRE in JSON per mantenere lo storico
        app.logger.info(f"Tentativo di salvataggio JSON per {date_str}")
        saved_filename = save_json_extraction(date_str, site, analysis_result)
        if saved_filename:
            analysis_result['saved_filename'] = saved_filename
            app.logger.info(f"JSON salvato con successo: {saved_filename}")
        else:
            app.logger.warning(f"Impossibile salvare JSON per {date_str}, ma continuo comunque")
        
        app.logger.info(f"Rendering template risultati per {date_str}")
        return render_template('risultati.html', data=analysis_result)
        
    except Exception as e:
        import traceback
        app.logger.error(f"Errore estrazione risultati per {date_str}: {traceback.format_exc()}")
        error_data = {
            'success': False,
            'error': f'Errore durante l\'estrazione: {str(e)}',
            'date': date_str,
            'statistics': {
                'totali': {
                    'totale_pezzi': 0,
                    'pezzi_checkati': 0,
                    'pezzi_da_checkare': 0,
                    'pezzi_accessori': 0,
                    'pezzi_crossdock': 0,
                    'totale_giri': 0,
                    'giri_completati': 0,
                    'giri_non_completati': 0,
                    'percentuale_completamento': 0,
                    'percentuale_completamento_giri': 0
                },
                'per_giro': [],
                'per_cc': []
            },
            'details': {},
            'accessori_details': {},
            'crossdock_details': {},
            'clienti_per_giro': {},
            'product_search': {},
            'product_descriptions': {}
        }
        return render_template('risultati.html', data=error_data)


@app.route('/static/sw.js')
def service_worker():
    """Serve il service worker con il content-type corretto"""
    return app.send_static_file('sw.js'), 200, {'Content-Type': 'application/javascript'}


if __name__ == '__main__':
    # In produzione, Render usa gunicorn, quindi questo viene eseguito solo in locale
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    port = int(os.environ.get('PORT', 5004))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

