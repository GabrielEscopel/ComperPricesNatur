# src/services.py
import re

def _extract_kg(text: str) -> Optional[float]:
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*kg\b", text, re.IGNORECASE)
    if not m:
        return None

    val = m.group(1).replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return None

def _merge_wrapped_lines(text: str) -> list[str]:
    """
    Junta linhas que foram quebradas na extração do PDF.
    Regra:
      - Se começa com número: nova linha de item
      - Senão: é continuação da linha anterior
    """
    merged: list[str] = []
    current = ""

    for raw in text.splitlines():
        ln = " ".join(raw.split())
        if not ln:
            continue

        if re.match(r"^\d+\s+", ln):  # começa com código
            if current:
                merged.append(current)
            current = ln
        else:
            # continuação
            if current:
                current += " " + ln
            else:
                current = ln

    if current:
        merged.append(current)

    return merged



#=================================
import re
from typing import List, Optional
from .domain import OfertaFornecedor

def _to_float_any(x: str) -> Optional[float]:
    x = x.strip()
    if not x:
        return None

    x = x.replace("R$", "").strip()

    # caso com vírgula (pt-br): "10,00"
    if "," in x:
        x = x.replace(".", "").replace(",", ".")
    # caso com ponto (en): "6.80" -> já ok

    try:
        return float(x)
    except ValueError:
        return None
# -----------------------------
# Fornecedor 2 (Tabela 44)
# Regra: usar "Outros Estados p/kg"
# Formato típico: COD NOME  preço_outros  preço_sp  preço_sn  embalagem
# Ex.: "486 Aveia em Flocos Finos 5,00 5,00 5,30 25 kg"
# -----------------------------


def _extract_kg(text: str) -> Optional[float]:
    """
    Extrai kg de pedaços tipo:
      "25 kg", "10 KG", "SACO 25 KG", "25,00 KG"
    """
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*kg\b", text, re.IGNORECASE)
    if not m:
        return None
    val = m.group(1).replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return None

#------------------------------
import re

def _merge_wrapped_lines(text: str) -> list[str]:
    merged: list[str] = []
    current = ""

    for raw in text.splitlines():
        ln = " ".join(raw.split())
        if not ln:
            continue

        if re.match(r"^\d+\s+", ln):
            if current:
                merged.append(current)
            current = ln
        else:
            if current:
                current += " " + ln
            else:
                current = ln

    if current:
        merged.append(current)

    return merged
#------------------------------
def parse_fornecedor2(text: str, fornecedor: str = "fornecedor2") -> List[OfertaFornecedor]:
    ofertas: List[OfertaFornecedor] = []

    skipped_no_kg = 0
    skipped_few_nums = 0
    skipped_no_price = 0
    parsed = 0



    for line in _merge_wrapped_lines(text):
        ln = " ".join(line.split())
        if not ln:
            continue

        # pula cabeçalhos comuns
        if "Tabela" in ln or "Outros Estados" in ln or "Embalagem" in ln:
            continue

        # precisa começar com código numérico
        if not re.match(r"^\d+\s+", ln):
            continue

        # pega embalagem no fim (ex: "25 kg")
        emb = _extract_kg(ln)
        if emb is None:
            skipped_no_kg += 1
            continue

        # pega os 3 preços no final antes da embalagem
        # estratégia: capturar todos os números com vírgula e pegar os 3 últimos antes do "kg"
        nums = re.findall(r"\d+(?:[.,]\d+)", ln)
        if len(nums) < 4:
            skipped_few_nums += 1
            continue

        # heuristic: últimos 4 números costumam ser: preco_outros, preco_sp, preco_sn, embalagem
        embalagem_guess = nums[-1]
        if "kg" not in ln.lower():
            continue

        preco_outros = _to_float_any(nums[-4])
        if preco_outros is None:
            skipped_no_price += 1
            continue

        # nome do produto = remove código e remove parte final (preços + embalagem)
        # Simplificação: remove os 4 últimos números e o "kg"
        nome_part = re.sub(r"^\d+\s+", "", ln)
        # remove do fim: "... X X X 25 kg"
        nome_part = re.sub(r"\s+\d+(?:[.,]\d+)\s+\d+(?:[.,]\d+)\s+\d+(?:[.,]\d+)\s+\d+(?:[.,]\d+)\s*kg\b.*$", "", nome_part, flags=re.IGNORECASE).strip()
        if not nome_part:
            continue

        parsed += 1

        ofertas.append(
            OfertaFornecedor(
                fornecedor=fornecedor,
                nome_pdf=nome_part,
                embalagem_kg=emb,
                preco_por_kg=preco_outros,
                tipo_preco="outros_estados",
                linha_origem=ln
            )
        )
    print(f"[{fornecedor}] parsed={parsed} skipped_no_kg={skipped_no_kg} skipped_few_nums={skipped_few_nums} skipped_no_price={skipped_no_price}")
    return ofertas

