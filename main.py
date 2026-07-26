import hashlib
import re
import streamlit as st

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Portal de Acesso",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. INICIALIZAÇÃO DO ESTADO DA SESSÃO (PERSISTÊNCIA EM MEMÓRIA)
# -----------------------------------------------------------------------------
if "users_db" not in st.session_state:
    st.session_state["users_db"] = {
        "igojose95@gmail.com": {
            "password_hash": hashlib.sha256("Ambev123!".encode()).hexdigest(),
            "is_first_login": True,
            "history": [hashlib.sha256("Ambev123!".encode()).hexdigest()]
        },
        "outro_email@ambev.com.br": {
            "password_hash": hashlib.sha256("Ambev123!".encode()).hexdigest(),
            "is_first_login": True,
            "history": [hashlib.sha256("Ambev123!".encode()).hexdigest()]
        }
    }

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "user_email" not in st.session_state:
    st.session_state["user_email"] = None


# -----------------------------------------------------------------------------
# 3. FUNÇÕES AUXILIARES DE SEGURANÇA E VALIDAÇÃO
# -----------------------------------------------------------------------------
def make_hash(password: str) -> str:
    """Gera o hash SHA-256 da senha."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_credentials(email: str, password_hash: str) -> bool:
    """Valida se o usuário existe e se o hash confere."""
    users = st.session_state["users_db"]
    return email in users and users[email]["password_hash"] == password_hash

def validate_password_complexity(password: str) -> tuple[bool, str]:
    """Garante regras mínimas de segurança para novas senhas."""
    if len(password) < 8:
        return False, "A senha deve ter pelo menos 8 caracteres."
    if not re.search(r"[A-Z]", password):
        return False, "A senha deve conter pelo menos uma letra maiúscula."
    if not re.search(r"[a-z]", password):
        return False, "A senha deve conter pelo menos uma letra minúscula."
    if not re.search(r"[0-9]", password):
        return False, "A senha deve conter pelo menos um número."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "A senha deve conter pelo menos um caractere especial."
    return True, ""

def logout():
    """Limpa as variáveis de sessão para desconectar o usuário."""
    st.session_state["logged_in"] = False
    st.session_state["user_email"] = None
    st.rerun()


# -----------------------------------------------------------------------------
# 4. CONTROLE DE FLUXO DA INTERFACE
# -----------------------------------------------------------------------------

# === FLUXO A: USUÁRIO LOGADO ===
if st.session_state["logged_in"]:
    email = st.session_state["user_email"]
    user_data = st.session_state["users_db"][email]

    # Painel Lateral para o usuário logado
    st.sidebar.title("👤 Usuário")
    st.sidebar.write(f"Conectado como:\n`{email}`")
    st.sidebar.divider()
    if st.sidebar.button("🚪 Sair da Conta", use_container_width=True):
        logout()

    # SUB-FLUXO 1: TROCA DE SENHA OBRIGATÓRIA (PRIMEIRO ACESSO)
    if user_data["is_first_login"]:
        st.header("🔑 Alteração de Senha Obrigatória")
        st.info("Identificamos que este é o seu primeiro acesso. Defina uma nova senha para continuar.")

        with st.form("form_change_password", clear_on_submit=False):
            new_password = st.text_input("Nova Senha", type="password", help="Mínimo 8 caracteres, maiúsculas, números e símbolos.")
            confirm_password = st.text_input("Confirme a Nova Senha", type="password")
            submit_change = st.form_submit_button("Salvar Nova Senha", use_container_width=True)

        if submit_change:
            new_hash = make_hash(new_password)
            is_valid_complexity, msg_error = validate_password_complexity(new_password)

            if new_password != confirm_password:
                st.error("❌ As senhas digitadas não coincidem.")
            elif not is_valid_complexity:
                st.warning(f"⚠️ {msg_error}")
            elif new_hash in user_data["history"]:
                st.error("❌ Você não pode reutilizar sua senha padrão ou senhas antigas.")
            else:
                # Atualização no banco de dados da sessão
                user_data["password_hash"] = new_hash
                user_data["history"].append(new_hash)
                user_data["is_first_login"] = False

                st.success("✅ Senha alterada com sucesso! Redirecionando...")
                st.rerun()

    # SUB-FLUXO 2: DASHBOARD / APLICAÇÃO PRINCIPAL
    else:
        st.title("📊 Painel de Controle")
        st.subheader(f"Seja bem-vindo(a)!")
        
        st.markdown("---")
        
        # Exemplo de conteúdo do seu sistema
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Status do Sistema", value="Ativo", delta="OK")
        with col2:
            st.metric(label="Sessão Iniciada", value="Ativa")

        st.success("Login e autenticação validados com sucesso.")

# === FLUXO B: USUÁRIO NÃO LOGADO (TELA DE LOGIN) ===
else:
    st.title("🔒 Acesso ao Sistema")
    st.caption("Insira suas credenciais para continuar.")

    with st.form("form_login"):
        email_input = st.text_input("E-mail corporativo").strip().lower()
        password_input = st.text_input("Senha", type="password")
        submit_login = st.form_submit_button("Entrar no Sistema", use_container_width=True)

    if submit_login:
        if not email_input or not password_input:
            st.warning("Preencha todos os campos para fazer login.")
        else:
            input_hash = make_hash(password_input)
            if verify_credentials(email_input, input_hash):
                st.session_state["logged_in"] = True
                st.session_state["user_email"] = email_input
                st.success("Credenciais validadas!")
                st.rerun()
            else:
                st.error("E-mail ou senha inválidos. Verifique os dados digitados.")