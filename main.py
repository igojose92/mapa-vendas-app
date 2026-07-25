from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import json
import os

app = FastAPI()

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

GOOGLE_MAPS_API_KEY = "AIzaSyAt_SgOgFsPosjtTeY1nMJVNBLbmYIBtho"
ICON_BASKET = '<svg class="basket-svg" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M17.21 9l-4.38-6.56c-.19-.28-.51-.42-.83-.42-.32 0-.64.14-.83.43L6.79 9H2c-.55 0-1 .45-1 1 0 .09.01.18.04.27l2.54 9.27c.23.84 1 1.46 1.92 1.46h13c.92 0 1.69-.62 1.93-1.46l2.54-9.27L23 10c0-.55-.45-1-1-1h-4.79zM9 9l3-4.4L15 9H9zm3 8c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/></svg>'

def formatar_setor(valor):
    if str(valor).strip() == '':
        return ''
    val_str = str(valor).split('.')[0].strip()
    return val_str.zfill(3) if val_str.isdigit() else val_str

def carregar_dados_e_gerar_html():
    caminho_arquivo = os.path.join("dados", "clientes_vendas_teste.xlsx")
    
    if not os.path.exists(caminho_arquivo):
        return f"<h1>Erro: O arquivo Excel não foi encontrado em '{caminho_arquivo}'. Verifique a pasta 'dados'.</h1>"

    try:
        df = pd.read_excel(caminho_arquivo, dtype={'Setor': str})
    except Exception as e:
        return f"<h1>Erro ao ler a planilha Excel: {e}</h1>"

    df = df.fillna('')
    df['Setor'] = df['Setor'].apply(formatar_setor)

    setores_unicos = sorted([str(s) for s in df['Setor'].unique() if str(s).strip() != ''])
    segmentacoes_unicas = sorted([str(s) for s in df['Segmentação'].unique() if str(s).strip() != ''])
    regioes_unicas = sorted([str(r) for r in df['Região (DF)'].unique() if str(r).strip() != ''])

    markers_list = []
    for _, row in df.iterrows():
        try:
            lat = float(row['Latitude'])
            lng = float(row['Longitude'])
        except (ValueError, TypeError):
            continue

        cliente = str(row['Nome Fantasia'])
        cnpj = str(row['CNPJ'])
        status_cadastral = str(row['Status']).strip()
        comprou = str(row['Comprou no Mês']).strip()
        setor_formatado = str(row['Setor'])
        
        status_lower = status_cadastral.lower()
        comprou_lower = comprou.lower()

        if 'prospec' in status_lower or 'prospeccao' in status_lower or 'prospecção' in status_lower:
            cor_hex = "#007bff"
            status_categoria = "prospeccao"
        elif 'inativo' in status_lower:
            cor_hex = "#7f8c8d"
            status_categoria = "inativo"
        elif comprou_lower == 'sim':
            cor_hex = "#28a745"
            status_categoria = "comprou_sim"
        else:
            cor_hex = "#FF3131"
            status_categoria = "comprou_nao"

        codigo_cli = str(row.iloc[0])
        search_tag = f"{cliente} {cnpj} {codigo_cli} {setor_formatado}".lower()
        
        # Estrutura adaptável e responsiva do Popup
        content_html = f"""
            <div style='width: 280px; max-width: 82vw; max-height: 75vh; overflow-y: auto; font-family: sans-serif; line-height: 1.4; color: #ffffff; background: #2c3e50; padding: 0; border-radius: 10px; box-shadow: 0 8px 20px rgba(0,0,0,0.4); position: relative; user-select: none; -webkit-user-select: none;'>
                <div style='background:{cor_hex}; color:white; padding: 12px; padding-right: 45px; border-radius: 10px 10px 0 0;'>
                    <div style='font-size:15px; font-weight:bold; word-wrap: break-word;'>{cliente}</div>
                    <div style='font-size:11px; opacity:0.9;'>CNPJ: {cnpj} | Cód: {codigo_cli}</div>
                </div>
                <div style='padding: 10px 12px 12px 12px;'>
                    <div style='font-size:12px; padding-bottom: 8px; color: #ecf0f1;'>
                        <b>Região:</b> {row['Região (DF)']}<br>
                        <b>Segmentação:</b> {row['Segmentação']}<br>
                        <b>Setor:</b> {setor_formatado}<br>
                        <b>Representante:</b> {row['Representante']}<br>
                        <b>Dia de Visita:</b> {row['Dia de Visita']}<br>
                        <b>Frequência:</b> {row['Frequência de Visita']}<br>
                        <b>Equipamentos (Freezers):</b> {row['Qtd Equipamentos (Freezers)']}<br>
                        <b>Data do Cadastro:</b> {row['Data de Cadastro']}<br>
                        <b>Pagamento:</b> {row['Tipo de Pagamento']} {f' - Prazo: {row["Prazo Boleto (Dias)"]}d' if str(row['Tipo de Pagamento']).lower() == 'boleto' else ''}<br>
                        <b>Limite Crédito:</b> <span style='color:#2ecc71; font-weight:bold;'>R$ {row['Limite de Crédito (R$)']}</span><br>
                        <b>Contato:</b> {row['Telefone Contato']}<br>
                        <b>E-mail:</b> {row['E-mail Contato']}
                    </div>
                    <div style='background:#34495e; padding:8px; border-radius:6px; margin:5px 0 10px 0; border-left:4px solid {cor_hex}; font-size:11px; color: #ffffff; display: flex; align-items: center; gap: 8px;'>
                        <div style='width:20px; color:{cor_hex}; flex-shrink: 0;'>{ICON_BASKET}</div>
                        <div><b>Comprou no Mês:</b> {comprou if comprou else 'Não'}<br><b>Cadastro:</b> {status_cadastral}</div>
                    </div>
                    <a href='http://maps.google.com/maps?daddr={lat},{lng}' target='_blank' rel='noopener noreferrer'
                       style='display:block; background:#4285F4; color:white; text-align:center; padding:10px; border-radius:25px; text-decoration:none; font-weight:bold; font-size:13px;'>
                        VER TRAJETO GOOGLE MAPS
                    </a>
                </div>
            </div>
        """

        markers_list.append({
            "nome": cliente,
            "lat": lat,
            "lng": lng,
            "cor_hex": cor_hex, 
            "search": search_tag,
            "content": content_html,
            "status_cat": status_categoria,
            "setor": setor_formatado,
            "segmentacao": str(row['Segmentação']),
            "regiao": str(row['Região (DF)'])
        })

    markers_json = json.dumps(markers_list)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        
        <link rel="manifest" href="/static/manifest.json">
        <link rel="icon" type="image/png" href="/static/icon.png">
        <link rel="apple-touch-icon" href="/static/icon.png">
        <meta name="theme-color" content="#2c3e50">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="Mapa Vendas">
        
        <title>Mapa de Vendas</title>
        <script src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}"></script>
        <style>
            body, html {{ 
                height: 100%; 
                margin: 0; 
                padding: 0; 
                font-family: 'Segoe UI', sans-serif; 
                overflow: hidden; 
                user-select: none;
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
            }}
            
            *:focus {{
                outline: none !important;
            }}

            #map {{ height: 100%; width: 100%; }}
            
            /* Ajustes da InfoWindow */
            .gm-style .gm-style-iw-c {{
                padding: 0 !important;
                background-color: transparent !important;
                box-shadow: none !important;
                border-radius: 10px !important;
                overflow: hidden !important;
                max-width: 90vw !important;
            }}
            .gm-style .gm-style-iw-d {{
                overflow: hidden !important;
                padding: 0 !important;
                max-width: 90vw !important;
            }}
            .gm-style .gm-style-iw-tc::after {{
                background-color: #2c3e50 !important;
            }}

            /* Botão de fechar (X) */
            .gm-ui-hover-effect {{ 
                position: absolute !important;
                top: 12px !important; 
                right: 0 !important; 
                margin: 0 !important;
                width: 32px !important; 
                height: 32px !important; 
                background-color: #ff3131 !important; 
                border-radius: 0 10px 0 10px !important; 
                display: flex !important; 
                align-items: center !important; 
                justify-content: center !important; 
                opacity: 1 !important; 
                z-index: 9999 !important; 
            }}
            .gm-ui-hover-effect span {{ 
                background-color: white !important; 
                margin: 0 !important; 
                width: 14px !important;
                height: 14px !important;
            }}

            /* Barra de busca responsiva */
            #search-wrapper {{ 
                position: absolute; 
                top: 15px; 
                left: 50%; 
                transform: translateX(-50%); 
                z-index: 10; 
                width: 80%; 
                max-width: 420px; 
            }}
            #search-container {{ 
                background: #2c3e50; 
                padding: 8px 15px; 
                border-radius: 35px; 
                box-shadow: 0 10px 25px rgba(0,0,0,0.5); 
                border: 1px solid #34495e; 
                display: flex; 
                align-items: center; 
                position: relative; 
            }}
            #search-input {{ 
                width: 100%; 
                border: none; 
                outline: none; 
                font-size: 14px; 
                text-align: center; 
                background: transparent; 
                color: #ffffff; 
                padding-right: 25px;
                user-select: text !important;
                -webkit-user-select: text !important;
            }}
            #clear-search {{ position: absolute; right: 15px; color: #ff3131; font-weight: bold; cursor: pointer; font-size: 20px; display: none; }}
            #suggestions {{ background: #2c3e50; border-radius: 20px; margin-top: 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.4); max-height: 200px; overflow-y: auto; display: none; border: 1px solid #34495e; }}
            .suggestion-item {{ padding: 12px 20px; cursor: pointer; border-bottom: 1px solid #34495e; font-size: 14px; color: #4285F4; }}
            
            .beam-container {{ position: absolute; pointer-events: none; }}
            .beam-shape {{ width: 0; height: 0; border-left: 40px solid transparent; border-right: 40px solid transparent; border-bottom: 120px solid rgba(66, 133, 244, 0.4); filter: blur(5px); transform-origin: 50% 100%; background: linear-gradient(to top, rgba(66, 133, 244, 0.8), transparent); clip-path: polygon(50% 100%, 0% 0%, 100% 0%); margin-left: -40px; margin-top: -120px; }}
            
            #legend-toggle {{ position: absolute; bottom: 25px; right: 10px; background: #2c3e50; color: white; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: bold; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.3); z-index: 6; border: 1px solid #34495e; }}
            #legend {{ position: absolute; bottom: 75px; right: 10px; background: white; padding: 10px; border-radius: 12px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); z-index: 5; font-size: 12px; border-left: 5px solid #4285F4; display: none; }}
            .legend-row {{ display: flex; align-items: center; margin-bottom: 5px; font-weight: 600; gap: 8px; }}
            .basket-svg {{ width: 18px; height: 18px; }}
            
            .custom-controls {{ position: absolute; left: 15px; top: 75px; z-index: 5; display: flex; flex-direction: column; gap: 8px; }}
            .map-btn {{ background: white; border: none; width: 40px; height: 40px; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 8px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center; }}
            
            #menu-container {{ position: absolute; left: 15px; top: 15px; z-index: 20; }}
            #menu-toggle {{ background: #2c3e50; color: white; width: 42px; height: 42px; border-radius: 50%; display: flex; flex-direction: column; justify-content: center; align-items: center; cursor: pointer; border: 1px solid #34495e; }}
            .bar {{ width: 20px; height: 2px; background-color: white; margin: 2px 0; }}
            
            #filter-menu {{ position: absolute; left: 0; top: 52px; background: #2c3e50; padding: 12px; border-radius: 15px; color: white; border: 1px solid #34495e; display: none; width: 230px; max-height: 70vh; overflow-y: auto; }}
            .filter-group {{ margin-bottom: 6px; }}
            .filter-header {{ display: flex; justify-content: space-between; align-items: center; cursor: pointer; font-weight: bold; font-size: 13px; padding: 8px 4px; border-bottom: 1px solid #34495e; user-select: none; }}
            .filter-header:hover {{ color: #4285F4; }}
            .arrow {{ transition: transform 0.3s ease; font-size: 10px; display: inline-block; }}
            .arrow.open {{ transform: rotate(180deg); }}
            .filter-content {{ display: none; padding: 8px 0 4px 0; }}
            .filter-option {{ display: flex; align-items: center; gap: 8px; font-size: 12px; margin-bottom: 6px; cursor: pointer; }}
            .btn-group {{ display: flex; gap: 6px; margin-bottom: 8px; }}
            .btn-group button {{ background: #34495e; color: white; border: none; padding: 3px 8px; border-radius: 4px; cursor: pointer; font-size: 11px; }}
            .btn-group button:hover {{ background: #4285F4; }}

            /* Responsividade para celulares pequenos */
            @media (max-width: 480px) {{
                #search-wrapper {{ width: 65%; left: 60%; }}
                #filter-menu {{ width: 200px; }}
            }}
        </style>
    </head>
    <body>
        <div id="menu-container">
            <div id="menu-toggle" onclick="toggleMenu()"><div class="bar"></div><div class="bar"></div><div class="bar"></div></div>
            <div id="filter-menu">
                
                <div class="filter-group">
                    <div class="filter-header" onclick="toggleAccordion(this)">
                        <span>STATUS:</span>
                        <span class="arrow">▼</span>
                    </div>
                    <div class="filter-content">
                        <div class="btn-group">
                            <button onclick="selectAll(this, true)">Tudo</button>
                            <button onclick="selectAll(this, false)">Limpar</button>
                        </div>
                        <label class="filter-option"><input type="checkbox" class="filter-check" value="comprou_sim" checked> Comprou</label>
                        <label class="filter-option"><input type="checkbox" class="filter-check" value="comprou_nao" checked> Não Comprou</label>
                        <label class="filter-option"><input type="checkbox" class="filter-check" value="inativo" checked> Inativo</label>
                        <label class="filter-option"><input type="checkbox" class="filter-check" value="prospeccao" checked> Prospecção</label>
                    </div>
                </div>

                <div class="filter-group">
                    <div class="filter-header" onclick="toggleAccordion(this)">
                        <span>SETOR:</span>
                        <span class="arrow">▼</span>
                    </div>
                    <div class="filter-content">
                        <div class="btn-group">
                            <button onclick="selectAll(this, true)">Tudo</button>
                            <button onclick="selectAll(this, false)">Limpar</button>
                        </div>
                        {"".join([f'<label class="filter-option"><input type="checkbox" class="filter-check set-filter" value="{setor}" checked> {setor}</label>' for setor in setores_unicos])}
                    </div>
                </div>

                <div class="filter-group">
                    <div class="filter-header" onclick="toggleAccordion(this)">
                        <span>SEGMENTAÇÃO:</span>
                        <span class="arrow">▼</span>
                    </div>
                    <div class="filter-content">
                        <div class="btn-group">
                            <button onclick="selectAll(this, true)">Tudo</button>
                            <button onclick="selectAll(this, false)">Limpar</button>
                        </div>
                        {"".join([f'<label class="filter-option"><input type="checkbox" class="filter-check seg-filter" value="{seg}" checked> {seg}</label>' for seg in segmentacoes_unicas])}
                    </div>
                </div>

                <div class="filter-group">
                    <div class="filter-header" onclick="toggleAccordion(this)">
                        <span>REGIÃO DF:</span>
                        <span class="arrow">▼</span>
                    </div>
                    <div class="filter-content">
                        <div class="btn-group">
                            <button onclick="selectAll(this, true)">Tudo</button>
                            <button onclick="selectAll(this, false)">Limpar</button>
                        </div>
                        {"".join([f'<label class="filter-option"><input type="checkbox" class="filter-check reg-filter" value="{reg}" checked> {reg}</label>' for reg in regioes_unicas])}
                    </div>
                </div>

            </div>
        </div>

        <div id="search-wrapper">
            <div id="search-container">
                <input id="search-input" type="text" placeholder="🔎 Buscar cliente ou CNPJ..." autocomplete="off">
                <div id="clear-search" onclick="clearSearchInput()">×</div>
            </div>
            <div id="suggestions"></div>
        </div>

        <div class="custom-controls">
            <button class="map-btn" style="font-size:20px;" onclick="map.setZoom(map.getZoom() + 1)">+</button>
            <button class="map-btn" style="font-size:20px;" onclick="map.setZoom(map.getZoom() - 1)">−</button>
            <button class="map-btn" onclick="findMe()">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#4285F4" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="22" y1="12" x2="18" y2="12"></line><line x1="6" y1="12" x2="2" y2="12"></line>
                    <line x1="12" y1="6" x2="12" y2="2"></line><line x1="12" y1="22" x2="12" y2="18"></line>
                    <circle cx="12" cy="12" r="3" fill="#4285F4"></circle>
                </svg>
            </button>
        </div>

        <div id="legend-toggle" onclick="toggleLegend()">?</div>
        <div id="legend">
            <b>DESEMPENHO DO MÊS</b><br>
            <div class="legend-row" style="color:#28a745;">{ICON_BASKET} Comprou</div>
            <div class="legend-row" style="color:#FF3131;">{ICON_BASKET} Não Comprou</div>
            <div class="legend-row" style="color:#7f8c8d;">{ICON_BASKET} Inativo</div>
            <div class="legend-row" style="color:#007bff;">{ICON_BASKET} Prospecção</div>
        </div>

        <div id="map"></div>

        <script>
            var map, markers = [], infoWindow, userMarker, beamOverlay;
            var data = {markers_json};

            function toggleMenu() {{ var m = document.getElementById('filter-menu'); m.style.display = (m.style.display === 'block') ? 'none' : 'block'; }}
            function toggleLegend() {{ var l = document.getElementById('legend'); l.style.display = (l.style.display === 'block') ? 'none' : 'block'; }}
            function clearSearchInput() {{ document.getElementById('search-input').value = ''; document.getElementById('clear-search').style.display = 'none'; document.getElementById('suggestions').style.display = 'none'; }}

            function toggleAccordion(header) {{
                var content = header.nextElementSibling;
                var arrow = header.querySelector('.arrow');
                if (content.style.display === "block") {{
                    content.style.display = "none";
                    arrow.classList.remove('open');
                }} else {{
                    content.style.display = "block";
                    arrow.classList.add('open');
                }}
            }}

            function selectAll(btn, checkState) {{
                var group = btn.closest('.filter-content');
                var checkboxes = group.querySelectorAll('input[type="checkbox"]');
                checkboxes.forEach(c => c.checked = checkState);
                applyFilters();
            }}

            function initMap() {{
                map = new google.maps.Map(document.getElementById('map'), {{ zoom: 11, center: {{lat: -15.7938, lng: -47.8827}}, disableDefaultUI: true }});
                infoWindow = new google.maps.InfoWindow();
                data.forEach(function(item) {{
                    var marker = new google.maps.Marker({{
                        position: {{lat: item.lat, lng: item.lng}}, map: map,
                        icon: {{ path: 'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-12-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z', fillColor: item.cor_hex, fillOpacity: 1, strokeWeight: 2, strokeColor: '#FFFFFF', scale: 2, anchor: new google.maps.Point(12, 22) }},
                        searchTag: item.search, nome: item.nome, metaStatusCat: item.status_cat, metaSetor: item.setor, metaSegmento: item.segmentacao, metaRegiao: item.regiao
                    }});
                    marker.addListener('click', () => {{ infoWindow.setContent(item.content); infoWindow.open(map, marker); }});
                    markers.push(marker);
                }});
                document.querySelectorAll('.filter-check').forEach(chk => chk.onchange = applyFilters);
            }}

            function applyFilters() {{
                const showSim = document.querySelector('input[value="comprou_sim"]').checked;
                const showNao = document.querySelector('input[value="comprou_nao"]').checked;
                const showInat = document.querySelector('input[value="inativo"]').checked;
                const showProsp = document.querySelector('input[value="prospeccao"]').checked;

                const activeSetores = Array.from(document.querySelectorAll('.set-filter:checked')).map(c => c.value);
                const activeSegs = Array.from(document.querySelectorAll('.seg-filter:checked')).map(c => c.value);
                const activeRegioes = Array.from(document.querySelectorAll('.reg-filter:checked')).map(c => c.value);

                markers.forEach(m => {{
                    let vStatus = (m.metaStatusCat === 'inativo' && showInat) || (m.metaStatusCat === 'comprou_sim' && showSim) || (m.metaStatusCat === 'comprou_nao' && showNao) || (m.metaStatusCat === 'prospeccao' && showProsp);
                    let vSetor = activeSetores.includes(m.metaSetor);
                    let vSeg = activeSegs.includes(m.metaSegmento);
                    let vRegiao = activeRegioes.includes(m.metaRegiao);

                    m.setVisible(vStatus && vSetor && vSeg && vRegiao);
                }});
            }}

            function BeamOverlay(pos) {{ this.pos = pos; this.div = null; this.setMap(map); }}
            BeamOverlay.prototype = new google.maps.OverlayView();
            BeamOverlay.prototype.onAdd = function() {{ var div = document.createElement('div'); div.className = 'beam-container'; div.innerHTML = '<div class="beam-shape"></div>'; this.div = div; this.getPanes().overlayMouseTarget.appendChild(div); }};
            BeamOverlay.prototype.draw = function() {{ var proj = this.getProjection(); var pxl = proj.fromLatLngToDivPixel(this.pos); this.div.style.left = pxl.x + 'px'; this.div.style.top = pxl.y + 'px'; }};

            function findMe() {{
                if (navigator.geolocation) {{
                    navigator.geolocation.getCurrentPosition(p => {{
                        var pos = {{lat: p.coords.latitude, lng: p.coords.longitude}};
                        map.setCenter(pos); map.setZoom(16);
                        if (userMarker) userMarker.setMap(null);
                        userMarker = new google.maps.Marker({{ position: pos, map: map, icon: {{ path: google.maps.SymbolPath.CIRCLE, scale: 8, fillColor: "#4285F4", fillOpacity: 1, strokeColor: "white", strokeWeight: 2 }} }});
                        if (beamOverlay) beamOverlay.setMap(null);
                        beamOverlay = new BeamOverlay(pos);
                        window.addEventListener('deviceorientationabsolute', e => {{ if (beamOverlay && beamOverlay.div && e.alpha !== null) {{ beamOverlay.div.firstChild.style.transform = 'rotate(' + (360 - e.alpha) + 'deg)'; }} }}, true);
                    }});
                }}
            }}

            const input = document.getElementById('search-input'), clearBtn = document.getElementById('clear-search'), suggs = document.getElementById('suggestions');
            input.oninput = () => {{
                var val = input.value.toLowerCase(); clearBtn.style.display = val ? 'block' : 'none'; suggs.innerHTML = '';
                if(val) {{
                    markers.forEach(m => {{ if(m.searchTag.includes(val) && m.getVisible()) {{ var d = document.createElement('div'); d.className = 'suggestion-item'; d.innerHTML = '📍 ' + m.nome; d.onclick = () => {{ map.setCenter(m.getPosition()); map.setZoom(17); google.maps.event.trigger(m, 'click'); suggs.style.display = 'none'; }}; suggs.appendChild(d); }} }});
                    suggs.style.display = 'block';
                }} else {{ suggs.style.display = 'none'; }}
            }};
            google.maps.event.addDomListener(window, 'load', initMap);
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/", response_class=HTMLResponse)
def index():
    return carregar_dados_e_gerar_html()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)