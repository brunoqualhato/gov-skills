"""CLI query tool for PGFN active debt in DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cnpj

app = typer.Typer(help="Query PGFN active debt records")
console = Console()


@app.command()
def search(
    cnpj: str = typer.Option(None, "--cnpj", "-c", help="CNPJ do devedor"),
    nome: str = typer.Option(None, "--nome", "-n", help="Nome ou razão social do devedor"),
    tipo: str = typer.Option(None, "--tipo", "-t", help="Tipo de dívida (TRIBUTARIA, FGTS, PREVIDENCIARIA)"),
    limit: int = typer.Option(15, "--limit", "-l", help="Quantidade máxima de resultados"),
):
    """Consulta débitos fiscais inscritos na Dívida Ativa da União."""
    db = get_db()
    if "pgfn_divida_ativa" not in db.list_tables():
        console.print("[yellow]A tabela 'pgfn_divida_ativa' ainda não existe. Execute o script de seed ou importação primeiro.[/yellow]")
        return

    where_clauses = []
    params = []

    if cnpj:
        cnpj_limpo, _, cnpj_raiz = normalize_cnpj(cnpj)
        where_clauses.append("(cnpj_cpf_devedor = ? OR cnpj_raiz = ?)")
        params.extend([cnpj_limpo, cnpj_raiz])

    if nome:
        where_clauses.append("LOWER(nome_devedor) LIKE ?")
        params.append(f"%{nome.lower()}%")

    if tipo:
        where_clauses.append("UPPER(tipo_divida) = ?")
        params.append(tipo.upper())

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
        SELECT 
            numero_inscricao AS inscricao,
            LEFT(nome_devedor, 30) AS devedor,
            cnpj_cpf_devedor AS doc,
            tipo_divida AS tipo,
            situacao_inscricao AS situacao,
            printf('R$ %,.2f', valor_consolidado) AS valor_divida,
            uf
        FROM pgfn_divida_ativa
        {where_sql}
        ORDER BY valor_consolidado DESC
        LIMIT {limit}
    """
    db.display_results(sql, params=params, limit=limit)


if __name__ == "__main__":
    app()
