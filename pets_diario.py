import os
import random
import json
import re
import time
import base64
import urllib.parse
import requests
from groq import Groq
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- CONFIGURAÇÕES ---
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY")
BLOGGER_ID        = os.environ.get("BLOGGER_ID_PETS")
CLIENT_ID         = os.environ.get("BLOGGER_CLIENT_ID")
CLIENT_SECRET     = os.environ.get("BLOGGER_CLIENT_SECRET")
REFRESH_TOKEN     = os.environ.get("BLOGGER_REFRESH_TOKEN")
POLLINATIONS_TOKEN = os.environ.get("POLLINATIONS_TOKEN")  # opcional: remove marca dagua e aumenta limite
# Sem token: 1 requisicao a cada 15s. Com token gratuito (auth.pollinations.ai): a cada 5s.
INTERVALO_POLLINATIONS = 6 if POLLINATIONS_TOKEN else 16
IMGBB_API_KEY     = os.environ.get("IMGBB_API_KEY")  # hospedagem permanente das imagens

for nome, valor in [
    ("GROQ_API_KEY",          GROQ_API_KEY),
    ("BLOGGER_ID_PETS",       BLOGGER_ID),
    ("BLOGGER_CLIENT_ID",     CLIENT_ID),
    ("BLOGGER_CLIENT_SECRET", CLIENT_SECRET),
    ("BLOGGER_REFRESH_TOKEN", REFRESH_TOKEN),
]:
    if not valor:
        raise ValueError(f"Faltou configurar a variável/segredo: {nome}")

if not IMGBB_API_KEY:
    print("⚠️  IMGBB_API_KEY não configurada — imagens geradas via IA serão embed como base64 (fallback).")

groq_client = Groq(api_key=GROQ_API_KEY)
MODELO_IA   = "openai/gpt-oss-120b"

# ─────────────────────────────────────────────
#  LISTA DE ANIMAIS — 30 opções variadas
# ─────────────────────────────────────────────
BICHOS = [
    {"nome": "Cachorro",              "img_en": "dog playing outdoors happy"},
    {"nome": "Gato",                  "img_en": "cat relaxing indoor cozy"},
    {"nome": "Papagaio",              "img_en": "colorful parrot perched branch"},
    {"nome": "Calopsita",             "img_en": "cockatiel bird cute pet"},
    {"nome": "Hamster",               "img_en": "hamster running wheel cute"},
    {"nome": "Coelho",                "img_en": "fluffy rabbit pet garden"},
    {"nome": "Peixe de aquário",      "img_en": "colorful aquarium fish tank"},
    {"nome": "Tartaruga",             "img_en": "turtle pet slow walk"},
    {"nome": "Periquito",             "img_en": "parakeet colorful bird cage"},
    {"nome": "Porquinho-da-índia",    "img_en": "guinea pig cute fluffy"},
    {"nome": "Ferret (Furão)",        "img_en": "ferret playful curious pet"},
    {"nome": "Chinchila",             "img_en": "chinchilla soft fluffy pet"},
    {"nome": "Iguana",                "img_en": "iguana reptile green pet"},
    {"nome": "Lagarto Barbaposada",   "img_en": "bearded dragon lizard pet"},
    {"nome": "Cobra (ofidofilia)",    "img_en": "ball python snake pet docile"},
    {"nome": "Aranha (tarântula)",    "img_en": "tarantula spider exotic pet"},
    {"nome": "Gerbil",                "img_en": "gerbil small rodent pet"},
    {"nome": "Rato Doméstico",        "img_en": "fancy rat intelligent pet"},
    {"nome": "Ouriço-africano",       "img_en": "hedgehog cute spiky pet"},
    {"nome": "Suricato",              "img_en": "meerkat curious alert pet"},
    {"nome": "Pato doméstico",        "img_en": "domestic duck waddling farm"},
    {"nome": "Galinha-d'angola",      "img_en": "guinea fowl spotted bird farm"},
    {"nome": "Mini porco",            "img_en": "mini pig cute teacup pet"},
    {"nome": "Axolote",               "img_en": "axolotl aquatic salamander cute"},
    {"nome": "Canário",               "img_en": "canary yellow singing bird"},
    {"nome": "Agapornis (Pássaro do Amor)", "img_en": "lovebird colorful pair perched"},
    {"nome": "Lagosta de água doce",  "img_en": "freshwater crayfish aquarium"},
    {"nome": "Esquilo-de-estimação",  "img_en": "pet squirrel playful branch"},
    {"nome": "Capivara doméstica",    "img_en": "capybara friendly calm water"},
    {"nome": "Sapo-de-estimação",     "img_en": "pet frog colorful terrarium"},
]

