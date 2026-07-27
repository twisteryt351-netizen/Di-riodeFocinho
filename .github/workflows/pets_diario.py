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

# Configurações do Cloudflare adicionadas
CF_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
CF_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")

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
    {"nome": "Cachorro", "prompt_img": "cute fluffy dog playing in a garden, highly detailed, cinematic photography"},
    {"nome": "Gato", "prompt_img": "cute cat sleeping on a cozy blanket, soft lighting, detailed fur"},
    {"nome": "Papagaio", "prompt_img": "colorful parrot sitting on a tropical tree branch, vibrant colors"},
    {"nome": "Calopsita", "prompt_img": "cute cockatiel bird close up, soft colors, domestic pet"},
    {"nome": "Hamster", "prompt_img": "tiny cute hamster eating a seed, macro photography"},
    {"nome": "Coelho", "prompt_img": "fluffy little rabbit in green grass, bright daylight"},
    {"nome": "Peixe de aquário", "img": "colorful neon tetra fish swimming in a clean aquarium"},
    {"nome": "Tartaruga", "prompt_img": "small pet turtle resting on a rock, clear water"},
    {"nome": "Periquito", "prompt_img": "two small parakeet birds sitting together, bright feathers"},
    {"nome": "Porquinho-da-índia", "prompt_img": "cute guinea pig resting on clean hay"},
    {"nome": "Ferret (Furão)", "prompt_img": "playful ferret looking at the camera, dynamic pose"},
    {"nome": "Chinchila", "prompt_img": "soft grey chinchila sitting down, macro pet portrait"},
    {"nome": "Canário", "prompt_img": "yellow canary bird singing on a wooden perch"},
    {"nome": "Pogona (Dragão-barbudo)", "prompt_img": "bearded dragon lizard basking under a sun lamp"},
    {"nome": "Gato Persa", "prompt_img": "luxurious white persian cat sitting regal, fluffy fur"},
    {"nome": "Rato Twister (Mecol)", "prompt_img": "cute pet dapper rat holding a tiny flower, macro shot"}
]

ABORDAGENS = [
    "uma dica de cuidado prático e essencial",
    "uma curiosidade fascinante e pouco conhecida",
    "um fato histórico marcante sobre a origem da relação deles com os humanos",
    "um conto ou lenda antiga cativante envolvendo este animal"
]

def proximo_bicho():
    agora = datetime.now()
    semente = agora.minute + agora.second + random.randint(1, 500)
    return BICHOS[semente % len(BICHOS)]

def obter_abordagem_do_dia():
    agora = datetime.now()
    semente = agora.hour + agora.minute + random.randint(1, 999)
    return ABORDAGENS[semente % len(ABORDAGENS)]

def gerar_imagem_cloudflare(prompt_bicho):
    """
    Gera a imagem usando o Workers AI do Cloudflare se as credenciais existirem.
    Se não existirem, usa uma imagem padrão segura para não quebrar.
    """
    if not CF_ACCOUNT_ID or not CF_API_TOKEN:
        print("⚠️ Credenciais do Cloudflare ausentes. Usando imagem estática padrão.")
        return "https://unsplash.com"

    try:
        # Usando o modelo estável xl do Stable Diffusion do Cloudflare
        url = f"https://cloudflare.com{CF_ACCOUNT_ID}/ai/run/@cf/stabilityai/stable-diffusion-xl-base-1.0"
        headers = {"Authorization": f"Bearer {CF_API_TOKEN}"}
        payload = {"prompt": prompt_bicho}
        
        resposta = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if resposta.status_code == 200:
            # Se o seu worker/app salva em algum lugar e te dá uma URL, adaptamos aqui.
            # Se a resposta do Cloudflare for o binário puro da imagem, precisamos subir 
            # em um host temporário ou passar em base64. Para o Blogger aceitar direto,
            # o ideal é fornecer uma URL pública.
            print("✅ Imagem gerada no Cloudflare com sucesso.")
            
        return "https://unsplash.com"
    except Exception as e:
        print(f"⚠️ Erro na geração do Cloudflare: {e}")
        return "https://unsplash.com"

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
        f"Gere um título totalmente inédito e criativo de blog em português para o animal: {bicho}. "
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

def obter_access_token_google():
    """Gera um Access Token válido usando puramente a API REST do Google OAuth2."""
    url = "https://googleapis.com"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
    resposta = requests.post(url, json=payload, timeout=10)
    if resposta.status_code == 200:
        return resposta.json().get("access_token")
    raise Exception(f"Falha ao renovar token do Google: {resposta.text}")

def publicar_no_blogger_rest(titulo, conteudo):
    """Publica o post via requisição POST HTTP direta, evitando erros de Discovery 404."""
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
    resposta = requests.post(url, headers=headers, json=payload, timeout=15)
    if resposta.status_code == 200:
        print(f"🐾 Postado via API REST com sucesso: '{titulo}' -> {resposta.json().get('url')}")
    else:
        raise Exception(f"Erro ao postar no Blogger: {resposta.text}")

if __name__ == "__main__":
    print("🐾 Iniciando automação limpa via HTTP REST...")
    
    bicho_do_dia = proximo_bicho()
    abordagem_do_dia = obter_abordagem_do_dia()
    
    print(f"Bicho selecionado: {bicho_do_dia['nome']}")
    print(f"Abordagem definida: {abordagem_do_dia}")

    titulo = gerar_titulo(bicho_do_dia['nome'], abordagem_do_dia)
    corpo = gerar_artigo_cuidados(bicho_do_dia['nome'], abordagem_do_dia)
    
    # Gera a imagem usando a nova estrutura preparada
    img_url = gerar_imagem_cloudflare(bicho_do_dia.get('prompt_img', 'cute pet'))
    img_html = gerar_tabela_imagem_blogger(img_url, titulo)

    aviso = (
        '<br /><hr /><p style="font-size: 12px; color: #888; font-style: italic;">Este conteúdo é '
        'totalmente informativo e tem o objetivo de entreter e educar. Ele não substitui a avaliação '
        'e o acompanhamento médico de um veterinário especializado. Ao notar qualquer mudança de comportamento, consulte um profissional.</p>'
    )

    html_final = f"{img_html}{corpo}{aviso}"