# -----------------------------
# Fornecedor 4 (à vista)
# Formato típico: "AÇÚCAR DEMERARA (CAIXA) 25 Kg R$ 5,43 R$ 5,49 AÇÚCAR"
# Regra: usar o primeiro preço (à vista)
# -----------------------------
def parse_fornecedor4(text: str, fornecedor: str = "fornecedor4") -> List[OfertaFornecedor]:
    ofertas: List[OfertaFornecedor] = []

    for line in _merge_wrapped_lines(text):
        ln = " ".join(line.split())
        if not ln:
            continue

        up = ln.upper()
        if up.startswith("PÁG") or up.startswith("PAG"):
            continue
        if "EMBALAGEM" in up and "PRODUTO" in up:
            continue

        # precisa ter kg e algum preço
        if "kg" not in ln.lower():
            continue

        emb = _extract_kg(ln)
        if emb is None:
            continue

        # captura preços no formato "R$ 12,34" ou "R$12.34"
        prices = re.findall(r"R\$\s*\d+(?:[.,]\d+)?", ln, flags=re.IGNORECASE)
        if not prices:
            # fallback: às vezes vem só "12,34" sem R$
            nums = re.findall(r"\d+(?:[.,]\d+)", ln)
            if len(nums) < 2:
                continue
            # tenta usar o primeiro número como preço
            preco_avista = _to_float_any(nums[0])
        else:
            preco_avista = _to_float_any(prices[0])

        if preco_avista is None:
            continue

        # nome = tudo antes do trecho de kg (heurística)
        idx = ln.lower().find("kg")
        nome_part = ln[:idx].strip()
        nome_part = re.sub(r"\s*\d+(?:[.,]\d+)?\s*$", "", nome_part).strip()

        if not nome_part:
            continue

        ofertas.append(
            OfertaFornecedor(
                fornecedor=fornecedor,
                nome_pdf=nome_part,
                embalagem_kg=emb,
                preco_por_kg=preco_avista,
                tipo_preco="avista",
                linha_origem=ln,
            )
        )

    return ofertas



#======================================================== Fornecedor 3 

def parse_fornecedor3(text: str, fornecedor: str = "fornecedor3") -> List[OfertaFornecedor]:
    ofertas: List[OfertaFornecedor] = []

    lines = _merge_wrapped_lines(text)

    for line in lines:
        ln = " ".join(line.split())
        if not ln:
            continue

        # ignora cabeçalhos
        up = ln.upper()
        if "TABELA DE PREÇO" in up or "R$/KG" in up or "PESO/UN" in up or "DESCRIÇÃO" in up:
            continue

        # precisa ter kg
        if "kg" not in ln.lower():
            continue

        emb = _extract_kg(ln)
        if emb is None:
            continue

        # pega números (ex: "... 5.00 125.00")
        nums = re.findall(r"\d+(?:[.,]\d+)", ln)
        if len(nums) < 2:
            continue

        # heurística: o penúltimo costuma ser o preço/kg
        preco_kg = _to_float_any(nums[-2])
        if preco_kg is None:
            continue

        # nome do produto: remove códigos no começo e corta o final numérico
        nome_part = re.sub(r"^\d+\s+", "", ln).strip()
        # remove trecho final típico: "25 KG 5.00 125.00"
        nome_part = re.sub(r"\s+\d+(?:[.,]\d+)?\s*kg\s+\d+(?:[.,]\d+)\s+\d+(?:[.,]\d+)\s*$", "", nome_part, flags=re.IGNORECASE).strip()

        if not nome_part:
            continue

        ofertas.append(
            OfertaFornecedor(
                fornecedor=fornecedor,
                nome_pdf=nome_part,
                embalagem_kg=emb,
                preco_por_kg=preco_kg,
                tipo_preco="tabela",
                linha_origem=ln
            )
        )

    return ofertas


#------------------------------------- Fornecedor1

