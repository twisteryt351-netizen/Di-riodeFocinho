import os
import requests
import random
from datetime import datetime
from groq import Groq

# --- CONFIGURAÇÕES ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
BLOGGER_ID = os.environ.get("BLOGGER_ID_PETS")
REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN")
CLIENT_ID = os.environ.get("BLOGGER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("BLOGGER_CLIENT_SECRET")

for nome, valor in [
    ("GROQ_API_KEY", GROQ_API_KEY),
    ("BLOGGER_ID_PETS", BLOGGER_ID),
    ("BLOGGER_REFRESH_TOKEN", REFRESH_TOKEN),
    ("BLOGGER_CLIENT_ID", CLIENT_ID),
    ("BLOGGER_CLIENT_SECRET", CLIENT_SECRET),
]:
    if not valor:
        raise ValueError(f"Faltou configurar a variável/segredo: {nome}")

groq_client = Groq(api_key=GROQ_API_KEY)
MODELO_IA = "llama-3.3-70b-versatile"

BICHOS = [
    {"nome": "Cachorro"}, {"nome": "Gato"}, {"nome": "Papagaio"}, {"nome": "Calopsita"},
    {"nome": "Hamster"}, {"nome": "Coelho"}, {"nome": "Peixe de aquário"}, {"nome": "Tartaruga"},
    {"nome": "Periquito"}, {"nome": "Porquinho-da-índia"}, {"nome": "Ferret (Furão)"},
    {"nome": "Chinchila"}, {"nome": "Canário"}, {"nome": "Pogona (Dragão-barbudo)"},
    {"nome": "Gato Persa"}, {"nome": "Rato Twister (Mecol)"}
]

ABORDAGENS = [
    "uma dica de cuidado prático e essencial do dia a dia",
    "uma curiosidade fascinante e extremamente rara sobre a anatomia ou sentidos dele",
    "um fato histórico marcante sobre a origem da relação e domesticação com humanos",
    "um conto antigo ou lenda tradicional cativante envolvendo o bicho",
    "um guia de enriquecimento ambiental focado em brinquedos caseiros e criativos",
    "mitos urbanos e verdades populares sobre o comportamento deste animal",
    "uma análise psicológica afetuosa sobre como ele demonstra amor pelo dono",
    "dicas essenciais de linguagem corporal para aprender a ler os sinais dele",
    "um roteiro prático focado focado em adestramento positivo e comandos simples",
    "curiosidades sobre como é a visão e a audição dele em comparação com os humanos",
    "um guia de cuidados especiais focados em quando ele atingir a idade idosa",
    "cuidados cruciais específicos voltados para as mudanças de estação (frio e calor intenso)",
    "uma história inspiradora e emocionante de lealdade real envolvendo a espécie",
    "erros comuns que donos iniciantes cometem sem perceber no manejo dele",
    "como introduzir novos hábitos na rotina dele sem gerar estresse ou ansiedade",
    "curiosidades divertidas sobre os hábitos de sono e os sonhos deste animal"
]

def proximo_bicho():
    dia_do_ano = datetime.now().timetuple().tm_yday
    return BICHOS[dia_do_ano % len(BICHOS)]

def obter_abordagem_do_dia():
    dia_do_ano = datetime.now().timetuple().tm_yday
    return ABORDAGENS[dia_do_ano % len(ABORDAGENS)]

IMAGEM_PADRAO = "https://unsplash.com"

def gerar_tabela_imagem_blogger(url_img, alt_title):
    return f'''<table align="center" cellpadding="0" cellspacing="0" class="tr-caption-container" style="margin-left: auto; margin-right: auto;"><tbody><tr><td style="text-align: center;"><img alt="{alt_title}" border="0" height="360" src="{url_img}" title="{alt_title}" width="640" /></td></tr></tbody></table><br />'''

def pedir_ia_groq(prompt, temperatura=1.0):
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODELO_IA,
        temperature=temperatura,
    )
    return response.choices.message.content.strip()

def gerar_titulo(bicho, abordagem):
    token_anti_cache = random.randint(10000, 99999)
    prompt = (
        f"Gere um título totalmente original e focado em SEO de blog para o animal: {bicho}. "
        f"O foco do título deve ser estritamente trazer {abordagem}. Não use clichês repetitivos. "
        f"Escreva em texto puro, sem aspas. Modificador anti-cache: {token_anti_cache}."
    )
    return pedir_ia_groq(prompt, temperatura=1.0).replace('"', '').strip()

