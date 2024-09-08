import streamlit as st
import pandas as pd
import os
from io import BytesIO
from bank_processors import process_bank_statement
from utils import merge_dataframes
import logging
import traceback
import sys
import requests
import time
import shutil

# Configure logging
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Procesador de Estados de Cuenta Bancarios", page_icon="💰", layout="wide")

st.title("Procesador y Fusionador de Estados de Cuenta Bancarios")

st.write("""
Esta aplicación te permite subir múltiples estados de cuenta bancarios, procesarlos y fusionar los resultados en un solo archivo.

Instrucciones:
1. Subir archivos de estados de cuenta (Excel o CSV).
2. Selecciona el banco para cada archivo subido.
3. Haz clic en el botón 'Procesar y Fusionar'.
4. Descarga el archivo de resultados fusionados.
""")

# Custom file uploader with additional parameters and error handling
def custom_file_uploader(label, accept_multiple_files=True, types=None, max_retries=3, retry_delay=2):
    try:
        logger.info(f"Attempting to upload files: {label}")
        uploaded_files = st.file_uploader(label, accept_multiple_files=accept_multiple_files, type=types, label_visibility="collapsed")
        
        if uploaded_files is None:
            logger.warning("No files were uploaded")
            st.warning("No se han subido archivos. Por favor, intenta nuevamente.")
            return None
        
        if not isinstance(uploaded_files, list):
            uploaded_files = [uploaded_files]
        
        processed_files = []
        for file in uploaded_files:
            for attempt in range(max_retries):
                try:
                    logger.info(f"Processing file: {file.name} (Attempt {attempt + 1})")
                    # Check file size
                    if file.size > 200 * 1024 * 1024:  # 200 MB limit
                        logger.warning(f"File {file.name} exceeds size limit")
                        st.warning(f"El archivo {file.name} excede el límite de tamaño de 200 MB.")
                        break

                    # Save file to a temporary directory
                    temp_dir = "temp_uploads"
                    os.makedirs(temp_dir, exist_ok=True)
                    file_path = os.path.join(temp_dir, file.name)
                    
                    # Fallback method using built-in open() function
                    with open(file_path, "wb") as f:
                        f.write(file.getvalue())

                    # Set necessary permissions
                    os.chmod(file_path, 0o644)

                    # Check file permissions
                    permissions = oct(os.stat(file_path).st_mode)[-3:]
                    logger.info(f"File {file.name} saved with permissions: {permissions}")
                    st.info(f"Archivo {file.name} guardado con permisos: {permissions}")

                    processed_files.append(file)
                    logger.info(f"File uploaded successfully: {file.name}, Size: {file.size} bytes")
                    st.success(f"Archivo subido correctamente: {file.name}, Tamaño: {file.size} bytes")
                    break
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error processing file {file.name}: {str(e)}", exc_info=True)
                    if attempt < max_retries - 1:
                        st.warning(f"Error de red al procesar el archivo {file.name}. Reintentando en {retry_delay} segundos...")
                        time.sleep(retry_delay)
                    else:
                        st.error(f"Error de red al procesar el archivo {file.name}. Por favor, verifica tu conexión a internet e intenta nuevamente.")
                        st.info(f"Detalles del error: {type(e).__name__} - {str(e)}")
                except PermissionError as e:
                    logger.error(f"Permission error processing file {file.name}: {str(e)}", exc_info=True)
                    st.error(f"Error de permisos al procesar el archivo {file.name}. Por favor, verifica los permisos del archivo y la carpeta de destino.")
                    st.info(f"Detalles del error: {type(e).__name__} - {str(e)}")
                    break
                except Exception as e:
                    logger.error(f"Error processing file {file.name}: {str(e)}", exc_info=True)
                    st.error(f"Error al procesar el archivo {file.name}. Por favor, verifica el formato del archivo y vuelve a intentarlo.")
                    st.info(f"Detalles del error: {type(e).__name__} - {str(e)}")
                    st.info("Si el problema persiste, contacta al soporte técnico.")
                    break
        
        return processed_files
    except Exception as e:
        logger.error(f"Error in file upload process: {str(e)}", exc_info=True)
        st.error("Error en el proceso de carga de archivos. Por favor, intenta nuevamente.")
        st.info(f"Detalles del error: {type(e).__name__} - {str(e)}")
        st.info("Si el problema persiste, contacta al soporte técnico.")
        return None