ARQUIVO_HISTORICO = "historico_pets.txt"
IMAGEM_PADRAO     = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/News_icon.svg/640px-News_icon.svg.png"

# Máx de posts recentes que ficam na "lista negra" (evita repetição)
JANELA_ANTIREPETIÇÃO = 8


# ─────────────────────────────────────────────
#  HISTÓRICO — anti-repetição aleatório
# ─────────────────────────────────────────────
def carregar_historico():
    if not os.path.exists(ARQUIVO_HISTORICO):
        return []
    with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


def marcar_bicho_usado(nome_bicho):
    with open(ARQUIVO_HISTORICO, "a", encoding="utf-8") as f:
        f.write(nome_bicho + "\n")


def escolher_bicho():
    """
    Escolhe aleatoriamente, evitando repetir os últimos JANELA_ANTIREPETIÇÃO animais.
    Garante que nenhum nome se repita até o ciclo ser suficientemente longo.
    """
    historico   = carregar_historico()
    recentes    = set(historico[-JANELA_ANTIREPETIÇÃO:])
    disponiveis = [b for b in BICHOS if b["nome"] not in recentes]

    # Se todos estiverem "bloqueados" (lista pequena), libera todos
    if not disponiveis:
        disponiveis = BICHOS

    escolhido = random.choice(disponiveis)
    print(f"🎲 Bicho escolhido: {escolhido['nome']}")
    return escolhido


# ─────────────────────────────────────────────
#  GROQ (texto)
# ─────────────────────────────────────────────
def pedir_ia_groq(prompt, temperatura=0.75):
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=MODELO_IA,
        temperature=temperatura,
    )
    return response.choices[0].message.content.strip()


# ─────────────────────────────────────────────
#  TÍTULO — anti-repetição forçada
# ─────────────────────────────────────────────
def gerar_titulo(bicho):
    historico = carregar_historico()
    titulos_recentes = historico[-20:] if len(historico) >= 20 else historico

    prompt = (
        f"Crie um título de blog original, carinhoso, bem-humorado e otimizado para SEO, "
        f"em português do Brasil, sem aspas, sobre cuidados com {bicho} de estimação.\n"
        f"IMPORTANTE: O título DEVE ser diferente e criativo — não pode ser parecido com nenhum destes já usados recentemente:\n"
        f"{chr(10).join(titulos_recentes) if titulos_recentes else '(nenhum ainda)'}\n\n"
        f"Use ângulos diferentes: pode focar em curiosidades, mitos, segredos, guia do dono "
        f"de primeira viagem, dicas que ninguém conta, confissões de quem tem {bicho} em casa, etc.\n"
        f"Responda apenas o título, texto puro."
    )
    return pedir_ia_groq(prompt, temperatura=0.85).replace('"', '').strip()


# ─────────────────────────────────────────────
#  ÂNGULOS — variedade de abordagem
# ─────────────────────────────────────────────
ANGULOS = [
    "Guia completo para quem está pensando em ter esse animal pela primeira vez, cheio de alertas honestos e dicas que ninguém conta.",
    "Desmistificando os maiores mitos e verdades sobre criar esse animal em apartamento ou casa pequena.",
    "Foco em comportamento e linguagem corporal: como entender o que esse animal está sentindo e o que ele tenta comunicar.",
    "Curiosidades científicas e fatos surpreendentes sobre a biologia e comportamento desse animal que vão mudar como você o vê.",
    "Guia de alimentação detalhado: o que pode, o que NUNCA pode e por que alguns alimentos 'naturais' são perigosos.",
    "Como enriquecer o ambiente e garantir qualidade de vida e saúde mental para esse animal em casa.",
    "Os erros mais comuns que donos cometem (sem saber!) e como corrigi-los antes que virem problema de saúde.",
    "Tudo sobre saúde preventiva: vacinas, vermifugação, consultas, sinais de alerta e quando correr pro veterinário.",
]

