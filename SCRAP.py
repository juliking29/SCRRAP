import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

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

            partidos = contenedor_partidos.find_all('div', class_='team-box')
            if not partidos:
                continue
                
            league_data = {
                "name": nombre_liga,
                "logo": logo_liga,
                "matches": []
            }

            for partido in partidos:    
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

                # Obtener marcador y estado del partido
                marcador_div = partido.find('div', class_='marker')
                tiempo = ""
                estado = "scheduled"  # por defecto asumimos que no ha comenzado
                marcador = ""
                
                if marcador_div:
                    # Verificar si es un partido en vivo
                    tiempo_tag = partido.find('span', class_='tag-nobg live')
                    if tiempo_tag:
                        estado = "live"
                        tiempo = tiempo_tag.find('b').text.strip()  # Obtener el minuto
                        marcador = marcador_div.get_text(strip=True)
                    else:
                        # Es un partido programado
                        hora = marcador_div.find('p', class_='match_hour time')
                        if hora:
                            tiempo = hora.text.strip()
                            estado = "scheduled"
                        else:
                            # Podría ser un partido finalizado
                            marcador = marcador_div.get_text(strip=True)
                            estado = "finished"
                
                # Usar la fecha actual para el partido
                today = datetime.now().strftime('%Y-%m-%d')
                
                # Crear objeto de partido
                match_data = {
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
                else:  # finished
                    match_data["score"] = marcador
                
                league_data["matches"].append(match_data)
                
            if league_data["matches"]:
                result["leagues"].append(league_data)
            
        return result
    else:
        return {"error": f"Error al obtener la página. Código de estado: {response.status_code}"}

if __name__ == "__main__":
    matches_data = scrape_matches()
    print(json.dumps(matches_data, ensure_ascii=False, indent=2))
