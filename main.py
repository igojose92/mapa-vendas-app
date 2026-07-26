import json
import os
import random
import re
import smtplib
from email.mime.text import MIMEText

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd

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
        "history": [DEFAULT_PASS],
    }
}

RESET_CODES = {}

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
      msg = MIMEText(
          f"Seu código de verificação para redefinição de senha é: {codigo}"
      )
      msg["Subject"] = "Código de Verificação - Mapa de Vendas"
      msg["From"] = SMTP_USER
      msg["To"] = destinatario

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
      "email": email_clean,
  }


@app.post("/api/change-password")
def change_password(
    email: str = Form(...),
    old_password: str = Form(...),
    new_password: str = Form(...),
):
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
    raise HTTPException(
        status_code=400,
        detail=(
            "A nova senha não pode ser igual a nenhuma das últimas 3 senhas"
            " utilizadas."
        ),
    )
  user["password"] = new_password
  user["first_login"] = False
  user["history"].append(new_password)
  return {"success": True, "message": "Senha alterada com sucesso!"}


@app.post("/api/forgot-password")
def forgot_password(email: str = Form(...)):
  email_clean = email.strip().lower()
  if email_clean not in USERS_DB:
    raise HTTPException(
        status_code=404, detail="E-mail não autorizado ou não cadastrado."
    )
  code = str(random.randint(100000, 999999))
  RESET_CODES[email_clean] = code
  enviar_codigo_email(email_clean, code)
  return {
      "success": True,
      "message": "Código de verificação enviado para o seu e-mail!",
  }


@app.post("/api/reset-password")
def reset_password(
    email: str = Form(...), code: str = Form(...), new_password: str = Form(...)
):
  email_clean = email.strip().lower()
  if email_clean not in USERS_DB:
    raise HTTPException(status_code=404, detail="Usuário não encontrado.")
  if RESET_CODES.get(email_clean) != code.strip():
    raise HTTPException(
        status_code=400, detail="Código de verificação inválido."
    )
  erro_validacao = validar_regras_senha(new_password)
  if erro_validacao:
    raise HTTPException(status_code=400, detail=erro_validacao)
  user = USERS_DB[email_clean]
  if new_password in user["history"][-3:]:
    raise HTTPException(
        status_code=400,
        detail=(
            "A nova senha não pode ser igual a nenhuma das últimas 3 senhas"
            " utilizadas."
        ),
    )
  user["password"] = new_password
  user["first_login"] = False
  user["history"].append(new_password)
  del RESET_CODES[email_clean]
  return {"success": True, "message": "Senha redefinida com sucesso!"}


def formatar_setor(valor):
  if str(valor).strip() == "":
    return ""
  val_str = str(valor).split(".")[0].strip()
  return val_str.zfill(3) if val_str.isdigit() else val_str


def encontrar_coluna(df, nomes_possiveis):
  for col in df.columns:
    col_clean = str(col).strip().lower()
    for nome in nomes_possiveis:
      if nome.lower() in col_clean:
        return col
  return None