# Variações do segmento do diário pessoal
MODOS_DIARIO = [
    # Vai direto sem apresentar os pets
    "direto",
    # Apresenta brevemente só no contexto da história
    "contexto_rapido",
]


# ─────────────────────────────────────────────
#  ARTIGO
# ─────────────────────────────────────────────
def gerar_artigo_cuidados(bicho, num_imagens):
    angulo = random.choice(ANGULOS)
    modo_diario = random.choice(MODOS_DIARIO)

    # Histórico de situações já contadas (evita repetição no diário)
    historico = carregar_historico()
    situacoes_recentes = historico[-15:] if len(historico) >= 15 else historico
    aviso_situacoes = (
        f"SITUAÇÕES JÁ CONTADAS RECENTEMENTE (NÃO repita nenhuma dessas):\n"
        f"{', '.join(situacoes_recentes) if situacoes_recentes else '(nenhuma ainda)'}\n"
    ) if situacoes_recentes else ""

    if modo_diario == "direto":
        instrucao_diario = (
            "No segmento do diário pessoal, vá DIRETO para a história sem apresentar "
            "Brunilda ou Thor — quem lê o blog já os conhece de cor. Comece já na cena, "
            "como se fosse um episódio de uma série que o leitor acompanha."
        )
    else:
        instrucao_diario = (
            "No segmento do diário pessoal, mencione o nome do pet envolvido de forma "
            "casual, dentro do contexto da história — sem aquela introdução formal de "
            "'tenho uma gata chamada...'. Quem acompanha o blog já sabe quem são."
        )

    marcadores_instrucao = ""
    if num_imagens > 1:
        marcadores_instrucao = (
            f"\nO artigo terá {num_imagens - 1} imagem(ns) além da capa. "
            f"Insira os marcadores <!--IMG_2-->, <!--IMG_3-->"
            + (f", <!--IMG_{num_imagens}-->" if num_imagens > 3 else "")
            + f" em momentos narrativos naturais (após parágrafos, antes de nova seção h2). "
            f"Não coloque dois marcadores seguidos.\n"
        )

    prompt = f"""
Você é o autor de um blog de pets muito querido, com persona carinhosa, bem-humorada e
divertida. Escreve como aquele amigo que sabe MUITO sobre bichos mas conta as coisas de
um jeito leve, sem ser chato ou didático demais. Usa analogias engraçadas, faz comparações
inesperadas, conta histórias, e de vez em quando joga uma piada seca que faz o leitor rir
sozinho. Tem uma gata siamesa chamada Brunilda (diva, mandona, ignora todo mundo mas ama
dormir no rosto do dono) e um golden retriever chamado Thor (caótico, alegre, destrói tudo
com amor e parece ter 3 anos eternamente).

ANIMAL DO DIA: {bicho}

ÂNGULO OBRIGATÓRIO PARA ESTE ARTIGO:
"{angulo}"

Use esse ângulo como fio condutor do artigo inteiro. Não é só um tópico — é a perspectiva
de toda a matéria.

REGRAS DE CONTEÚDO:
- NÃO seja genérico. Dicas têm que ser específicas para {bicho}.
- Inclua CURIOSIDADES científicas ou comportamentais surpreendentes sobre {bicho} — coisas
  que a maioria dos donos não sabe (ex: fisiologia incomum, comportamentos instintivos,
  recordes, fatos evolutivos, mitos populares desbancados).
- Tom: divertido, engraçado, com analogias criativas. Pode usar humor, mas nunca debochado
  ou ofensivo com os animais.
- Quando falar de saúde/doença, oriente sempre a buscar veterinário. Não invente dados.
- Tamanho do conteúdo de dicas: entre 900 e 1300 palavras.
- PROIBIDO repetir a mesma ideia em parágrafos diferentes com outras palavras.
{marcadores_instrucao}
REGRAS DE FORMATO (HTML puro, sem Markdown):
1. Parágrafo de abertura (<p>) envolvente que entra no ângulo já de cara, sem rodeios.
2. NO MÍNIMO 4 subtítulos <h2> cobrindo aspectos diferentes do ângulo escolhido.
3. Pelo menos 1 lista <ul> com dicas práticas e específicas.
4. 2 a 3 <blockquote> com comentários bem-humorados, tipo nota de rodapé de fã dos bichos.
5. Não esquece de incluir as Tag´s dos post´s.

Depois do conteúdo principal, adicione:
<h2>Diário da Semana 🐾</h2>
{instrucao_diario}
Escreva 2 parágrafos grandes, no estilo diário pessoal bem-humorado (tipo Marley & Eu mas
com mais caos e menos drama). A cena deve ser NOVA, cotidiana e específica — uma trapalhada,
um momento absurdo, uma coisa que só quem tem pet entende.
{aviso_situacoes}
O humor pode ser absurdo, auto-depreciativo (do narrador), mas sempre carinhoso com os bichos.
"""
    return pedir_ia_groq(prompt, temperatura=0.82)


