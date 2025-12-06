"""
Modulo per gestire lo storage persistente dei dati.
Su Vercel usa MongoDB, in locale usa file system.
"""
import os
import json
from datetime import datetime
from typing import Optional, Dict, List, Any

# Prova a importare pymongo (opzionale)
try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    MongoClient = None

# Configurazione MongoDB da variabili d'ambiente
MONGODB_URI = os.environ.get('MONGODB_URI')
MONGODB_DB_NAME = os.environ.get('MONGODB_DB_NAME', 'easyloading')

# Flag per usare MongoDB (solo se URI è configurato)
USE_MONGODB = bool(MONGODB_URI) and PYMONGO_AVAILABLE

# Client MongoDB (singleton)
_mongo_client = None
_mongo_db = None


def get_mongo_client():
    """Ottiene il client MongoDB (singleton)"""
    global _mongo_client, _mongo_db
    
    if not USE_MONGODB:
        print(f"⚠️ USE_MONGODB è False. MONGODB_URI={bool(MONGODB_URI)}, PYMONGO_AVAILABLE={PYMONGO_AVAILABLE}")
        return None, None
    
    if _mongo_client is None:
        try:
            print(f"🔄 Tentativo connessione MongoDB... URI length: {len(MONGODB_URI) if MONGODB_URI else 0}")
            # Aumenta il timeout per dare più tempo alla connessione
            _mongo_client = MongoClient(
                MONGODB_URI, 
                serverSelectionTimeoutMS=10000,  # 10 secondi invece di 5
                connectTimeoutMS=10000,
                socketTimeoutMS=10000
            )
            # Testa la connessione
            print("🔄 Testing ping...")
            _mongo_client.admin.command('ping')
            print("✅ Ping riuscito!")
            _mongo_db = _mongo_client[MONGODB_DB_NAME]
            print(f"✅ Connesso a MongoDB: {MONGODB_DB_NAME}")
            return _mongo_client, _mongo_db
        except ConnectionFailure as e:
            error_msg = f"⚠️ ConnectionFailure: {str(e)}"
            print(error_msg)
            _mongo_client = None
            _mongo_db = None
            raise Exception(error_msg)  # Rilancia per essere catturato dall'endpoint
        except ServerSelectionTimeoutError as e:
            error_msg = f"⚠️ ServerSelectionTimeoutError: {str(e)}"
            print(error_msg)
            _mongo_client = None
            _mongo_db = None
            raise Exception(error_msg)  # Rilancia per essere catturato dall'endpoint
        except Exception as e:
            error_msg = f"⚠️ Errore MongoDB generico: {type(e).__name__}: {str(e)}"
            print(error_msg)
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            _mongo_client = None
            _mongo_db = None
            raise Exception(error_msg)  # Rilancia per essere catturato dall'endpoint
    
    return _mongo_client, _mongo_db


# ==================== ANAGRAFICA ====================

