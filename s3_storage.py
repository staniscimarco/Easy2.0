"""
Modulo per gestire l'upload e download di file su AWS S3.
Usato per file > 4.5MB che superano il limite di Vercel.
"""
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import io

# Prova a importare boto3 (opzionale)
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None
    print("⚠️ boto3 non disponibile, upload S3 disabilitato")

# Configurazione AWS da variabili d'ambiente
AWS_ACCESS_KEY_ID = os.environ.get('S3_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('S3_SECRET_ACCESS_KEY')
AWS_REGION = os.environ.get('AWS_REGION', 'eu-west-1')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'chatpdfgpt')

# Flag per usare S3 (solo se credenziali sono configurate)
USE_S3 = bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and S3_BUCKET_NAME) and BOTO3_AVAILABLE

# Client S3 (singleton)
_s3_client = None


def get_s3_client():
    """Ottiene il client S3 (singleton)"""
    global _s3_client
    
    if not USE_S3:
        return None
    
    if _s3_client is None:
        try:
            _s3_client = boto3.client(
                's3',
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_REGION
            )
            # Testa la connessione
            _s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
            print(f"✅ Connesso a S3 bucket: {S3_BUCKET_NAME}")
        except NoCredentialsError:
            print("❌ Credenziali AWS non valide")
            return None
        except ClientError as e:
            print(f"❌ Errore connessione S3: {e}")
            return None
        except Exception as e:
            print(f"❌ Errore imprevisto S3: {e}")
            return None
    
    return _s3_client


def upload_file_to_s3(file_bytes: bytes, file_id: str, filename: str) -> bool:
    """
    Carica un file su S3
    
    Args:
        file_bytes: Contenuto del file in bytes
        file_id: ID univoco del file
        filename: Nome originale del file
    
    Returns:
        True se l'upload è riuscito, False altrimenti
    """
    if not USE_S3:
        return False
    
    s3_client = get_s3_client()
    if s3_client is None:
        return False
    
    try:
        # Crea la chiave S3 (path nel bucket)
        s3_key = f"csv_uploads/{file_id}/{filename}"
        
        # Carica il file
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_bytes,
            ContentType='text/csv'
        )
        
        print(f"✅ File caricato su S3: {s3_key}")
        return True
    except Exception as e:
        print(f"❌ Errore upload S3: {e}")
        return False


def download_file_from_s3(file_id: str, filename: str) -> Optional[bytes]:
    """
    Scarica un file da S3
    
    Args:
        file_id: ID univoco del file
        filename: Nome originale del file
    
    Returns:
        Contenuto del file in bytes, None se errore
    """
    if not USE_S3:
        return None
    
    s3_client = get_s3_client()
    if s3_client is None:
        return None
    
    try:
        s3_key = f"csv_uploads/{file_id}/{filename}"
        
        response = s3_client.get_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key
        )
        
        file_bytes = response['Body'].read()
        print(f"✅ File scaricato da S3: {s3_key}")
        return file_bytes
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            print(f"❌ File non trovato su S3: {s3_key}")
        else:
            print(f"❌ Errore download S3: {e}")
        return None
    except Exception as e:
        print(f"❌ Errore imprevisto download S3: {e}")
        return None


def delete_file_from_s3(file_id: str, filename: str) -> bool:
    """
    Elimina un file da S3
    
    Args:
        file_id: ID univoco del file
        filename: Nome originale del file
    
    Returns:
        True se l'eliminazione è riuscita, False altrimenti
    """
    if not USE_S3:
        return False
    
    s3_client = get_s3_client()
    if s3_client is None:
        return False
    
    try:
        s3_key = f"csv_uploads/{file_id}/{filename}"
        
        s3_client.delete_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key
        )
        
        print(f"✅ File eliminato da S3: {s3_key}")
        return True
    except Exception as e:
        print(f"❌ Errore eliminazione S3: {e}")
        return False


def generate_presigned_url(file_id: str, filename: str, expiration: int = 3600) -> Optional[str]:
    """
    Genera un URL presigned per il download diretto del file
    
    Args:
        file_id: ID univoco del file
        filename: Nome originale del file
        expiration: Tempo di scadenza in secondi (default: 1 ora)
    
    Returns:
        URL presigned, None se errore
    """
    if not USE_S3:
        return None
    
    s3_client = get_s3_client()
    if s3_client is None:
        return None
    
    try:
        s3_key = f"csv_uploads/{file_id}/{filename}"
        
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET_NAME,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        
        return url
    except Exception as e:
        print(f"❌ Errore generazione URL presigned: {e}")
        return None

