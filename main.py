from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import json
import os
import re
import random
import smtplib
from email.mime.text import MIMEText

app = FastAPI()

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

GOOGLE_MAPS_API_KEY = "AIzaSyAt_SgOgFsPosjtTeY1nMJVNBLbmYIBtho"
ICON_BASKET = '<svg class="basket-svg" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M17.21 9l-4.38-6.56c-.19-.28-.51-.42-.83-.42-.32 0-.64.14-.83.43L6.79 9H2c-.55 0-1 .45-1 1 0 .09.01.18.04.27l2.54 9.27c.23.84 1 1.46 1.92 1.46h13c.92 0 1.69-.62 1.93-1.46l2.54-9.27L23 10c0-.55-.45-1-1-1h-4.79zM9 9l3-4.4L15 9H9zm3 8c-1.1 0-2-.9-2-2s.9-2 2-2 2-.9 2-2 2-2z"/></svg>'

# Base de Dados de Usuários em Memória
DEFAULT_PASS = "Ambev123!"

USERS_DB = {
    "igojose95@gmail.com": {
        "password": DEFAULT_PASS,
        "first_login": True,
        "history": [DEFAULT_PASS]
    }
}

# Armazenamento temporário dos códigos de recuperação
RESET_CODES = {}

# Configurações de SMTP para envio de e-mail
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

def validar_regras_senha(senha: str) -> str:
    if len(senha) < 6:
        return "A senha deve ter no mínimo 6 caracteres."
    if not re.search(r"[A-Z]", senha):
        return "A senha deve conter pelo menos uma letra maiúscula."
    if not re.search(r"[0-9]", senha):
        return "A senha deve conter pelo menos um número."
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", senha):
        return "A senha deve conter pelo menos um caractere especial."
    return ""

def enviar_codigo_email(destinatario: str, codigo: str):
    if SMTP_USER and SMTP_PASS:
        try:
            msg = MIMEText(f"Seu código de verificação para redefinição de senha é: {codigo}")
            msg['Subject'] = 'Código de Verificação - Mapa de Vendas'
            msg['From'] = SMTP_USER
            msg['To'] = destinatario

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_USER, [destinatario], msg.as_string())
        except Exception as e:
            print(f"Erro ao enviar e-mail via SMTP: {e}")
    else:
        print(f"[LOG DE SEGURANÇA] Código enviado para {destinatario}: {codigo}")

@app.post("/api/login")
def login(email: str = Form(...), password: str = Form(...)):
    email_clean = email.strip().lower()
    
    if email_clean not in USERS_DB:
        raise HTTPException(status_code=401, detail="E-mail não autorizado.")
    
    user = USERS_DB[email_clean]
    
    if user["password"] != password:
        raise HTTPException(status_code=401, detail="Senha incorreta.")
    
    return {
        "success": True,
        "first_login": user["first_login"],
        "email": email_clean
    }

@app.post("/api/change-password")
def change_password(email: str = Form(...), old_password: str = Form(...), new_password: str = Form(...)):
    email_clean = email.strip().lower()
    
    if email_clean not in USERS_DB:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    user = USERS_DB[email_clean]
    
    if user["password"] != old_password:
        raise HTTPException(status_code=400, detail="Senha atual não confere.")
        
    erro_validacao = validar_regras_senha(new_password)
    if erro_validacao:
        raise HTTPException(status_code=400, detail=erro_validacao)
        
    if new_password in user["history"][-3:]:
        raise HTTPException(status_code=400, detail="A nova senha não pode ser igual a nenhuma das últimas 3 senhas utilizadas.")
        
    user["password"] = new_password
    user["first_login"] = False
    user["history"].append(new_password)
    
    return {"success": True, "message": "Senha alterada com sucesso!"}

@app.post("/api/forgot-password")
def forgot_password(email: str = Form(...)):
    email_clean = email.strip().lower()
    
    if email_clean not in USERS_DB:
        raise HTTPException(status_code=404, detail="E-mail não autorizado ou não cadastrado.")
    
    code = str(random.randint(100000, 999999))
    RESET_CODES[email_clean] = code
    
    enviar_codigo_email(email_clean, code)
    
    return {"success": True, "message": "Código de verificação enviado para o seu e-mail!"}

@app.post("/api/reset-password")
def reset_password(email: str = Form(...), code: str = Form(...), new_password: str = Form(...)):
    email_clean = email.strip().lower()
    
    if email_clean not in USERS_DB:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        
    if RESET_CODES.get(email_clean) != code.strip():
        raise HTTPException(status_code=400, detail="Código de verificação inválido.")
        
    erro_validacao = validar_regras_senha(new_password)
    if erro_validacao:
        raise HTTPException(status_code=400, detail=erro_validacao)
        
    user = USERS_DB[email_clean]
    if new_password in user["history"][-3:]:
        raise HTTPException(status_code=400, detail="A nova senha não pode ser igual a nenhuma das últimas 3 senhas utilizadas.")
        
    user["password"] = new_password
    user["first_login"] = False
    user["history"].append(new_password)
    del RESET_CODES[email_clean]
    
    return {"success": True, "message": "Senha redefinida com sucesso!"}

def formatar_setor(valor):
    if str(valor).strip() == '':
        return ''
    val_str = str(valor).split('.')[0].strip()
    return val_str.zfill(3) if val_str.isdigit() else val_str