# ─────────────────────────────────────────────
#  PROMPTS DE IMAGEM (via Groq)
# ─────────────────────────────────────────────
def gerar_prompts_imagens(bicho, titulo, num_imagens):
    outros = ""
    if num_imagens > 1:
        outros = (
            f"\n- Imagens 2 a {num_imagens}: cenas conceituais e emocionais que ilustram "
            f"momentos de cuidado, brincadeira, afeto ou curiosidade sobre {bicho}. "
            f"Cada uma deve ser visualmente única e transmitir uma emoção diferente."
        )

    prompt = f"""
You are an expert art director creating image prompts for a warm, fun pet care blog.

Animal: "{bicho}"
Article title: "{titulo}"

Create exactly {num_imagens} image concepts:

- Image 1 (COVER): eye-catching thumbnail-style image of {bicho}. Must be irresistible
  to click: bold composition, vibrant warm colors, adorable or funny expression, soft
  cinematic lighting, 8K photorealistic quality. Style: magazine cover meets viral social
  media post. No text or watermarks in the image.{outros}

For EACH image, provide:
- "prompt": one vivid descriptive paragraph in ENGLISH for the image generator. No text,
  logos or words inside the image. Photorealistic preferred, warm/cozy/emotional tone,
  8K, sharp details, professional pet photography aesthetic.
- "legenda": a short caption in BRAZILIAN PORTUGUESE (under 12 words) describing what the
  image shows, written like a photo caption a reader would see under the image — not a
  repeat of the article title.

Return ONLY a valid JSON array of {num_imagens} objects, nothing else.
Example: [{{"prompt": "...", "legenda": "..."}}, {{"prompt": "...", "legenda": "..."}}]
"""
    raw = pedir_ia_groq(prompt, temperatura=0.6)
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        try:
            itens = json.loads(match.group())
            if isinstance(itens, list) and all(isinstance(i, dict) for i in itens):
                resultado = [
                    {"prompt": str(i.get("prompt", "")).strip(),
                     "legenda": str(i.get("legenda", "")).strip()}
                    for i in itens[:num_imagens]
                ]
                if all(r["prompt"] for r in resultado):
                    return resultado
        except Exception:
            pass
    # fallback: sem legenda estruturada
    return [{"prompt": f"{bicho} cute pet photography 8K, scene {i+1}", "legenda": ""}
            for i in range(num_imagens)]


# ─────────────────────────────────────────────
#  GERAÇÃO DE IMAGEM — Pollinations.ai (b64)
# ─────────────────────────────────────────────
DIMENSOES_RATIO = {
    "16:9": (1280, 720),
    "1:1": (1024, 1024),
    "9:16": (720, 1280),
}


