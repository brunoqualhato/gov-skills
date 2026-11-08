"""CLI query tool for PNCP contracts stored in DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cnpj

app = typer.Typer(help="Query public contracts from PNCP")
console = Console()


@app.command()
def search(
    fornecedor: str = typer.Option(None, "--fornecedor", "-f", help="CNPJ ou parte do nome do fornecedor"),
    objeto: str = typer.Option(None, "--objeto", "-o", help="Palavra-chave no objeto da contratação"),
    uf: str = typer.Option(None, "--uf", help="UF do órgão contratante"),
    min_valor: float = typer.Option(None, "--min-valor", help="Valor mínimo do contrato"),
    limit: int = typer.Option(15, "--limit", "-l", help="Quantidade máxima de resultados"),
):
    """Consulta contratos públicos salvos no banco analítico DuckDB."""
    db = get_db()
    if "pncp_contratos" not in db.list_tables():
        console.print("[yellow]A tabela 'pncp_contratos' ainda não existe. Execute o script de fetch primeiro.[/yellow]")
        return

    where_clauses = []
    params = []

    if fornecedor:
        cnpj_limpo, _, _ = normalize_cnpj(fornecedor)
        if cnpj_limpo and len(cnpj_limpo) == 14:
            where_clauses.append("ni_fornecedor = ?")
            params.append(cnpj_limpo)
        else:
            where_clauses.append("(LOWER(nome_fornecedor) LIKE ? OR ni_fornecedor LIKE ?)")
            term = f"%{fornecedor.lower()}%"
            params.extend([term, term])

    if objeto:
        where_clauses.append("LOWER(objeto) LIKE ?")
        params.append(f"%{objeto.lower()}%")

    if uf:
        where_clauses.append("orgao_uf = ?")
        params.append(uf.upper())

    if min_valor is not None:
        where_clauses.append("valor_global >= ?")
        params.append(min_valor)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
        SELECT 
            numero_contrato,
            orgao_uf AS uf,
            LEFT(orgao_nome, 30) AS orgao,
            LEFT(nome_fornecedor, 25) AS fornecedor,
            ni_fornecedor,
            printf('R$ %,.2f', valor_global) AS valor,
            data_assinatura,
            LEFT(objeto, 40) AS objeto
        FROM pncp_contratos
        {where_sql}
        ORDER BY valor_global DESC
        LIMIT {limit}
    """

    db.display_results(sql, params=params, limit=limit)


@app.command()
def top_fornecedores(limit: int = typer.Option(10, "--limit", "-l", help="Quantidade de fornecedores")):
    """Exibe os maiores fornecedores por volume financeiro total."""
    db = get_db()
    if "pncp_contratos" not in db.list_tables():
        console.print("[yellow]A tabela 'pncp_contratos' ainda não existe.[/yellow]")
        return

    sql = f"""
        SELECT 
            nome_fornecedor AS fornecedor,
            ni_fornecedor AS cnpj_cpf,
            COUNT(*) AS total_contratos,
            printf('R$ %,.2f', SUM(valor_global)) AS montante_total
        FROM pncp_contratos
        WHERE valor_global > 0
        GROUP BY nome_fornecedor, ni_fornecedor
        ORDER BY SUM(valor_global) DESC
        LIMIT {limit}
    """
    db.display_results(sql, params=params, limit=limit)


if __name__ == "__main__":
    app()
