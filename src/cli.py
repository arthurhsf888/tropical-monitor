import typer
from src.etl.fetch_dengue import fetch_dengue
from src.etl.clean_normalize import clean
from src.etl.build_timeseries import build_ts
from src.etl.merge_weekly import merge_weekly
from src.etl.fetch_mg_bulletin import run as mg_run
from src.geo.make_choropleth import make_map
from src.report.render_weekly import render_weekly

app = typer.Typer(help="CLI do Tropical Disease Monitor")

@app.command()
def fetch():
    """Copia/gera dados brutos (mock local)."""
    fetch_dengue()

@app.command()
def fetch_mg():
    """Baixa e processa o último boletim da SES-MG."""
    mg_run()

@app.command()
def prepare():
    """
    Limpa e constroi a série semanal a partir do ingest,
    e então substitui MG pelos dados oficiais (se existirem).
    """
    clean()
    build_ts()
    merge_weekly()

@app.command()
def visuals():
    """Gera mapa/figuras da semana."""
    make_map()

@app.command()
def report():
    """Gera payload JSON consumido pelo Dify."""
    render_weekly()

if __name__ == "__main__":
    app()