def gerar_imagem_worker_b64(prompt_img, ratio="16:9"):
    """Gera a imagem via Pollinations.ai (gratuito, sem chave, sem cota diaria)
    e retorna o base64 bruto da imagem."""
    largura, altura = DIMENSOES_RATIO.get(ratio, (1280, 720))
    prompt_codificado = urllib.parse.quote(prompt_img)
    url = f"https://image.pollinations.ai/prompt/{prompt_codificado}"
    params = {
        "width": largura,
        "height": altura,
        "model": "flux",
        "seed": random.randint(1, 999999),
        "nologo": "true",
    }
    headers = {}
    if POLLINATIONS_TOKEN:
        headers["Authorization"] = f"Bearer {POLLINATIONS_TOKEN}"
    resp = requests.get(url, params=params, headers=headers, timeout=120)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "")
    if "image" not in content_type:
        raise ValueError(f"Resposta nao parece ser uma imagem (Content-Type: {content_type})")
    b64 = base64.b64encode(resp.content).decode("utf-8")
    if not b64:
        raise ValueError("Pollinations.ai retornou imagem vazia.")
    return b64


# ─────────────────────────────────────────────
#  HOSPEDAGEM — ImgBB (b64 → URL pública)
# ─────────────────────────────────────────────
def hospedar_imgbb(b64_data, nome="pets_img"):
    """
    Envia o base64 para o ImgBB e retorna a URL pública da imagem.
    Levanta exceção se falhar.
    """
    if not IMGBB_API_KEY:
        raise ValueError("IMGBB_API_KEY não configurada.")

    resp = requests.post(
        "https://api.imgbb.com/1/upload",
        data={
            "key":    IMGBB_API_KEY,
            "image":  b64_data,
            "name":   nome[:100],
        },
        timeout=60,
    )
    resp.raise_for_status()
    resultado = resp.json()
    if not resultado.get("success"):
        raise ValueError(f"ImgBB recusou o upload: {resultado}")
    url = resultado["data"]["url"]
    print(f"  ☁️  ImgBB hospedou: {url}")
    return url


def verificar_url_imagem(url, tentativas=5, espera_segundos=2):
    """Confirma que a URL da imagem já está de fato acessível antes de
    usar no post. O ImgBB (e às vezes o Pollinations) podem levar alguns
    segundos pra propagar no CDN deles — sem essa checagem, o post é
    publicado com um link que ainda dá 404/timeout, e só passa a
    funcionar quando o Blogger recarrega o conteúdo depois (ex: ao
    clicar em 'Atualizar')."""
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            if resp.status_code == 200:
                return True
            # alguns hosts não respondem bem a HEAD, tenta GET como fallback
            if resp.status_code in (403, 405):
                resp = requests.get(url, timeout=10, stream=True)
                if resp.status_code == 200:
                    return True
        except requests.RequestException:
            pass
        if tentativa < tentativas:
            time.sleep(espera_segundos)
    return False


# ─────────────────────────────────────────────
#  FALLBACK — Openverse (imagens com licença CC)
# ─────────────────────────────────────────────
def buscar_imagens_openverse(palavra_chave, quantidade=3):
    try:
        resposta = requests.get(
            "https://api.openverse.org/v1/images/",
            params={
                "q":            palavra_chave,
                "license_type": "commercial",
                "page_size":    max(quantidade, 5),
                "mature":       "false",
            },
            headers={"User-Agent": "RoboPets/1.0"},
            timeout=15,
        )
        resultados = resposta.json().get("results", [])
        urls = [r["url"] for r in resultados[:quantidade]]
        return urls if urls else [IMAGEM_PADRAO]
    except Exception as e:
        print(f"⚠️ Erro Openverse: {e}")
        return [IMAGEM_PADRAO]


