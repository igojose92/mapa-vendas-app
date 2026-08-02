# -*- coding: utf-8 -*-
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
import pandas as pd
import os

app = FastAPI()

# Função para carregar os dados do CSV e gerar o HTML completo do aplicativo
def carregar_dados_e_gerar_html():
    # Caminho do arquivo CSV de clientes/vendas
    csv_path = "dados/clientes_vendas_testes.csv"
    
    # DataFrame padrão de segurança caso o arquivo não exista
    df = pd.DataFrame(columns=[
        'id', 'cliente', 'endereco', 'bairro', 'cidade', 'estado', 
        'latitude', 'longitude', 'status_venda', 'valor_compra', 'tipo_cliente'
    ])
    
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
        except Exception:
            try:
                df = pd.read_csv(csv_path, encoding='latin1')
            except Exception:
                pass

    # Converte os dados do DataFrame para formato JSON seguro para o Front-end
    dados_json = df.to_json(orient='records', force_ascii=False)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Meu App de Vendas e Clientes</title>
        
        <!-- Tailwind CSS -->
        <script src="https://cdn.tailwindcss.com"></script>
        <!-- Leaflet CSS & JS -->
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <!-- FontAwesome -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
        <!-- Google Fonts -->
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">

        <style>
            body {{
                font-family: 'Inter', sans-serif;
            }}
            #map {{
                height: calc(100vh - 4rem);
                width: 100%;
                z-index: 10;
            }}
            .custom-scrollbar::-webkit-scrollbar {{
                width: 6px;
                height: 6px;
            }}
            .custom-scrollbar::-webkit-scrollbar-track {{
                background: #f1f1f1;
            }}
            .custom-scrollbar::-webkit-scrollbar-thumb {{
                background: #cbd5e1;
                border-radius: 3px;
            }}
            .custom-scrollbar::-webkit-scrollbar-thumb:hover {{
                background: #94a3b8;
            }}
        </style>
    </head>
    <body class="bg-slate-100 text-slate-800 h-screen flex flex-col overflow-hidden">

        <!-- HEADER SUPERIOR -->
        <header class="bg-slate-900 text-white h-16 flex items-center justify-between px-6 shadow-md shrink-0 z-30">
            <div class="flex items-center space-x-3">
                <div class="bg-indigo-600 p-2 rounded-lg text-white flex items-center justify-center shadow-sm">
                    <i class="fa-solid fa-chart-line text-lg"></i>
                </div>
                <div>
                    <h1 class="text-base font-bold tracking-wide">Painel de Vendas & Clientes</h1>
                    <p class="text-xs text-slate-400">Gestão Comercial Inteligente</p>
                </div>
            </div>

            <!-- PERFIL DO USUÁRIO E MENU -->
            <div class="flex items-center space-x-4">
                <div class="relative">
                    <button id="user-menu-button" onclick="toggleUserMenu()" class="flex items-center space-x-3 focus:outline-none bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-full transition border border-slate-700">
                        <div class="w-8 h-8 rounded-full bg-indigo-500 text-white flex items-center justify-center font-bold text-sm overflow-hidden relative shadow-inner">
                            <span id="avatar-btn-initial">U</span>
                            <img id="avatar-btn-img" src="" alt="Perfil" class="w-full h-full object-cover hidden" />
                        </div>
                        <span id="user-name-display" class="text-sm font-medium text-slate-200">Igor José</span>
                        <i class="fa-solid fa-chevron-down text-xs text-slate-400"></i>
                    </button>

                    <!-- Dropdown do Usuário -->
                    <div id="user-dropdown" class="hidden absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl py-2 text-slate-700 z-50 border border-slate-100">
                        <div class="px-4 py-2 border-b border-slate-100">
                            <p class="text-xs text-slate-400">Conectado como</p>
                            <p id="user-email-display" class="text-sm font-semibold text-slate-800 truncate">igojose95@gmail.com</p>
                        </div>
                        <label class="w-full text-left px-4 py-2.5 text-sm hover:bg-slate-50 flex items-center space-x-2 text-slate-600 cursor-pointer">
                            <i class="fa-solid fa-camera w-4 text-indigo-500"></i>
                            <span>Alterar Foto</span>
                            <input type="file" id="image-upload" accept="image/*" class="hidden" onchange="handleImageUpload(event)" />
                        </label>
                        <button onclick="editName()" class="w-full text-left px-4 py-2.5 text-sm hover:bg-slate-50 flex items-center space-x-2 text-slate-600">
                            <i class="fa-solid fa-pen w-4 text-indigo-500"></i>
                            <span>Alterar Nome</span>
                        </button>
                        <div class="border-t border-slate-100 my-1"></div>
                        <div class="px-4 py-2">
                            <p class="text-xs font-semibold text-slate-400 mb-1.5">Tema do Sistema</p>
                            <div class="grid grid-cols-3 gap-1 bg-slate-100 p-1 rounded-lg">
                                <button onclick="setTheme('light')" id="theme-light-btn" class="text-xs py-1 rounded font-medium text-slate-600 hover:bg-white transition">Claro</button>
                                <button onclick="setTheme('dark')" id="theme-dark-btn" class="text-xs py-1 rounded font-medium text-slate-600 hover:bg-white transition">Escuro</button>
                                <button onclick="setTheme('device')" id="theme-device-btn" class="text-xs py-1 rounded font-medium text-slate-600 hover:bg-white transition">Auto</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </header>

        <!-- CORPO PRINCIPAL -->
        <div class="flex flex-1 overflow-hidden relative">
            
            <!-- PAINEL LATERAL DE FILTROS E LISTA -->
            <aside class="w-96 bg-white border-r border-slate-200 flex flex-col shrink-0 z-20 shadow-lg">
                
                <!-- Barra de Pesquisa e Filtros Gerais -->
                <div class="p-4 border-b border-slate-200 bg-slate-50 space-y-3">
                    <div class="relative">
                        <span class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-slate-400">
                            <i class="fa-solid fa-search"></i>
                        </span>
                        <input type="text" id="search-input" oninput="filtrarDados()" placeholder="Buscar cliente, bairro, cidade..." 
                            class="w-full pl-10 pr-4 py-2 bg-white border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 shadow-sm transition">
                    </div>

                    <!-- Filtros Rápidos (Cores normais, sem neon) -->
                    <div class="grid grid-cols-2 gap-2 text-xs">
                        <div>
                            <label class="block font-semibold text-slate-600 mb-1">Status da Venda</label>
                            <select id="filter-status" onchange="filtrarDados()" class="w-full p-2 bg-white border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                                <option value="">Todos Status</option>
                                <option value="Realizada">Realizada (Verde)</option>
                                <option value="Pendente">Pendente (Vermelho)</option>
                            </select>
                        </div>
                        <div>
                            <label class="block font-semibold text-slate-600 mb-1">Faixa de Compra</label>
                            <select id="filter-valor" onchange="filtrarDados()" class="w-full p-2 bg-white border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-none">
                                <option value="">Todos Valores</option>
                                <option value="baixo">&lt; R$ 1.000</option>
                                <option value="medio">R$ 1k - R$ 5k</option>
                                <option value="alto">&gt; R$ 5.000</option>
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Resumo dos Indicadores (Cores sem neon) -->
                <div class="grid grid-cols-2 gap-2 p-3 bg-slate-100 border-b border-slate-200 text-xs">
                    <div class="bg-white p-2.5 rounded-lg border border-slate-200 shadow-sm flex items-center justify-between">
                        <div>
                            <p class="text-slate-500 font-medium">Total Clientes</p>
                            <p id="kpi-total-clientes" class="text-base font-bold text-slate-800">0</p>
                        </div>
                        <div class="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                            <i class="fa-solid fa-users"></i>
                        </div>
                    </div>
                    <div class="bg-white p-2.5 rounded-lg border border-slate-200 shadow-sm flex items-center justify-between">
                        <div>
                            <p class="text-slate-500 font-medium">Vendas Realizadas</p>
                            <!-- Cores normais (verde normal, sem neon) -->
                            <p id="kpi-total-vendas" class="text-base font-bold text-emerald-600">R$ 0</p>
                        </div>
                        <div class="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
                            <i class="fa-solid fa-wallet"></i>
                        </div>
                    </div>
                </div>

                <!-- Lista de Clientes -->
                <div id="clientes-list" class="flex-1 overflow-y-auto custom-scrollbar divide-y divide-slate-100">
                    <!-- Preenchido via JavaScript -->
                </div>
            </aside>

            <!-- ÁREA DO MAPA -->
            <main class="flex-1 relative">
                <div id="map"></div>
            </main>
        </div>

        <!-- Script Principal com Dados e Lógica do App -->
        <script>
            // Dados injetados pelo Python
            const dadosClientes = {json.dumps(df.to_dict(orient='records'), ensure_ascii=False)};

            let map;
            let markersLayer = L.layerGroup();
            let loggedUserEmail = "igojose95@gmail.com";

            // Inicialização daAplicação
            document.addEventListener('DOMContentLoaded', function() {{
                initMap();
                loadUserProfile();
                renderizarClientes(dadosClientes);
                atualizarKPIs(dadosClientes);
            }});

            function initMap() {{
                // Coordenadas iniciais centradas (exemplo padrão Brasil)
                map = L.map('map', {{ zoomControl: false }}).setView([-15.7885, -47.8929], 4);

                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    maxZoom: 19,
                    attribution: '&copy; OpenStreetMap contributors'
                }}).addTo(map);

                // Adiciona controle de zoom no canto superior direito
                L.control.zoom({{ position: 'topright' }}).addTo(map);
                markersLayer.addTo(map);

                atualizarMarkers(dadosClientes);
            }}

            function renderizarClientes(clientes) {{
                const container = document.getElementById('clientes-list');
                container.innerHTML = '';

                if (clientes.length === 0) {{
                    container.innerHTML = `
                        <div class="p-8 text-center text-slate-400">
                            <i class="fa-solid fa-folder-open text-3xl mb-2"></i>
                            <p class="text-sm">Nenhum registro encontrado.</p>
                        </div>
                    `;
                    return;
                }}

                clientes.forEach(c => {{
                    const isRealizada = c.status_venda && c.status_venda.toLowerCase() === 'realizada';
                    // Cores normais (verde normal / vermelho normal, sem neon)
                    const statusBgClass = isRealizada ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700';
                    const statusDotClass = isRealizada ? 'bg-emerald-500' : 'bg-rose-500';

                    const card = document.createElement('div');
                    card.className = "p-3.5 hover:bg-slate-50 cursor-pointer transition border-l-4 " + (isRealizada ? "border-emerald-500" : "border-rose-500");
                    card.onclick = () => centralizarCliente(c.latitude, c.longitude, c.id);
                    
                    card.innerHTML = `
                        <div class="flex items-start justify-between">
                            <h3 class="text-sm font-semibold text-slate-800 truncate max-w-[200px]">${{c.cliente || 'Cliente sem Nome'}}</h3>
                            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${{statusBgClass}}">
                                <span class="w-1.5 h-1.5 mr-1.5 rounded-full ${{statusDotClass}}"></span>
                                ${{c.status_venda || 'Pendente'}}
                            </span>
                        </div>
                        <p class="text-xs text-slate-500 mt-1 truncate"><i class="fa-solid fa-location-dot mr-1 text-slate-400"></i>${{c.endereco || ''}}, ${{c.bairro || ''}}</p>
                        <div class="mt-2 flex items-center justify-between text-xs">
                            <span class="font-bold text-slate-700">R$ ${{Number(c.valor_compra || 0).toLocaleString('pt-BR', {{minimumFractionDigits: 2}})}}</span>
                            <span class="text-slate-400">${{c.cidade || ''}} / ${{c.estado || ''}}</span>
                        </div>
                    `;
                    container.appendChild(card);
                }});
            }}

            function atualizarMarkers(clientes) {{
                markersLayer.clearLayers();

                clientes.forEach(c => {{
                    if (c.latitude && c.longitude) {{
                        const isRealizada = c.status_venda && c.status_venda.toLowerCase() === 'realizada';
                        
                        // Cores normais para os pinos do mapa (verde normal / vermelho normal, sem neon)
                        const pinColor = isRealizada ? '#10b981' : '#f43f5e'; 
                        
                        const customIcon = L.divIcon({{
                            className: 'custom-pin',
                            html: `<div style="background-color: ${{pinColor}}; width: 24px; height: 24px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-size: 10px;"><i class="fa-solid fa-store"></i></div>`,
                            iconSize: [24, 24],
                            iconAnchor: [12, 12]
                        }});

                        const marker = L.marker([c.latitude, c.longitude], {{ icon: customIcon }});
                        
                        marker.bindPopup(`
                            <div class="p-2 text-xs">
                                <h4 class="font-bold text-slate-800 text-sm mb-1">${{c.cliente}}</h4>
                                <p class="text-slate-600 mb-1"><i class="fa-solid fa-location-dot mr-1"></i>${{c.endereco}}, ${{c.bairro}} - ${{c.cidade}}/${{c.estado}}</p>
                                <p class="font-semibold text-slate-700 mb-1">Valor: R$ ${{Number(c.valor_compra || 0).toLocaleString('pt-BR', {{minimumFractionDigits: 2}})}}</p>
                                <span class="inline-block px-2 py-0.5 rounded text-white font-medium ${{isRealizada ? 'bg-emerald-600' : 'bg-rose-600'}}">${{c.status_venda || 'Pendente'}}</span>
                            </div>
                        `);

                        markersLayer.addLayer(marker);
                    }}
                }});
            }}

            function centralizarCliente(lat, lon, id) {{
                if (lat && lon) {{
                    map.setView([lat, lon], 16, {{ animate: true }});
                }}
            }}

            function filtrarDados() {{
                const termo = document.getElementById('search-input').value.toLowerCase();
                const statusFiltro = document.getElementById('filter-status').value.toLowerCase();
                const valorFiltro = document.getElementById('filter-valor').value;

                const filtrados = dadosClientes.filter(c => {{
                    const nomeMatch = (c.cliente || '').toLowerCase().includes(termo) ||
                                      (c.bairro || '').toLowerCase().includes(termo) ||
                                      (c.cidade || '').toLowerCase().includes(termo);
                    
                    const statusMatch = !statusFiltro || (c.status_venda || '').toLowerCase() === statusFiltro;

                    let valorMatch = true;
                    const val = Number(c.valor_compra || 0);
                    if (valorFiltro === 'baixo') valorMatch = val < 1000;
                    else if (valorFiltro === 'medio') valorMatch = val >= 1000 && val <= 5000;
                    else if (valorFiltro === 'alto') valorMatch = val > 5000;

                    return nomeMatch && statusMatch && valorMatch;
                }});

                renderizarClientes(filtrados);
                atualizarMarkers(filtrados);
                atualizarKPIs(filtrados);
            }}

            function atualizarKPIs(clientes) {{
                document.getElementById('kpi-total-clientes').innerText = clientes.length;
                
                const somaVendas = clientes
                    .filter(c => c.status_venda && c.status_venda.toLowerCase() === 'realizada')
                    .reduce((acc, curr) => acc + Number(curr.valor_compra || 0), 0);

                document.getElementById('kpi-total-vendas').innerText = 'R$ ' + somaVendas.toLocaleString('pt-BR', {{ minimumFractionDigits: 2 }});
            }}

            // Funções de Perfil e Persistência de Dados
            function toggleUserMenu() {{
                const dropdown = document.getElementById('user-dropdown');
                dropdown.classList.toggle('hidden');
            }}

            window.onclick = function(event) {{
                if (!event.target.closest('#user-menu-button') && !event.target.closest('#user-dropdown')) {{
                    document.getElementById('user-dropdown').classList.add('hidden');
                }}
            }}

            function handleImageUpload(evt) {{
                var file = evt.target.files[0];
                if (file) {{
                    var reader = new FileReader();
                    reader.onload = function(e) {{
                        var imgData = e.target.result;
                        localStorage.setItem('persistent_user_avatar', imgData);
                        if (loggedUserEmail) {{
                            localStorage.setItem('user_avatar_' + loggedUserEmail, imgData);
                        }}
                        atualizarInterfaceAvatar(imgData);
                    }};
                    reader.readAsDataURL(file);
                }}
            }}

            function atualizarInterfaceAvatar(imgData) {{
                if (imgData) {{
                    document.getElementById('avatar-btn-img').src = imgData;
                    document.getElementById('avatar-btn-img').style.display = 'block';
                    document.getElementById('avatar-btn-initial').style.display = 'none';
                }} else {{
                    var initialLetter = loggedUserEmail ? loggedUserEmail.charAt(0).toUpperCase() : 'U';
                    document.getElementById('avatar-btn-img').style.display = 'none';
                    document.getElementById('avatar-btn-initial').innerText = initialLetter;
                    document.getElementById('avatar-btn-initial').style.display = 'block';
                }}
            }}

            function editName() {{
                var nameDisplay = document.getElementById('user-name-display');
                var currentName = nameDisplay.innerText;
                var newName = prompt('Digite seu nome:', currentName);
                if (newName && newName.trim() !== '') {{
                    var nomeFinal = newName.trim();
                    nameDisplay.innerText = nomeFinal;
                    localStorage.setItem('persistent_user_name', nomeFinal);
                    if (loggedUserEmail) {{
                        localStorage.setItem('user_name_' + loggedUserEmail, nomeFinal);
                    }}
                }}
            }}

            function loadUserProfile() {{
                var savedName = localStorage.getItem('persistent_user_name') || (loggedUserEmail ? localStorage.getItem('user_name_' + loggedUserEmail) : null);
                if (savedName) {{
                    document.getElementById('user-name-display').innerText = savedName;
                }} else {{
                    document.getElementById('user-name-display').innerText = "Igor José";
                }}

                var savedAvatar = localStorage.getItem('persistent_user_avatar') || (loggedUserEmail ? localStorage.getItem('user_avatar_' + loggedUserEmail) : null);
                atualizarInterfaceAvatar(savedAvatar);

                var savedTheme = localStorage.getItem('user_theme') || 'device';
                setTheme(savedTheme);
            }}

            function setTheme(theme) {{
                localStorage.setItem('user_theme', theme);
                ['light', 'dark', 'device'].forEach(t => {{
                    const btn = document.getElementById('theme-' + t + '-btn');
                    if (btn) {{
                        if (t === theme) {{
                            btn.classList.add('bg-white', 'shadow-sm', 'text-indigo-600');
                            btn.classList.remove('text-slate-600');
                        }} else {{
                            btn.classList.remove('bg-white', 'shadow-sm', 'text-indigo-600');
                            btn.classList.add('text-slate-600');
                        }}
                    }}
                }});
            }}
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/", response_class=HTMLResponse)
def read_root():
    return carregar_dados_e_gerar_html()