def save_anagrafica(data: Dict[str, str], local_file: str = 'anagrafica.json') -> bool:
    """Salva l'anagrafica in MongoDB o file system locale"""
    client, db = get_mongo_client()
    
    if client is not None and db is not None:
        try:
            # Salva in MongoDB
            collection = db['anagrafica']
            # Sostituisci tutto il documento
            collection.delete_many({})
            if data:
                collection.insert_one({'data': data, 'type': 'anagrafica'})
            print(f"✅ Anagrafica salvata in MongoDB")
            
            # Salva anche in locale come backup
            try:
                with open(local_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except:
                pass  # Ignora errori di scrittura locale su Vercel
            
            return True
        except Exception as e:
            print(f"⚠️ Errore salvataggio MongoDB: {e}. Provo file system locale.")
    
    # Fallback: file system locale
    try:
        with open(local_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Errore salvataggio anagrafica: {e}")
        return False


def load_anagrafica(local_file: str = 'anagrafica.json') -> Optional[Dict[str, str]]:
    """Carica l'anagrafica da MongoDB o file system locale"""
    client, db = get_mongo_client()
    
    if client is not None and db is not None:
        try:
            # Carica da MongoDB
            collection = db['anagrafica']
            doc = collection.find_one({'type': 'anagrafica'})
            if doc and 'data' in doc:
                print(f"✅ Anagrafica caricata da MongoDB ({len(doc['data'])} articoli)")
                return doc['data']
        except Exception as e:
            print(f"⚠️ Errore caricamento MongoDB: {e}. Provo file system locale.")
    
    # Fallback: file system locale
    if os.path.exists(local_file):
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ Anagrafica caricata da file locale ({len(data)} articoli)")
                return data
        except Exception as e:
            print(f"❌ Errore caricamento anagrafica: {e}")
    
    return None


# ==================== CONFIG OData ====================

def save_odata_config(config: Dict[str, Any], local_file: str = 'odata_config.json') -> bool:
    """Salva la configurazione OData in MongoDB o file system locale"""
    client, db = get_mongo_client()
    
    if client is not None and db is not None:
        try:
            # Salva in MongoDB
            collection = db['config']
            # Sostituisci tutto il documento
            collection.delete_many({'type': 'odata_config'})
            collection.insert_one({'type': 'odata_config', 'config': config})
            print(f"✅ Config OData salvata in MongoDB")
            
            # Salva anche in locale come backup
            try:
                with open(local_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            except:
                pass
            
            return True
        except Exception as e:
            print(f"⚠️ Errore salvataggio MongoDB: {e}. Provo file system locale.")
    
    # Fallback: file system locale
    try:
        with open(local_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Errore salvataggio config OData: {e}")
        return False


def load_odata_config(local_file: str = 'odata_config.json') -> Optional[Dict[str, Any]]:
    """Carica la configurazione OData da MongoDB o file system locale"""
    client, db = get_mongo_client()
    
    if client is not None and db is not None:
        try:
            # Carica da MongoDB
            collection = db['config']
            doc = collection.find_one({'type': 'odata_config'})
            if doc and 'config' in doc:
                print(f"✅ Config OData caricata da MongoDB")
                return doc['config']
        except Exception as e:
            print(f"⚠️ Errore caricamento MongoDB: {e}. Provo file system locale.")
    
    # Fallback: file system locale
    if os.path.exists(local_file):
        try:
            with open(local_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"✅ Config OData caricata da file locale")
                return config
        except Exception as e:
            print(f"❌ Errore caricamento config OData: {e}")
    
    return None


# ==================== ESTRAZIONI JSON ====================

def save_extraction(date_str: str, site: str, data: Dict[str, Any], uploads_dir: str) -> Optional[str]:
    """Salva un'estrazione in MongoDB o file system locale"""
    client, db = get_mongo_client()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"estrazione_{date_str.replace('-', '')}_{timestamp}.json"
    
    # Prepara i dati da salvare
    extraction_data = {
        'date': date_str,
        'site': site,
        'extraction_date': datetime.now().isoformat(),
        'count': data.get('count', 0),
        **data  # Includi tutti i dati dell'analisi
    }
    
    if client is not None and db is not None:
        try:
            # Salva in MongoDB
            collection = db['extractions']
            # Rimuovi estrazioni più vecchie per la stessa data (mantieni solo la più recente)
            collection.delete_many({'date': date_str, 'site': site})
            # Inserisci la nuova estrazione
            extraction_data['_id'] = f"{date_str}_{site}_{timestamp}"
            collection.insert_one(extraction_data)
            print(f"✅ Estrazione {date_str} salvata in MongoDB")
            
            # Salva anche in locale come backup (se possibile)
            try:
                os.makedirs(uploads_dir, exist_ok=True)
                filepath = os.path.join(uploads_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(extraction_data, f, ensure_ascii=False, indent=2)
            except:
                pass  # Ignora errori su Vercel
            
            return filename
        except Exception as e:
            print(f"⚠️ Errore salvataggio MongoDB: {e}. Provo file system locale.")
    
    # Fallback: file system locale
    try:
        os.makedirs(uploads_dir, exist_ok=True)
        filepath = os.path.join(uploads_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(extraction_data, f, ensure_ascii=False, indent=2)
        return filename
    except Exception as e:
        print(f"❌ Errore salvataggio estrazione: {e}")
        return None


def load_extraction(date_str: str, site: str, uploads_dir: str) -> Optional[Dict[str, Any]]:
    """Carica un'estrazione da MongoDB o file system locale"""
    client, db = get_mongo_client()
    
    if client is not None and db is not None:
        try:
            # Carica da MongoDB
            collection = db['extractions']
            # Trova l'estrazione più recente per questa data e sito
            doc = collection.find_one(
                {'date': date_str, 'site': site},
                sort=[('extraction_date', -1)]
            )
            if doc:
                # Rimuovi _id prima di restituire
                doc.pop('_id', None)
                print(f"✅ Estrazione {date_str} caricata da MongoDB")
                return doc
        except Exception as e:
            print(f"⚠️ Errore caricamento MongoDB: {e}. Provo file system locale.")
    
    # Fallback: file system locale
    date_pattern = date_str.replace('-', '')
    matching_files = []
    
    if os.path.exists(uploads_dir):
        for filename in os.listdir(uploads_dir):
            if filename.startswith('estrazione_') and filename.endswith('.json'):
                if date_pattern in filename:
                    filepath = os.path.join(uploads_dir, filename)
                    try:
                        mtime = os.path.getmtime(filepath)
                        matching_files.append((filepath, mtime, filename))
                    except:
                        continue
        
        if matching_files:
            matching_files.sort(key=lambda x: x[1], reverse=True)
            filepath, _, filename = matching_files[0]
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'data' in data or 'statistics' in data:
                        print(f"✅ Estrazione {date_str} caricata da file locale")
                        return data
            except Exception as e:
                print(f"❌ Errore caricamento estrazione: {e}")
    
    return None


def list_extractions(uploads_dir: str) -> List[Dict[str, Any]]:
    """Lista tutte le estrazioni da MongoDB o file system locale"""
    client, db = get_mongo_client()
    extractions = []
    
    if client is not None and db is not None:
        try:
            # Carica da MongoDB
            collection = db['extractions']
            # Raggruppa per data (prendi solo la più recente per ogni data)
            pipeline = [
                {'$sort': {'extraction_date': -1}},
                {'$group': {
                    '_id': {'date': '$date', 'site': '$site'},
                    'latest': {'$first': '$$ROOT'}
                }},
                {'$replaceRoot': {'newRoot': '$latest'}},
                {'$sort': {'extraction_date': -1}}
            ]
            
            for doc in collection.aggregate(pipeline):
                doc.pop('_id', None)
                extractions.append({
                    'filename': f"estrazione_{doc.get('date', 'N/A').replace('-', '')}_{doc.get('extraction_date', '').replace(':', '').replace('-', '').split('.')[0]}.json",
                    'date': doc.get('date', 'N/A'),
                    'site': doc.get('site', 'N/A'),
                    'count': doc.get('count', 0),
                    'extraction_date': doc.get('extraction_date', 'N/A')
                })
            
            print(f"✅ Trovate {len(extractions)} estrazioni in MongoDB")
        except Exception as e:
            print(f"⚠️ Errore caricamento MongoDB: {e}. Provo file system locale.")
    
    # Fallback: file system locale
    if not extractions and os.path.exists(uploads_dir):
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
                            if date_str not in date_files or mtime > date_files[date_str][1]:
                                date_files[date_str] = (filename, mtime, data)
                except Exception as e:
                    print(f"⚠️ Errore lettura {filename}: {e}")
        
        for date_str, (filename, mtime, data) in date_files.items():
            extractions.append({
                'filename': filename,
                'date': date_str,
                'site': data.get('site', 'N/A'),
                'count': data.get('count', 0),
                'extraction_date': data.get('extraction_date', 'N/A')
            })
        
        extractions.sort(key=lambda x: x.get('extraction_date', ''), reverse=True)
        print(f"✅ Trovate {len(extractions)} estrazioni in file system locale")
    
    return extractions


# ==================== CHUNKED UPLOAD ====================

def save_chunk(file_id: str, chunk_index: int, chunk_data: bytes) -> bool:
    """Salva un chunk di file in MongoDB"""
    client, db = get_mongo_client()
    
    if client is not None and db is not None:
        try:
            collection = db['csv_chunks']
            collection.insert_one({
                'file_id': file_id,
                'chunk_index': chunk_index,
                'chunk_data': chunk_data.hex(),  # Salva come hex string
                'created_at': datetime.now().isoformat()
            })
            return True
        except Exception as e:
            print(f"⚠️ Errore salvataggio chunk MongoDB: {e}")
            return False
    
    return False


def merge_chunks(file_id: str, original_filename: str) -> Optional[str]:
    """Ricomponi i chunk in un file completo e restituisci il file_id del file completo"""
    client, db = get_mongo_client()
    
    if client is not None and db is not None:
        try:
            collection = db['csv_chunks']
            # Recupera tutti i chunk per questo file_id, ordinati per indice
            chunks = list(collection.find({'file_id': file_id}).sort('chunk_index', 1))
            
            if not chunks:
                print(f"❌ Nessun chunk trovato per file_id: {file_id}")
                return None
            
            # Ricomponi il file
            file_data = b''
            for chunk_doc in chunks:
                chunk_bytes = bytes.fromhex(chunk_doc['chunk_data'])
                file_data += chunk_bytes
            
            # Salva il file completo in una nuova collection
            complete_collection = db['csv_transforms']
            transform_doc = {
                'file_id': file_id,
                'original_filename': original_filename,
                'file_data': file_data.hex(),
                'created_at': datetime.now().isoformat(),
                'status': 'merged'
            }
            complete_collection.insert_one(transform_doc)
            
            # Cancella i chunk dopo il merge
            collection.delete_many({'file_id': file_id})
            
            print(f"✅ File {file_id} ricomposto da {len(chunks)} chunk")
            return file_id
        except Exception as e:
            print(f"⚠️ Errore merge chunks: {e}")
            return None
    
    return None


def get_transformed_file(file_id: str) -> Optional[Dict[str, Any]]:
    """Recupera il file trasformato da MongoDB"""
    client, db = get_mongo_client()
    
    if client is not None and db is not None:
        try:
            collection = db['csv_transforms']
            doc = collection.find_one({'file_id': file_id})
            if doc:
                return {
                    'file_id': doc.get('file_id'),
                    'original_filename': doc.get('original_filename'),
                    'output_filename': doc.get('output_filename'),
                    'file_data': bytes.fromhex(doc.get('file_data', '')),
                    'rows_processed': doc.get('rows_processed'),
                    'rows_transformed': doc.get('rows_transformed'),
                    'missing_codes': doc.get('missing_codes', [])
                }
        except Exception as e:
            print(f"⚠️ Errore recupero file trasformato: {e}")
    
    return None


def delete_transformed_file(file_id: str) -> bool:
    """Cancella il file trasformato da MongoDB"""
    client, db = get_mongo_client()
    
    if client is not None and db is not None:
        try:
            collection = db['csv_transforms']
            result = collection.delete_one({'file_id': file_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"⚠️ Errore cancellazione file trasformato: {e}")
    
    return False

