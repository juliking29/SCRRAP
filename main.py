import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request

app = FastAPI()

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def scrape_matches():
    url = 'https://www.besoccer.com'
    response = requests.get(url)
    
    result = {"leagues": []}
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        paneles = soup.find_all('div', class_='panel-head')

        if not paneles:
            return {"error": "No se encontraron ligas."}
        
        for panel in paneles:
            titulo_div = panel.find('div', class_='panel-title')
            if not titulo_div:
                continue
                
            nombre_liga = titulo_div.find('span').text.strip() if titulo_div else "Liga desconocida"
            logo_liga = titulo_div.find('img')['src'] if titulo_div and titulo_div.find('img') else ""

            contenedor_partidos = panel.find_next_sibling('div')
            if not contenedor_partidos:
                continue

            partidos = contenedor_partidos.find_all('a', class_='match-link')  # Cambiado a 'a' para obtener el href
            if not partidos:
                continue
                
            league_data = {
                "name": nombre_liga,
                "logo": logo_liga,
                "matches": []
            }

            for partido in partidos:    
                match_href = partido['href']
                
                equipos = partido.find_all('div', class_='team-info')

                if len(equipos) >= 2:
                    local_div = equipos[0]
                    visitante_div = equipos[1]

                    nombre_local = local_div.find('div', class_='team-name').text.strip()
                    logo_local = local_div.find('img')['src'] if local_div.find('img') else ""

                    nombre_visitante = visitante_div.find('div', class_='team-name').text.strip()
                    logo_visitante = visitante_div.find('img')['src'] if visitante_div.find('img') else ""
                else:
                    continue

                marcador_div = partido.find('div', class_='marker')
                tiempo = ""
                estado = "scheduled"
                marcador = ""
                
                if marcador_div:
                    tiempo_tag = partido.find('span', class_='tag-nobg live')
                    if tiempo_tag:
                        estado = "live"
                        tiempo = tiempo_tag.find('b').text.strip()
                        marcador = marcador_div.get_text(strip=True)
                    else:
                        hora = marcador_div.find('p', class_='match_hour time')
                        if hora:
                            tiempo = hora.text.strip()
                            estado = "scheduled"
                        else:
                            marcador = marcador_div.get_text(strip=True)
                            estado = "finished"
                
                today = datetime.now().strftime('%Y-%m-%d')
                
                match_data = {
                    "href": match_href,  # Añadido el href
                    "homeTeam": {
                        "name": nombre_local,
                        "logo": logo_local
                    },
                    "awayTeam": {
                        "name": nombre_visitante,
                        "logo": logo_visitante
                    },
                    "date": today,
                    "status": estado,
                }
                
                if estado == "live":
                    match_data["currentTime"] = tiempo
                    match_data["score"] = marcador
                elif estado == "scheduled":
                    match_data["time"] = tiempo
                else:
                    match_data["score"] = marcador
                
                league_data["matches"].append(match_data)
                
            if league_data["matches"]:
                result["leagues"].append(league_data)
            
        return result
    else:
        return {"error": f"Error al obtener la página. Código: {response.status_code}"}

def scrape_match_details(match_url: str):
    try:
        print(f"Iniciando scraping de: {match_url}")  # ← Log importante
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(match_url, headers=headers, timeout=10)
        print(f"Status code recibido: {response.status_code}")  # ← Log importante
        
        if response.status_code != 200:
            return {"error": f"Besoccer respondió con código {response.status_code}"}

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Verifica que la página contiene los elementos esperados
        if not soup.find('div', class_='info match-link'):
            return {"error": "Estructura de página no reconocida"}

        # ... resto de tu lógica de scraping ...
        
    except Exception as e:
        print(f"Error durante scraping: {str(e)}")  # ← Log importante
        return {"error": f"Error al scrapear: {str(e)}"}

@app.get("/")
def root():
    return {"message": "Bienvenido al scraper de BeSoccer"}

@app.get("/scrape")
def get_matches():
    try:
        data = scrape_matches()
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel

class MatchRequest(BaseModel):
    url: str

from fastapi import HTTPException, Request
import json

@app.post("/scrape_match")
async def get_match_details(request: Request):
    try:
        # 1. Obtener el cuerpo de la solicitud
        body = await request.json()
        print("Cuerpo recibido:", body)  # ← Log importante

        # 2. Validar que existe el campo 'url'
        if "url" not in body:
            raise HTTPException(status_code=422, detail="Falta el campo 'url' en el cuerpo")
        
        url = body["url"]
        print("URL recibida para scraping:", url)  # ← Log importante

        # 3. Validar formato de URL
        if not isinstance(url, str):
            raise HTTPException(status_code=400, detail="URL debe ser texto")
            
        if not url.startswith('https://www.besoccer.com/match/'):
            raise HTTPException(status_code=400, detail="URL debe ser de Besoccer")

        # 4. Ejecutar scraping
        result = scrape_match_details(url)
        
        if "error" in result:
            print("Error en scraping:", result["error"])  # ← Log importante
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
        
    except json.JSONDecodeError:
        print("Error: Cuerpo no es JSON válido")
        raise HTTPException(status_code=400, detail="Cuerpo debe ser JSON")
    except Exception as e:
        print("Error interno:", str(e))  # ← Log importante
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
# Para ejecutar localmente: uvicorn main:app --reload