def parse_fornecedor1(text: str, fornecedor: str = "fornecedor1") -> List[OfertaFornecedor]:
    ofertas: List[OfertaFornecedor] = []

    skipped_header = 0
    skipped_no_emb = 0
    skipped_no_prices = 0
    parsed = 0

    #print("[fornecedor1] DEBUG linhas split:", len(text.splitlines()))


    # ⚠️ fornecedor1: NÃO usar _merge_wrapped_lines, pois ele pode colar tudo em 1 linha
    for raw in text.splitlines():
        ln = " ".join(raw.split())
        if not ln:
            continue

        up = ln.upper()

        # cabeçalhos
        if up.startswith("TABELA DIA") or "PRODUTOS A GRANEL" in up or "PREÇO/KG" in up or "PRECO/KG" in up:
            skipped_header += 1
            continue
        if "PRODUTOS" in up and "NACIONAIS" in up:
            skipped_header += 1
            continue
        if "EMBALAGEM" in up and ("PRODUTOS" in up or "PUROS" in up):
            skipped_header += 1
            continue

        # precisa achar algo tipo SACO25KG
        emb = _extract_kg(ln)
        if emb is None:
            skipped_no_emb += 1
            continue

        # preços: R$ 19.00, R$ 21,10 etc
        prices = re.findall(r"R\$\s*\d+(?:[.,]\d+)?", ln, flags=re.IGNORECASE)
        if not prices:
            skipped_no_prices += 1
            continue

        vals = []
        for p in prices:
            v = _to_float_any(p)
            if v is not None:
                vals.append(v)

        if not vals:
            skipped_no_prices += 1
            continue

        preco_kg = min(vals)  # regra: menor preço da linha

        # nome: tudo antes do SACOxxKG
        nome_part = re.split(r"\bSACO\s*\d+(?:[.,]\d+)?\s*KG\b", ln, flags=re.IGNORECASE)[0].strip()
        if not nome_part:
            nome_part = ln.split("R$")[0].strip()

        if not nome_part:
            skipped_header += 1
            continue

        ofertas.append(
            OfertaFornecedor(
                fornecedor=fornecedor,
                nome_pdf=nome_part,
                embalagem_kg=emb,
                preco_por_kg=preco_kg,
                tipo_preco="menor_preco",
                linha_origem=ln,
            )
        )
        parsed += 1

    #print(f"[{fornecedor}] parsed={parsed} skipped_header={skipped_header} skipped_no_emb={skipped_no_emb} skipped_no_prices={skipped_no_prices}")
    return ofertas

#----------------------------- lIMPEZA
import re
from .io import normalize_name

_STOPWORDS = {
    "kg", "quilo", "quilos", "un", "unidade", "unidades",
    "caixa", "cx", "pct", "pacote", "saco", "lata",
    "torrada", "torrado", "sal", "s/", "sem",
    "w1", "w2", "w3", "w4", "meta", "runner", "cru",
}

_SINONIMOS = {
    "castanha do para": ["castanha do pará", "castanha para", "castanha pará"],
    "aveia em flocos": ["flocos finos", "flocos grossos", "aveia flocos", "aveia em flocos finos"],
    "farinha de trigo": ["trigo farinha", "farinha trigo"],
    "chia": ["semente chia", "chia seed"],
}

def _clean_for_match(s: str) -> str:
    """
    Limpa texto para bater nomes:
    - normaliza (lower, sem acento)
    - remove parênteses
    - remove códigos/nums isolados
    - remove stopwords comuns
    """
    s = normalize_name(s)
    s = re.sub(r"\(.*?\)", " ", s)                 # remove ( ... )
    s = re.sub(r"[^a-z0-9\s]", " ", s)             # tira pontuação
    tokens = [t for t in s.split() if t not in _STOPWORDS]
    # remove tokens que são só números ou muito curtos tipo "w1"
    tokens = [t for t in tokens if not t.isdigit() and len(t) > 1]
    return " ".join(tokens).strip()

def _expand_query(nome_base: str) -> list[str]:
    """Gera variações do nome usando sinônimos."""
    base = normalize_name(nome_base)
    vars = [base]
    for k, vs in _SINONIMOS.items():
        if base == normalize_name(k):
            vars.extend([normalize_name(v) for v in vs])
    return list(dict.fromkeys(vars))  # remove duplicados mantendo ordem




#----------------------------------------------------------------

# Camparando os preços : MOTOR DO PROGRAMA

import math
from dataclasses import asdict
from difflib import SequenceMatcher

