import os
import requests
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

# --- RODÍZIO DE BICHOS (ordem fixa, um por dia, não aleatório) ---
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
]

ARQUIVO_HISTORICO = "historico_pets.txt"


def proximo_bicho():
    """Pega o próximo bicho da lista, em ordem de rodízio, sem repetir até passar por todos."""
    if not os.path.exists(ARQUIVO_HISTORICO):
        return BICHOS[0]

    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        linhas = f.read().splitlines()

    if not linhas:
        return BICHOS[0]

    ultimo_nome = linhas[-1]
    nomes = [b["nome"] for b in BICHOS]

    if ultimo_nome not in nomes:
        return BICHOS[0]

    indice_atual = nomes.index(ultimo_nome)
    proximo_indice = (indice_atual + 1) % len(BICHOS)
    return BICHOS[proximo_indice]


def marcar_bicho_usado(nome_bicho):
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as f:
        f.write(nome_bicho + "\n")


IMAGEM_PADRAO = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/News_icon.svg/640px-News_icon.svg.png"


def buscar_imagem_openverse(palavra_chave):
    try:
        resposta = requests.get(
            "https://api.openverse.org/v1/images/",
            params={
                "q": palavra_chave,
                "license_type": "commercial",
                "page_size": 3,
                "mature": "false",
            },
            headers={"User-Agent": "RoboPets/1.0"},
            timeout=10,
        )
        resultados = resposta.json().get("results", [])
        return resultados[0]["url"] if resultados else IMAGEM_PADRAO
    except Exception as e:
        print(f"⚠️ Erro ao buscar imagem: {e}")
        return IMAGEM_PADRAO


def gerar_tabela_imagem_blogger(url_img, alt_title):
    return f'''<table align="center" cellpadding="0" cellspacing="0" class="tr-caption-container" style="margin-left: auto; margin-right: auto;"><tbody><tr><td style="text-align: center;"><img alt="{alt_title}" border="0" height="360" src="{url_img}" title="{alt_title}" width="640" /></td></tr></tbody></table><br />'''


def pedir_ia_groq(prompt, temperatura=0.75):
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODELO_IA,
        temperature=temperatura,
    )
    return response.choices[0].message.content.strip()


def gerar_titulo(bicho):
    prompt = (
        f"Crie um título de blog carinhoso e otimizado para SEO, em português do Brasil, sem "
        f"aspas, sobre cuidados com {bicho} de estimação. Responda apenas o título, texto puro."
    )
    return pedir_ia_groq(prompt, temperatura=0.7).replace('"', '').strip()


def gerar_artigo_cuidados(bicho):
    prompt = f"""
    Você é o autor de um blog de pets muito querido pelos leitores. Sua persona: uma pessoa
    caseira, carinhosa e cuidadosa, que ama animais e adora dar dicas práticas — como aquele
    amigo que todo mundo pede conselho antes de levar um bichinho pra casa. Você tem uma gata
    siamesa chamada Brunilda e um golden retriever chamado Thor.

    Escreva um artigo COMPLETO, bem escrito e otimizado para SEO sobre cuidados com: {bicho}.

    REGRAS DE FORMATO (HTML puro, sem Markdown):
    1. Um parágrafo de abertura (<p>) caloroso, puxando o leitor pelo tom de amizade e carinho
       pelos bichos (sem ainda falar de Brunilda ou Thor — isso fica pro final).
    2. NO MÍNIMO 4 subtítulos <h2> cobrindo: alimentação adequada, cuidados com saúde/higiene,
       ambiente/espaço ideal, e comportamento/bem-estar emocional do animal.
    3. Inclua dicas práticas e específicas (não genéricas) sobre {bicho}.
    4. IMPORTANTE: não dê conselhos médicos definitivos que substituam um veterinário — sempre
       que mencionar sintomas de doença ou situação de saúde, oriente o leitor a procurar um
       veterinário de confiança.
    5. Não invente estatísticas ou fatos veterinários específicos que você não tenha certeza.
    6. O texto principal (sem contar os parágrafos finais do diário pessoal) deve ter entre
       800 e 1000 palavras, bem escrito, útil e envolvente.
    7. Não inclua links nem chamadas de venda.

    Ao final do texto de dicas, adicione uma transição natural como um subtítulo
    <h2>Um Pouquinho do Meu Dia a Dia</h2> e escreva DOIS parágrafos grandes, no estilo de um
    diário pessoal e bem-humorado (tipo o filme Marley & Eu), contando uma trapalhada ou
    momento fofo real e específico que aconteceu com a Brunilda (gata siamesa) e/ou com o
    Thor (golden retriever) no dia a dia — invente uma cena cotidiana, engraçada e carinhosa
    (ex: Thor roubando meia, Brunilda derrubando planta, os dois brigando por espaço no sofá,
    etc). Mantenha um tom pessoal, próximo e afetuoso, como se estivesse contando pra um amigo.
    """
    return pedir_ia_groq(prompt, temperatura=0.8)


def obter_credenciais():
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return creds


def publicar_no_blogger(titulo, conteudo):
    creds = obter_credenciais()
    blogger = build('blogger', 'v3', credentials=creds)
    corpo_postagem = {'kind': 'blogger#post', 'title': titulo, 'content': conteudo}
    resultado = blogger.posts().insert(blogId=BLOGGER_ID, body=corpo_postagem).execute()
    print(f"🐾 Postado: '{titulo}' -> {resultado.get('url')}")


if __name__ == "__main__":
    print("🐾 Gerando artigo de cuidados com pets do dia...")
    bicho = proximo_bicho()
    print(f"Bicho de hoje: {bicho['nome']}")

    titulo = gerar_titulo(bicho['nome'])
    corpo = gerar_artigo_cuidados(bicho['nome'])
    img_url = buscar_imagem_openverse(bicho['img'])
    img_html = gerar_tabela_imagem_blogger(img_url, titulo)

    aviso = (
        '<p style="font-size: 12px; color: #888; font-style: italic;">Este conteúdo é '
        'informativo e não substitui a avaliação de um médico veterinário. Em caso de '
        'sintomas ou dúvidas sobre a saúde do seu animal, procure um profissional.</p>'
    )

    html_final = f"{img_html}{corpo}{aviso}"
    publicar_no_blogger(titulo, html_final)
    marcar_bicho_usado(bicho['nome'])
    print("✅ Concluído!")
