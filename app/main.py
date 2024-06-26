from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Form
from langchain.chat_models import ChatOpenAI
from langchain.schema.messages import SystemMessage, HumanMessage
from langchain.document_loaders import Docx2txtLoader, PDFPlumberLoader
from openai import OpenAI
from langchain.schema.output_parser import StrOutputParser
import json
from fastapi.responses import JSONResponse
import os
from pydantic import BaseModel
import tempfile
from dotenv import load_dotenv

load_dotenv()  # carga las variables de entorno del archivo .env

# variables de entorno usando os.getenv
langchain_tracing_v2 = os.getenv('LANGCHAIN_TRACING_V2')
langchain_endpoint = os.getenv('LANGCHAIN_ENDPOINT')
langchain_api_key = os.getenv('LANGCHAIN_API_KEY')
langchain_project = os.getenv('LANGCHAIN_PROJECT')


openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

app = FastAPI()

class Seccion(BaseModel):
    seccion: str
    documento: str

class DocumentSection(BaseModel):
    seccion: str
    documento: str

# Modelo Pydantic para la entrada del endpoint
class GenerateDocumentInput(BaseModel):
    info: dict    


# Ruta para cargar y procesar el documento pnrl-poder notarial de representante legal
@app.post("/process-pnrl/")
async def process_word(uploaded_file: UploadFile = File(...)):
    try:
        # Crear un archivo temporal para guardar el contenido del archivo cargado
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
            content = await uploaded_file.read()  # Leer el contenido del archivo cargado
            temp_file.write(content)  # Escribir el contenido en el archivo temporal
            temp_file_path = temp_file.name  # Guardar la ruta del archivo temporal
        # Cargar el archivo Word utilizando Docx2txtLoader
        loader = Docx2txtLoader(temp_file_path)
        document = loader.load()[0]  # Suponiendo que solo hay un documento en el archivo
        content_text = document.page_content
        # Procesar el contenido del documento con el modelo de OpenAI
        chat = ChatOpenAI(model="gpt-4-0125-preview", temperature=0, openai_api_key=openai_api_key).bind(
            response_format={"type": "json_object"}
        )
        output = chat.invoke(
            [
                SystemMessage(
                        content="""Extrae la informacion del documento en caso de que exista, sino se encuentra aclara que la informacion no es proporcionada en el documento:
                Representante legal: Localiza el nombre completo de alguno o varios representantes legales o apoderados que son los que se solicitan al notario el otorgamieto del muevo poder estos deben de estar al principio del documentos necesariamente en los primeros parrafos.  Si no se encuentra el nombre, indica que no está disponible,
                Apoderado: Identifica y extrae el nombre completo de la persona a quien se le otorga el poder para actuar en nombre del representante legal. Si no se proporciona el nombre, señala que no se incluyó,
                Poderes Otorgados:  Busca y registra los detalles específicos sobre los poderes otorgados al apoderado, incluyendo las acciones que está autorizado a realizar en nombre del representante legal. Si no se especifican los poderes, menciona que no se encontró esa información,
                Fecha de otorgamiento: Localiza y anota la fecha en que se otorgó el poder notarial. Si no se indica una fecha de otorgamiento, aclara que no se proporcionó,
                Cual es la vigencia del poder notarial otrogado en este documento puede ser vigencia indefinida o por ciertos años, por ley tiene que encontrarse en el documento, generalmente la información relevante está en la sección que dice: "La presente Autorización tiene una vigencia ..",
                Número de protocolo: Identifica y registra el número de protocolo del poder notarial, si se proporciona. Si no se encuentra el número de protocolo, señala que no se incluyó,
                Datos notariales: Extrae la información sobre el notario que certificó el poder notarial, incluyendo su nombre completo, número de registro y ubicación de su notaría, si se proporcionan. Si alguno de estos datos falta, indica cuál no se encontró,
                Firma y sello: Verifica si el poder notarial incluye la firma y sello del notario que lo certificó y menciona las respectivas firmas. Si no se encuentran la firma y sello, menciona que no se incluyeron en el documento proporcionado.
                Return a JSON list."""
                ),
                HumanMessage(
                    content=content_text
                ),
            ]
        )
         # Convertir la respuesta en un diccionario de Python
        info = json.loads(output.content)
        
        # Eliminar el archivo temporal
        os.unlink(temp_file_path)
       
        # Devolver la respuesta
        return {"info": info}
    except Exception as e:
        # Si algo sale mal, asegúrate de eliminar el archivo temporal
        if 'temp_file_path' in locals():
            os.unlink(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))

