# src/io.py
import csv
import unicodedata
from pathlib import Path
from typing import List, Optional

from .domain import ProdutoDesejado


def _normalize_name(text: str) -> str:
    """
    Normaliza o nome para facilitar comparação:
    - lower
    - remove acentos
    - remove espaços duplicados
    """
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = " ".join(text.split())
    return text


def _to_kg(value: float, unit: str) -> float:
    unit = unit.strip().lower()
    if unit == "kg":
        return float(value)
    if unit == "g":
        return float(value) / 1000.0
    raise ValueError(f"Unidade não suportada: '{unit}'. Use 'kg' ou 'g'.")


def read_products_csv(path: str | Path, delimiter: Optional[str] = None) -> List[ProdutoDesejado]:
    """
    Lê um CSV com colunas: produto, demanda, unidade
    Retorna lista de ProdutoDesejado com demanda em kg.

    Observação: alguns Excels salvam CSV com ';'. Se der erro, passe delimiter=';'
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    # Se não informarem delimiter, tenta detectar entre ',' e ';'
    if delimiter is None:
        sample = path.read_text(encoding="utf-8", errors="ignore")[:2048]
        delimiter = ";" if sample.count(";") > sample.count(",") else ","

    produtos: List[ProdutoDesejado] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        required = {"produto", "demanda", "unidade"}

        header = {h.strip().lower() for h in (reader.fieldnames or [])}
        if not required.issubset(header):
            raise ValueError(
                f"CSV precisa ter colunas {sorted(required)}. "
                f"Colunas encontradas: {sorted(header)}"
            )

        for i, row in enumerate(reader, start=2):  # linha 1 é header
            produto_raw = (row.get("produto") or row.get("Produto") or "").strip()
            demanda_raw = (row.get("demanda") or row.get("Demanda") or "").strip()
            unidade_raw = (row.get("unidade") or row.get("Unidade") or "").strip()

            if not produto_raw:
                raise ValueError(f"Linha {i}: campo 'produto' vazio.")
            if not demanda_raw:
                raise ValueError(f"Linha {i}: campo 'demanda' vazio.")
            if not unidade_raw:
                raise ValueError(f"Linha {i}: campo 'unidade' vazio.")

            # troca vírgula decimal por ponto (ex: "1,5")
            demanda_raw = demanda_raw.replace(",", ".")
            try:
                demanda = float(demanda_raw)
            except ValueError:
                raise ValueError(f"Linha {i}: demanda inválida '{demanda_raw}'.")

            if demanda <= 0:
                raise ValueError(f"Linha {i}: demanda deve ser > 0. Recebido: {demanda}")

            demanda_kg = _to_kg(demanda, unidade_raw)
            produtos.append(
                ProdutoDesejado(
                    nome_base=_normalize_name(produto_raw),
                    demanda_kg=demanda_kg
                )
            )

    return produtos

from pathlib import Path

def extract_text_from_pdf(pdf_path: str | Path) -> str:
    import pdfplumber

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")

    chunks: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                chunks.append(text)

    return "\n".join(chunks)