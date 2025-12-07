from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify
import csv
import os
import io
import json
from datetime import datetime, date, timedelta
from urllib.parse import quote
from werkzeug.utils import secure_filename
from werkzeug import exceptions as werkzeug_exceptions
import requests
import pandas as pd

# Import modulo storage per persistenza dati
try:
    import storage
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    print("⚠️ Modulo storage non disponibile, uso solo file system locale")

# Import modulo S3 per file grandi
try:
    import s3_storage
    S3_AVAILABLE = s3_storage.USE_S3
except ImportError:
    S3_AVAILABLE = False
    print("⚠️ Modulo s3_storage non disponibile, upload S3 disabilitato")

app = Flask(__name__, static_folder='static', static_url_path='/static')
# Usa la secret key da variabile d'ambiente o una di default per sviluppo
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')

# Configurazione cartella uploads
# Su Vercel (serverless), usa /tmp per i file (filesystem è read-only tranne /tmp)
# In locale o su altri hosting, usa la cartella uploads
if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
else:
    app.config['UPLOAD_FOLDER'] = 'uploads'

# Limite file size: 20MB
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max file size

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
    """Salva l'anagrafica in un file JSON o MongoDB"""
    global anagrafica_data
    if anagrafica_data:
        if STORAGE_AVAILABLE:
            storage.save_anagrafica(anagrafica_data, ANAGRAFICA_JSON)
        else:
            # Fallback: file system locale
            try:
                with open(ANAGRAFICA_JSON, 'w', encoding='utf-8') as f:
                    json.dump(anagrafica_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Errore salvataggio anagrafica: {e}")


def load_anagrafica_json():
    """Carica l'anagrafica dal file JSON o MongoDB se esiste"""
    global anagrafica_data
    if STORAGE_AVAILABLE:
        data = storage.load_anagrafica(ANAGRAFICA_JSON)
        if data:
            anagrafica_data = data
            return len(anagrafica_data)
    else:
        # Fallback: file system locale
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


def process_csv_file(input_filepath=None, output_filepath=None, file_bytes=None):
    """Processa il file CSV applicando le trasformazioni
    Può lavorare con filepath (filesystem) o file_bytes (memoria)"""
    global anagrafica_data
    
    if anagrafica_data is None:
        raise ValueError("Anagrafica non caricata. Carica prima l'anagrafica articoli.")
    
    # Se file_bytes è fornito, usa quello (memoria), altrimenti usa filepath (filesystem)
    if file_bytes:
        # Lavora in memoria
        input_data = file_bytes.decode('utf-8-sig')
        input_stream = io.StringIO(input_data)
        output_stream = io.StringIO()
    else:
        # Lavora con filesystem
        input_stream = open(input_filepath, 'r', encoding='utf-8-sig')
        output_stream = open(output_filepath, 'w', encoding='utf-8', newline='')
    
    try:
        # Rileva il delimitatore
        first_line = input_stream.readline()
        delimiter = ';' if ';' in first_line else ','
        input_stream.seek(0)  # Reset per rileggere dall'inizio
        
        rows_processed = 0
        rows_transformed = 0
        missing_codes = set()
        
        reader = csv.reader(input_stream, delimiter=delimiter)
        writer = csv.writer(output_stream, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
        
        # Leggi e scrivi l'header
        header = next(reader)
        writer.writerow(header)
        
        # Trova l'indice della colonna ARTICLE (N)
        try:
            article_col_index = header.index('ARTICLE')
        except ValueError:
            article_col_index = next((i for i, col in enumerate(header) if col.upper() == 'ARTICLE'), None)
            if article_col_index is None:
                raise ValueError("Colonna 'ARTICLE' non trovata nel file CSV")
        
        # Processa ogni riga
        for row in reader:
            if len(row) > article_col_index:
                original_code = row[article_col_index].strip() if row[article_col_index] else ''
                
                if original_code:
                    transformed_code = transform_article_code(original_code)
                    
                    if transformed_code and transformed_code.lower().startswith('cso_'):
                        search_code = transformed_code.upper()
                        if search_code in anagrafica_data:
                            replacement = anagrafica_data[search_code]
                            if replacement and replacement.strip():
                                transformed_code = replacement.strip()
                                rows_transformed += 1
                        else:
                            missing_codes.add(search_code)
                    
                    row[article_col_index] = transformed_code
                else:
                    row[article_col_index] = original_code
                
                rows_processed += 1
            
            writer.writerow(row)
        
        # Se lavoriamo in memoria, restituisci i bytes del risultato
        if file_bytes:
            output_stream.seek(0)
            result_bytes = output_stream.getvalue().encode('utf-8')
            return rows_processed, rows_transformed, list(missing_codes), result_bytes
        else:
            return rows_processed, rows_transformed, list(missing_codes)
    finally:
        if not file_bytes:
            input_stream.close()
            output_stream.close()


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
    """Endpoint per caricare e trasformare il file CSV - DEPRECATO: usa /api/upload_direct o /api/upload_chunk"""
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
    
    # Blocca file > 4.5MB - devono usare MongoDB
    max_size = 4.5 * 1024 * 1024  # 4.5MB
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > max_size:
        flash(f'File troppo grande ({file_size / 1024 / 1024:.2f}MB). I file > 4.5MB devono essere caricati tramite MongoDB. Usa il pulsante "Trasforma e Scarica" che gestisce automaticamente file grandi.', 'error')
        return redirect(url_for('index'))
    
    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        input_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_filepath)
        
        try:
            # Crea il nome del file di output nel formato: YDMXEL_YYYYMMDD_HHMM.csv
            now = datetime.now()
            output_filename = f"YDMXEL_{now.strftime('%Y%m%d_%H%M')}.csv"
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


@app.route('/api/upload_direct', methods=['POST'])
def upload_direct():
    """Endpoint DEPRECATO - usa sempre /api/upload_chunk per evitare limiti Vercel"""
    return jsonify({
        'error': 'Questo endpoint è deprecato. Usa sempre il sistema a chunk per tutti i file.',
        'message': 'Il sistema gestisce automaticamente file di qualsiasi dimensione tramite chunk.'
    }), 400


def process_uploaded_file(file_id, file_bytes, filename):
    """Processa un file caricato in MongoDB"""
    try:
        global anagrafica_data
        if anagrafica_data is None:
            return jsonify({'error': 'Anagrafica non caricata'}), 400
        
        # Salva temporaneamente per processarlo
        uploads_dir = app.config['UPLOAD_FOLDER']
        input_filepath = os.path.join(uploads_dir, f'{file_id}_{filename}')
        with open(input_filepath, 'wb') as f:
            f.write(file_bytes)
        
        # Processa il file
        now = datetime.now()
        output_filename = f"YDMXEL_{now.strftime('%Y%m%d_%H%M')}.csv"
        output_filepath = os.path.join(uploads_dir, output_filename)
        
        rows_processed, rows_transformed, missing_codes = process_csv_file(input_filepath, output_filepath)
        
        # Leggi il file trasformato
        with open(output_filepath, 'rb') as f:
            transformed_content = f.read()
        
        # Salva il risultato in MongoDB
        if STORAGE_AVAILABLE:
            client, db = storage.get_mongo_client()
            if client is not None and db is not None:
                collection = db['csv_transforms']
                collection.update_one(
                    {'file_id': file_id},
                    {
                        '$set': {
                            'output_filename': output_filename,
                            'file_data': transformed_content.hex(),
                            'rows_processed': rows_processed,
                            'rows_transformed': rows_transformed,
                            'missing_codes': missing_codes,
                            'status': 'processed',
                            'updated_at': datetime.now().isoformat()
                        }
                    }
                )
                app.logger.info(f"File trasformato salvato in MongoDB: {file_id}")
        
        # Cancella i file temporanei
        try:
            os.remove(input_filepath)
            os.remove(output_filepath)
        except:
            pass
        
        return jsonify({
            'success': True,
            'download_id': file_id,
            'outputFilename': output_filename,
            'rowsProcessed': rows_processed,
            'rowsTransformed': rows_transformed,
            'missingCodes': missing_codes,
            'hasMissingCodes': len(missing_codes) > 0
        })
    except Exception as e:
        import traceback
        app.logger.error(f"Errore processamento file: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload_chunk', methods=['POST'])
def upload_chunk():
    """Endpoint per caricare un chunk del file CSV - usa JSON per evitare limite Vercel"""
    try:
        # Accetta JSON invece di FormData per evitare limite 4.5MB
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Richiesta deve essere JSON'}), 400
        
        chunk_data_hex = data.get('chunkData')  # Base64 string invece di file
        chunk_index = int(data.get('chunkIndex', 0))
        total_chunks = int(data.get('totalChunks', 0))
        file_id = data.get('fileId')
        filename = data.get('filename', 'upload.csv')
        
        if not chunk_data_hex or chunk_index is None or total_chunks is None or not file_id:
            return jsonify({'error': 'Parametri mancanti'}), 400
        
        # Decodifica da Base64
        try:
            import base64
            chunk_bytes = base64.b64decode(chunk_data_hex)
            app.logger.info(f"Chunk {chunk_index + 1}/{total_chunks} decodificato: {len(chunk_bytes)} bytes")
        except Exception as e:
            app.logger.error(f"Errore decodifica Base64: {e}")
            return jsonify({'error': f'Formato chunk non valido: {str(e)}'}), 400
        
        # Per file grandi (> 4.5MB), usa S3 invece di MongoDB
        # I chunk vengono salvati temporaneamente in MongoDB, poi il file completo va su S3
        if not STORAGE_AVAILABLE:
            app.logger.error("STORAGE_AVAILABLE è False")
            return jsonify({'error': 'MongoDB non disponibile. Configura MONGODB_URI su Vercel.'}), 500
        
        app.logger.info(f"Tentativo salvataggio chunk {chunk_index + 1}/{total_chunks} per file {file_id}")
        success = storage.save_chunk(file_id, chunk_index, chunk_bytes)
        if success:
            app.logger.info(f"Chunk {chunk_index + 1}/{total_chunks} salvato temporaneamente per file {file_id}")
            return jsonify({
                'success': True,
                'chunkIndex': chunk_index,
                'message': f'Chunk {chunk_index + 1}/{total_chunks} caricato'
            })
        else:
            app.logger.error(f"save_chunk ha restituito False per chunk {chunk_index + 1}/{total_chunks}")
            return jsonify({'error': 'Errore nel salvataggio del chunk. Verifica la connessione MongoDB.'}), 500
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        app.logger.error(f"Errore upload chunk: {error_trace}")
        return jsonify({'error': f'Errore server: {str(e)}'}), 500


@app.route('/api/merge_chunks', methods=['POST'])
def merge_chunks():
    """Ricomponi i chunk in un file completo e processalo - tutto in MongoDB"""
    try:
        data = request.get_json()
        file_id = data.get('fileId')
        filename = data.get('filename', 'upload.csv')
        
        if not file_id:
            return jsonify({'error': 'Parametri mancanti'}), 400
        
        global anagrafica_data
        if anagrafica_data is None:
            return jsonify({'error': 'Anagrafica non caricata'}), 400
        
        # Verifica MongoDB disponibile
        if not STORAGE_AVAILABLE:
            return jsonify({'error': 'MongoDB non disponibile. Configura MONGODB_URI su Vercel.'}), 500
        
        # Ricomponi il file in MongoDB
        merged_file_id = storage.merge_chunks(file_id, filename)
        if not merged_file_id:
            return jsonify({'error': 'Errore nel merge dei chunk in MongoDB'}), 500
        
        # Recupera il file completo da MongoDB
        file_doc = storage.get_transformed_file(merged_file_id)
        if not file_doc:
            return jsonify({'error': 'File non trovato dopo il merge'}), 404
        
        # Processa il file direttamente da memoria (evita filesystem Vercel)
        file_bytes = file_doc['file_data']
        
        # Processa in memoria senza usare filesystem
        now = datetime.now()
        output_filename = f"YDMXEL_{now.strftime('%Y%m%d_%H%M')}.csv"
        
        try:
            result = process_csv_file(file_bytes=file_bytes)
            rows_processed, rows_transformed, missing_codes, transformed_content = result
        except TypeError:
            # Fallback se process_csv_file non supporta file_bytes (vecchia versione)
            # Usa filesystem temporaneo solo se necessario
            uploads_dir = app.config['UPLOAD_FOLDER']
            input_filepath = os.path.join(uploads_dir, f'{file_id}_{filename}')
            output_filepath = os.path.join(uploads_dir, output_filename)
            
            with open(input_filepath, 'wb') as f:
                f.write(file_bytes)
            
            rows_processed, rows_transformed, missing_codes = process_csv_file(input_filepath, output_filepath)
            
            with open(output_filepath, 'rb') as f:
                transformed_content = f.read()
            
            # Cancella file temporanei
            try:
                os.remove(input_filepath)
                os.remove(output_filepath)
            except:
                pass
        
        # Se il file è > 4.5MB, salvalo su S3 invece di MongoDB
        file_size = len(transformed_content)
        max_mongodb_size = 4.5 * 1024 * 1024  # 4.5MB
        
        if file_size > max_mongodb_size and S3_AVAILABLE:
            # Salva su S3 per file grandi
            if s3_storage.upload_file_to_s3(transformed_content, file_id, output_filename):
                # Salva solo metadata in MongoDB
                client, db = storage.get_mongo_client()
                if client is not None and db is not None:
                    collection = db['csv_transforms']
                    collection.update_one(
                        {'file_id': file_id},
                        {
                            '$set': {
                                'output_filename': output_filename,
                                'file_size': file_size,
                                'storage_type': 's3',
                                'rows_processed': rows_processed,
                                'rows_transformed': rows_transformed,
                                'missing_codes': missing_codes,
                                'status': 'processed',
                                'updated_at': datetime.now().isoformat()
                            }
                        },
                        upsert=True
                    )
                    app.logger.info(f"File grande salvato su S3: {file_id} ({file_size / 1024 / 1024:.2f}MB)")
                else:
                    return jsonify({'error': 'MongoDB non disponibile per salvare metadata'}), 500
            else:
                return jsonify({'error': 'Errore nel salvataggio su S3'}), 500
        else:
            # Salva in MongoDB per file piccoli
            client, db = storage.get_mongo_client()
            if client is not None and db is not None:
                collection = db['csv_transforms']
                collection.update_one(
                    {'file_id': file_id},
                    {
                        '$set': {
                            'output_filename': output_filename,
                            'file_data': transformed_content.hex(),  # Salva come hex
                            'file_size': file_size,
                            'storage_type': 'mongodb',
                            'rows_processed': rows_processed,
                            'rows_transformed': rows_transformed,
                            'missing_codes': missing_codes,
                            'status': 'processed',
                            'updated_at': datetime.now().isoformat()
                        }
                    },
                    upsert=True
                )
                app.logger.info(f"File piccolo salvato in MongoDB: {file_id} ({file_size / 1024 / 1024:.2f}MB)")
            else:
                return jsonify({'error': 'MongoDB non disponibile per salvare il risultato'}), 500
        
        return jsonify({
            'success': True,
            'download_id': file_id,  # Usa file_id come download_id
            'outputFilename': output_filename,
            'rowsProcessed': rows_processed,
            'rowsTransformed': rows_transformed,
            'missingCodes': missing_codes,
            'hasMissingCodes': len(missing_codes) > 0
        })
    except Exception as e:
        import traceback
        app.logger.error(f"Errore merge chunks: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/download_transformed/<file_id>')
def download_transformed(file_id):
    """Scarica il file trasformato da S3 (per file grandi) o MongoDB (per file piccoli)"""
    try:
        # Recupera metadata da MongoDB
        if not STORAGE_AVAILABLE:
            return jsonify({'error': 'Storage non disponibile'}), 500
        
        file_doc = storage.get_transformed_file(file_id)
        if not file_doc:
            return jsonify({'error': 'File non trovato'}), 404
        
        output_filename = file_doc.get('output_filename', 'YDMXEL_trasformato.csv')
        storage_type = file_doc.get('storage_type', 'mongodb')
        
        # Se è su S3, scarica da S3
        if storage_type == 's3' and S3_AVAILABLE:
            file_content = s3_storage.download_file_from_s3(file_id, output_filename)
            if file_content:
                # Elimina da S3 dopo il download
                s3_storage.delete_file_from_s3(file_id, output_filename)
                # Elimina metadata da MongoDB
                storage.delete_transformed_file(file_id)
                
                # Crea file temporaneo per il download
                uploads_dir = app.config['UPLOAD_FOLDER']
                temp_path = os.path.join(uploads_dir, output_filename)
                with open(temp_path, 'wb') as f:
                    f.write(file_content)
                
                return send_file(
                    temp_path,
                    as_attachment=True,
                    download_name=output_filename,
                    mimetype='text/csv'
                )
            else:
                return jsonify({'error': 'Errore nel download da S3'}), 500
        else:
            # File piccolo, scarica da MongoDB
            file_content = file_doc['file_data']
            if isinstance(file_content, str):
                # Decodifica da hex
                file_content = bytes.fromhex(file_content)
            
            # Crea file temporaneo per il download
            uploads_dir = app.config['UPLOAD_FOLDER']
            temp_path = os.path.join(uploads_dir, output_filename)
            with open(temp_path, 'wb') as f:
                f.write(file_content)
            
            # Cancella da MongoDB dopo il download
            storage.delete_transformed_file(file_id)
            
            return send_file(
                    temp_path,
                    as_attachment=True,
                    download_name=output_filename,
                    mimetype='text/csv'
                )
        
        # Fallback: cerca nel file system
        uploads_dir = app.config['UPLOAD_FOLDER']
        # Cerca file che iniziano con YDMXEL_
        for filename in os.listdir(uploads_dir):
            if filename.startswith('YDMXEL_') and filename.endswith('.csv'):
                filepath = os.path.join(uploads_dir, filename)
                return send_file(
                    filepath,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='text/csv'
                )
        
        return jsonify({'error': 'File non trovato'}), 404
        
    except Exception as e:
        app.logger.error(f"Errore download trasformato: {str(e)}")
        return jsonify({'error': str(e)}), 500


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
    """Salva la configurazione OData in JSON o MongoDB"""
    if STORAGE_AVAILABLE:
        return storage.save_odata_config(config, ODATA_CONFIG_JSON)
    else:
        # Fallback: file system locale
        try:
            with open(ODATA_CONFIG_JSON, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Errore nel salvataggio config OData: {e}")
            return False


def get_json_extraction(date_str, site='TST - EDC Torino'):
    """Recupera un'estrazione dal file JSON più recente per quella data (MongoDB o cache)"""
    uploads_dir = app.config['UPLOAD_FOLDER']
    
    if STORAGE_AVAILABLE:
        data = storage.load_extraction(date_str, site, uploads_dir)
        if data:
            return data
    
    # Fallback: file system locale
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
                    app.logger.info(f"Trovato JSON in cache per {date_str}: {filename}")
                    return json_data
        except Exception as e:
            app.logger.warning(f"Errore nel caricamento JSON {filename}: {e}")
    
    return None


def is_within_days(date_str, days=7):
    """Verifica se una data è entro N giorni da oggi"""
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        today = date.today()
        days_diff = (today - target_date).days
        return days_diff <= days
    except:
        return False


def is_today_or_yesterday(date_str):
    """Verifica se la data è oggi o ieri"""
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        today = date.today()
        yesterday = today - timedelta(days=1)
        return target_date == today or target_date == yesterday
    except:
        return False


def save_json_extraction(date_str, site, analysis_result):
    """Salva un'estrazione come file JSON nella cartella uploads o MongoDB"""
    uploads_dir = app.config['UPLOAD_FOLDER']
    
    if STORAGE_AVAILABLE:
        filename = storage.save_extraction(date_str, site, analysis_result, uploads_dir)
        if filename:
            app.logger.info(f"Estrazione {date_str} salvata in storage persistente: {filename}")
            return filename
    
    # Fallback: file system locale
    try:
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
    """Lista tutte le estrazioni JSON salvate (MongoDB o cartella uploads)"""
    try:
        uploads_dir = app.config['UPLOAD_FOLDER']
        
        if STORAGE_AVAILABLE:
            extractions = storage.list_extractions(uploads_dir)
        else:
            # Fallback: file system locale
            extractions = []
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
    """API endpoint per estrarre dati OData, analizzarli e restituirli
    SEMPRE salva il JSON dopo l'analisi
    Logica:
    - Oggi/Ieri: sempre chiamata API diretta e salva JSON
    - 2-7 giorni fa: chiamata API, se restituisce dati salva JSON
    - Oltre 7 giorni: solo JSON (non chiama API)
    """
    try:
        data = request.get_json()
        date_str = data.get('date')
        site = data.get('site', 'TST - EDC Torino')
        
        if not date_str:
            return jsonify({'error': 'Data non specificata'}), 400
        
        # Converti la data
        try:
            date_start = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato data non valido. Usa YYYY-MM-DD'}), 400
        
        # Calcola differenza giorni da oggi
        today = date.today()
        days_diff = (today - date_start).days
        
        # Controlla se esiste un JSON salvato (cache)
        json_data = get_json_extraction(date_str, site)
        
        # LOGICA: Oltre 7 giorni → solo JSON (cache), non chiamare API
        if days_diff > 7:
            app.logger.info(f"Data {date_str} è oltre 7 giorni (diff: {days_diff} giorni) → uso solo JSON cache")
            if json_data:
                result = json_data.copy()
                result['from_json'] = True
                result['api_available'] = False
                result['message'] = 'Dati dal JSON salvato (data oltre 7 giorni, API non disponibile)'
                return jsonify(result)
            else:
                return jsonify({
                    'success': False,
                    'error': f'Data oltre 7 giorni e nessun JSON salvato disponibile. L\'API OData mantiene solo gli ultimi 7 giorni.',
                    'date': date_str
                }), 404
        
        # LOGICA: Oggi/Ieri → sempre chiamata API diretta
        # LOGICA: 2-7 giorni fa → chiamata API con fallback a JSON
        # Per entrambi i casi, chiamiamo l'API
        
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
        
        # Se l'API non ha restituito dati
        if not api_has_data:
            # Se è oggi o ieri, dobbiamo sempre avere dati dall'API
            if is_today_or_yesterday(date_str):
                app.logger.warning(f"API non ha restituito dati per {date_str} (oggi/ieri) - questo non dovrebbe accadere")
                # Usa JSON se disponibile, altrimenti errore
                if json_data:
                    app.logger.info(f"Usando JSON salvato per {date_str} (oggi/ieri) come fallback")
                    result = json_data.copy()
                    result['from_json'] = True
                    result['api_available'] = False
                    result['message'] = 'Nessun dato dall\'API per oggi/ieri, uso JSON salvato'
                    return jsonify(result)
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Nessun dato disponibile dall\'API per oggi/ieri. Riprova più tardi.',
                        'date': date_str
                    }), 404
            else:
                # Per 2-7 giorni fa, usa JSON se disponibile
                if json_data:
                    app.logger.info(f"API non ha restituito dati per {date_str}, uso JSON salvato")
                    result = json_data.copy()
                    result['from_json'] = True
                    result['api_available'] = False
                    result['message'] = 'Nessun dato dall\'API, uso JSON salvato'
                    return jsonify(result)
                else:
                    # Nessun dato dall'API e nessun JSON disponibile
                    if response.status_code != 200:
                        error_msg = f"Errore HTTP {response.status_code}"
                        if response.text:
                            error_msg += f": {response.text[:500]}"
                        app.logger.warning(f"Errore API e nessun JSON disponibile per {date_str}: {error_msg}")
                        return jsonify({
                            'success': False,
                            'error': error_msg,
                            'date': date_str,
                            'message': 'Nessun dato disponibile dall\'API e nessuna estrazione precedente salvata per questa data.'
                        }), response.status_code
                    else:
                        app.logger.info(f"API restituita vuota per {date_str}, nessun JSON disponibile")
                        return jsonify({
                            'success': False,
                            'error': 'Nessun dato disponibile per questa data',
                            'date': date_str,
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
    Logica:
    - Se from_db=true: carica SOLO da MongoDB (veloce, per pagina Salvataggio)
    - Oggi/Ieri: sempre chiamata API diretta (dal calendario)
    - 2-7 giorni fa: chiamata API con fallback a JSON
    - Oltre 7 giorni: solo JSON (cache)
    """
    try:
        # Controlla se deve caricare da MongoDB (parametro from_db)
        from_db = request.args.get('from_db', 'false').lower() == 'true'
        
        if from_db:
            # Carica SOLO da MongoDB (più veloce, per pagina Salvataggio)
            app.logger.info(f"=== Caricamento da MongoDB per data: {date_str} ===")
            site = 'TST - EDC Torino'
            
            if STORAGE_AVAILABLE:
                json_data = storage.load_extraction(date_str, site, app.config['UPLOAD_FOLDER'])
                if json_data:
                    app.logger.info(f"✅ Dati caricati da MongoDB per {date_str}")
                    result = json_data.copy()
                    result['from_json'] = True
                    result['api_available'] = False
                    result['from_mongodb'] = True
                    result['message'] = 'Dati caricati da MongoDB (veloce)'
                    return render_template('risultati.html', data=result)
            
            # Fallback: prova file system locale
            json_data = get_json_extraction(date_str, site)
            if json_data:
                app.logger.info(f"✅ Dati caricati da file system locale per {date_str}")
                result = json_data.copy()
                result['from_json'] = True
                result['api_available'] = False
                result['from_mongodb'] = False
                result['message'] = 'Dati caricati da file system locale'
                return render_template('risultati.html', data=result)
            
            # Nessun dato trovato
            error_data = {
                'success': False,
                'error': f'Nessun dato salvato trovato per la data {date_str}. Estrai i dati dal calendario prima di visualizzare.',
                'date': date_str,
                'statistics': {
                    'totali': {
                        'totale_pezzi': 0, 'pezzi_checkati': 0, 'pezzi_da_checkare': 0,
                        'pezzi_accessori': 0, 'pezzi_crossdock': 0, 'totale_giri': 0,
                        'giri_completati': 0, 'giri_non_completati': 0,
                        'percentuale_completamento': 0, 'percentuale_completamento_giri': 0
                    },
                    'per_giro': [], 'per_cc': []
                },
                'details': {}, 'accessori_details': {}, 'crossdock_details': {},
                'clienti_per_giro': {}, 'product_search': {}, 'product_descriptions': {}
            }
            return render_template('risultati.html', data=error_data)
        
        # Comportamento normale: chiamata API diretta (dal calendario)
        app.logger.info(f"=== INIZIO estrazione risultati per data: {date_str} (chiamata API diretta) ===")
        
        # Estrai e analizza i dati per la data specificata
        site = 'TST - EDC Torino'
        date_field = 'LaunchDate'
        
        # Converti la data
        try:
            date_start = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Formato data non valido', 'error')
            return redirect(url_for('calendario_estrazione'))
        
        # Calcola differenza giorni da oggi
        today = date.today()
        days_diff = (today - date_start).days
        
        # Controlla se esiste un JSON salvato (cache)
        json_data = get_json_extraction(date_str, site)
        
        # LOGICA: Oggi o Ieri → sempre chiamata API diretta
        if is_today_or_yesterday(date_str):
            app.logger.info(f"Data {date_str} è oggi o ieri (diff: {days_diff} giorni) → SEMPRE chiamata API diretta")
            # Non usare cache, sempre API
        
        # LOGICA: Oltre 7 giorni → solo JSON (cache), non chiamare API
        elif days_diff > 7:
            app.logger.info(f"Data {date_str} è oltre 7 giorni (diff: {days_diff} giorni) → uso solo JSON cache")
            if json_data:
                result = json_data.copy()
                result['from_json'] = True
                result['api_available'] = False
                result['message'] = f'Dati dal JSON salvato (data oltre 7 giorni, API non disponibile)'
                return render_template('risultati.html', data=result)
            else:
                error_data = {
                    'success': False,
                    'error': f'Data oltre 7 giorni e nessun JSON salvato disponibile. L\'API OData mantiene solo gli ultimi 7 giorni.',
                    'date': date_str,
                    'statistics': {
                        'totali': {
                            'totale_pezzi': 0, 'pezzi_checkati': 0, 'pezzi_da_checkare': 0,
                            'pezzi_accessori': 0, 'pezzi_crossdock': 0, 'totale_giri': 0,
                            'giri_completati': 0, 'giri_non_completati': 0,
                            'percentuale_completamento': 0, 'percentuale_completamento_giri': 0
                        },
                        'per_giro': [], 'per_cc': []
                    },
                    'details': {}, 'accessori_details': {}, 'crossdock_details': {},
                    'clienti_per_giro': {}, 'product_search': {}, 'product_descriptions': {}
                }
                return render_template('risultati.html', data=error_data)
        
        # LOGICA: 2-7 giorni fa → chiamata API con fallback a JSON
        else:
            app.logger.info(f"Data {date_str} è tra 2-7 giorni fa (diff: {days_diff} giorni) → chiamata API con fallback a JSON")
            # Continua con chiamata API, useremo JSON come fallback se API fallisce
        
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
        
        # Fai la richiesta DMX con timeout breve (5 secondi) per evitare timeout
        records = []
        try:
            app.logger.info(f"Inizio richiesta OData per {date_str} (timeout 5s)")
            app.logger.info(f"URL completo: {full_url}")
            app.logger.info(f"Auth configurata: {auth is not None}")
            
            response = requests.get(full_url, headers=headers, auth=auth, timeout=5, allow_redirects=True)
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
            app.logger.info(f"Caricamento Loadings (timeout 3s)")
            loadings_response = requests.get(loadings_url, headers=headers, auth=auth, timeout=3, allow_redirects=True)
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
        analysis_result['success'] = True
        
        # Salva SEMPRE in JSON per mantenere lo storico
        # Per oggi e ieri, questo aggiorna sempre il JSON con i dati più recenti
        app.logger.info(f"Salvataggio JSON per {date_str} (diff giorni: {days_diff})")
        saved_filename = save_json_extraction(date_str, site, analysis_result)
        if saved_filename:
            analysis_result['saved_filename'] = saved_filename
            analysis_result['message'] = f'Dati aggiornati dall\'API e salvati in JSON (file: {saved_filename})'
            app.logger.info(f"JSON salvato con successo: {saved_filename}")
        else:
            app.logger.error(f"ERRORE: Impossibile salvare JSON per {date_str}")
            analysis_result['message'] = 'Dati aggiornati dall\'API ma ERRORE nel salvataggio JSON'
        
        app.logger.info(f"Rendering template risultati per {date_str}")
        return render_template('risultati.html', data=analysis_result)
        
    except requests.exceptions.Timeout as e:
        import traceback
        app.logger.error(f"TIMEOUT OData per {date_str}: {e}")
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Timeout nella richiesta OData - mostra messaggio chiaro
        error_data = {
            'success': False,
            'error': f'Timeout nella richiesta OData (oltre 5 secondi). Estrai i dati dal calendario prima di visualizzare i dettagli.',
            'date': date_str,
            'hint': 'Vai su "Calendario Estrazione", clicca sul giorno per estrarre i dati, poi torna qui per visualizzare i dettagli.',
            'statistics': {
                'totali': {
                    'totale_pezzi': 0, 'pezzi_checkati': 0, 'pezzi_da_checkare': 0,
                    'pezzi_accessori': 0, 'pezzi_crossdock': 0, 'totale_giri': 0,
                    'giri_completati': 0, 'giri_non_completati': 0,
                    'percentuale_completamento': 0, 'percentuale_completamento_giri': 0
                },
                'per_giro': [], 'per_cc': []
            },
            'details': {}, 'accessori_details': {}, 'crossdock_details': {},
            'clienti_per_giro': {}, 'product_search': {}, 'product_descriptions': {}
        }
        return render_template('risultati.html', data=error_data)
        
    except requests.exceptions.RequestException as e:
        import traceback
        app.logger.error(f"ERRORE richiesta OData per {date_str}: {e}")
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Prova a usare JSON salvato (cache) come fallback
        json_data = get_json_extraction(date_str, site)
        if json_data:
            app.logger.info(f"Errore OData per {date_str}, uso JSON cache salvato")
            result = json_data.copy()
            result['from_json'] = True
            result['api_available'] = False
            result['error'] = f'Errore di connessione OData: {str(e)}, dati dal JSON cache salvato'
            return render_template('risultati.html', data=result)
        
        # Nessun JSON disponibile
        error_data = {
            'success': False,
            'error': f'Errore di connessione all\'API OData: {str(e)}',
            'date': date_str,
            'statistics': {
                'totali': {
                    'totale_pezzi': 0, 'pezzi_checkati': 0, 'pezzi_da_checkare': 0,
                    'pezzi_accessori': 0, 'pezzi_crossdock': 0, 'totale_giri': 0,
                    'giri_completati': 0, 'giri_non_completati': 0,
                    'percentuale_completamento': 0, 'percentuale_completamento_giri': 0
                },
                'per_giro': [], 'per_cc': []
            },
            'details': {}, 'accessori_details': {}, 'crossdock_details': {},
            'clienti_per_giro': {}, 'product_search': {}, 'product_descriptions': {}
        }
        return render_template('risultati.html', data=error_data)
        
    except Exception as e:
        import traceback
        app.logger.error(f"ERRORE GENERALE estrazione risultati per {date_str}: {e}")
        app.logger.error(f"Traceback completo: {traceback.format_exc()}")
        
        # Prova a usare JSON salvato come ultimo tentativo
        try:
            json_data = get_json_extraction(date_str, 'TST - EDC Torino')
            if json_data:
                app.logger.info(f"Usando JSON salvato dopo errore generale per {date_str}")
                result = json_data.copy()
                result['from_json'] = True
                result['api_available'] = False
                result['error'] = f'Errore durante l\'estrazione: {str(e)}, dati dal JSON salvato'
                return render_template('risultati.html', data=result)
        except:
            pass
        
        # Nessun JSON disponibile, mostra errore
        error_data = {
            'success': False,
            'error': f'Errore durante l\'estrazione: {str(e)}',
            'date': date_str,
            'statistics': {
                'totali': {
                    'totale_pezzi': 0, 'pezzi_checkati': 0, 'pezzi_da_checkare': 0,
                    'pezzi_accessori': 0, 'pezzi_crossdock': 0, 'totale_giri': 0,
                    'giri_completati': 0, 'giri_non_completati': 0,
                    'percentuale_completamento': 0, 'percentuale_completamento_giri': 0
                },
                'per_giro': [], 'per_cc': []
            },
            'details': {}, 'accessori_details': {}, 'crossdock_details': {},
            'clienti_per_giro': {}, 'product_search': {}, 'product_descriptions': {}
        }
        return render_template('risultati.html', data=error_data)


@app.route('/api/test_mongodb')
def test_mongodb():
    """Endpoint di test per verificare la connessione MongoDB"""
    try:
        # Informazioni di debug
        debug_info = {
            'storage_available': STORAGE_AVAILABLE,
            'mongodb_uri_set': bool(os.environ.get('MONGODB_URI')),
            'mongodb_uri_length': len(os.environ.get('MONGODB_URI', '')) if os.environ.get('MONGODB_URI') else 0,
            'mongodb_db_name': os.environ.get('MONGODB_DB_NAME', 'easyloading'),
        }
        
        # Verifica se pymongo è installato
        try:
            import pymongo
            debug_info['pymongo_installed'] = True
            debug_info['pymongo_version'] = pymongo.__version__
        except ImportError:
            debug_info['pymongo_installed'] = False
            debug_info['pymongo_version'] = None
        
        if not STORAGE_AVAILABLE:
            return jsonify({
                'success': False,
                'message': 'Modulo storage non disponibile',
                'using_filesystem': True,
                'debug': debug_info
            }), 200
        
        # Verifica USE_MONGODB
        if hasattr(storage, 'USE_MONGODB'):
            debug_info['use_mongodb_flag'] = storage.USE_MONGODB
        else:
            debug_info['use_mongodb_flag'] = None
        
        # Prova a connettersi a MongoDB
        try:
            client, db = storage.get_mongo_client()
            
            if client is not None and db is not None:
                # Test di scrittura
                test_collection = db['test']
                test_doc = {
                    'test': True,
                    'timestamp': datetime.now().isoformat(),
                    'message': 'Test connessione MongoDB'
                }
                test_collection.insert_one(test_doc)
                
                # Test di lettura
                result = test_collection.find_one({'test': True})
                
                # Pulisci il documento di test
                test_collection.delete_one({'test': True})
                
                # Conta le collezioni
                collections = db.list_collection_names()
                
                return jsonify({
                    'success': True,
                    'message': '✅ MongoDB connesso e funzionante!',
                    'database': storage.MONGODB_DB_NAME if hasattr(storage, 'MONGODB_DB_NAME') else 'easyloading',
                    'collections': collections,
                    'test_write_read': 'OK',
                    'using_mongodb': True,
                    'using_filesystem': False,
                    'debug': debug_info
                }), 200
            else:
                # Prova a ottenere più informazioni sull'errore
                error_details = []
                if not debug_info.get('pymongo_installed'):
                    error_details.append('pymongo non installato')
                if not debug_info.get('mongodb_uri_set'):
                    error_details.append('MONGODB_URI non configurato')
                elif debug_info.get('use_mongodb_flag') is False:
                    error_details.append('USE_MONGODB è False (verifica pymongo e MONGODB_URI)')
                
                return jsonify({
                    'success': False,
                    'message': '⚠️ MongoDB non configurato, uso file system locale',
                    'using_mongodb': False,
                    'using_filesystem': True,
                    'error_details': error_details,
                    'debug': debug_info
                }), 200
        except Exception as conn_error:
            import traceback
            error_traceback = traceback.format_exc()
            # Log anche su console per debug
            app.logger.error(f"MongoDB connection error: {str(conn_error)}")
            app.logger.error(f"Traceback: {error_traceback}")
            
            return jsonify({
                'success': False,
                'message': f'❌ Errore durante connessione MongoDB: {str(conn_error)}',
                'error': str(conn_error),
                'error_type': type(conn_error).__name__,
                'using_mongodb': False,
                'using_filesystem': True,
                'debug': debug_info,
                'traceback': error_traceback
            }), 200
            
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'❌ Errore generale: {str(e)}',
            'error': str(e),
            'traceback': traceback.format_exc(),
            'using_mongodb': False,
            'using_filesystem': True
        }), 500


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve i file statici (logo, icone, manifest, ecc.)"""
    try:
        # Log per debug
        app.logger.info(f"Richiesta file statico: {filename}, static_folder: {app.static_folder}")
        
        # Determina il content-type in base all'estensione
        content_type = 'application/octet-stream'
        if filename.endswith('.png'):
            content_type = 'image/png'
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif filename.endswith('.webp'):
            content_type = 'image/webp'
        elif filename.endswith('.json'):
            content_type = 'application/json'
        elif filename.endswith('.js'):
            content_type = 'application/javascript'
        elif filename.endswith('.css'):
            content_type = 'text/css'
        
        response = app.send_static_file(filename)
        response.headers['Content-Type'] = content_type
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        app.logger.info(f"File statico servito con successo: {filename}")
        return response
    except Exception as e:
        app.logger.error(f"Errore servizio file statico {filename}: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        # Restituisci 404 con dettagli per debug
        return jsonify({'error': f'File non trovato: {filename}', 'static_folder': app.static_folder}), 404

@app.route('/favicon.ico')
def favicon():
    """Serve il favicon"""
    try:
        response = app.send_static_file('icon-192.png')
        response.headers['Content-Type'] = 'image/png'
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response
    except Exception as e:
        app.logger.error(f"Errore servizio favicon: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return '', 204  # No content se non trovato

@app.route('/manifest.json')
def manifest():
    """Serve il manifest.json"""
    try:
        response = app.send_static_file('manifest.json')
        response.headers['Content-Type'] = 'application/json'
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response
    except Exception as e:
        app.logger.error(f"Errore servizio manifest: {e}")
        return '', 404

@app.route('/static/sw.js')
def service_worker():
    """Serve il service worker con il content-type corretto"""
    return app.send_static_file('sw.js'), 200, {'Content-Type': 'application/javascript'}


if __name__ == '__main__':
    # In produzione su Render, questo viene eseguito solo in locale
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    port = int(os.environ.get('PORT', 5004))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