from .io import normalize_name
from .domain import ProdutoDesejado, OfertaFornecedor


from difflib import SequenceMatcher

def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def match_ofertas_por_nome(
    produto_nome: str,
    ofertas: list[OfertaFornecedor],
    top_n: int = 20,
    min_score: float = 0.52,
) -> list[tuple[OfertaFornecedor, float]]:
    queries = _expand_query(produto_nome)  # inclui sinônimos
    scored: list[tuple[OfertaFornecedor, float]] = []

    for o in ofertas:
        cand = _clean_for_match(o.nome_pdf)
        if not cand:
            continue

        best_s = 0.0
        for q in queries:
            qclean = _clean_for_match(q)
            s = _similarity(qclean, cand)
            if s > best_s:
                best_s = s

        if best_s >= min_score:
            scored.append((o, best_s))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]


import math
import re
from difflib import SequenceMatcher
from typing import Optional

from .domain import ProdutoDesejado, OfertaFornecedor
from .io import normalize_name


# --- matching helpers ---

_STOPWORDS = {
    "kg", "quilo", "quilos", "un", "unidade", "unidades",
    "caixa", "cx", "pct", "pacote", "saco", "lata",
    "meta", "runner", "cru",
}

_SINONIMOS = {
    "castanha do para": ["castanha do pará", "castanha para", "castanha pará"],
    "aveia em flocos": ["aveia flocos", "flocos finos", "flocos grossos"],
    "farinha de trigo": ["farinha trigo", "trigo farinha"],
    "chia": ["semente chia", "chia seed"],
}


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _clean_for_match(s: str) -> str:
    s = normalize_name(s)
    s = re.sub(r"\(.*?\)", " ", s)         # remove ( ... )
    s = re.sub(r"[^a-z0-9\s]", " ", s)     # remove pontuação
    tokens = [t for t in s.split() if t not in _STOPWORDS]
    tokens = [t for t in tokens if not t.isdigit() and len(t) > 1]
    return " ".join(tokens).strip()


def _expand_query(nome_base: str) -> list[str]:
    base = normalize_name(nome_base)
    vars = [base]
    for k, vs in _SINONIMOS.items():
        if base == normalize_name(k):
            vars.extend([normalize_name(v) for v in vs])
    # remove duplicados preservando ordem
    out = []
    for x in vars:
        if x not in out:
            out.append(x)
    return out


def match_ofertas_por_nome(
    produto_nome: str,
    ofertas: list[OfertaFornecedor],
    top_n: int = 20,
    min_score: float = 0.52,
) -> list[tuple[OfertaFornecedor, float]]:
    queries = _expand_query(produto_nome)
    scored: list[tuple[OfertaFornecedor, float]] = []

    for o in ofertas:
        cand = _clean_for_match(o.nome_pdf)
        if not cand:
            continue

        best_s = 0.0
        for q in queries:
            qclean = _clean_for_match(q)
            s = _similarity(qclean, cand)
            if s > best_s:
                best_s = s

        if best_s >= min_score:
            scored.append((o, best_s))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]


# --- FUNÇÃO QUE O MAIN PRECISA (adicionei aqui) ---

def melhor_compra_para_produto(
    p: ProdutoDesejado,
    ofertas: list[OfertaFornecedor],
    top_n: int = 20,
    min_score: float = 0.52,
) -> Optional[dict]:
    candidatos = match_ofertas_por_nome(p.nome_base, ofertas, top_n=top_n, min_score=min_score)
    if not candidatos:
        return None

    melhor = None

    for o, score in candidatos:
        if o.embalagem_kg <= 0:
            continue

        pacotes = math.ceil(p.demanda_kg / o.embalagem_kg)
        qtd_comprada_kg = pacotes * o.embalagem_kg
        custo_total = qtd_comprada_kg * o.preco_por_kg

        item = {
            "produto": p.nome_base,
            "demanda_kg": p.demanda_kg,
            "fornecedor": o.fornecedor,
            "nome_pdf": o.nome_pdf,
            "match_score": round(score, 3),
            "embalagem_kg": o.embalagem_kg,
            "preco_por_kg": o.preco_por_kg,
            "pacotes": pacotes,
            "qtd_comprada_kg": qtd_comprada_kg,
            "custo_total": round(custo_total, 2),
            "tipo_preco": o.tipo_preco,
        }

        if (melhor is None) or (item["custo_total"] < melhor["custo_total"]):
            melhor = item

    return melhor
