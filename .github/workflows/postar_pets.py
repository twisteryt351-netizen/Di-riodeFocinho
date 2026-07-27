import os
import requests
import random
from datetime import datetime
from groq import Groq
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- CONFIGURAÇÕES ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
BLOGGER_ID = os.environ.get("BLOGGER_ID_PETS")
CLIENT_ID = os.environ.get("BLOGGER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("BLOGGER_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN")

for nome, valor in [
    ("GROQ_API_KEY", GROQ_API_KEY),
    ("BLOGGER_ID_PETS", BLOGGER_ID),
    ("BLOGGER_CLIENT_ID", CLIENT_ID),
    ("BLOGGER_CLIENT_SECRET", CLIENT_SECRET),
    ("BLOGGER_REFRESH_TOKEN", REFRESH_TOKEN),
]:
    if not valor:
        raise ValueError(f"Faltou configurar a variável/segredo: {nome}")

groq_client = Groq(api_key=GROQ_API_KEY)
MODELO_IA = "llama-3.3-70b-versatile"

BICHOS = [
    {"nome": "Cachorro", "img": "dog pet care"},
    {"nome": "Gato", "img": "cat pet care"},
    {"nome": "Papagaio", "img": "parrot bird pet"},
    {"nome": "Calopsita", "img": "cockatiel bird pet"},
    {"nome": "Hamster", "img": "hamster pet care"},
    {"nome": "Coelho", "img": "rabbit pet care"},
    {"nome": "Peixe de aquário", "img": "aquarium fish pet"},
    {"nome": "Tartaruga", "img": "turtle pet care"},
    {"nome": "Periquito", "img": "parakeet bird pet"},
    {"nome": "Porquinho-da-índia", "img": "guinea pig pet"},
    {"nome": "Ferret (Furão)", "img": "ferret pet"},
    {"nome": "Chinchila", "img": "chinchila pet"},
    {"nome": "Canário", "img": "canary bird pet"},
    {"nome": "Pogona (Dragão-barbudo)", "img": "bearded dragon pet"},
    {"nome": "Gato Persa", "img": "persian cat pet"},
    {"nome": "Rato Twister (Mecol)", "img": "pet rat care"}
]

ABORDAGENS = [
    "uma dica de cuidado prático e essencial",
    "uma curiosidade fascinante e pouco conhecida",
    "um fato histórico marcante sobre a origem da relação deles com os humanos",
    "um conto ou lenda antiga cativante envolvendo este animal"
]

def proximo_bicho():
    # Semente totalmente dinâmica baseada em minutos e segundos para mudar a cada teste manual
    agora = datetime.now()
    semente = agora.minute + agora.second + random.randint(1, 500)
    return BICHOS[semente % len(BICHOS)]

def obter_abordagem_do_dia():
    agora = datetime.now()
    semente = agora.hour + agora.minute + random.randint(1, 999)
    return ABORDAGENS[semente % len(ABORDAGENS)]

IMAGEM_PADRAO = "https://wikimedia.org"

def buscar_imagem_openverse(palavra_chave):
    try:
        resposta = requests.get(
            "https://openverse.org",
            params={
                "q": palabra_chave,
                "license_type": "commercial",
                "page_size": 3,
                "mature": "false",
            },
            headers={"User-Agent": "RoboPets/1.0"},
            timeout=10,
        )
        resultados = resposta.json().get("results", [])
        # CORREÇÃO CRUCIAL: Retornando o índice zero para evitar travamento do script
        return resultados[0]["url"] if resultados else IMAGEM_PADRAO
    except Exception as e:
        print(f"⚠️ Erro ao buscar imagem: {e}")
        return IMAGEM_PADRAO

def gerar_tabela_imagem_blogger(url_img, alt_title):
    return f'''<table align="center" cellpadding="0" cellspacing="0" class="tr-caption-container" style="margin-left: auto; margin-right: auto;"><tbody><tr><td style="text-align: center;"><img alt="{alt_title}" border="0" height="360" src="{url_img}" title="{alt_title}" width="640" /></td></tr></tbody></table><br />'''

def pedir_ia_groq(prompt, temperatura=1.0):
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODELO_IA,
        temperature=temperatura,
    )
    return response.choices[0].message.content.strip()

def gerar_titulo(bicho, abordagem):
    token_anti_cache = random.randint(10000, 99999)
    prompt = (
        f"Gere um título totalmente original e criativo de blog em português para o animal: {bicho}. "
        f"O tema central deve ser obrigatoriamente {abordagem}. Proibido usar palavras repetidas como 'amigo fiel' ou 'vida saudável'. "
        f"Escreva estritamente em formato de texto puro, sem aspas. Modificador numérico: {token_anti_cache}."
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

def obter_credenciais():
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri="https://googleapis.com",
    )
    creds.refresh(Request())
    return creds

def publicar_no_blogger(titulo, conteudo):
    creds = obter_credenciais()
    blogger = build('blogger', 'v3', credentials=creds)
    corpo_postagem = {'kind': 'blogger#post', 'title': titulo, 'content': conteudo}
    resultado = blogger.posts().insert(blogId=BLOGGER_ID, body=corpo_postagem).execute()
    print(f"🐾 Postado com sucesso: '{titulo}' -> {resultado.get('url')}")

if __name__ == "__main__":
    print("🐾 Iniciando automação de artigos diários...")
    
    bicho_do_dia = proximo_bicho()
    abordagem_do_dia = obter_abordagem_do_dia()
    
    print(f"Bicho selecionado: {bicho_do_dia['nome']}")
    print(f"Abordagem definida: {abordagem_do_dia}")

    titulo = gerar_titulo(bicho_do_dia['nome'], abordagem_do_dia)
    corpo = gerar_artigo_cuidados(bicho_do_dia['nome'], abordagem_do_dia)
    img_url = buscar_imagem_openverse(bicho_do_dia['img'])
    img_html = gerar_tabela_imagem_blogger(img_url, titulo)

    aviso = (
        '<br /><hr /><p style="font-size: 12px; color: #888; font-style: italic;">Este conteúdo é '
        'totalmente informativo e tem o objetivo de entreter e educar. Ele não substitui a avaliação '
        'e o acompanhamento médico de um veterinário especializado. Ao notar qualquer mudança de comportamento, consulte um profissional.</p>'
    )

    html_final = f"{img_html}{corpo}{aviso}"
    publicar_no_blogger(titulo, html_final)
    print("✅ Processo concluído com sucesso!")