def gerar_artigo_cuidados(bicho, abordagem):
    id_historia = random.randint(1000, 9999)
    prompt = f"""
    Você é o autor de um blog de pets muito querido pelos leitores. Sua persona: uma pessoa
    caseira, carinhosa e cuidadosa, que ama animais e adora conversar com seus leitores. Você tem uma gata
    siamesa chamada Brunilda e um golden retriever chamado Thor.

    Escreva um artigo COMPLETO, profundo e otimizado para SEO sobre {bicho}, desenvolvendo especificamente {abordagem}.

    REGRAS DE FORMATO (HTML puro, sem Markdown, sem blocos de código como ```html):
    1. Um parágrafo de abertura (<p>) caloroso e envolvendo o leitor, introduzindo o animal e o tema de hoje ({abordagem}) com muito afeto.
    2. NO MÍNIMO 4 subtítulos <h2> desenvolvendo detalhadamente o assunto de forma criativa.
    3. Inclua detalhes práticos, fatos interessantes e específicos (não genéricos) sobre {bicho}.
    4. IMPORTANTE: não dê conselhos médicos definitivos que substituam um veterinário — sempre oriente a buscar ajuda profissional.
    5. O texto principal deve ter entre 800 e 1000 palavras, bem formatado com parágrafos (<p>).

    Ao final do texto, adicione obrigatoriamente a transição:
    <h2>Um Pouquinho do Meu Dia a Dia</h2> 
    E escreva DOIS parágrafos grandes, no estilo de um diário pessoal e muito bem-humorado, contando uma trapalhada inédita que aconteceu com a Brunilda e/ou com o Thor em sua casa. 
    Chave de variação da história: {id_historia}. Crie uma narrativa completamente nova e mude a forma de começar para não repetir postagens antigas.
    """
    artigo = pedir_ia_groq(prompt, temperatura=1.0)
    if artigo.startswith("```"):
        artigo = artigo.strip("`").replace("html\n", "", 1)
    return artigo

def obter_access_token_google():
    """Usa data= payload no lugar de json= para passar na autenticação sem gerar erro 404."""
    url = "https://googleapis.com"
    payload = {
        "client_id": CLIENT_ID.strip(),
        "client_secret": CLIENT_SECRET.strip(),
        "refresh_token": REFRESH_TOKEN.strip(),
        "grant_type": "refresh_token"
    }
    # Envio via corpo de formulário HTTP x-www-form-urlencoded
    resposta = requests.post(url, data=payload, timeout=10)
    if resposta.status_code == 200:
        return resposta.json().get("access_token")
    raise Exception(f"Falha na validação OAuth2 do Google: {resposta.text}")

def publicar_no_blogger_rest(titulo, conteudo):
    token = obter_access_token_google()
    url = f"https://googleapis.com{BLOGGER_ID}/posts"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "kind": "blogger#post",
        "title": titulo,
        "content": conteudo
    }
    resposta = requests.post(url, json=payload, headers=headers, timeout=15)
    if resposta.status_code == 200:
        print(f"🐾 Postado com sucesso via REST Direto: '{titulo}'")
    else:
        raise Exception(f"Erro ao postar no Blogger: {resposta.text}")

if __name__ == "__main__":
    print("🐾 Iniciando automação limpa via HTTP REST Direto...")
    bicho_do_dia = proximo_bicho()
    abordagem_do_dia = obter_abordagem_do_dia()
    
    print(f"Bicho: {bicho_do_dia['nome']} | Abordagem: {abordagem_do_dia}")

    titulo = gerar_titulo(bicho_do_dia['nome'], abordagem_do_dia)
    corpo = gerar_artigo_cuidados(bicho_do_dia['nome'], abordagem_do_dia)
    img_html = gerar_tabela_imagem_blogger(IMAGEM_PADRAO, titulo)

    aviso = (
        '<br /><hr /><p style="font-size: 12px; color: #888; font-style: italic;">Este conteúdo é '
        'totalmente informativo e tem o objetivo de entreter e educar. Ele não substitui a avaliação '
        'e o acompanhamento médico de um veterinário especializado.</p>'
    )

    html_final = f"{img_html}{corpo}{aviso}"
    publicar_no_blogger_rest(titulo, html_final)
    print("✅ Processo concluído com sucesso total!")
