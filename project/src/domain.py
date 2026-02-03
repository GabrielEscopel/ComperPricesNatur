# src/domain.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ProdutoDesejado:
    nome_base: str      # nome normalizado (simples)
    demanda_kg: float   # sempre em kg
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OfertaFornecedor:
    fornecedor: str
    nome_pdf: str

    embalagem_kg: Optional[float]   # ex: 25.0 (se não tiver, None)
    preco_por_kg: Optional[float]   # ex: 5.43  (se não der pra calcular, None)

    tipo_preco: str                 # "outros_estados", "avista", etc.
    linha_origem: str               # linha original (ajuda debug)