# Ruta para cargar y procesar el documento acta constitutiva
@app.post("/process-acta/")
async def process_acta(uploaded_file: UploadFile = File(...)):
    try:
        # Crear un archivo temporal para guardar el contenido del archivo cargado
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
            content = await uploaded_file.read()  # Leer el contenido del archivo cargado
            temp_file.write(content)  # Escribir el contenido en el archivo temporal
            temp_file_path = temp_file.name  # Guardar la ruta del archivo temporal
        
        # Cargar el archivo Word utilizando Docx2txtLoader
        loader = Docx2txtLoader(temp_file_path)
        document = loader.load()[0]  # Suponiendo que solo hay un documento en el archivo
        content_text = document.page_content
        
        # Procesar el contenido del documento con el modelo de OpenAI
        chat = ChatOpenAI(model="gpt-4-0125-preview", temperature=0, openai_api_key=openai_api_key).bind(
            response_format={"type": "json_object"}
        )
        output = chat.invoke(
            [
                SystemMessage(
                    content="""Extrae la informacion del documento en caso de que exista, sino se encuentra aclara que la informacion no es proporcionada en el documento:
                    Razón social de la empresa: Nombre Completo: Localiza y captura el nombre completo y oficial de la empresa tal como está registrado en el Acta Constitutiva. Si no se encuentra el nombre, indica que no está disponible,
                    Tipo de sociedad:  Clasificación: Identifica y extrae el tipo de sociedad constituida (por ejemplo, S.A., S. de R.L., etc.). Si no se especifica el tipo de sociedad, menciona que no se incluyó,
                    Objeto social: Descripción: Busca y registra la descripción detallada de las actividades y propósitos para los cuales fue constituida la empresa. Si no se encuentra el objeto social, señala que no se proporcionó,
                    Capital social: Monto y División: Captura el monto total del capital con el que se constituyó la empresa y la forma en que se divide entre los socios, si se especifica. Si no se menciona el capital social, indica que no se incluyó,
                    Domicilio social: Dirección: Localiza y anota la dirección legal de la empresa, incluyendo calle, número, colonia o urbanización, municipio o alcaldía, estado y país. Si no se proporciona el domicilio social, aclara que no se encontró,
                    Duración de la sociedad: Periodo: Identifica y registra el periodo de tiempo durante el cual la sociedad estará en operación, si es determinado o indefinido. Si no se especifica la duración, señala que no se incluyó,
                    Nombre de los socios fundadores: Identificación de las personas o entidades que participaron en la fundación de la empresa,
                    Representante legal: Designación del representante legal o administrador de la empresa, junto con sus facultades y restricciones,
                    Órganos de gobierno: Descripción de los órganos de gobierno de la empresa, como el Consejo de Administración o la Asamblea de Socios, y sus funciones,
                    Reglas de funcionamiento: Estatutos y reglamentos internos que rigen el funcionamiento y la toma de decisiones dentro de la empresa,
                    Datos notariales: Información sobre el notario que certificó el Acta Constitutiva, incluyendo su nombre completo, número de registro y la ubicación de su notaría,
                    Firma y sello: La firma y sello del notario que certificó el Acta Constitutiva, que garantizan su autenticidad.
                    Return a JSON list."""
                ),
                HumanMessage(
                    content=content_text
                ),
            ]
        )
        
        # Convertir la respuesta en un diccionario de Python
        info = json.loads(output.content)
        
        # Eliminar el archivo temporal
        os.unlink(temp_file_path)
       
        # Devolver la respuesta
        return {"info": info}
    except Exception as e:
        # Si algo sale mal, asegúrate de eliminar el archivo temporal
        if 'temp_file_path' in locals():
            os.unlink(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))
    
