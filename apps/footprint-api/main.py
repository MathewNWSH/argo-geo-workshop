from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import rasterio
from raster_footprint import footprint_from_data
import antimeridian
import asyncio
from functools import partial

app = FastAPI(
    title="Raster Footprint API",
    description="Serwis do pobierania poprawionego footprintu rastra w formacie GeoJSON"
)


class FootprintRequest(BaseModel):
    url: str


def _process_raster(url: str) -> dict:
    with rasterio.open(url) as src:
        data = src.read()
        nodata = src.nodata

        footprint = footprint_from_data(
            data=data,
            transform=src.transform,
            source_crs=src.crs,
            nodata=nodata,
        )

    geojson_feature = {
        "type": "Feature",
        "geometry": footprint,
        "properties": {
            "source_url": url,
        }
    }

    return antimeridian.fix_geojson(geojson_feature)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/footprint")
async def get_footprint(request: FootprintRequest):
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, partial(_process_raster, request.url))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd przetwarzania: {str(e)}")


@app.get("/")
async def root():
    return {
        "message": "Raster Footprint API",
        "endpoints": ["/health", "/footprint"],
    }