# New function to delete temporary files
def delete_temp_files():
    temp_dir = "temp_uploads"
    try:
        shutil.rmtree(temp_dir)
        logger.info(f"Temporary directory {temp_dir} deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting temporary directory {temp_dir}: {str(e)}", exc_info=True)
        st.warning(f"No se pudieron eliminar algunos archivos temporales. Error: {str(e)}")

# Use the custom file uploader
uploaded_files = custom_file_uploader("Subir archivos de estados de cuenta (Explorar archivos)", accept_multiple_files=True, types=['xlsx', 'csv'])

# Bank selection
bank_options = ['Galicia', 'MercadoPago', 'ICBC', 'Supervielle', 'Macro', 'Nación']
selected_banks = []

if uploaded_files:
    st.write("Selecciona el banco para cada archivo subido:")
    for file in uploaded_files:
        selected_bank = st.selectbox(f"Banco para {file.name}", bank_options, key=file.name)
        selected_banks.append(selected_bank)

# Process and merge button
if st.button("Procesar y Fusionar"):
    if not uploaded_files:
        st.error("Por favor, sube al menos un archivo antes de procesar.")
    elif len(uploaded_files) != len(selected_banks):
        st.error("Por favor, selecciona un banco para cada archivo subido.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            processed_dfs = []
            for i, (file, bank) in enumerate(zip(uploaded_files, selected_banks)):
                try:
                    status_text.text(f"Procesando {file.name} ({bank})...")
                    logger.info(f"Processing file: {file.name} for bank: {bank}")
                    df = process_bank_statement(file, bank)
                    processed_dfs.append(df)
                    progress_bar.progress((i + 1) / len(uploaded_files))
                except Exception as e:
                    logger.error(f"Error processing {file.name}: {str(e)}", exc_info=True)
                    st.error(f"Error al procesar {file.name}. Asegúrate de que el archivo tenga el formato correcto para el banco {bank}.")
                    st.info(f"Detalles del error: {type(e).__name__} - {str(e)}")
            
            if processed_dfs:
                status_text.text("Fusionando archivos procesados...")
                logger.info("Merging processed files")
                merged_df = merge_dataframes(processed_dfs)
                
                # Create a BytesIO object to store the Excel file
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    merged_df.to_excel(writer, index=False, sheet_name='Estados Fusionados')
                
                status_text.text("¡Procesamiento completo!")
                progress_bar.progress(100)
                
                # Provide download link
                st.download_button(
                    label="Descargar Archivo Fusionado",
                    data=output.getvalue(),
                    file_name="estados_de_cuenta_fusionados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                logger.info("Processing complete, download button created")
                
                # Delete temporary files after processing
                delete_temp_files()
            else:
                logger.warning("No files were processed successfully")
                st.warning("No se pudo procesar ningún archivo. Por favor, verifica los archivos subidos e intenta nuevamente.")
        except Exception as e:
            logger.error(f"Error during processing: {str(e)}", exc_info=True)
            st.error("Error durante el procesamiento. Por favor, verifica que todos los archivos se hayan cargado correctamente y tengan el formato adecuado.")
            st.info(f"Detalles del error: {type(e).__name__} - {str(e)}")
            st.info("Si el problema persiste, contacta al soporte técnico.")
        finally:
            # Ensure temporary files are deleted even if an error occurs
            delete_temp_files()

st.write("---")
st.write("Desarrollado con ❤️ usando Streamlit")
