from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import json

app = FastAPI(title="GDAL Info API", description="Prosty serwis do pobierania metadanych GeoTIFF")

class GdalInfoRequest(BaseModel):
    url: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/gdalinfo")
def gdalinfo(request: GdalInfoRequest):
    """Zwraca metadane dla pliku GeoTIFF (lokalnego lub zdalnego URL)"""
    try:
        result = subprocess.run(
            ["gdalinfo", "-json", request.url],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            raise HTTPException(status_code=400, detail=result.stderr)
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid GDAL output")

@app.get("/")
def root():
    return {"message": "GDAL Info API", "endpoints": ["/health", "/gdalinfo"]}
# trigger build
