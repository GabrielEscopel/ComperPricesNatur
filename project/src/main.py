from pathlib import Path
import csv
from collections import Counter
from .services import melhor_compra_para_produto
from .io import read_products_csv
from .services import melhor_compra_para_produto
from .services import match_ofertas_por_nome



from .io import extract_text_from_pdf
from .services import (
    parse_fornecedor1,
    parse_fornecedor2,
    parse_fornecedor3,
    parse_fornecedor4,
)

def main():
    base_dir = Path(__file__).resolve().parents[1]
    folder = base_dir / "data" / "fornecedores"

    # extrai texto dos PDFs
    t1 = extract_text_from_pdf(folder / "fornecedor1.pdf")
    print("DEBUG fornecedor1: chars =", len(t1))
    print("DEBUG fornecedor1: primeiras 300 chars:\n", t1[:300])

    t2 = extract_text_from_pdf(folder / "fornecedor2.pdf")
    t3 = extract_text_from_pdf(folder / "fornecedor3.pdf")
    t4 = extract_text_from_pdf(folder / "fornecedor4.pdf")

    # parseia ofertas
    ofertas = []
    ofertas += parse_fornecedor1(t1, "fornecedor1")
    ofertas += parse_fornecedor2(t2, "fornecedor2")
    ofertas += parse_fornecedor3(t3, "fornecedor3")
    ofertas += parse_fornecedor4(t4, "fornecedor4")

    #---------------------------------------------------
    # ---- Lê produtos desejados ----
    produtos_path = base_dir / "data" / "produtos.csv"
    produtos = read_products_csv(produtos_path)

    print("\nProdutos desejados:", len(produtos))
    for p in produtos:
        print("-", p)

    # ---- Calcula melhor compra por produto ----
    recomendadas = []
    nao_encontrados = []

    for p in produtos:
        best = melhor_compra_para_produto(p, ofertas, top_n=20, min_score=0.52)

        if best is None:
            nao_encontrados.append(p.nome_base)

            print("\n[NAO ENCONTRADO]", p.nome_base)
            candidatos = match_ofertas_por_nome(p.nome_base, ofertas, top_n=8, min_score=0.0)
            for o, s in candidatos:
                print("   cand:", round(s, 3), "|", o.fornecedor, "|", o.nome_pdf[:90])

        else:
            recomendadas.append(best)
            print("\n[OK]", p.nome_base, "->", best["fornecedor"], "| score:", best["match_score"])

    # ---- Salva CSV final ----
        
    out_final = folder / "compras_recomendadas.csv"
    with out_final.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "produto", "demanda_kg", "fornecedor", "nome_pdf", "match_score",
            "embalagem_kg", "preco_por_kg", "pacotes", "qtd_comprada_kg",
            "custo_total", "tipo_preco"
        ])

        for r in recomendadas:
            w.writerow([
                r["produto"], r["demanda_kg"], r["fornecedor"], r["nome_pdf"], r["match_score"],
                r["embalagem_kg"], r["preco_por_kg"], r["pacotes"], r["qtd_comprada_kg"],
                r["custo_total"], r["tipo_preco"]
             ])

    print("\nCSV final gerado:", out_final)

    
    #---------------------------------------------------
    # prints "bonitos"
    print("Total de ofertas extraídas:", len(ofertas))
    print("Ofertas por fornecedor:", Counter([o.fornecedor for o in ofertas]))

    from collections import defaultdict

    print("\nAmostra (2 por fornecedor):")
    por_forn = defaultdict(list)

    for o in ofertas:
        if len(por_forn[o.fornecedor]) < 2:
            por_forn[o.fornecedor].append(o)

    for forn in sorted(por_forn.keys()):
        for o in por_forn[forn]:
            print(f"- {o.fornecedor:11} | {o.embalagem_kg:>6} kg | {o.preco_por_kg:>8} R$/kg | {o.nome_pdf[:70]}")

    # salva CSV
    out_csv = folder / "ofertas_extraidas.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fornecedor", "nome_pdf", "embalagem_kg", "preco_por_kg", "tipo_preco"])
        for o in ofertas:
            w.writerow([o.fornecedor, o.nome_pdf, o.embalagem_kg, o.preco_por_kg, o.tipo_preco])

    print("\nCSV gerado:", out_csv)

if __name__ == "__main__":
    main()
