from pathlib import Path
import csv

from .io import extract_text_from_pdf
from .services import parse_fornecedor2, parse_fornecedor4

def main():
    base_dir = Path(__file__).resolve().parents[1]
    folder = base_dir / "data" / "fornecedores"

    # extrai texto direto do PDF (sem depender do .txt)
    t2 = extract_text_from_pdf(folder / "fornecedor2.pdf")
    t4 = extract_text_from_pdf(folder / "fornecedor4.pdf")

    ofertas = []
    ofertas += parse_fornecedor2(t2, "fornecedor2")
    ofertas += parse_fornecedor4(t4, "fornecedor4")

    print("Total de ofertas extraídas:", len(ofertas))
    print("Amostra (primeiras 10):")
    for o in ofertas[:10]:
        print("-", o.fornecedor, "|", o.nome_pdf, "|", o.embalagem_kg, "kg |", o.preco_por_kg, "R$/kg")

    # salva CSV para conferir no Excel
    out_csv = folder / "ofertas_extraidas.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fornecedor", "nome_pdf", "embalagem_kg", "preco_por_kg", "tipo_preco"])
        for o in ofertas:
            w.writerow([o.fornecedor, o.nome_pdf, o.embalagem_kg, o.preco_por_kg, o.tipo_preco])

    print("CSV gerado:", out_csv)

if __name__ == "__main__":
    main()