def carregar_dados_e_gerar_html():
    try:
        df = None
        pasta_dados = "dados"
        
        if not os.path.exists(pasta_dados):
            return f"<h1 style='font-family:sans-serif; color:#ff3131; padding:20px;'>Erro: A pasta '{pasta_dados}' não foi encontrada no projeto.</h1>"

        arquivos = [f for f in os.listdir(pasta_dados) if not f.startswith("~$")]
        
        for nome in arquivos:
            if "clientes_vendas_teste" in nome:
                caminho_completo = os.path.join(pasta_dados, nome)
                
                try:
                    df = pd.read_csv(caminho_completo, dtype={'Setor': str}, sep=None, engine='python', encoding='utf-8-sig')
                    break
                except Exception:
                    pass

                try:
                    df = pd.read_csv(caminho_completo, dtype={'Setor': str}, sep=None, engine='python', encoding='latin1')
                    break
                except Exception:
                    pass

                try:
                    df = pd.read_excel(caminho_completo, engine='openpyxl', dtype={'Setor': str})
                    break
                except Exception:
                    pass

        if df is None:
            return f"<h1 style='font-family:sans-serif; color:#ff3131; padding:20px;'>Erro: Não foi possível ler o arquivo de dados na pasta 'dados/'. Certifique-se de que o arquivo 'clientes_vendas_teste' está lá.</h1>"

        df = df.fillna('')
        df.columns = [str(c).strip() for c in df.columns]

        if 'Setor' in df.columns:
            df['Setor'] = df['Setor'].apply(formatar_setor)

        col_setor = 'Setor' if 'Setor' in df.columns else ''
        col_seg = 'Segmentação' if 'Segmentação' in df.columns else ''
        col_reg = 'Região (DF)' if 'Região (DF)' in df.columns else ''

        setores_unicos = sorted([str(s) for s in df[col_setor].unique() if str(s).strip() != '']) if col_setor else []
        segmentacoes_unicas = sorted([str(s) for s in df[col_seg].unique() if str(s).strip() != '']) if col_seg else []
        regioes_unicas = sorted([str(r) for r in df[col_reg].unique() if str(r).strip() != '']) if col_reg else []

        markers_list = []
        for _, row in df.iterrows():
            try:
                lat_str = str(row['Latitude']).replace(',', '.').strip()
                lng_str = str(row['Longitude']).replace(',', '.').strip()
                lat = float(lat_str)
                lng = float(lng_str)
            except (ValueError, TypeError, KeyError):
                continue

            cliente = str(row.get('Nome Fantasia', 'Cliente'))
            cnpj = str(row.get('CNPJ', ''))
            status_cadastral = str(row.get('Status', '')).strip()
            comprou = str(row.get('Comprou no Mês', '')).strip()
            setor_formatado = str(row.get('Setor', ''))
            
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
            
            content_html = f"""
                <div style='width: 280px; max-width: 82vw; max-height: 75vh; overflow-y: auto; font-family: sans-serif; line-height: 1.4; color: #ffffff; background: #2c3e50; padding: 0; border-radius: 10px; box-shadow: 0 8px 20px rgba(0,0,0,0.4); position: relative; user-select: none; -webkit-user-select: none;'>
                    <div style='background:{cor_hex}; color:white; padding: 12px; padding-right: 45px; border-radius: 10px 10px 0 0;'>
                        <div style='font-size:15px; font-weight:bold; word-wrap: break-word;'>{cliente}</div>
                        <div style='font-size:11px; opacity:0.9;'>CNPJ: {cnpj} | Cód: {codigo_cli}</div>
                    </div>
                    <div style='padding: 10px 12px 12px 12px;'>
                        <div style='font-size:12px; padding-bottom: 8px; color: #ecf0f1;'>
                            <b>Região:</b> {row.get('Região (DF)', '')}<br>
                            <b>Segmentação:</b> {row.get('Segmentação', '')}<br>
                            <b>Setor:</b> {setor_formatado}<br>
                            <b>Representante:</b> {row.get('Representante', '')}<br>
                            <b>Dia de Visita:</b> {row.get('Dia de Visita', '')}<br>
                            <b>Frequência:</b> {row.get('Frequência de Visita', '')}<br>
                            <b>Equipamentos (Freezers):</b> {row.get('Qtd Equipamentos (Freezers)', '')}<br>
                            <b>Data do Cadastro:</b> {row.get('Data de Cadastro', '')}<br>
                            <b>Pagamento:</b> {row.get('Tipo de Pagamento', '')} {f" - Prazo: {row.get('Prazo Boleto (Dias)', '')}d" if str(row.get('Tipo de Pagamento', '')).lower() == 'boleto' else ''}<br>
                            <b>Limite Crédito:</b> <span style='color:#2ecc71; font-weight:bold;'>R$ {row.get('Limite de Crédito (R$)', '')}</span><br>
                            <b>Contato:</b> {row.get('Telefone Contato', '')}<br>
                            <b>E-mail:</b> {row.get('E-mail Contato', '')}
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
                "segmentacao": str(row.get('Segmentação', '')),
                "regiao": str(row.get('Região (DF)', ''))
            })

        markers_json = json.dumps(markers_list)

        # Gerando checkboxes dinamicos para Setor, Segmentação e Região DF
        checkboxes_setor = "".join([
            f'<label class="chk-item"><input type="checkbox" class="chk-setor" value="{s}" checked onchange="applyFilters()"> {s}</label>'
            for s in setores_unicos
        ])
        
        checkboxes_seg = "".join([
            f'<label class="chk-item"><input type="checkbox" class="chk-seg" value="{s}" checked onchange="applyFilters()"> {s}</label>'
            for s in segmentacoes_unicas
        ])
        
        checkboxes_reg = "".join([
            f'<label class="chk-item"><input type="checkbox" class="chk-reg" value="{r}" checked onchange="applyFilters()"> {r}</label>'
            for r in regioes_unicas
        ])

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
            <script src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&v=weekly"></script>
            <style>
                :root {{
                    --bg-primary: #2c3e50;
                    --bg-secondary: #34495e;
                    --text-color: #ffffff;
                    --border-color: #34495e;
                    --card-bg: #2c3e50;
                    --blue-accent: #308ce8;
                }}

                body.light-theme {{
                    --bg-primary: #ffffff;
                    --bg-secondary: #f0f3f6;
                    --text-color: #2c3e50;
                    --border-color: #dcdde1;
                    --card-bg: #ffffff;
                }}

                body, html {{ 
                    height: 100%; 
                    margin: 0; 
                    padding: 0; 
                    font-family: 'Segoe UI', sans-serif; 
                    overflow: hidden; 
                    user-select: none;
                    -webkit-user-select: none;
                }}
                
                *:focus {{ outline: none !important; }}

                #auth-overlay {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100vw;
                    height: 100vh;
                    background: #1e2833;
                    z-index: 99999;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                    box-sizing: border-box;
                }}

                .auth-card {{
                    background: #2c3e50;
                    border: 1px solid #34495e;
                    border-radius: 16px;
                    padding: 25px;
                    width: 100%;
                    max-width: 360px;
                    color: #ffffff;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                    box-sizing: border-box;
                }}

                .auth-card h2 {{
                    margin-top: 0;
                    font-size: 20px;
                    text-align: center;
                    color: #4285F4;
                    margin-bottom: 20px;
                }}

                .auth-field {{ margin-bottom: 15px; }}

                .auth-field label {{
                    display: block;
                    font-size: 12px;
                    font-weight: bold;
                    margin-bottom: 5px;
                    text-transform: uppercase;
                    opacity: 0.8;
                }}

                .auth-input {{
                    width: 100%;
                    padding: 12px;
                    border-radius: 8px;
                    background: #34495e;
                    color: #ffffff;
                    border: 1px solid #4a627a;
                    font-size: 14px;
                    box-sizing: border-box;
                    user-select: text !important;
                    -webkit-user-select: text !important;
                }}

                .auth-btn {{
                    width: 100%;
                    padding: 12px;
                    border-radius: 25px;
                    background: #4285F4;
                    color: white;
                    border: none;
                    font-weight: bold;
                    font-size: 14px;
                    cursor: pointer;
                    margin-top: 10px;
                }}

                .auth-link {{
                    display: block;
                    text-align: center;
                    margin-top: 15px;
                    font-size: 12px;
                    color: #3498db;
                    cursor: pointer;
                    text-decoration: underline;
                }}

                .auth-error {{
                    color: #ff3131;
                    font-size: 12px;
                    margin-top: 10px;
                    text-align: center;
                    display: none;
                }}

                #map {{ height: 100%; width: 100%; }}
                
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
                    background: var(--bg-primary); 
                    padding: 8px 15px; 
                    border-radius: 35px; 
                    box-shadow: 0 10px 25px rgba(0,0,0,0.5); 
                    border: 1px solid var(--border-color); 
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
                    color: var(--text-color); 
                    padding-right: 25px;
                    user-select: text !important;
                    -webkit-user-select: text !important;
                }}
                #clear-search {{ position: absolute; right: 15px; color: #ff3131; font-weight: bold; cursor: pointer; font-size: 20px; display: none; }}
                #suggestions {{ background: var(--bg-primary); border-radius: 20px; margin-top: 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.4); max-height: 200px; overflow-y: auto; display: none; border: 1px solid var(--border-color); }}
                .suggestion-item {{ padding: 12px 20px; cursor: pointer; border-bottom: 1px solid var(--border-color); font-size: 14px; color: #4285F4; }}
                
                #legend-toggle {{ position: absolute; bottom: 25px; right: 10px; background: var(--bg-primary); color: var(--text-color); width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: bold; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.3); z-index: 6; border: 1px solid var(--border-color); }}
                #legend {{ position: absolute; bottom: 75px; right: 10px; background: white; padding: 10px; border-radius: 12px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); z-index: 5; font-size: 12px; border-left: 5px solid #4285F4; display: none; color: #2c3e50; }}
                .legend-row {{ display: flex; align-items: center; margin-bottom: 5px; font-weight: 600; gap: 8px; }}
                .basket-svg {{ width: 18px; height: 18px; }}
                
                #profile-btn {{ 
                    position: absolute; 
                    left: 15px; 
                    top: 15px; 
                    z-index: 20; 
                    width: 44px; 
                    height: 44px; 
                    border-radius: 50%; 
                    overflow: hidden; 
                    cursor: pointer; 
                    border: 2px solid #4285F4; 
                    box-shadow: 0 4px 10px rgba(0,0,0,0.3); 
                    background: #000000; 
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                }}
                #profile-btn img {{ width: 100%; height: 100%; object-fit: cover; display: none; }}
                #profile-btn .avatar-initial {{ color: #ffffff; font-weight: bold; font-size: 20px; text-transform: uppercase; }}

                .action-btn {{ position: absolute; left: 15px; z-index: 20; width: 42px; height: 42px; border-radius: 50%; background: var(--bg-primary); color: var(--text-color); display: flex; align-items: center; justify-content: center; cursor: pointer; border: 1px solid var(--border-color); box-shadow: 0 4px 10px rgba(0,0,0,0.3); transition: all 0.2s ease; }}
                .action-btn:hover {{ transform: scale(1.05); }}
                .action-btn svg {{ width: 22px; height: 22px; fill: var(--blue-accent); }}

                #filter-toggle-btn {{ top: 70px; }}
                #location-btn {{ top: 122px; }}

                /* Botão de Fechar Quadrado Vermelho com X */
                .close-window-btn {{
                    position: absolute;
                    top: 12px;
                    right: 12px;
                    width: 28px;
                    height: 28px;
                    background-color: #ff3131;
                    border-radius: 6px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    font-size: 16px;
                    cursor: pointer;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                    z-index: 30;
                    user-select: none;
                }}
                .close-window-btn:hover {{
                    background-color: #d62828;
                }}

                /* Menu de Perfil */
                #profile-menu {{ 
                    position: absolute; 
                    left: 15px; 
                    top: 68px; 
                    background: var(--bg-primary); 
                    padding: 20px 15px 15px 15px; 
                    border-radius: 15px; 
                    color: var(--text-color); 
                    border: 1px solid var(--border-color); 
                    display: none; 
                    width: 250px; 
                    box-shadow: 0 10px 25px rgba(0,0,0,0.5); 
                    z-index: 25; 
                }}
                .profile-header {{ display: flex; flex-direction: column; align-items: center; margin-bottom: 15px; border-bottom: 1px solid var(--border-color); padding-bottom: 12px; }}
                .profile-img-wrapper {{ 
                    width: 70px; 
                    height: 70px; 
                    border-radius: 50%; 
                    overflow: hidden; 
                    border: 2px solid #4285F4; 
                    cursor: pointer; 
                    position: relative; 
                    margin-bottom: 8px; 
                    background: #000000; 
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                }}
                .profile-img-wrapper img {{ width: 100%; height: 100%; object-fit: cover; display: none; }}
                .profile-img-wrapper .avatar-initial-large {{ color: #ffffff; font-weight: bold; font-size: 32px; text-transform: uppercase; }}
                .profile-img-wrapper::after {{ content: '📷'; position: absolute; bottom: 0; background: rgba(0,0,0,0.6); width: 100%; text-align: center; font-size: 10px; color: white; padding: 2px 0; }}
                .profile-name {{ font-weight: bold; font-size: 15px; cursor: pointer; display: flex; align-items: center; gap: 5px; color: var(--text-color); }}
                .profile-name:hover {{ color: #4285F4; }}
                .theme-section {{ margin-top: 10px; }}
                .theme-title {{ font-size: 12px; font-weight: bold; margin-bottom: 8px; opacity: 0.8; text-transform: uppercase; }}
                .theme-options {{ display: flex; flex-direction: column; gap: 6px; }}
                .theme-btn {{ background: var(--bg-secondary); color: var(--text-color); border: 1px solid var(--border-color); padding: 8px 10px; border-radius: 8px; cursor: pointer; font-size: 12px; text-align: left; display: flex; align-items: center; justify-content: space-between; }}
                .theme-btn.active {{ border-color: #4285F4; font-weight: bold; background: #4285F4; color: white; }}

                /* Menu de Filtros Avançado (Igual ao Vídeo) */
                #filter-menu {{ 
                    position: absolute; 
                    left: 15px; 
                    top: 125px; 
                    background: #1e2833; 
                    padding: 15px; 
                    border-radius: 15px; 
                    color: #ffffff; 
                    border: 1px solid #34495e; 
                    display: none; 
                    width: 270px; 
                    max-height: 75vh; 
                    overflow-y: auto; 
                    box-shadow: 0 10px 25px rgba(0,0,0,0.6); 
                    z-index: 25; 
                }}
                
                .filter-section {{ margin-bottom: 18px; }}
                .filter-header-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #34495e; }}
                .filter-title {{ font-size: 13px; font-weight: bold; letter-spacing: 0.5px; text-transform: uppercase; color: #ffffff; }}
                .btn-group-action {{ display: flex; gap: 4px; }}
                .btn-mini {{ background: #34495e; color: #ecf0f1; border: none; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; cursor: pointer; }}
                .btn-mini:hover {{ background: #4285F4; color: #ffffff; }}
                
                .chk-list {{ display: flex; flex-direction: column; gap: 6px; padding-left: 2px; }}
                .chk-item {{ display: flex; align-items: center; gap: 8px; font-size: 13px; color: #dcdde1; cursor: pointer; user-select: none; }}
                .chk-item input[type="checkbox"] {{ width: 16px; height: 16px; accent-color: #4285F4; cursor: pointer; }}

                #photo-source-modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 100; align-items: center; justify-content: center; }}
                .modal-box {{ background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 16px; padding: 20px; width: 80%; max-width: 280px; text-align: center; color: var(--text-color); }}
                .modal-title {{ font-weight: bold; font-size: 16px; margin-bottom: 15px; }}
                .modal-btn {{ display: block; width: 100%; padding: 12px; margin-bottom: 8px; border-radius: 10px; background: #4285F4; color: white; border: none; font-weight: bold; cursor: pointer; font-size: 14px; }}
                .modal-btn.cancel {{ background: #7f8c8d; }}
            </style>
        </head>
        <body>

            <div id="auth-overlay">
                <div id="card-login" class="auth-card">
                    <h2>Mapa de Vendas</h2>
                    <div class="auth-field">
                        <label>E-mail Autorizado</label>
                        <input type="email" id="login-email" class="auth-input" placeholder="seu@email.com">
                    </div>
                    <div class="auth-field">
                        <label>Senha</label>
                        <input type="password" id="login-pass" class="auth-input" placeholder="••••••••">
                    </div>
                    <button class="auth-btn" onclick="executarLogin()">ENTRAR</button>
                    <div id="login-err" class="auth-error"></div>
                    <span class="auth-link" onclick="mostrarTela('card-forgot')">Esqueceu a senha?</span>
                </div>

                <div id="card-first-change" class="auth-card" style="display:none;">
                    <h2>Atualizar Senha</h2>
                    <p style="font-size:12px; opacity:0.8; text-align:center;">Este é seu primeiro acesso. Atualize sua senha inicial para continuar.</p>
                    <div class="auth-field">
                        <label>Nova Senha</label>
                        <input type="password" id="first-new-pass" class="auth-input" placeholder="Nova senha">
                    </div>
                    <button class="auth-btn" onclick="executarTrocaPrimeiroAcesso()">SALVAR E CONTINUAR</button>
                    <div id="first-err" class="auth-error"></div>
                </div>

                <div id="card-forgot" class="auth-card" style="display:none;">
                    <h2>Recuperar Senha</h2>
                    <div class="auth-field">
                        <label>E-mail Autorizado</label>
                        <input type="email" id="forgot-email" class="auth-input" placeholder="seu@email.com">
                    </div>
                    <button class="auth-btn" onclick="executarEsqueceuSenha()">ENVIAR CÓDIGO</button>
                    <div id="forgot-err" class="auth-error"></div>
                    <span class="auth-link" onclick="mostrarTela('card-login')">Voltar ao Login</span>
                </div>

                <div id="card-reset" class="auth-card" style="display:none;">
                    <h2>Criar Nova Senha</h2>
                    <div class="auth-field">
                        <label>Código de Verificação</label>
                        <input type="text" id="reset-code" class="auth-input" placeholder="Código de 6 dígitos">
                    </div>
                    <div class="auth-field">
                        <label>Nova Senha</label>
                        <input type="password" id="reset-new-pass" class="auth-input" placeholder="Nova senha">
                    </div>
                    <button class="auth-btn" onclick="executarRedefinicaoSenha()">REDEFINIR SENHA</button>
                    <div id="reset-err" class="auth-error"></div>
                    <span class="auth-link" onclick="mostrarTela('card-login')">Voltar ao Login</span>
                </div>
            </div>

            <div id="profile-btn" onclick="toggleProfileMenu()">
                <img id="avatar-btn-img" src="" alt="Perfil">
                <span id="avatar-btn-initial" class="avatar-initial"></span>
            </div>

            <div id="filter-toggle-btn" class="action-btn" title="Filtros" onclick="toggleFilterMenu()">
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M10 18h4v-2h-4v2zM3 6v2h18V6H3zm3 7h12v-2H6v2z"/>
                </svg>
            </div>

            <div id="location-btn" class="action-btn" title="Minha Localização Atual" onclick="getUserLocation()">
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm0-13a5 5 0 1 0 5 5 5 5 0 0 0-5-5zm0 8a3 3 0 1 1 3-3 3 3 0 0 1-3 3z"/>
                    <path d="M12 1v3m0 16v3M1 12h3m16 0h3" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
                </svg>
            </div>

            <div id="profile-menu">
                <div class="close-window-btn" onclick="toggleProfileMenu()">✕</div>
                <div class="profile-header">
                    <div class="profile-img-wrapper" onclick="openPhotoModal()">
                        <img id="avatar-menu-img" src="" alt="Perfil">
                        <span id="avatar-menu-initial" class="avatar-initial-large"></span>
                    </div>
                    <div class="profile-name" onclick="editName()">
                        <span id="user-name-display">Usuário</span> ✏️
                    </div>
                </div>
                <div class="theme-section">
                    <div class="theme-title">Tema</div>
                    <div class="theme-options">
                        <button class="theme-btn" id="btn-theme-light" onclick="setTheme('light')">☀️ Claro</button>
                        <button class="theme-btn" id="btn-theme-dark" onclick="setTheme('dark')">🌙 Escuro</button>
                        <button class="theme-btn" id="btn-theme-device" onclick="setTheme('device')">📱 Tema do dispositivo</button>
                    </div>
                </div>
            </div>

            <div id="filter-menu">
                <div class="close-window-btn" onclick="toggleFilterMenu()">✕</div>
                
                <div class="filter-section">
                    <div class="filter-header-row">
                        <span class="filter-title">STATUS:</span>
                        <div class="btn-group-action">
                            <button class="btn-mini" onclick="selectAll('chk-status', true)">Tudo</button>
                            <button class="btn-mini" onclick="selectAll('chk-status', false)">Limpar</button>
                        </div>
                    </div>
                    <div class="chk-list">
                        <label class="chk-item"><input type="checkbox" class="chk-status" value="comprou_sim" checked onchange="applyFilters()"> Comprou</label>
                        <label class="chk-item"><input type="checkbox" class="chk-status" value="comprou_nao" checked onchange="applyFilters()"> Não Comprou</label>
                        <label class="chk-item"><input type="checkbox" class="chk-status" value="inativo" checked onchange="applyFilters()"> Inativo</label>
                        <label class="chk-item"><input type="checkbox" class="chk-status" value="prospeccao" checked onchange="applyFilters()"> Prospecção</label>
                    </div>
                </div>

                <div class="filter-section">
                    <div class="filter-header-row">
                        <span class="filter-title">SETOR:</span>
                        <div class="btn-group-action">
                            <button class="btn-mini" onclick="selectAll('chk-setor', true)">Tudo</button>
                            <button class="btn-mini" onclick="selectAll('chk-setor', false)">Limpar</button>
                        </div>
                    </div>
                    <div class="chk-list">
                        {checkboxes_setor}
                    </div>
                </div>

                <div class="filter-section">
                    <div class="filter-header-row">
                        <span class="filter-title">SEGMENTAÇÃO:</span>
                        <div class="btn-group-action">
                            <button class="btn-mini" onclick="selectAll('chk-seg', true)">Tudo</button>
                            <button class="btn-mini" onclick="selectAll('chk-seg', false)">Limpar</button>
                        </div>
                    </div>
                    <div class="chk-list">
                        {checkboxes_seg}
                    </div>
                </div>

                <div class="filter-section">
                    <div class="filter-header-row">
                        <span class="filter-title">REGIÃO DF:</span>
                        <div class="btn-group-action">
                            <button class="btn-mini" onclick="selectAll('chk-reg', true)">Tudo</button>
                            <button class="btn-mini" onclick="selectAll('chk-reg', false)">Limpar</button>
                        </div>
                    </div>
                    <div class="chk-list">
                        {checkboxes_reg}
                    </div>
                </div>
            </div>

            <div id="search-wrapper">
                <div id="search-container">
                    <input type="text" id="search-input" placeholder="Buscar cliente, CNPJ, código..." onkeyup="handleSearch(event)">
                    <span id="clear-search" onclick="clearSearch()">×</span>
                </div>
                <div id="suggestions"></div>
            </div>

            <div id="legend-toggle" onclick="toggleLegend()">?</div>
            <div id="legend">
                <div class="legend-row"><span style="color:#28a745;">●</span> Comprou no Mês</div>
                <div class="legend-row"><span style="color:#FF3131;">●</span> Não Comprou no Mês</div>
                <div class="legend-row"><span style="color:#007bff;">●</span> Prospecção</div>
                <div class="legend-row"><span style="color:#7f8c8d;">●</span> Inativo</div>
            </div>

            <div id="map"></div>

            <div id="photo-source-modal">
                <div class="modal-box">
                    <div class="modal-title">Alterar Foto de Perfil</div>
                    <button class="modal-btn" onclick="triggerFileInput('camera')">📷 Tirar Foto</button>
                    <button class="modal-btn" onclick="triggerFileInput('gallery')">🖼️ Escolher da Galeria</button>
                    <button class="modal-btn cancel" onclick="closePhotoModal()">Cancelar</button>
                </div>
            </div>

            <input type="file" id="camera-input" accept="image/*" capture="environment" style="display:none;" onchange="handleImageUpload(event)">
            <input type="file" id="gallery-input" accept="image/*" style="display:none;" onchange="handleImageUpload(event)">

            <script>
                var map;
                var markersData = {markers_json};
                var mapMarkers = [];
                var currentInfoWindow = null;
                var loggedUserEmail = "";
                var userLocationMarker = null;

                function initMap() {{
                    var centro = {{ lat: -15.7942, lng: -47.8822 }};
                    
                    if (markersData.length > 0) {{
                        centro = {{ lat: markersData[0].lat, lng: markersData[0].lng }};
                    }}

                    map = new google.maps.Map(document.getElementById('map'), {{
                        zoom: 11,
                        center: centro,
                        disableDefaultUI: true,
                        zoomControl: true
                    }});

                    var bounds = new google.maps.LatLngBounds();

                    markersData.forEach(function(item) {{
                        var latLng = new google.maps.LatLng(item.lat, item.lng);
                        bounds.extend(latLng);

                        var pinIcon = {{
                            path: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z",
                            fillColor: item.cor_hex,
                            fillOpacity: 1,
                            strokeWeight: 1,
                            strokeColor: "#ffffff",
                            scale: 1.8,
                            anchor: new google.maps.Point(12, 24)
                        }};

                        var marker = new google.maps.Marker({{
                            position: latLng,
                            map: map,
                            title: item.nome,
                            icon: pinIcon
                        }});

                        var infowindow = new google.maps.InfoWindow({{ content: item.content }});

                        marker.addListener('click', function() {{
                            if (currentInfoWindow) currentInfoWindow.close();
                            infowindow.open(map, marker);
                            currentInfoWindow = infowindow;
                        }});

                        mapMarkers.push({{
                            marker: marker,
                            data: item
                        }});
                    }});

                    if (markersData.length > 1) {{
                        map.fitBounds(bounds);
                    }}

                    // Listener para alteração do tema do sistema/dispositivo
                    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {{
                        var currentThemeSetting = localStorage.getItem('user_theme') || 'device';
                        if (currentThemeSetting === 'device') {{
                            applyThemePreference('device');
                        }}
                    }});

                    checkSession();
                }}

                window.onload = initMap;

                function getUserLocation() {{
                    if (navigator.geolocation) {{
                        navigator.geolocation.getCurrentPosition(
                            function(position) {{
                                var pos = {{
                                    lat: position.coords.latitude,
                                    lng: position.coords.longitude
                                }};

                                if (userLocationMarker) {{
                                    userLocationMarker.setPosition(pos);
                                }} else {{
                                    userLocationMarker = new google.maps.Marker({{
                                        position: pos,
                                        map: map,
                                        title: "Sua Localização",
                                        icon: {{
                                            path: google.maps.SymbolPath.CIRCLE,
                                            scale: 8,
                                            fillColor: "#308ce8",
                                            fillOpacity: 1,
                                            strokeColor: "#ffffff",
                                            strokeWeight: 3
                                        }}
                                    }});
                                }}

                                map.setCenter(pos);
                                map.setZoom(15);
                            }},
                            function() {{
                                alert("Não foi possível obter a sua localização. Verifique as permissões do seu navegador/dispositivo.");
                            }}
                        );
                    }} else {{
                        alert("Seu navegador não suporta geolocalização.");
                    }}
                }}

                function checkSession() {{
                    var savedEmail = localStorage.getItem('mapa_user_email');
                    if (savedEmail) {{
                        loggedUserEmail = savedEmail;
                        document.getElementById('auth-overlay').style.display = 'none';
                        loadUserProfile();
                    }} else {{
                        document.getElementById('auth-overlay').style.display = 'flex';
                    }}
                }}

                function mostrarTela(cardId) {{
                    document.querySelectorAll('.auth-card').forEach(c => c.style.display = 'none');
                    document.getElementById(cardId).style.display = 'block';
                }}

                function mostrarErro(elementId, msg) {{
                    var errDiv = document.getElementById(elementId);
                    errDiv.innerText = msg;
                    errDiv.style.display = 'block';
                }}

                async function executarLogin() {{
                    var email = document.getElementById('login-email').value;
                    var pass = document.getElementById('login-pass').value;
                    document.getElementById('login-err').style.display = 'none';

                    var formData = new FormData();
                    formData.append('email', email);
                    formData.append('password', pass);

                    try {{
                        var res = await fetch('/api/login', {{ method: 'POST', body: formData }});
                        var data = await res.json();
                        
                        if (!res.ok) {{
                            mostrarErro('login-err', data.detail || 'Erro ao realizar login.');
                            return;
                        }}

                        loggedUserEmail = data.email;
                        if (data.first_login) {{
                            mostrarTela('card-first-change');
                        }} else {{
                            localStorage.setItem('mapa_user_email', loggedUserEmail);
                            document.getElementById('auth-overlay').style.display = 'none';
                            loadUserProfile();
                        }}
                    }} catch (e) {{
                        mostrarErro('login-err', 'Falha na comunicação com o servidor.');
                    }}
                }}

                async function executarTrocaPrimeiroAcesso() {{
                    var newPass = document.getElementById('first-new-pass').value;
                    document.getElementById('first-err').style.display = 'none';

                    var formData = new FormData();
                    formData.append('email', loggedUserEmail);
                    formData.append('old_password', '{DEFAULT_PASS}');
                    formData.append('new_password', newPass);

                    try {{
                        var res = await fetch('/api/change-password', {{ method: 'POST', body: formData }});
                        var data = await res.json();

                        if (!res.ok) {{
                            mostrarErro('first-err', data.detail || 'Erro ao alterar senha.');
                            return;
                        }}

                        localStorage.setItem('mapa_user_email', loggedUserEmail);
                        document.getElementById('auth-overlay').style.display = 'none';
                        loadUserProfile();
                    }} catch (e) {{
                        mostrarErro('first-err', 'Falha ao conectar com o servidor.');
                    }}
                }}

                async function executarEsqueceuSenha() {{
                    var email = document.getElementById('forgot-email').value;
                    document.getElementById('forgot-err').style.display = 'none';

                    var formData = new FormData();
                    formData.append('email', email);

                    try {{
                        var res = await fetch('/api/forgot-password', {{ method: 'POST', body: formData }});
                        var data = await res.json();

                        if (!res.ok) {{
                            mostrarErro('forgot-err', data.detail || 'Erro ao solicitar código.');
                            return;
                        }}

                        loggedUserEmail = email;
                        mostrarTela('card-reset');
                    }} catch (e) {{
                        mostrarErro('forgot-err', 'Erro na requisição.');
                    }}
                }}

                async function executarRedefinicaoSenha() {{
                    var code = document.getElementById('reset-code').value;
                    var newPass = document.getElementById('reset-new-pass').value;
                    document.getElementById('reset-err').style.display = 'none';

                    var formData = new FormData();
                    formData.append('email', loggedUserEmail);
                    formData.append('code', code);
                    formData.append('new_password', newPass);

                    try {{
                        var res = await fetch('/api/reset-password', {{ method: 'POST', body: formData }});
                        var data = await res.json();

                        if (!res.ok) {{
                            mostrarErro('reset-err', data.detail || 'Erro ao redefinir.');
                            return;
                        }}

                        alert('Senha redefinida com sucesso!');
                        mostrarTela('card-login');
                    }} catch (e) {{
                        mostrarErro('reset-err', 'Erro ao conectar.');
                    }}
                }}

                // Lógica de seleção "Tudo" e "Limpar" para Filtros
                function selectAll(className, check) {{
                    var checkboxes = document.querySelectorAll('.' + className);
                    checkboxes.forEach(function(chk) {{
                        chk.checked = check;
                    }});
                    applyFilters();
                }}

                // Filtro multi-seleção por checkboxes
                function applyFilters() {{
                    var selectedStatus = Array.from(document.querySelectorAll('.chk-status:checked')).map(c => c.value);
                    var selectedSetor = Array.from(document.querySelectorAll('.chk-setor:checked')).map(c => c.value);
                    var selectedSeg = Array.from(document.querySelectorAll('.chk-seg:checked')).map(c => c.value);
                    var selectedReg = Array.from(document.querySelectorAll('.chk-reg:checked')).map(c => c.value);

                    mapMarkers.forEach(function(m) {{
                        var matchStatus = selectedStatus.length === 0 || selectedStatus.includes(m.data.status_cat);
                        var matchSetor = selectedSetor.length === 0 || selectedSetor.includes(m.data.setor);
                        var matchSeg = selectedSeg.length === 0 || selectedSeg.includes(m.data.segmentacao);
                        var matchReg = selectedReg.length === 0 || selectedReg.includes(m.data.regiao);

                        if (matchStatus && matchSetor && matchSeg && matchReg) {{
                            m.marker.setVisible(true);
                        }} else {{
                            m.marker.setVisible(false);
                        }}
                    }});
                }}

                function handleSearch(e) {{
                    var query = e.target.value.toLowerCase().trim();
                    var clearBtn = document.getElementById('clear-search');
                    var suggBox = document.getElementById('suggestions');

                    if (query.length > 0) {{
                        clearBtn.style.display = 'block';
                    }} else {{
                        clearBtn.style.display = 'none';
                        suggBox.style.display = 'none';
                        return;
                    }}

                    var matches = mapMarkers.filter(m => m.data.search.includes(query)).slice(0, 5);
                    
                    if (matches.length > 0) {{
                        suggBox.innerHTML = '';
                        matches.forEach(m => {{
                            var div = document.createElement('div');
                            div.className = 'suggestion-item';
                            div.innerText = m.data.nome + " (" + m.data.setor + ")";
                            div.onclick = function() {{
                                map.setCenter(m.marker.getPosition());
                                map.setZoom(16);
                                google.maps.event.trigger(m.marker, 'click');
                                suggBox.style.display = 'none';
                            }};
                            suggBox.appendChild(div);
                        }});
                        suggBox.style.display = 'block';
                    }} else {{
                        suggBox.style.display = 'none';
                    }}
                }}

                function clearSearch() {{
                    document.getElementById('search-input').value = '';
                    document.getElementById('clear-search').style.display = 'none';
                    document.getElementById('suggestions').style.display = 'none';
                }}

                function toggleLegend() {{
                    var leg = document.getElementById('legend');
                    leg.style.display = leg.style.display === 'block' ? 'none' : 'block';
                }}

                function toggleProfileMenu() {{
                    var pm = document.getElementById('profile-menu');
                    var fm = document.getElementById('filter-menu');
                    fm.style.display = 'none';
                    pm.style.display = pm.style.display === 'block' ? 'none' : 'block';
                }}

                function toggleFilterMenu() {{
                    var fm = document.getElementById('filter-menu');
                    var pm = document.getElementById('profile-menu');
                    pm.style.display = 'none';
                    fm.style.display = fm.style.display === 'block' ? 'none' : 'block';
                }}

                function openPhotoModal() {{ document.getElementById('photo-source-modal').style.display = 'flex'; }}
                function closePhotoModal() {{ document.getElementById('photo-source-modal').style.display = 'none'; }}

                function triggerFileInput(type) {{
                    closePhotoModal();
                    if (type === 'camera') document.getElementById('camera-input').click();
                    else document.getElementById('gallery-input').click();
                }}

                function handleImageUpload(evt) {{
                    var file = evt.target.files[0];
                    if (file) {{
                        var reader = new FileReader();
                        reader.onload = function(e) {{
                            var imgData = e.target.result;
                            
                            // Exibe fotos e esconde a inicial
                            document.getElementById('avatar-btn-img').src = imgData;
                            document.getElementById('avatar-btn-img').style.display = 'block';
                            document.getElementById('avatar-btn-initial').style.display = 'none';

                            document.getElementById('avatar-menu-img').src = imgData;
                            document.getElementById('avatar-menu-img').style.display = 'block';
                            document.getElementById('avatar-menu-initial').style.display = 'none';

                            localStorage.setItem('user_avatar_' + loggedUserEmail, imgData);
                        }};
                        reader.readAsDataURL(file);
                    }}
                }}

                function editName() {{
                    var nameDisplay = document.getElementById('user-name-display');
                    var currentName = nameDisplay.innerText;
                    var newName = prompt('Digite seu nome:', currentName);
                    if (newName && newName.trim() !== '') {{
                        nameDisplay.innerText = newName.trim();
                        localStorage.setItem('user_name_' + loggedUserEmail, newName.trim());
                    }}
                }}

                function loadUserProfile() {{
                    var savedName = localStorage.getItem('user_name_' + loggedUserEmail);
                    if (savedName) document.getElementById('user-name-display').innerText = savedName;

                    var savedAvatar = localStorage.getItem('user_avatar_' + loggedUserEmail);
                    if (savedAvatar) {{
                        document.getElementById('avatar-btn-img').src = savedAvatar;
                        document.getElementById('avatar-btn-img').style.display = 'block';
                        document.getElementById('avatar-btn-initial').style.display = 'none';

                        document.getElementById('avatar-menu-img').src = savedAvatar;
                        document.getElementById('avatar-menu-img').style.display = 'block';
                        document.getElementById('avatar-menu-initial').style.display = 'none';
                    }} else {{
                        // Exibe a primeira letra do e-mail em fundo preto se não houver foto
                        var initialLetter = loggedUserEmail ? loggedUserEmail.charAt(0).toUpperCase() : 'U';
                        
                        document.getElementById('avatar-btn-img').style.display = 'none';
                        document.getElementById('avatar-btn-initial').innerText = initialLetter;
                        document.getElementById('avatar-btn-initial').style.display = 'block';

                        document.getElementById('avatar-menu-img').style.display = 'none';
                        document.getElementById('avatar-menu-initial').innerText = initialLetter;
                        document.getElementById('avatar-menu-initial').style.display = 'block';
                    }}

                    var savedTheme = localStorage.getItem('user_theme') || 'device';
                    setTheme(savedTheme);
                }}

                function setTheme(theme) {{
                    localStorage.setItem('user_theme', theme);
                    applyThemePreference(theme);
                }}

                function applyThemePreference(theme) {{
                    document.getElementById('btn-theme-light').classList.remove('active');
                    document.getElementById('btn-theme-dark').classList.remove('active');
                    document.getElementById('btn-theme-device').classList.remove('active');

                    var effectiveTheme = theme;
                    if (theme === 'device') {{
                        document.getElementById('btn-theme-device').classList.add('active');
                        var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                        effectiveTheme = prefersDark ? 'dark' : 'light';
                    }} else if (theme === 'light') {{
                        document.getElementById('btn-theme-light').classList.add('active');
                    }} else {{
                        document.getElementById('btn-theme-dark').classList.add('active');
                    }}

                    if (effectiveTheme === 'light') {{
                        document.body.classList.add('light-theme');
                    }} else {{
                        document.body.classList.remove('light-theme');
                    }}
                }}
            </script>
        </body>
        </html>
        """
        return html_content
    except Exception as e:
        return f"<div style='font-family:sans-serif; color:white; background:#c0392b; padding:20px; border-radius:10px; margin:20px;'><h2>Erro Interno no Servidor:</h2><pre>{str(e)}</pre></div>"

@app.get("/", response_class=HTMLResponse)
def read_root():
    return carregar_dados_e_gerar_html()