@app.get("/", response_class=HTMLResponse)
def carregar_dados_e_gerar_html():
  try:
    df = None
    pasta_dados = "dados"
    if not os.path.exists(pasta_dados):
      return (
          "<h1 style='font-family:sans-serif; color:#ff3131;"
          f" padding:20px;'>Erro: A pasta '{pasta_dados}' não foi encontrada"
          " no projeto.</h1>"
      )

    arquivos = [f for f in os.listdir(pasta_dados) if not f.startswith("~$")]
    for nome in arquivos:
      if "clientes_vendas_teste" in nome:
        caminho_completo = os.path.join(pasta_dados, nome)
        try:
          df = pd.read_csv(
              caminho_completo,
              dtype={"Setor": str},
              sep=None,
              engine="python",
              encoding="utf-8-sig",
          )
          break
        except Exception:
          pass
        try:
          df = pd.read_csv(
              caminho_completo,
              dtype={"Setor": str},
              sep=None,
              engine="python",
              encoding="latin1",
          )
          break
        except Exception:
          pass
        try:
          df = pd.read_excel(
              caminho_completo, engine="openpyxl", dtype={"Setor": str}
          )
          break
        except Exception:
          pass

    if df is None:
      return (
          "<h1 style='font-family:sans-serif; color:#ff3131;"
          " padding:20px;'>Erro: Não foi possível ler o arquivo de dados na"
          " pasta 'dados/'.</h1>"
      )

    df = df.fillna("")
    df.columns = [str(c).strip() for c in df.columns]

    # Identificação inteligente das colunas
    col_setor = encontrar_coluna(df, ["setor"])
    col_seg = encontrar_coluna(
        df, ["segmenta", "segm", "ramo", "categoria"]
    )
    col_reg = encontrar_coluna(
        df,
        [
            "regiao",
            "região",
            "cidade",
            "bairro",
            "endereco",
            "endereço",
            "df",
        ],
    )

    if col_setor:
      df[col_setor] = df[col_setor].apply(formatar_setor)

    setores_unicos = (
        sorted([
            str(s).strip()
            for s in df[col_setor].unique()
            if str(s).strip() != ""
        ])
        if col_setor
        else []
    )
    segmentacoes_unicas = (
        sorted([
            str(s).strip() for s in df[col_seg].unique() if str(s).strip() != ""
        ])
        if col_seg
        else []
    )
    regioes_unicas = (
        sorted([
            str(r).strip() for r in df[col_reg].unique() if str(r).strip() != ""
        ])
        if col_reg
        else []
    )

    markers_list = []
    for _, row in df.iterrows():
      try:
        lat_str = str(row["Latitude"]).replace(",", ".").strip()
        lng_str = str(row["Longitude"]).replace(",", ".").strip()
        lat = float(lat_str)
        lng = float(lng_str)
      except (ValueError, TypeError, KeyError):
        continue

      cliente = str(row.get("Nome Fantasia", "Cliente"))
      cnpj = str(row.get("CNPJ", ""))
      status_cadastral = str(row.get("Status", "")).strip()
      comprou = str(row.get("Comprou no Mês", "")).strip()
      setor_formatado = str(row.get(col_setor, "")) if col_setor else ""
      segmentacao_val = str(row.get(col_seg, "")).strip() if col_seg else ""
      regiao_val = str(row.get(col_reg, "")).strip() if col_reg else ""

      status_lower = status_cadastral.lower()
      comprou_lower = comprou.lower()

      if (
          "prospec" in status_lower
          or "prospeccao" in status_lower
          or "prospecção" in status_lower
      ):
        cor_hex = "#007bff"
        status_categoria = "prospeccao"
      elif "inativo" in status_lower:
        cor_hex = "#7f8c8d"
        status_categoria = "inativo"
      elif comprou_lower == "sim":
        cor_hex = "#28a745"
        status_categoria = "comprou_sim"
      else:
        cor_hex = "#FF3131"
        status_categoria = "comprou_nao"

      codigo_cli = str(row.iloc[0])
      search_tag = (
          f"{cliente} {cnpj} {codigo_cli} {setor_formatado} {segmentacao_val}"
          f" {regiao_val}".lower()
      )

      content_html = f"""
                <div style='width: 280px; max-width: 82vw; max-height: 75vh; overflow-y: auto; font-family: sans-serif; line-height: 1.4; color: #ffffff; background: #2c3e50; padding: 0; border-radius: 10px; box-shadow: 0 8px 20px rgba(0,0,0,0.4); position: relative; user-select: none; -webkit-user-select: none;'>
                    <div style='background:{cor_hex}; color:white; padding: 12px; padding-right: 45px; border-radius: 10px 10px 0 0;'>
                        <div style='font-size:15px; font-weight:bold; word-wrap: break-word;'>{cliente}</div>
                        <div style='font-size:11px; opacity:0.9;'>CNPJ: {cnpj} | Cód: {codigo_cli}</div>
                    </div>
                    <div style='padding: 10px 12px 12px 12px;'>
                        <div style='font-size:12px; padding-bottom: 8px; color: #ecf0f1;'>
                            <b>Região:</b> {regiao_val}<br>
                            <b>Segmentação:</b> {segmentacao_val}<br>
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
          "segmentacao": segmentacao_val,
          "regiao": regiao_val,
      })

    markers_json = json.dumps(markers_list)

    checkboxes_setor = (
        "".join([
            f'<label class="chk-item"><input type="checkbox" class="chk-setor"'
            f' value="{s}" checked onchange="applyFilters()"> {s}</label>'
            for s in setores_unicos
        ])
        if setores_unicos
        else (
            '<div style="font-size:12px; color:#bdc3c7;">Nenhum setor'
            " encontrado</div>"
        )
    )

    checkboxes_seg = (
        "".join([
            f'<label class="chk-item"><input type="checkbox" class="chk-seg"'
            f' value="{s}" checked onchange="applyFilters()"> {s}</label>'
            for s in segmentacoes_unicas
        ])
        if segmentacoes_unicas
        else (
            '<div style="font-size:12px; color:#bdc3c7;">Nenhuma segmentação'
            " encontrada</div>"
        )
    )

    checkboxes_reg = (
        "".join([
            f'<label class="chk-item"><input type="checkbox" class="chk-reg"'
            f' value="{r}" checked onchange="applyFilters()"> {r}</label>'
            for r in regioes_unicas
        ])
        if regioes_unicas
        else (
            '<div style="font-size:12px; color:#bdc3c7;">Nenhuma região'
            " encontrada</div>"
        )
    )

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

                /* Botão de Fechar Quadrado Vermelho colado no canto da janela */
                .close-window-btn {{
                    position: absolute;
                    top: 0;
                    right: 0;
                    width: 32px;
                    height: 32px;
                    background-color: #ff3131;
                    border-radius: 0 15px 0 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    font-size: 16px;
                    cursor: pointer;
                    box-shadow: -2px 2px 6px rgba(0,0,0,0.2);
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
                    padding: 25px 15px 15px 15px; 
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
                
                .logout-btn {{
                    margin-top: 15px;
                    width: 100%;
                    background: #ff3131;
                    color: #ffffff;
                    border: none;
                    padding: 10px;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 13px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.2);
                    transition: background 0.2s ease;
                }}
                .logout-btn:hover {{
                    background: #d62828;
                }}

                /* Menu de Filtros Avançado com Expandir/Recolher (Accordion) */
                #filter-menu {{ 
                    position: absolute; 
                    left: 15px; 
                    top: 125px; 
                    background: #1e2833; 
                    padding: 28px 15px 15px 15px; 
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
                
                .filter-section {{ margin-bottom: 12px; border-bottom: 1px solid #34495e; padding-bottom: 8px; }}
                .filter-header-row {{ 
                    display: flex; 
                    justify-content: space-between; 
                    align-items: center; 
                    cursor: pointer;
                    user-select: none;
                    padding: 4px 0;
                }}
                .filter-title-group {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }}
                .filter-title {{ font-size: 13px; font-weight: bold; letter-spacing: 0.5px; text-transform: uppercase; color: #ffffff; }}
                .arrow-icon {{ font-size: 11px; transition: transform 0.2s ease; display: inline-block; color: #4285F4; }}
                .arrow-icon.open {{ transform: rotate(180deg); }}
                
                .filter-body {{
                    display: none;
                    margin-top: 10px;
                }}
                .filter-body.open {{
                    display: block;
                }}

                .filter-actions-row {{
                    display: flex;
                    justify-content: flex-end;
                    margin-bottom: 8px;
                }}

                .btn-group-action {{ display: flex; gap: 4px; }}
                .btn-mini {{ background: #34495e; color: #ecf0f1; border: none; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; cursor: pointer; }}
                .btn-mini:hover {{ background: #4285F4; color: #ffffff; }}
                
                .chk-list {{ display: flex; flex-direction: column; gap: 6px; padding-left: 2px; max-height: 180px; overflow-y: auto; }}
                .chk-item {{ display: flex; align-items: center; gap: 8px; font-size: 13px; color: #dcdde1; cursor: pointer; user-select: none; }}
                .chk-item input[type="checkbox"] {{ width: 16px; height: 16px; accent-color: #4285F4; cursor: pointer; }}

                #photo-source-modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 100; align-items: center; justify-content: center; }}
                .modal-box {{ background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 16px; padding: 20px; width: 80%; max-width: 280px; text-align: center; color: var(--text-color); }}
                .modal-title {{ font-weight: bold; font-size: 16px; margin-bottom: 15px; }}
                .modal-btn {{ width: 100%; padding: 10px; margin-bottom: 8px; border-radius: 8px; border: none; background: #4285F4; color: white; font-weight: bold; cursor: pointer; }}
                .modal-btn.cancel {{ background: #ff3131; }}
            </style>
        </head>
        <body>

            <div id="auth-overlay">
                <div class="auth-card" id="card-login">
                    <h2>MAPA DE VENDAS</h2>
                    <form onsubmit="handleLogin(event)">
                        <div class="auth-field">
                            <label>E-mail Autorizado</label>
                            <input type="email" id="login-email" class="auth-input" required placeholder="seu@email.com">
                        </div>
                        <div class="auth-field">
                            <label>Senha</label>
                            <input type="password" id="login-pass" class="auth-input" required placeholder="******">
                        </div>
                        <button type="submit" class="auth-btn">ENTRAR NO SISTEMA</button>
                        <span class="auth-link" onclick="showAuthCard('card-forgot')">Esqueceu sua senha?</span>
                        <div id="login-error" class="auth-error"></div>
                    </form>
                </div>

                <div class="auth-card" id="card-change-pass" style="display:none;">
                    <h2>ALTERAR SENHA PADRÃO</h2>
                    <p style="font-size: 11px; text-align: center; opacity: 0.8; margin-bottom: 15px;">
                        Por razões de segurança, altere sua senha de primeiro acesso.
                    </p>
                    <form onsubmit="handleChangePassword(event)">
                        <div class="auth-field">
                            <label>Senha Atual</label>
                            <input type="password" id="change-old-pass" class="auth-input" required>
                        </div>
                        <div class="auth-field">
                            <label>Nova Senha</label>
                            <input type="password" id="change-new-pass" class="auth-input" required placeholder="Mín. 6 chars, 1 maiúscula, 1 num, 1 especial">
                        </div>
                        <button type="submit" class="auth-btn">ATUALIZAR SENHA</button>
                        <div id="change-pass-error" class="auth-error"></div>
                    </form>
                </div>

                <div class="auth-card" id="card-forgot" style="display:none;">
                    <h2>RECUPERAR ACESSO</h2>
                    <form onsubmit="handleForgotPassword(event)">
                        <div class="auth-field">
                            <label>Seu E-mail</label>
                            <input type="email" id="forgot-email" class="auth-input" required placeholder="seu@email.com">
                        </div>
                        <button type="submit" class="auth-btn">ENVIAR CÓDIGO</button>
                        <span class="auth-link" onclick="showAuthCard('card-login')">Voltar para o Login</span>
                        <div id="forgot-error" class="auth-error"></div>
                    </form>
                </div>

                <div class="auth-card" id="card-reset" style="display:none;">
                    <h2>REDEFINIR SENHA</h2>
                    <form onsubmit="handleResetPassword(event)">
                        <div class="auth-field">
                            <label>Código de Verificação</label>
                            <input type="text" id="reset-code" class="auth-input" required placeholder="6 dígitos">
                        </div>
                        <div class="auth-field">
                            <label>Nova Senha</label>
                            <input type="password" id="reset-new-pass" class="auth-input" required placeholder="Nova Senha">
                        </div>
                        <button type="submit" class="auth-btn">REDEFINIR SENHA</button>
                        <span class="auth-link" onclick="showAuthCard('card-login')">Cancelar</span>
                        <div id="reset-error" class="auth-error"></div>
                    </form>
                </div>
            </div>

            <div id="profile-btn" onclick="toggleProfileMenu()">
                <img id="avatar-img" src="" alt="Avatar">
                <span id="avatar-initial" class="avatar-initial">U</span>
            </div>

            <div id="filter-toggle-btn" class="action-btn" onclick="toggleFilterMenu()" title="Filtros Avançados">
                <svg viewBox="0 0 24 24"><path d="M10 18h4v-2h-4v2zM3 6v2h18V6H3zm3 7h12v-2H6v2z"/></svg>
            </div>

            <div id="location-btn" class="action-btn" onclick="centerOnUserLocation()" title="Minha Localização">
                <svg viewBox="0 0 24 24"><path d="M12 8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm8.94 3c-.46-4.17-3.77-7.48-7.94-7.94V1h-2v2.06C6.83 3.52 3.52 6.83 3.06 11H1v2h2.06c.46 4.17 3.77 7.48 7.94 7.94V23h2v-2.06c4.17-.46 7.48-3.77 7.94-7.94H23v-2h-2.06zM12 19c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z"/></svg>
            </div>

            <div id="search-wrapper">
                <div id="search-container">
                    <input type="text" id="search-input" placeholder="🔍 Buscar por Cliente, CNPJ, Cód, Setor, Região..." oninput="onSearchInput()">
                    <span id="clear-search" onclick="clearSearch()">×</span>
                </div>
                <div id="suggestions"></div>
            </div>

            <div id="profile-menu">
                <div class="close-window-btn" onclick="toggleProfileMenu()">×</div>
                <div class="profile-header">
                    <div class="profile-img-wrapper" onclick="openPhotoModal()">
                        <img id="menu-avatar-img" src="" alt="Avatar">
                        <span id="menu-avatar-initial" class="avatar-initial-large">U</span>
                    </div>
                    <div class="profile-name" onclick="editProfileName()">
                        <span id="display-user-name">Usuário</span> ✏️
                    </div>
                </div>
                <div class="theme-section">
                    <div class="theme-title">Tema do Mapa</div>
                    <div class="theme-options">
                        <button class="theme-btn active" id="btn-theme-dark" onclick="setTheme('dark')">Escuro (Padrão) <span>🌙</span></button>
                        <button class="theme-btn" id="btn-theme-light" onclick="setTheme('light')">Claro <span>☀️</span></button>
                    </div>
                </div>
                <button class="logout-btn" onclick="logout()">
                    🚪 Sair da Conta
                </button>
            </div>

            <div id="filter-menu">
                <div class="close-window-btn" onclick="toggleFilterMenu()">×</div>

                <div class="filter-section">
                    <div class="filter-header-row" onclick="toggleAccordion('body-status', 'arrow-status')">
                        <div class="filter-title-group">
                            <span class="arrow-icon open" id="arrow-status">▼</span>
                            <span class="filter-title">Status & Compras</span>
                        </div>
                    </div>
                    <div class="filter-body open" id="body-status">
                        <div class="filter-actions-row">
                            <div class="btn-group-action">
                                <button class="btn-mini" onclick="checkAllCategory('status', true)">Todos</button>
                                <button class="btn-mini" onclick="checkAllCategory('status', false)">Nenhum</button>
                            </div>
                        </div>
                        <div class="chk-list">
                            <label class="chk-item"><input type="checkbox" class="chk-status" value="comprou_sim" checked onchange="applyFilters()"> 🟢 Comprou no Mês</label>
                            <label class="chk-item"><input type="checkbox" class="chk-status" value="comprou_nao" checked onchange="applyFilters()"> 🔴 Não Comprou no Mês</label>
                            <label class="chk-item"><input type="checkbox" class="chk-status" value="inativo" checked onchange="applyFilters()"> ⚪ Inativo</label>
                            <label class="chk-item"><input type="checkbox" class="chk-status" value="prospeccao" checked onchange="applyFilters()"> 🔵 Prospecção</label>
                        </div>
                    </div>
                </div>

                <div class="filter-section">
                    <div class="filter-header-row" onclick="toggleAccordion('body-setores', 'arrow-setores')">
                        <div class="filter-title-group">
                            <span class="arrow-icon" id="arrow-setores">▼</span>
                            <span class="filter-title">Setores</span>
                        </div>
                    </div>
                    <div class="filter-body" id="body-setores">
                        <div class="filter-actions-row">
                            <div class="btn-group-action">
                                <button class="btn-mini" onclick="checkAllCategory('setor', true)">Todos</button>
                                <button class="btn-mini" onclick="checkAllCategory('setor', false)">Nenhum</button>
                            </div>
                        </div>
                        <div class="chk-list">
                            {checkboxes_setor}
                        </div>
                    </div>
                </div>

                <div class="filter-section">
                    <div class="filter-header-row" onclick="toggleAccordion('body-seg', 'arrow-seg')">
                        <div class="filter-title-group">
                            <span class="arrow-icon" id="arrow-seg">▼</span>
                            <span class="filter-title">Segmentação</span>
                        </div>
                    </div>
                    <div class="filter-body" id="body-seg">
                        <div class="filter-actions-row">
                            <div class="btn-group-action">
                                <button class="btn-mini" onclick="checkAllCategory('seg', true)">Todos</button>
                                <button class="btn-mini" onclick="checkAllCategory('seg', false)">Nenhum</button>
                            </div>
                        </div>
                        <div class="chk-list">
                            {checkboxes_seg}
                        </div>
                    </div>
                </div>

                <div class="filter-section">
                    <div class="filter-header-row" onclick="toggleAccordion('body-reg', 'arrow-reg')">
                        <div class="filter-title-group">
                            <span class="arrow-icon" id="arrow-reg">▼</span>
                            <span class="filter-title">Região DF</span>
                        </div>
                    </div>
                    <div class="filter-body" id="body-reg">
                        <div class="filter-actions-row">
                            <div class="btn-group-action">
                                <button class="btn-mini" onclick="checkAllCategory('reg', true)">Todos</button>
                                <button class="btn-mini" onclick="checkAllCategory('reg', false)">Nenhum</button>
                            </div>
                        </div>
                        <div class="chk-list">
                            {checkboxes_reg}
                        </div>
                    </div>
                </div>

            </div>

            <div id="legend-toggle" onclick="toggleLegend()">?</div>
            <div id="legend">
                <div class="legend-row"><span style="color:#28a745; font-size:16px;">🟢</span> Comprou no Mês</div>
                <div class="legend-row"><span style="color:#FF3131; font-size:16px;">🔴</span> Não Comprou no Mês</div>
                <div class="legend-row"><span style="color:#7f8c8d; font-size:16px;">⚪</span> Inativo</div>
                <div class="legend-row"><span style="color:#007bff; font-size:16px;">🔵</span> Prospecção</div>
            </div>

            <div id="photo-source-modal">
                <div class="modal-box">
                    <div class="modal-title">Alterar Foto de Perfil</div>
                    <button class="modal-btn" onclick="triggerFileInput('camera')">📷 Tirar Foto (Câmera)</button>
                    <button class="modal-btn" onclick="triggerFileInput('gallery')">📁 Escolher da Galeria</button>
                    <button class="modal-btn cancel" onclick="closePhotoModal()">Cancelar</button>
                </div>
            </div>

            <input type="file" id="file-input-camera" accept="image/*" capture="environment" style="display:none;" onchange="handlePhotoSelected(event)">
            <input type="file" id="file-input-gallery" accept="image/*" style="display:none;" onchange="handlePhotoSelected(event)">

            <div id="map"></div>

            <script>
                var map;
                var allMarkersData = {markers_json};
                var activeMarkers = [];
                var activeInfoWindow = null;
                var userLocationMarker = null;
                var currentUserEmail = "";

                // ESTILOS DE TEMA PARA O GOOGLE MAPS
                var darkMapStyle = [
                    {{ "elementType": "geometry", "stylers": [{{ "color": "#242f3e" }}] }},
                    {{ "elementType": "labels.text.fill", "stylers": [{{ "color": "#746855" }}] }},
                    {{ "elementType": "labels.text.stroke", "stylers": [{{ "color": "#242f3e" }}] }},
                    {{ "featureType": "administrative.locality", "elementType": "labels.text.fill", "stylers": [{{ "color": "#d59563" }}] }},
                    {{ "featureType": "poi", "elementType": "labels.text.fill", "stylers": [{{ "color": "#d59563" }}] }},
                    {{ "featureType": "poi.park", "elementType": "geometry", "stylers": [{{ "color": "#263c3f" }}] }},
                    {{ "featureType": "poi.park", "elementType": "labels.text.fill", "stylers": [{{ "color": "#6b9a76" }}] }},
                    {{ "featureType": "road", "elementType": "geometry", "stylers": [{{ "color": "#38414e" }}] }},
                    {{ "featureType": "road", "elementType": "geometry.stroke", "stylers": [{{ "color": "#212a37" }}] }},
                    {{ "featureType": "road", "elementType": "labels.text.fill", "stylers": [{{ "color": "#9ca5b3" }}] }},
                    {{ "featureType": "road.highway", "elementType": "geometry", "stylers": [{{ "color": "#746855" }}] }},
                    {{ "featureType": "road.highway", "elementType": "geometry.stroke", "stylers": [{{ "color": "#1f2835" }}] }},
                    {{ "featureType": "road.highway", "elementType": "labels.text.fill", "stylers": [{{ "color": "#f3d19c" }}] }},
                    {{ "featureType": "transit", "elementType": "geometry", "stylers": [{{ "color": "#2f3948" }}] }},
                    {{ "featureType": "transit.station", "elementType": "labels.text.fill", "stylers": [{{ "color": "#d59563" }}] }},
                    {{ "featureType": "water", "elementType": "geometry", "stylers": [{{ "color": "#17263c" }}] }},
                    {{ "featureType": "water", "elementType": "labels.text.fill", "stylers": [{{ "color": "#515c6d" }}] }},
                    {{ "featureType": "water", "elementType": "labels.text.stroke", "stylers": [{{ "color": "#17263c" }}] }}
                ];

                function initMap() {{
                    var dfCenter = {{ lat: -15.7981, lng: -47.8659 }};
                    
                    map = new google.maps.Map(document.getElementById('map'), {{
                        zoom: 11,
                        center: dfCenter,
                        styles: darkMapStyle,
                        disableDefaultUI: true,
                        zoomControl: true,
                        gestureHandling: 'greedy'
                    }});

                    loadMarkers(allMarkersData);
                    loadUserProfile();
                }}

                window.onload = initMap;

                /* AUTENTICAÇÃO E NAVEGAÇÃO */
                function showAuthCard(cardId) {{
                    document.getElementById('card-login').style.display = 'none';
                    document.getElementById('card-change-pass').style.display = 'none';
                    document.getElementById('card-forgot').style.display = 'none';
                    document.getElementById('card-reset').style.display = 'none';
                    document.getElementById(cardId).style.display = 'block';
                }}

                function handleLogin(e) {{
                    e.preventDefault();
                    var email = document.getElementById('login-email').value;
                    var pass = document.getElementById('login-pass').value;
                    var errDiv = document.getElementById('login-error');
                    errDiv.style.display = 'none';

                    var formData = new FormData();
                    formData.append('email', email);
                    formData.append('password', pass);

                    fetch('/api/login', {{ method: 'POST', body: formData }})
                    .then(res => res.json().then(data => ({{ status: res.status, body: data }})))
                    .then(res => {{
                        if (res.status === 200) {{
                            currentUserEmail = res.body.email;
                            if (res.body.first_login) {{
                                showAuthCard('card-change-pass');
                            }} else {{
                                document.getElementById('auth-overlay').style.display = 'none';
                                updateProfileDisplay(currentUserEmail);
                            }}
                        }} else {{
                            errDiv.innerText = res.body.detail || "Erro de autenticação.";
                            errDiv.style.display = 'block';
                        }}
                    }});
                }}

                function logout() {{
                    toggleProfileMenu();
                    document.getElementById('login-pass').value = '';
                    document.getElementById('login-error').style.display = 'none';
                    showAuthCard('card-login');
                    document.getElementById('auth-overlay').style.display = 'flex';
                }}

                function handleChangePassword(e) {{
                    e.preventDefault();
                    var oldPass = document.getElementById('change-old-pass').value;
                    var newPass = document.getElementById('change-new-pass').value;
                    var errDiv = document.getElementById('change-pass-error');
                    errDiv.style.display = 'none';

                    var formData = new FormData();
                    formData.append('email', currentUserEmail);
                    formData.append('old_password', oldPass);
                    formData.append('new_password', newPass);

                    fetch('/api/change-password', {{ method: 'POST', body: formData }})
                    .then(res => res.json().then(data => ({{ status: res.status, body: data }})))
                    .then(res => {{
                        if (res.status === 200) {{
                            alert('Senha alterada com sucesso!');
                            document.getElementById('auth-overlay').style.display = 'none';
                            updateProfileDisplay(currentUserEmail);
                        }} else {{
                            errDiv.innerText = res.body.detail || "Erro ao alterar senha.";
                            errDiv.style.display = 'block';
                        }}
                    }});
                }}

                function handleForgotPassword(e) {{
                    e.preventDefault();
                    var email = document.getElementById('forgot-email').value;
                    var errDiv = document.getElementById('forgot-error');
                    errDiv.style.display = 'none';

                    var formData = new FormData();
                    formData.append('email', email);

                    fetch('/api/forgot-password', {{ method: 'POST', body: formData }})
                    .then(res => res.json().then(data => ({{ status: res.status, body: data }})))
                    .then(res => {{
                        if (res.status === 200) {{
                            currentUserEmail = email;
                            alert(res.body.message);
                            showAuthCard('card-reset');
                        }} else {{
                            errDiv.innerText = res.body.detail || "Erro ao solicitar recuperação.";
                            errDiv.style.display = 'block';
                        }}
                    }});
                }}

                function handleResetPassword(e) {{
                    e.preventDefault();
                    var code = document.getElementById('reset-code').value;
                    var newPass = document.getElementById('reset-new-pass').value;
                    var errDiv = document.getElementById('reset-error');
                    errDiv.style.display = 'none';

                    var formData = new FormData();
                    formData.append('email', currentUserEmail);
                    formData.append('code', code);
                    formData.append('new_password', newPass);

                    fetch('/api/reset-password', {{ method: 'POST', body: formData }})
                    .then(res => res.json().then(data => ({{ status: res.status, body: data }})))
                    .then(res => {{
                        if (res.status === 200) {{
                            alert('Senha redefinida com sucesso!');
                            showAuthCard('card-login');
                        }} else {{
                            errDiv.innerText = res.body.detail || "Erro ao redefinir senha.";
                            errDiv.style.display = 'block';
                        }}
                    }});
                }}

                /* CARREGAR MARCADORES NO MAPA */
                function loadMarkers(data) {{
                    clearActiveMarkers();
                    data.forEach(function(item) {{
                        var marker = new google.maps.Marker({{
                            position: {{ lat: item.lat, lng: item.lng }},
                            map: map,
                            title: item.nome,
                            icon: {{
                                path: google.maps.SymbolPath.CIRCLE,
                                scale: 8,
                                fillColor: item.cor_hex,
                                fillOpacity: 0.9,
                                strokeColor: '#ffffff',
                                strokeWeight: 2
                            }}
                        }});

                        var infowindow = new google.maps.InfoWindow({{
                            content: item.content
                        }});

                        marker.addListener('click', function() {{
                            if (activeInfoWindow) activeInfoWindow.close();
                            infowindow.open(map, marker);
                            activeInfoWindow = infowindow;
                        }});

                        marker.itemData = item;
                        activeMarkers.push(marker);
                    }});
                }}

                function clearActiveMarkers() {{
                    activeMarkers.forEach(m => m.setMap(null));
                    activeMarkers = [];
                }}

                /* BUSCA E SUGESTÕES */
                function onSearchInput() {{
                    var val = document.getElementById('search-input').value.toLowerCase().trim();
                    var clearBtn = document.getElementById('clear-search');
                    var sugDiv = document.getElementById('suggestions');

                    if (val.length > 0) {{
                        clearBtn.style.display = 'block';
                        
                        var matches = allMarkersData.filter(m => m.search.includes(val)).slice(0, 8);
                        if (matches.length > 0) {{
                            sugDiv.innerHTML = matches.map(m => 
                                `<div class="suggestion-item" onclick="selectSuggestion('${{m.nome.replace(/'/g, "\\'")}}')">${{m.nome}}</div>`
                            ).join('');
                            sugDiv.style.display = 'block';
                        }} else {{
                            sugDiv.style.display = 'none';
                        }}
                    }} else {{
                        clearBtn.style.display = 'none';
                        sugDiv.style.display = 'none';
                    }}
                    applyFilters();
                }}

                function selectSuggestion(nome) {{
                    document.getElementById('search-input').value = nome;
                    document.getElementById('suggestions').style.display = 'none';
                    applyFilters();

                    var target = activeMarkers.find(m => m.itemData.nome === nome && m.getMap() !== null);
                    if (target) {{
                        map.setCenter(target.getPosition());
                        map.setZoom(16);
                        google.maps.event.trigger(target, 'click');
                    }}
                }}

                function clearSearch() {{
                    document.getElementById('search-input').value = '';
                    onSearchInput();
                }}

                /* ACCORDION FILTROS AVANÇADOS */
                function toggleAccordion(bodyId, arrowId) {{
                    var bodyEl = document.getElementById(bodyId);
                    var arrowEl = document.getElementById(arrowId);
                    
                    if (bodyEl.classList.contains('open')) {{
                        bodyEl.classList.remove('open');
                        arrowEl.classList.remove('open');
                    }} else {{
                        bodyEl.classList.add('open');
                        arrowEl.classList.add('open');
                    }}
                }}

                function checkAllCategory(catClass, checkState) {{
                    var checkboxes = document.querySelectorAll('.chk-' + catClass);
                    checkboxes.forEach(cb => cb.checked = checkState);
                    applyFilters();
                }}

                /* APLICAR FILTROS COMBINADOS */
                function applyFilters() {{
                    var searchVal = document.getElementById('search-input').value.toLowerCase().trim();

                    var selectedStatus = Array.from(document.querySelectorAll('.chk-status:checked')).map(cb => cb.value);
                    var selectedSetores = Array.from(document.querySelectorAll('.chk-setor:checked')).map(cb => cb.value);
                    var selectedSeg = Array.from(document.querySelectorAll('.chk-seg:checked')).map(cb => cb.value);
                    var selectedReg = Array.from(document.querySelectorAll('.chk-reg:checked')).map(cb => cb.value);

                    activeMarkers.forEach(function(marker) {{
                        var data = marker.itemData;

                        var matchSearch = searchVal === "" || data.search.includes(searchVal);
                        var matchStatus = selectedStatus.includes(data.status_cat);
                        var matchSetor = selectedSetores.length === 0 || selectedSetores.includes(data.setor);
                        var matchSeg = selectedSeg.length === 0 || selectedSeg.includes(data.segmentacao);
                        var matchReg = selectedReg.length === 0 || selectedReg.includes(data.regiao);

                        if (matchSearch && matchStatus && matchSetor && matchSeg && matchReg) {{
                            marker.setMap(map);
                        }} else {{
                            marker.setMap(null);
                        }}
                    }});
                }}

                /* LOCALIZAÇÃO DO USUÁRIO NO MAPA */
                function centerOnUserLocation() {{
                    if (navigator.geolocation) {{
                        navigator.geolocation.getCurrentPosition(function(position) {{
                            var pos = {{
                                lat: position.coords.latitude,
                                lng: position.coords.longitude
                            }};

                            if (userLocationMarker) userLocationMarker.setMap(null);

                            userLocationMarker = new google.maps.Marker({{
                                position: pos,
                                map: map,
                                title: "Sua Localização",
                                icon: {{
                                    path: google.maps.SymbolPath.CIRCLE,
                                    scale: 9,
                                    fillColor: '#4285F4',
                                    fillOpacity: 1,
                                    strokeColor: '#ffffff',
                                    strokeWeight: 3
                                }}
                            }});

                            map.setCenter(pos);
                            map.setZoom(15);
                        }}, function() {{
                            alert("Não foi possível obter sua localização. Verifique as permissões do seu navegador/dispositivo.");
                        }});
                    }} else {{
                        alert("Geolocalização não é suportada neste navegador.");
                    }}
                }}

                /* GERENCIAMENTO DE PERFIL E TEMA */
                function toggleProfileMenu() {{
                    var menu = document.getElementById('profile-menu');
                    menu.style.display = (menu.style.display === 'block') ? 'none' : 'block';
                    document.getElementById('filter-menu').style.display = 'none';
                }}

                function toggleFilterMenu() {{
                    var menu = document.getElementById('filter-menu');
                    menu.style.display = (menu.style.display === 'block') ? 'none' : 'block';
                    document.getElementById('profile-menu').style.display = 'none';
                }}

                function toggleLegend() {{
                    var leg = document.getElementById('legend');
                    leg.style.display = (leg.style.display === 'block') ? 'none' : 'block';
                }}

                function setTheme(theme) {{
                    var btnDark = document.getElementById('btn-theme-dark');
                    var btnLight = document.getElementById('btn-theme-light');

                    if (theme === 'dark') {{
                        document.body.classList.remove('light-theme');
                        map.setOptions({{ styles: darkMapStyle }});
                        btnDark.classList.add('active');
                        btnLight.classList.remove('active');
                    }} else {{
                        document.body.classList.add('light-theme');
                        map.setOptions({{ styles: [] }});
                        btnLight.classList.add('active');
                        btnDark.classList.remove('active');
                    }}
                    localStorage.setItem('map_theme', theme);
                }}

                function updateProfileDisplay(email) {{
                    var name = localStorage.getItem('user_profile_name') || email.split('@')[0];
                    document.getElementById('display-user-name').innerText = name;
                    
                    var initial = name.charAt(0).toUpperCase();
                    document.getElementById('avatar-initial').innerText = initial;
                    document.getElementById('menu-avatar-initial').innerText = initial;

                    var savedPhoto = localStorage.getItem('user_profile_photo');
                    if (savedPhoto) {{
                        document.getElementById('avatar-img').src = savedPhoto;
                        document.getElementById('avatar-img').style.display = 'block';
                        document.getElementById('avatar-initial').style.display = 'none';

                        document.getElementById('menu-avatar-img').src = savedPhoto;
                        document.getElementById('menu-avatar-img').style.display = 'block';
                        document.getElementById('menu-avatar-initial').style.display = 'none';
                    }} else {{
                        document.getElementById('avatar-img').style.display = 'none';
                        document.getElementById('avatar-initial').style.display = 'block';

                        document.getElementById('menu-avatar-img').style.display = 'none';
                        document.getElementById('menu-avatar-initial').style.display = 'block';
                    }}
                }}

                function editProfileName() {{
                    var current = document.getElementById('display-user-name').innerText;
                    var newName = prompt("Digite seu nome de exibição:", current);
                    if (newName && newName.trim() !== '') {{
                        localStorage.setItem('user_profile_name', newName.trim());
                        updateProfileDisplay(currentUserEmail);
                    }}
                }}

                function openPhotoModal() {{
                    document.getElementById('photo-source-modal').style.display = 'flex';
                }}

                function closePhotoModal() {{
                    document.getElementById('photo-source-modal').style.display = 'none';
                }}

                function triggerFileInput(type) {{
                    closePhotoModal();
                    if (type === 'camera') {{
                        document.getElementById('file-input-camera').click();
                    }} else {{
                        document.getElementById('file-input-gallery').click();
                    }}
                }}

                function handlePhotoSelected(e) {{
                    var file = e.target.files[0];
                    if (file) {{
                        var reader = new FileReader();
                        reader.onload = function(evt) {{
                            var base64 = evt.target.result;
                            localStorage.setItem('user_profile_photo', base64);
                            updateProfileDisplay(currentUserEmail);
                        }};
                        reader.readAsDataURL(file);
                    }}
                }}

                function loadUserProfile() {{
                    var savedTheme = localStorage.getItem('map_theme') || 'dark';
                    setTheme(savedTheme);
                }}
            </script>
        </body>
        </html>
        """
    return HTMLResponse(content=html_content)

  except Exception as e:
    return (
        "<h1 style='font-family:sans-serif; color:#ff3131; padding:20px;'>Erro"
        f" interno no servidor: {e}</h1>"
    )