# Ruta para cargar y procesar el documento constancia de situacion fiscal
@app.post("/process-CSF/")
async def process_acta(uploaded_file: UploadFile = File(...)):
    try:
        # Crear un archivo temporal para guardar el contenido del archivo cargado
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = await uploaded_file.read()  # Leer el contenido del archivo cargado
            temp_file.write(content)  # Escribir el contenido en el archivo temporal
            temp_file_path = temp_file.name  # Guardar la ruta del archivo temporal
        
        # Cargar el archivo Word utilizando PDFPlumberLoader
        loader = PDFPlumberLoader(temp_file_path)
        document = loader.load()[0]  # Suponiendo que solo hay un documento en el archivo
        content_text = document.page_content
        
        # Procesar el contenido del documento con el modelo de OpenAI
        chat = ChatOpenAI(model="gpt-4-0125-preview", temperature=0, openai_api_key=openai_api_key).bind(
            response_format={"type": "json_object"}
        )
        output = chat.invoke(
            [
                SystemMessage(
                    content="""Extrae la informacion del documento en caso de que exista, sino se encuentra aclara que la informacion no es proporcionada en el documento:
                    Nombre o Razón Social: Localiza y extrae el nombre completo o razón social del contribuyente. Si no se encuentra esta información, indica que no está disponible,
                    RFC: Busca y captura el Registro Federal de Contribuyentes (RFC) del contribuyente. Si no se incluye el RFC, señala que no se proporcionó,
                    Domicilio Fiscal: Identifica y registra la dirección del domicilio fiscal listado en la constancia. Si no se especifica un domicilio, menciona que no se encontró,
                    Fecha de Emisión: Encuentra y anota la fecha en que se emitió la Constancia de Situación Fiscal. Si no se indica una fecha, aclara que no se incluyó,
                    Régimen Fiscal: Determina el tipo de régimen fiscal en el que está inscrito el contribuyente (régimen general, simplificado, etc.). Si no se especifica el régimen, indica que no se proporcionó esa información,
                    Situación Fiscal: Verifica si la constancia indica que el contribuyente está al corriente con sus obligaciones fiscales. Si no se menciona explícitamente, señala que no se aclaró la situación fiscal.
                    Return a JSON list."""
                ),
                HumanMessage(
                    content=content_text
                ),
            ]
        )
        
        # Convertir la respuesta en un diccionario de Python
        info = json.loads(output.content)
        
        # Eliminar el archivo temporal
        os.unlink(temp_file_path)
       
        # Devolver la respuesta
        return {"info": info}
    except Exception as e:
        # Si algo sale mal, asegúrate de eliminar el archivo temporal
        if 'temp_file_path' in locals():
            os.unlink(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))
    
    # Ruta para cargar y procesar el documento de caratula bancaria
