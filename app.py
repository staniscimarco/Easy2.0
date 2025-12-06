# Aggiungiamo nuove route per upload in chunk
@app.route('/api/upload_chunk', methods=['POST'])
def upload_chunk():
    """Endpoint per caricare un chunk del file CSV"""
    try:
        chunk_data = request.files.get('chunk')
        chunk_index = request.form.get('chunkIndex', type=int)
        total_chunks = request.form.get('totalChunks', type=int)
        file_id = request.form.get('fileId')  # ID univoco per questo upload
        filename = request.form.get('filename', 'upload.csv')
        
        if not chunk_data or chunk_index is None or total_chunks is None or not file_id:
            return jsonify({'error': 'Parametri mancanti'}), 400
        
        # Salva il chunk in MongoDB o file system temporaneo
        uploads_dir = app.config['UPLOAD_FOLDER']
        chunks_dir = os.path.join(uploads_dir, 'chunks', file_id)
        os.makedirs(chunks_dir, exist_ok=True)
        
        chunk_filename = f'chunk_{chunk_index}'
        chunk_path = os.path.join(chunks_dir, chunk_filename)
        chunk_data.save(chunk_path)
        
        app.logger.info(f"Chunk {chunk_index + 1}/{total_chunks} salvato per file {file_id}")
        
        return jsonify({
            'success': True,
            'chunkIndex': chunk_index,
            'message': f'Chunk {chunk_index + 1}/{total_chunks} caricato'
        })
    except Exception as e:
        import traceback
        app.logger.error(f"Errore upload chunk: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/merge_chunks', methods=['POST'])
def merge_chunks():
    """Ricomponi i chunk in un file completo e processalo"""
    try:
        data = request.get_json()
        file_id = data.get('fileId')
        filename = data.get('filename', 'upload.csv')
        total_chunks = data.get('totalChunks', type=int)
        
        if not file_id or total_chunks is None:
            return jsonify({'error': 'Parametri mancanti'}), 400
        
        global anagrafica_data
        if anagrafica_data is None:
            return jsonify({'error': 'Anagrafica non caricata'}), 400
        
        uploads_dir = app.config['UPLOAD_FOLDER']
        chunks_dir = os.path.join(uploads_dir, 'chunks', file_id)
        
        if not os.path.exists(chunks_dir):
            return jsonify({'error': 'Chunk directory non trovata'}), 404
        
        # Verifica che tutti i chunk siano presenti
        for i in range(total_chunks):
            chunk_path = os.path.join(chunks_dir, f'chunk_{i}')
            if not os.path.exists(chunk_path):
                return jsonify({'error': f'Chunk {i} mancante'}), 400
        
        # Ricomponi il file
        input_filepath = os.path.join(uploads_dir, f'{file_id}_{filename}')
        with open(input_filepath, 'wb') as outfile:
            for i in range(total_chunks):
                chunk_path = os.path.join(chunks_dir, f'chunk_{i}')
                with open(chunk_path, 'rb') as chunk_file:
                    outfile.write(chunk_file.read())
                # Cancella il chunk dopo averlo letto
                os.remove(chunk_path)
        
        # Cancella la directory chunks
        try:
            os.rmdir(chunks_dir)
        except:
            pass
        
        # Processa il file
        now = datetime.now()
        output_filename = f"YDMXEL_{now.strftime('%Y%m%d_%H%M')}.csv"
        output_filepath = os.path.join(uploads_dir, output_filename)
        
        rows_processed, rows_transformed, missing_codes = process_csv_file(input_filepath, output_filepath)
        
        # Salva il risultato in MongoDB per il download
        if STORAGE_AVAILABLE:
            # Leggi il file trasformato
            with open(output_filepath, 'rb') as f:
                file_content = f.read()
            
            # Salva in MongoDB
            client, db = storage.get_mongo_client()
            if client is not None and db is not None:
                collection = db['csv_transforms']
                transform_doc = {
                    'file_id': file_id,
                    'original_filename': filename,
                    'output_filename': output_filename,
                    'rows_processed': rows_processed,
                    'rows_transformed': rows_transformed,
                    'missing_codes': missing_codes,
                    'created_at': datetime.now().isoformat(),
                    'file_content': file_content.hex()  # Salva come hex string
                }
                collection.insert_one(transform_doc)
                app.logger.info(f"File trasformato salvato in MongoDB: {file_id}")
        
        # Cancella il file input originale
        try:
            os.remove(input_filepath)
        except:
            pass
        
        return jsonify({
            'success': True,
            'fileId': file_id,
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
    """Scarica il file trasformato da MongoDB o file system"""
    try:
        uploads_dir = app.config['UPLOAD_FOLDER']
        
        # Prova a caricare da MongoDB
        if STORAGE_AVAILABLE:
            client, db = storage.get_mongo_client()
            if client is not None and db is not None:
                collection = db['csv_transforms']
                doc = collection.find_one({'file_id': file_id})
                if doc:
                    # Decodifica il contenuto
                    file_content = bytes.fromhex(doc['file_content'])
                    output_filename = doc.get('output_filename', 'YDMXEL_trasformato.csv')
                    
                    # Crea un file temporaneo
                    temp_path = os.path.join(uploads_dir, output_filename)
                    with open(temp_path, 'wb') as f:
                        f.write(file_content)
                    
                    # Cancella da MongoDB dopo il download
                    collection.delete_one({'file_id': file_id})
                    
                    return send_file(
                        temp_path,
                        as_attachment=True,
                        download_name=output_filename,
                        mimetype='text/csv'
                    )
        
        # Fallback: cerca nel file system
        # (per compatibilità con vecchi upload)
        return jsonify({'error': 'File non trovato'}), 404
        
    except Exception as e:
        app.logger.error(f"Errore download trasformato: {str(e)}")
        return jsonify({'error': str(e)}), 500