# ─────────────────────────────────────────────
#  HTML DE IMAGEM (Blogger)
# ─────────────────────────────────────────────
def html_imagem_blogger(src, alt_title, legenda="", height=360, width=640):
    """src deve ser sempre uma URL pública (ImgBB, Openverse ou data URI como último recurso)."""
    legenda_html = ""
    if legenda:
        legenda_html = (
            f'<div style="font-size:13px;color:#777;font-style:italic;'
            f'text-align:center;margin-top:6px;margin-bottom:20px;">{legenda}</div>'
        )
    return (
        '<table align="center" cellpadding="0" cellspacing="0" '
        'class="tr-caption-container" '
        'style="margin-left:auto;margin-right:auto;margin-bottom:8px;">'
        '<tbody><tr><td style="text-align:center;">'
        f'<img alt="{legenda or alt_title}" border="0" height="{height}" src="{src}" '
        f'title="{legenda or alt_title}" width="{width}" '
        'style="max-width:100%;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.12);" />'
        '</td></tr></tbody></table>'
        f'{legenda_html}'
    )


# ─────────────────────────────────────────────
#  ORQUESTRADOR DE IMAGENS
#  Cascata: Pollinations.ai → ImgBB → (fallback) Openverse
# ─────────────────────────────────────────────
def obter_imagens_html(itens_imagem, titulo, img_en_fallback):
    """
    itens_imagem: lista de dicts {'prompt':..., 'legenda':...}
    Para cada item:
      1. Gera imagem via Pollinations.ai (b64)
      2. Hospeda no ImgBB → URL pública limpa para o Blogger
      3. Confirma que a URL já está acessível antes de usar (evita imagem
         quebrada até alguém dar "Atualizar" manualmente no post)
      4. Se Pollinations.ai falhar: tenta Openverse (URL direta, sem ImgBB)
      5. Se ImgBB falhar/não propagar: usa data URI base64 como último recurso
    """
    imagens_html    = []
    openverse_cache = None

    for i, item in enumerate(itens_imagem):
        prompt_img = item["prompt"]
        legenda = item.get("legenda", "")
        src = None

        # ── Tentativa 1: Pollinations.ai + ImgBB ──────────
        try:
            print(f"  🖼️  [{i+1}/{len(itens_imagem)}] Gerando via Pollinations.ai...")
            b64 = gerar_imagem_worker_b64(prompt_img, ratio="16:9")

            try:
                nome_img = f"pets_{titulo[:40].replace(' ','_')}_{i+1}"
                url_imgbb = hospedar_imgbb(b64, nome=nome_img)
                print(f"  ⏳ Confirmando que a URL do ImgBB já está acessível...")
                if verificar_url_imagem(url_imgbb):
                    src = url_imgbb
                    print(f"  ✅ URL confirmada: {src[:60]}...")
                else:
                    raise ValueError("URL do ImgBB não respondeu 200 depois de várias tentativas.")
            except Exception as e_imgbb:
                # ImgBB falhou/não propagou mas temos o b64 — usa data URI como backup
                print(f"  ⚠️  ImgBB falhou/não propagou ({e_imgbb}). Usando data URI como backup...")
                src = f"data:image/png;base64,{b64}"

        # ── Tentativa 2: Openverse (Pollinations.ai falhou) ─
        except Exception as e_ia:
            print(f"  ⚠️  Pollinations.ai falhou ({e_ia}). Buscando no Openverse...")
            if openverse_cache is None:
                openverse_cache = buscar_imagens_openverse(
                    img_en_fallback, quantidade=len(itens_imagem)
                )
            src = openverse_cache[i % len(openverse_cache)]
            print(f"  🔄 Openverse: {src[:60]}...")

        altura = 420 if i == 0 else 300
        imagens_html.append(html_imagem_blogger(src, titulo, legenda=legenda, height=altura))

        if i < len(itens_imagem) - 1:
            time.sleep(INTERVALO_POLLINATIONS)  # respeita o rate limit do Pollinations.ai

    return imagens_html


