from pathlib import Path
import json
import pandas as pd
import folium
import requests

PROCESSED = Path("data/processed/dengue_weekly.parquet")
OUT_HTML = Path("reports/figures/incidencia_semana.html")

# População aproximada (p/ incidência por 100k). Adicione UFs se precisar.
UF_POP = {
    "AC": 0.9e6, "AL": 3.4e6, "AP": 0.9e6, "AM": 4.3e6, "BA": 14.9e6,
    "CE": 9.2e6, "DF": 3.1e6, "ES": 4.2e6, "GO": 7.3e6, "MA": 7.2e6,
    "MT": 3.8e6, "MS": 2.9e6, "MG": 21.4e6, "PA": 8.7e6, "PB": 4.1e6,
    "PR": 11.6e6, "PE": 9.7e6, "PI": 3.3e6, "RJ": 17.3e6, "RN": 3.6e6,
    "RS": 11.3e6, "RO": 1.8e6, "RR": 0.7e6, "SC": 7.6e6, "SP": 46.6e6,
    "SE": 2.4e6, "TO": 1.6e6,
}

# Fallback: GeoJSON simplificado contendo apenas MG e RJ (caso o download falhe).
FALLBACK_GEOJSON = {
  "type":"FeatureCollection",
  "features":[
    {"type":"Feature","properties":{"sigla":"MG","name":"Minas Gerais"},
     "geometry":{"type":"Polygon","coordinates":[[
       [-44.5,-20.5],[-44.0,-18.0],[-42.0,-18.0],[-41.5,-20.0],[-43.0,-21.5],[-44.5,-20.5]
     ]]}},
    {"type":"Feature","properties":{"sigla":"RJ","name":"Rio de Janeiro"},
     "geometry":{"type":"Polygon","coordinates":[[
       [-43.7,-22.9],[-43.0,-22.3],[-41.5,-22.3],[-41.0,-22.9],[-42.0,-23.2],[-43.7,-22.9]
     ]]}}
  ]
}

def _download_uf_geojson():
    # GeoJSON de UFs do IBGE (qualidade mínima). Se mudar a URL, ainda temos fallback.
    url = "https://servicodados.ibge.gov.br/api/v3/malhas/unidades/UF?formato=application/vnd.geo+json&qualidade=minima"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        gj = r.json()
        # Normalizar propriedades – IBGE usa 'sigla' ou 'UF'
        for f in gj.get("features", []):
            props = f.setdefault("properties", {})
            if "sigla" not in props:
                # tenta vários campos comuns
                sigla = props.get("UF") or props.get("uf") or props.get("sigla_uf") or ""
                props["sigla"] = sigla
        return gj
    except Exception:
        return FALLBACK_GEOJSON

def make_map():
    df = pd.read_parquet(PROCESSED)
    last_week = df["week"].max()
    ref = df[df["week"] == last_week].copy()

    # Incidência por 100k
    ref["pop"] = ref["state"].map(UF_POP).fillna(1.0)  # evita div/0 se aparecer UF desconhecida
    ref["incidence_100k"] = (ref["cases"] / ref["pop"]) * 1e5

    # DataFrame para o choropleth
    data_for_map = ref[["state", "incidence_100k"]].rename(columns={"state":"sigla"})

    # Baixa GeoJSON ou usa fallback
    gj = _download_uf_geojson()

    # Mapa centrado aproximado no Brasil
    m = folium.Map(location=[-14.2, -51.9], zoom_start=4, tiles="cartodbpositron")

    # Choropleth por UF
    folium.Choropleth(
        geo_data=gj,
        name="Incidência (por 100k)",
        data=data_for_map,
        columns=["sigla", "incidence_100k"],
        key_on="feature.properties.sigla",
        fill_opacity=0.8,
        line_opacity=0.6,
        legend_name=f"Incidência por 100k - semana {pd.to_datetime(last_week).date()}",
        nan_fill_opacity=0.2,
        nan_fill_color="lightgray",
    ).add_to(m)

    # Popups com valores
    for _, row in data_for_map.iterrows():
        # Para fallback, usamos centroids aproximados por UF (MG e RJ renderizam OK).
        # Em GeoJSON do IBGE, podemos extrair centroid no futuro via shapely (opcional).
        if row["sigla"] == "MG":
            folium.Marker(location=[-19.9, -44.0], tooltip=f"MG: {row['incidence_100k']:.1f}/100k").add_to(m)
        elif row["sigla"] == "RJ":
            folium.Marker(location=[-22.8, -43.3], tooltip=f"RJ: {row['incidence_100k']:.1f}/100k").add_to(m)

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    m.save(OUT_HTML)
    print(f"[geo] choropleth saved -> {OUT_HTML}")

if __name__ == "__main__":
    make_map()