@app.post("/process-CB/")
async def process_acta(uploaded_file: UploadFile = File(...)):
    try:
        # Crear un archivo temporal para guardar el contenido del archivo cargado
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = await uploaded_file.read()  # Leer el contenido del archivo cargado
            temp_file.write(content)  # Escribir el contenido en el archivo temporal
            temp_file_path = temp_file.name  # Guardar la ruta del archivo temporal
        
        # Cargar el archivo Word utilizando PDFPlumberLoader
        loader = PDFPlumberLoader(temp_file_path)
        document = loader.load()[0]  # Suponiendo que solo hay un documento en el archivo
        content_text = document.page_content
        
        # Procesar el contenido del documento con el modelo de OpenAI
        chat = ChatOpenAI(model="gpt-4-0125-preview", temperature=0, openai_api_key=openai_api_key).bind(
            response_format={"type": "json_object"}
        )
        output = chat.invoke(
            [
                SystemMessage(
                    content="""Extrae la informacion del documento en caso de que exista, sino se encuentra aclara que la informacion no es proporcionada en el documento:
                    Titural de la Cuenta:  Localiza y captura el nombre completo o razón social del titular de la cuenta bancaria, ya sea una persona física o moral. Si no se encuentra el titular, indica que no está disponible,
                    Número de Cuenta: Busca y registra el número de cuenta bancaria asociado al titular. Si no se proporciona el número de cuenta, menciona que no se incluyó,
                    Institución Bancaria: Identifica y anota el nombre de la institución bancaria donde se encuentra la cuenta. Si no se especifica el nombre del banco, señala que no se encontró,
                    CLABE Bancaria:  Localiza y captura la CLABE (Clave Bancaria Estandarizada) interbancaria, que es un código único que identifica la cuenta bancaria en el sistema financiero mexicano. Si no se proporciona la CLABE, indica que no se incluyó,
                    Sucursal Bancaria: Si la cuenta está asociada a una sucursal bancaria específica, busca y registra la información sobre dicha sucursal, como su nombre, dirección o código. Si no se menciona la sucursal bancaria, señala que no se encontró,
                    Fecha de Emisión:  Identifica y anota la fecha en que se emitió la carátula bancaria. Si no se especifica la fecha de emisión, indica que no se proporcionó,
                    Firma y Sello de la Institución Bancaria: Verifica si la carátula bancaria incluye la firma y el sello oficial del banco emisor para validar la autenticidad del documento. La misma figura como CADENA ORIGINAL DEL COMPLEMENTO DE CERTIFICACIÓN DIGITAL DEL SAT, SELLO DIGITAL DEL EMISOR y SELLO DIGITAL SAT. Si no se encuentran la firma y el sello, menciona que no se incluyeron en el documento proporcionado.
                    Return a JSON list."""
                ),
                HumanMessage(
                    content=content_text
                ),
            ]
        )
        
        # Convertir la respuesta en un diccionario de Python
        info = json.loads(output.content)
        
        # Eliminar el archivo temporal
        os.unlink(temp_file_path)
       
        # Devolver la respuesta
        return {"info": info}
    except Exception as e:
        # Si algo sale mal, asegúrate de eliminar el archivo temporal
        if 'temp_file_path' in locals():
            os.unlink(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))
    
        # Ruta para cargar y procesar el documento de ID
@app.post("/process-ID/")
async def process_acta(uploaded_file: UploadFile = File(...)):
    try:
        # Crear un archivo temporal para guardar el contenido del archivo cargado
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = await uploaded_file.read()  # Leer el contenido del archivo cargado
            temp_file.write(content)  # Escribir el contenido en el archivo temporal
            temp_file_path = temp_file.name  # Guardar la ruta del archivo temporal
        
        # Cargar el archivo Word utilizando PDFPlumberLoader
        loader = PDFPlumberLoader(temp_file_path)
        document = loader.load()[0]  # Suponiendo que solo hay un documento en el archivo
        content_text = document.page_content
        
        # Procesar el contenido del documento con el modelo de OpenAI
        chat = ChatOpenAI(model="gpt-4-0125-preview", temperature=0, openai_api_key=openai_api_key).bind(
            response_format={"type": "json_object"}
        )
        output = chat.invoke(
            [
                SystemMessage(
                    content="""Extrae la informacion de este documento de identificacion, ten en cuenta que fue pasado por OCR por tanto trata de adaptarte al formato y tenlo presente a la hora de extraer:
                    Nombre Completo: Localiza y captura el nombre completo de la persona tal como aparece en el documento de identificación, recuerda que la persona puede tener dos apellidos y dos nombres, en el caso de que no sea legible aclaralo,
                    Número de Identificación: Busca y registra el número único de identificación como el número CURP en (INE) o el número de pasaporte, en el caso de que no sea legible aclaralo,
                    Fecha de expedición: La fecha en que se emitió el documento de identificación, en el caso de que no se encuentre aclaralo,
                    Fecha de vigencia: La fecha de vencimiento del documento de identificación, en el caso de que no sea legible aclaralo.
                    Return a JSON list."""
                ),
                HumanMessage(
                    content=content_text
                ),
            ]
        )
        
        # Convertir la respuesta en un diccionario de Python
        info = json.loads(output.content)
        
        # Eliminar el archivo temporal
        os.unlink(temp_file_path)
       
        # Devolver la respuesta
        return {"info": info}
    except Exception as e:
        # Si algo sale mal, asegúrate de eliminar el archivo temporal
        if 'temp_file_path' in locals():
            os.unlink(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))
    
    