# ─────────────────────────────────────────────
#  MONTAGEM DO HTML FINAL
# ─────────────────────────────────────────────
def montar_html(corpo_artigo, imagens_html, aviso):
    html_corpo = corpo_artigo

    # Injeta imagens de corpo nos marcadores <!--IMG_N-->
    for idx in range(1, len(imagens_html)):
        marcador = f"<!--IMG_{idx + 1}-->"
        if marcador in html_corpo:
            html_corpo = html_corpo.replace(marcador, imagens_html[idx], 1)
        else:
            # Appenda ao final se marcador não veio
            html_corpo += imagens_html[idx]

    cta = """
<div style="background-color:#fff8f0;border-left:4px solid #ff9800;border-radius:8px;
margin:32px 0;padding:20px 24px;font-family:sans-serif;">
    <p style="font-size:16px;font-weight:bold;color:#333;margin:0 0 8px 0;">
        🐾 Conta pra mim!</p>
    <p style="font-size:14px;color:#555;margin:0 0 14px 0;">
        Você tem um(a) {bicho} em casa? Deixa nos comentários a maior trapalhada
        que ele(a) já aprontou — prometo que não vou julgar. Muito. 😂</p>
    <div style="display:flex;flex-wrap:wrap;gap:10px;">
        <a href="#" onclick="window.open('https://api.whatsapp.com/send?text='
+encodeURIComponent(document.title+' - '+window.location.href),'_blank');return false;"
style="background-color:#25d366;color:white;padding:9px 16px;border-radius:8px;
text-decoration:none;font-size:13px;font-weight:bold;">WhatsApp</a>
        <a href="#" onclick="window.open('https://www.facebook.com/sharer/sharer.php?u='
+encodeURIComponent(window.location.href),'_blank');return false;"
style="background-color:#1877f2;color:white;padding:9px 16px;border-radius:8px;
text-decoration:none;font-size:13px;font-weight:bold;">Facebook</a>
        <a href="#" onclick="window.open('https://twitter.com/intent/tweet?url='
+encodeURIComponent(window.location.href),'_blank');return false;"
style="background-color:#000;color:white;padding:9px 16px;border-radius:8px;
text-decoration:none;font-size:13px;font-weight:bold;">X</a>
    </div>
</div>
"""
    return f"{imagens_html[0]}{html_corpo}{cta}{aviso}"


# ─────────────────────────────────────────────
#  BLOGGER
# ─────────────────────────────────────────────
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
    creds   = obter_credenciais()
    blogger = build("blogger", "v3", credentials=creds)
    corpo   = {"kind": "blogger#post", "title": titulo, "content": conteudo}
    res     = blogger.posts().insert(blogId=BLOGGER_ID, body=corpo).execute()
    print(f"🐾 Postado: '{titulo}' -> {res.get('url')}")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("🐾 Gerando artigo de pets do dia...")

    bicho       = escolher_bicho()
    nome_bicho  = bicho["nome"]
    img_en      = bicho["img_en"]

    # Número de imagens: 3 para bichos comuns, 4 para exóticos
    exoticos = {
        "Iguana", "Lagarto Barbaposada", "Cobra (ofidofilia)", "Aranha (tarântula)",
        "Axolote", "Lagosta de água doce", "Suricato", "Capivara doméstica",
        "Sapo-de-estimação", "Mini porco"
    }
    num_imagens = 4 if nome_bicho in exoticos else 3

    print(f"📝 Gerando título...")
    titulo = gerar_titulo(nome_bicho)
    print(f"✏️  Título: {titulo}")

    print(f"🖊️  Gerando prompts de imagem...")
    itens_imagem = gerar_prompts_imagens(nome_bicho, titulo, num_imagens)

    print(f"🖼️  Obtendo {num_imagens} imagens...")
    imagens_html = obter_imagens_html(itens_imagem, titulo, img_en)

    print(f"📖 Escrevendo artigo sobre {nome_bicho}...")
    corpo = gerar_artigo_cuidados(nome_bicho, num_imagens)

    aviso = (
        '<p style="font-size:12px;color:#999;font-style:italic;margin-top:24px;">'
        '⚕️ Este conteúdo é informativo e não substitui a avaliação de um médico veterinário. '
        'Em caso de sintomas ou dúvidas sobre a saúde do seu animal, procure um profissional.</p>'
    )

    html_final = montar_html(corpo, imagens_html, aviso)
    publicar_no_blogger(titulo, html_final)
    marcar_bicho_usado(nome_bicho)
    print(f"✅ Concluído! Animal postado: {nome_bicho}")
