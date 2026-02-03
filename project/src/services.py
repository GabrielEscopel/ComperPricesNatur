# src/services.py
import re

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
            continue

        # pega os 3 preços no final antes da embalagem
        # estratégia: capturar todos os números com vírgula e pegar os 3 últimos antes do "kg"
        nums = re.findall(r"\d+(?:[.,]\d+)", ln)
        if len(nums) < 4:
            continue

        # heuristic: últimos 4 números costumam ser: preco_outros, preco_sp, preco_sn, embalagem
        embalagem_guess = nums[-1]
        if "kg" not in ln.lower():
            continue

        preco_outros = _to_float_any(nums[-4])
        if preco_outros is None:
            continue

        # nome do produto = remove código e remove parte final (preços + embalagem)
        # Simplificação: remove os 4 últimos números e o "kg"
        nome_part = re.sub(r"^\d+\s+", "", ln)
        # remove do fim: "... X X X 25 kg"
        nome_part = re.sub(r"\s+\d+(?:[.,]\d+)\s+\d+(?:[.,]\d+)\s+\d+(?:[.,]\d+)\s+\d+(?:[.,]\d+)\s*kg\b.*$", "", nome_part, flags=re.IGNORECASE).strip()
        if not nome_part:
            continue

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

        # pula cabeçalhos
        if "PRODUTO" in ln and "EMBALAGEM" in ln:
            continue
        if ln.upper().startswith("PÁG."):
            continue

        # precisa ter kg e R$
        if "kg" not in ln.lower() or "r$" not in ln.lower():
            continue

        emb = _extract_kg(ln)
        if emb is None:
            continue

        # pega preços "R$ 5,43" -> captura 2 preços (avista, aprazo)
        prices = re.findall(r"R\$\s*\d+(?:[.,]\d+)?", ln, flags=re.IGNORECASE)
        if not prices:
            continue

        preco_avista = _to_float_br(prices[0])
        if preco_avista is None:
            continue

        # nome = tudo antes da embalagem (heurística)
        idx = ln.lower().find("kg")
        nome_part = ln[:idx].strip()
        # remove o número do kg do nome (ex: "... 25")
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
                linha_origem=ln
            )
        )

    return ofertas
